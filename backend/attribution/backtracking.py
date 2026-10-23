"""Reverse Lagrangian Backtracking Engine with Negative Time RK4 Integration.

Traces observed marine debris detections backward in time (-dt) to identify
probable upstream release locations and compute source domain intersection
frequencies across Singapore and regional waters.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from shapely.geometry import Point, Polygon, LineString

from backend.attribution.sources import SOURCE_DOMAINS, SourceDomain, find_containing_source
from backend.weather.interpolator import VectorFieldInterpolator

# Earth geometric constants
METERS_PER_DEG_LAT = 111139.0
EARTH_RADIUS_METERS = 6371000.0


@dataclass
class BackwardParticle:
    id: str
    lat: float
    lng: float
    initial_lat: float
    initial_lng: float
    leeway_factor: float
    status: str = "active"          # "active" | "terminated_source" | "exited_domain"
    terminal_source_id: Optional[str] = None
    terminal_time_hours_ago: float = 0.0
    trajectory: List[Tuple[float, float, float]] = field(default_factory=list) # (lat, lng, hours_ago)
    source_hits: List[str] = field(default_factory=list) # All source domains intersected


@dataclass
class BacktrackingResult:
    hotspot_id: str
    hotspot_name: str
    detection_lat: float
    detection_lng: float
    ensemble_size: int
    backtracking_horizon_hours: float
    estimated_origin_lat: float
    estimated_origin_lng: float
    estimated_release_hours_ago: float
    dominant_source_id: str
    source_hit_counts: Dict[str, int]
    source_hit_percentages: Dict[str, float]
    trajectory_points: List[Tuple[float, float, float]] # (lat, lng, hours_ago)
    geojson_trajectory: Dict[str, Any]
    geojson_origin_marker: Dict[str, Any]


class ReverseRK4Backtracker:
    """Reverse 4th-Order Runge-Kutta integrator for upstream trajectory backtracking."""

    def __init__(
        self,
        interpolator: VectorFieldInterpolator,
        diffusion_kh: float = 2.5,        # Horizontal diffusion coefficient in m²/s
        domain_bounds: Tuple[float, float, float, float] = (103.50, 1.05, 104.25, 1.50),
    ):
        self.interpolator = interpolator
        self.diffusion_kh = diffusion_kh
        self.min_lng, self.min_lat, self.max_lng, self.max_lat = domain_bounds

    def get_reverse_velocity(
        self,
        lat: float,
        lng: float,
        leeway: float,
    ) -> Tuple[float, float]:
        """Get negative velocity vector (-u, -v) in m/s for backward advection."""
        drift_vec = self.interpolator.interpolate(lat, lng, leeway_factor=leeway)
        # Invert velocity vector for backward-in-time integration
        return -drift_vec.total_u_ms, -drift_vec.total_v_ms

    def step_backward(
        self,
        particle: BackwardParticle,
        dt_seconds: float,
        elapsed_seconds: float,
    ) -> BackwardParticle:
        """Advect a single particle backward in time by dt_seconds using RK4."""
        if particle.status != "active":
            return particle

        lat = particle.lat
        lng = particle.lng
        leeway = particle.leeway_factor
        rad_lat = math.radians(lat)
        meters_per_deg_lng = max(100.0, METERS_PER_DEG_LAT * math.cos(rad_lat))

        # --- Stage 1: k1 (negative velocity) ---
        u1, v1 = self.get_reverse_velocity(lat, lng, leeway)
        d_lat1 = (v1 * dt_seconds) / METERS_PER_DEG_LAT
        d_lng1 = (u1 * dt_seconds) / meters_per_deg_lng

        # --- Stage 2: k2 ---
        lat2 = lat + 0.5 * d_lat1
        lng2 = lng + 0.5 * d_lng1
        u2, v2 = self.get_reverse_velocity(lat2, lng2, leeway)
        d_lat2 = (v2 * dt_seconds) / METERS_PER_DEG_LAT
        d_lng2 = (u2 * dt_seconds) / meters_per_deg_lng

        # --- Stage 3: k3 ---
        lat3 = lat + 0.5 * d_lat2
        lng3 = lng + 0.5 * d_lng2
        u3, v3 = self.get_reverse_velocity(lat3, lng3, leeway)
        d_lat3 = (v3 * dt_seconds) / METERS_PER_DEG_LAT
        d_lng3 = (u3 * dt_seconds) / meters_per_deg_lng

        # --- Stage 4: k4 ---
        lat4 = lat + d_lat3
        lng4 = lng + d_lng3
        u4, v4 = self.get_reverse_velocity(lat4, lng4, leeway)
        d_lat4 = (v4 * dt_seconds) / METERS_PER_DEG_LAT
        d_lng4 = (u4 * dt_seconds) / meters_per_deg_lng

        # Weighted RK4 displacement in degrees
        disp_lat = (d_lat1 + 2.0 * d_lat2 + 2.0 * d_lat3 + d_lat4) / 6.0
        disp_lng = (d_lng1 + 2.0 * d_lng2 + 2.0 * d_lng3 + d_lng4) / 6.0

        # Turbulent diffusion in reverse time (expands uncertainty cone backward)
        if self.diffusion_kh > 0:
            diff_step_m = math.sqrt(2.0 * self.diffusion_kh * dt_seconds)
            eta_x = random.gauss(0.0, 1.0) * diff_step_m
            eta_y = random.gauss(0.0, 1.0) * diff_step_m
            disp_lng += eta_x / meters_per_deg_lng
            disp_lat += eta_y / METERS_PER_DEG_LAT

        new_lat = lat + disp_lat
        new_lng = lng + disp_lng
        current_hours_ago = round((elapsed_seconds + dt_seconds) / 3600.0, 2)

        # Check domain boundaries
        if not (self.min_lng <= new_lng <= self.max_lng and self.min_lat <= new_lat <= self.max_lat):
            particle.status = "exited_domain"
            particle.terminal_time_hours_ago = current_hours_ago
            # If exited south, attribute to regional transboundary / shipping channel
            if new_lat <= self.min_lat:
                particle.terminal_source_id = "transboundary_riau"
                particle.source_hits.append("transboundary_riau")
            elif new_lat >= self.max_lat:
                particle.terminal_source_id = "johor_strait"
                particle.source_hits.append("johor_strait")
            return particle

        # Check source domain containment
        containing_src = find_containing_source(new_lat, new_lng)
        if containing_src:
            if containing_src.id not in particle.source_hits:
                particle.source_hits.append(containing_src.id)

        particle.lat = new_lat
        particle.lng = new_lng
        particle.trajectory.append((round(new_lat, 5), round(new_lng, 5), current_hours_ago))
        return particle

    def backtrack_hotspot(
        self,
        hotspot_id: str,
        hotspot_name: str,
        centroid_lat: float,
        centroid_lng: float,
        backtracking_horizon_hours: float = 48.0,
        ensemble_size: int = 40,
        dt_seconds: float = 300.0,
    ) -> BacktrackingResult:
        """Run an ensemble of reverse Lagrangian particles to trace a hotspot back to origin."""
        total_steps = int((backtracking_horizon_hours * 3600.0) / dt_seconds)
        particles: List[BackwardParticle] = []

        # Seed ensemble with Gaussian spatial spread (sigma ~ 60m) and leeway variability
        for i in range(ensemble_size):
            p_lat = centroid_lat + random.gauss(0.0, 0.0006)
            p_lng = centroid_lng + random.gauss(0.0, 0.0006)
            leeway = random.uniform(0.018, 0.026)
            p = BackwardParticle(
                id=f"{hotspot_id}_back_{i:02d}",
                lat=p_lat,
                lng=p_lng,
                initial_lat=p_lat,
                initial_lng=p_lng,
                leeway_factor=leeway,
                trajectory=[(round(p_lat, 5), round(p_lng, 5), 0.0)],
            )
            # Check if initially located in recreational shoreline or canal
            init_src = find_containing_source(p_lat, p_lng)
            if init_src:
                p.source_hits.append(init_src.id)
            particles.append(p)

        # Advect ensemble backward step by step
        elapsed = 0.0
        for _ in range(total_steps):
            active_count = 0
            for p in particles:
                if p.status == "active":
                    self.step_backward(p, dt_seconds, elapsed)
                    if p.status == "active":
                        active_count += 1
            elapsed += dt_seconds
            if active_count == 0:
                break

        # Tally source domain intersections
        source_hit_counts: Dict[str, int] = {k: 0 for k in SOURCE_DOMAINS.keys()}
        for p in particles:
            # If particle hit explicit source domains, count them
            if p.source_hits:
                for src_id in set(p.source_hits):
                    if src_id in source_hit_counts:
                        source_hit_counts[src_id] += 1
            else:
                # If no direct hit, find nearest source domain at terminal position
                dists = {src_id: src.distance_to_point_km(p.lat, p.lng) for src_id, src in SOURCE_DOMAINS.items()}
                nearest_src = min(dists, key=dists.get)
                source_hit_counts[nearest_src] += 1

        total_hits = max(sum(source_hit_counts.values()), 1)
        source_hit_percentages = {
            k: round((v / total_hits) * 100.0, 1) for k, v in source_hit_counts.items()
        }

        # Compute ensemble mean trajectory (backwards in time)
        max_traj_len = max(len(p.trajectory) for p in particles)
        ensemble_trajectory: List[Tuple[float, float, float]] = []

        for step_idx in range(max_traj_len):
            lats_at_step = []
            lngs_at_step = []
            hrs_at_step = 0.0
            for p in particles:
                if step_idx < len(p.trajectory):
                    pt = p.trajectory[step_idx]
                    lats_at_step.append(pt[0])
                    lngs_at_step.append(pt[1])
                    hrs_at_step = pt[2]
            if lats_at_step:
                mean_lat = float(np.mean(lats_at_step))
                mean_lng = float(np.mean(lngs_at_step))
                ensemble_trajectory.append((round(mean_lat, 5), round(mean_lng, 5), hrs_at_step))

        # Terminal origin estimation
        terminal_lats = [p.lat for p in particles]
        terminal_lngs = [p.lng for p in particles]
        estimated_origin_lat = round(float(np.mean(terminal_lats)), 5)
        estimated_origin_lng = round(float(np.mean(terminal_lngs)), 5)
        estimated_release_hours_ago = round(ensemble_trajectory[-1][2] if ensemble_trajectory else backtracking_horizon_hours, 1)

        dominant_source_id = max(source_hit_counts, key=source_hit_counts.get)

        # Build GeoJSON Linestring for trajectory
        # Coordinates in GeoJSON: [lng, lat]
        geojson_coords = [[pt[1], pt[0]] for pt in ensemble_trajectory]
        dominant_src = SOURCE_DOMAINS[dominant_source_id]

        geojson_trajectory = {
            "type": "Feature",
            "properties": {
                "hotspot_id": hotspot_id,
                "hotspot_name": hotspot_name,
                "direction": "backtracking",
                "horizon_hours": backtracking_horizon_hours,
                "release_hours_ago": estimated_release_hours_ago,
                "dominant_source_id": dominant_source_id,
                "dominant_source_name": dominant_src.name,
                "color": dominant_src.color,
                "stroke_style": "dashed",
            },
            "geometry": {
                "type": "LineString",
                "coordinates": geojson_coords,
            },
        }

        geojson_origin_marker = {
            "type": "Feature",
            "properties": {
                "hotspot_id": hotspot_id,
                "hotspot_name": hotspot_name,
                "feature_type": "estimated_origin",
                "dominant_source_id": dominant_source_id,
                "dominant_source_name": dominant_src.name,
                "color": dominant_src.color,
                "release_hours_ago": estimated_release_hours_ago,
                "lat": estimated_origin_lat,
                "lng": estimated_origin_lng,
            },
            "geometry": {
                "type": "Point",
                "coordinates": [estimated_origin_lng, estimated_origin_lat],
            },
        }

        return BacktrackingResult(
            hotspot_id=hotspot_id,
            hotspot_name=hotspot_name,
            detection_lat=round(centroid_lat, 5),
            detection_lng=round(centroid_lng, 5),
            ensemble_size=ensemble_size,
            backtracking_horizon_hours=backtracking_horizon_hours,
            estimated_origin_lat=estimated_origin_lat,
            estimated_origin_lng=estimated_origin_lng,
            estimated_release_hours_ago=estimated_release_hours_ago,
            dominant_source_id=dominant_source_id,
            source_hit_counts=source_hit_counts,
            source_hit_percentages=source_hit_percentages,
            trajectory_points=ensemble_trajectory,
            geojson_trajectory=geojson_trajectory,
            geojson_origin_marker=geojson_origin_marker,
        )

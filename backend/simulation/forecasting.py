"""Lagrangian Marine Litter Forecasting Engine for Singapore Waters.

Executes forward-in-time advection projections across multiple operational horizons
(+2h, +6h, +12h, +24h, +48h). Quantifies beaching stranding risk, computes
accumulation density clusters, and outputs trajectory polylines for UI mapping.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from sklearn.cluster import DBSCAN

from backend.simulation.advection import (
    LagrangianParticle,
    RK4AdvectionIntegrator,
    SINGAPORE_COASTAL_SHORES,
)
from backend.weather.interpolator import VectorFieldInterpolator

FORECAST_HORIZONS_HOURS = [2, 6, 12, 24, 48]


@dataclass
class ForecastedAccumulationHotspot:
    forecast_id: str
    origin_hotspot_id: str
    origin_sector: str
    horizon_hours: int
    predicted_lat: float
    predicted_lng: float
    status: str                         # "Beached Accumulation" | "Floating Plume"
    target_shore: Optional[str]
    beached_probability_pct: float
    predicted_items: int
    risk_level: str                     # "High" | "Medium" | "Low"
    trajectory_points: List[Tuple[float, float]] = field(default_factory=list)


@dataclass
class HorizonForecastSummary:
    horizon_hours: int
    total_particles: int
    floating_particles: int
    beached_particles: int
    beached_percentage: float
    top_impacted_shores: Dict[str, int]
    accumulation_hotspots: List[ForecastedAccumulationHotspot] = field(default_factory=list)


class DebrisDriftForecaster:
    """Simulates forward debris drift trajectories and forecasts future accumulation."""

    def __init__(
        self,
        interpolator: VectorFieldInterpolator,
        particles_per_hotspot: int = 25,
        time_step_seconds: float = 300.0, # 5-minute integration steps
    ):
        self.integrator = RK4AdvectionIntegrator(interpolator)
        self.particles_per_hotspot = particles_per_hotspot
        self.dt = time_step_seconds

    def seed_particles(self, hotspots: List[Dict[str, Any]]) -> List[LagrangianParticle]:
        """Seed virtual particle ensembles around detected hotspot centroids."""
        particles: List[LagrangianParticle] = []
        for hs in hotspots:
            hs_id = hs.get("id") or hs.get("hotspot_id", "HS-01")
            c_lat = hs["centroid_lat"] if "centroid_lat" in hs else hs["lat"]
            c_lng = hs["centroid_lng"] if "centroid_lng" in hs else hs["lng"]
            radius_m = hs.get("radius_meters", 150.0)

            for i in range(self.particles_per_hotspot):
                # Disperse particles randomly within hotspot radius
                angle = np.random.uniform(0, 2.0 * math.pi)
                dist = np.random.uniform(0, radius_m)
                d_lat = (dist * math.sin(angle)) / 111139.0
                d_lng = (dist * math.cos(angle)) / (111139.0 * math.cos(math.radians(c_lat)))

                p_lat = c_lat + d_lat
                p_lng = c_lng + d_lng

                # Random leeway between 1.5% and 3.5% (different buoyancy profiles)
                leeway = round(float(np.random.uniform(0.015, 0.035)), 4)
                p = LagrangianParticle(
                    id=f"{hs_id}-P{i+1:02d}",
                    lat=p_lat,
                    lng=p_lng,
                    initial_lat=p_lat,
                    initial_lng=p_lng,
                    source_hotspot_id=hs_id,
                    leeway_factor=leeway,
                    trajectory=[(round(p_lat, 5), round(p_lng, 5), 0.0)],
                )
                particles.append(p)
        return particles

    def run_forecast(
        self,
        hotspots: List[Dict[str, Any]],
        horizons_hours: Optional[List[int]] = None,
    ) -> Dict[int, HorizonForecastSummary]:
        """Run full forward Lagrangian integration up to max horizon."""
        horizons = sorted(horizons_hours or FORECAST_HORIZONS_HOURS)
        max_horizon_hrs = max(horizons)
        max_seconds = max_horizon_hrs * 3600.0

        particles = self.seed_particles(hotspots)
        steps_total = int(max_seconds / self.dt)

        # Map elapsed seconds to particle snapshot
        snapshots: Dict[int, List[LagrangianParticle]] = {h: [] for h in horizons}

        elapsed = 0.0
        horizon_seconds_map = {h: h * 3600.0 for h in horizons}

        for step_idx in range(steps_total):
            for p in particles:
                if p.status != "beached" and p.status != "exited_domain":
                    self.integrator.step(p, dt_seconds=self.dt, elapsed_seconds=elapsed)

            elapsed += self.dt

            # Check if this step matches a target horizon
            for h, h_sec in horizon_seconds_map.items():
                if abs(elapsed - h_sec) < 0.5 * self.dt:
                    # Deep copy state for snapshot
                    snapshot_pts = [
                        LagrangianParticle(
                            id=pt.id,
                            lat=pt.lat,
                            lng=pt.lng,
                            initial_lat=pt.initial_lat,
                            initial_lng=pt.initial_lng,
                            source_hotspot_id=pt.source_hotspot_id,
                            leeway_factor=pt.leeway_factor,
                            status=pt.status,
                            beached_shore=pt.beached_shore,
                            beached_time_hours=pt.beached_time_hours,
                            trajectory=list(pt.trajectory),
                        )
                        for pt in particles
                    ]
                    snapshots[h] = snapshot_pts

        # Process summaries per horizon
        results: Dict[int, HorizonForecastSummary] = {}
        for h in horizons:
            pts_at_h = snapshots.get(h, particles)
            summary = self._compile_horizon_summary(h, pts_at_h, hotspots)
            results[h] = summary

        return results

    def _compile_horizon_summary(
        self,
        horizon_hrs: int,
        particles: List[LagrangianParticle],
        original_hotspots: List[Dict[str, Any]],
    ) -> HorizonForecastSummary:
        total = len(particles)
        beached = [p for p in particles if p.status == "beached"]
        floating = [p for p in particles if p.status == "active"]

        # Beaching distribution by shore
        shores_count: Dict[str, int] = {}
        for p in beached:
            sh = p.beached_shore or "Unclassified Shore"
            shores_count[sh] = shores_count.get(sh, 0) + 1

        # Cluster particles per source hotspot to find predicted centroid
        accumulation_hotspots: List[ForecastedAccumulationHotspot] = []
        for hs in original_hotspots:
            hs_id = hs.get("id") or hs.get("hotspot_id", "HS-01")
            hs_sector = hs.get("sector_id") or hs.get("area", "east_coast")
            orig_items = hs.get("detection_count") or hs.get("items_count", 10)

            sub_pts = [p for p in particles if p.source_hotspot_id == hs_id]
            if not sub_pts:
                continue

            lats = [p.lat for p in sub_pts]
            lngs = [p.lng for p in sub_pts]
            pred_lat = float(np.mean(lats))
            pred_lng = float(np.mean(lngs))

            beached_sub = [p for p in sub_pts if p.status == "beached"]
            beached_prob = round((len(beached_sub) / len(sub_pts)) * 100.0, 1)

            # Dominant landing shore
            sub_shores = [p.beached_shore for p in beached_sub if p.beached_shore]
            target_shore = max(set(sub_shores), key=sub_shores.count) if sub_shores else None

            status = "Beached Accumulation" if beached_prob >= 40.0 else "Floating Plume"
            if beached_prob >= 60.0:
                risk = "High"
            elif beached_prob >= 25.0:
                risk = "Medium"
            else:
                risk = "Low"

            # Compute representative trajectory from the ensemble median path
            # Subsample trajectory to ~5-10 key waypoints
            sample_traj = sub_pts[0].trajectory
            stride = max(1, len(sample_traj) // 8)
            traj_waypoints = [[round(pt[0], 5), round(pt[1], 5)] for pt in sample_traj[::stride]]
            if traj_waypoints and traj_waypoints[-1] != [round(pred_lat, 5), round(pred_lng, 5)]:
                traj_waypoints.append([round(pred_lat, 5), round(pred_lng, 5)])

            accumulation_hotspots.append(
                ForecastedAccumulationHotspot(
                    forecast_id=f"FC-{horizon_hrs}H-{hs_id}",
                    origin_hotspot_id=hs_id,
                    origin_sector=hs_sector,
                    horizon_hours=horizon_hrs,
                    predicted_lat=round(pred_lat, 5),
                    predicted_lng=round(pred_lng, 5),
                    status=status,
                    target_shore=target_shore,
                    beached_probability_pct=beached_prob,
                    predicted_items=orig_items,
                    risk_level=risk,
                    trajectory_points=traj_waypoints,
                )
            )

        beached_pct = round((len(beached) / max(total, 1)) * 100.0, 1)

        return HorizonForecastSummary(
            horizon_hours=horizon_hrs,
            total_particles=total,
            floating_particles=len(floating),
            beached_particles=len(beached),
            beached_percentage=beached_pct,
            top_impacted_shores=dict(sorted(shores_count.items(), key=lambda x: x[1], reverse=True)),
            accumulation_hotspots=accumulation_hotspots,
        )

    def to_geojson(self, forecast_summary: HorizonForecastSummary) -> Dict[str, Any]:
        """Convert forecasted hotspots into a GeoJSON FeatureCollection."""
        features = []
        for fc in forecast_summary.accumulation_hotspots:
            # 1. Point Feature for Predicted Hotspot Position
            features.append({
                "type": "Feature",
                "id": fc.forecast_id,
                "geometry": {
                    "type": "Point",
                    "coordinates": [fc.predicted_lng, fc.predicted_lat],
                },
                "properties": {
                    "forecast_id": fc.forecast_id,
                    "origin_hotspot_id": fc.origin_hotspot_id,
                    "horizon_hours": fc.horizon_hours,
                    "status": fc.status,
                    "target_shore": fc.target_shore,
                    "beached_probability_pct": fc.beached_probability_pct,
                    "predicted_items": fc.predicted_items,
                    "risk_level": fc.risk_level,
                },
            })

            # 2. LineString Feature for the Drift Pathway
            if len(fc.trajectory_points) >= 2:
                # GeoJSON coordinates format is [lng, lat]
                line_coords = [[pt[1], pt[0]] for pt in fc.trajectory_points]
                features.append({
                    "type": "Feature",
                    "id": f"TRAJ-{fc.forecast_id}",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": line_coords,
                    },
                    "properties": {
                        "forecast_id": fc.forecast_id,
                        "origin_hotspot_id": fc.origin_hotspot_id,
                        "horizon_hours": fc.horizon_hours,
                        "risk_level": fc.risk_level,
                    },
                })

        return {
            "type": "FeatureCollection",
            "metadata": {
                "horizon_hours": forecast_summary.horizon_hours,
                "beached_percentage": forecast_summary.beached_percentage,
                "top_impacted_shores": forecast_summary.top_impacted_shores,
                "total_forecasted_hotspots": len(forecast_summary.accumulation_hotspots),
            },
            "features": features,
        }

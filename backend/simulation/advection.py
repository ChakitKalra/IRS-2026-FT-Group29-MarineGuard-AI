"""2D Lagrangian Particle Advection Core with RK4 Integration and Shoreline Trapping.

Simulates the transport, dispersion, and beaching of marine debris in Singapore coastal waters.
Solves the advection-diffusion kinematic equation using 4th-Order Runge-Kutta (RK4) integration:
    d x / dt = u_current(x, t) + alpha * w_wind(x, t) + u_diffusion(x, t)
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from shapely.geometry import Point, Polygon

from backend.weather.interpolator import VectorFieldInterpolator

# Earth geometric constants
METERS_PER_DEG_LAT = 111139.0
EARTH_RADIUS_METERS = 6371000.0

# Singapore Shoreline Geometries (simplified coastal polygons for beaching collision)
# Coordinates format: [(lng, lat), ...] for Shapely Polygon
SINGAPORE_COASTAL_SHORES = {
    "East Coast Park Shoreline": Polygon([
        (103.885, 1.298), (103.955, 1.309), (103.968, 1.318), (103.972, 1.330),
        (103.950, 1.335), (103.890, 1.315)
    ]),
    "Pasir Ris Beach & Estuary": Polygon([
        (103.935, 1.378), (103.965, 1.378), (103.972, 1.395), (103.955, 1.405),
        (103.930, 1.392)
    ]),
    "Changi Beach Coast": Polygon([
        (103.975, 1.365), (104.010, 1.385), (104.015, 1.405), (103.985, 1.400)
    ]),
    "Sentosa & Southern Islands": Polygon([
        (103.810, 1.240), (103.845, 1.245), (103.855, 1.258), (103.815, 1.262)
    ]),
    "Pulau Ubin Mangrove Shores": Polygon([
        (103.945, 1.400), (103.980, 1.400), (103.990, 1.425), (103.950, 1.425)
    ]),
    "Jurong / Tuas Industrial Basin": Polygon([
        (103.620, 1.260), (103.670, 1.265), (103.675, 1.310), (103.625, 1.310)
    ]),
    "Sungei Buloh Wetland Reserve": Polygon([
        (103.715, 1.435), (103.740, 1.440), (103.745, 1.455), (103.720, 1.455)
    ]),
}


@dataclass
class LagrangianParticle:
    id: str
    lat: float
    lng: float
    initial_lat: float
    initial_lng: float
    source_hotspot_id: str
    leeway_factor: float = 0.02
    status: str = "active"          # "active" | "beached" | "exited_domain"
    beached_shore: Optional[str] = None
    beached_time_hours: Optional[float] = None
    trajectory: List[Tuple[float, float, float]] = field(default_factory=list) # (lat, lng, elapsed_hrs)


class RK4AdvectionIntegrator:
    """4th-Order Runge-Kutta advection engine for marine litter transport."""

    def __init__(
        self,
        interpolator: VectorFieldInterpolator,
        diffusion_kh: float = 2.5,        # Horizontal diffusion coefficient in m²/s
        domain_bounds: Tuple[float, float, float, float] = (103.55, 1.10, 104.15, 1.50),
    ):
        self.interpolator = interpolator
        self.diffusion_kh = diffusion_kh
        self.min_lng, self.min_lat, self.max_lng, self.max_lat = domain_bounds

    def check_shoreline_collision(self, lat: float, lng: float) -> Tuple[bool, Optional[str]]:
        """Check if a particle's coordinates have beached on a Singapore shoreline."""
        pt = Point(lng, lat)
        for shore_name, polygon in SINGAPORE_COASTAL_SHORES.items():
            if polygon.contains(pt):
                return True, shore_name
        return False, None

    def get_velocity(
        self,
        lat: float,
        lng: float,
        leeway: float,
    ) -> Tuple[float, float]:
        """Get combined (u, v) drift velocity in m/s at a specific coordinate."""
        drift_vec = self.interpolator.interpolate(lat, lng, leeway_factor=leeway)
        return drift_vec.total_u_ms, drift_vec.total_v_ms

    def step(
        self,
        particle: LagrangianParticle,
        dt_seconds: float,
        elapsed_seconds: float,
    ) -> LagrangianParticle:
        """Advance a single Lagrangian particle by dt_seconds using RK4 integration."""
        if particle.status == "beached":
            return particle

        lat = particle.lat
        lng = particle.lng
        leeway = particle.leeway_factor
        rad_lat = math.radians(lat)
        meters_per_deg_lng = max(100.0, METERS_PER_DEG_LAT * math.cos(rad_lat))

        # --- Stage 1: k1 ---
        u1, v1 = self.get_velocity(lat, lng, leeway)
        d_lat1 = (v1 * dt_seconds) / METERS_PER_DEG_LAT
        d_lng1 = (u1 * dt_seconds) / meters_per_deg_lng

        # --- Stage 2: k2 ---
        lat2 = lat + 0.5 * d_lat1
        lng2 = lng + 0.5 * d_lng1
        u2, v2 = self.get_velocity(lat2, lng2, leeway)
        d_lat2 = (v2 * dt_seconds) / METERS_PER_DEG_LAT
        d_lng2 = (u2 * dt_seconds) / meters_per_deg_lng

        # --- Stage 3: k3 ---
        lat3 = lat + 0.5 * d_lat2
        lng3 = lng + 0.5 * d_lng2
        u3, v3 = self.get_velocity(lat3, lng3, leeway)
        d_lat3 = (v3 * dt_seconds) / METERS_PER_DEG_LAT
        d_lng3 = (u3 * dt_seconds) / meters_per_deg_lng

        # --- Stage 4: k4 ---
        lat4 = lat + d_lat3
        lng4 = lng + d_lng3
        u4, v4 = self.get_velocity(lat4, lng4, leeway)
        d_lat4 = (v4 * dt_seconds) / METERS_PER_DEG_LAT
        d_lng4 = (u4 * dt_seconds) / meters_per_deg_lng

        # Weighted RK4 displacement in degrees
        disp_lat = (d_lat1 + 2.0 * d_lat2 + 2.0 * d_lat3 + d_lat4) / 6.0
        disp_lng = (d_lng1 + 2.0 * d_lng2 + 2.0 * d_lng3 + d_lng4) / 6.0

        # Turbulent horizontal diffusion (Brownian random walk)
        if self.diffusion_kh > 0:
            diff_step_m = math.sqrt(2.0 * self.diffusion_kh * dt_seconds)
            eta_x = random.gauss(0.0, 1.0) * diff_step_m
            eta_y = random.gauss(0.0, 1.0) * diff_step_m
            disp_lng += eta_x / meters_per_deg_lng
            disp_lat += eta_y / METERS_PER_DEG_LAT

        new_lat = lat + disp_lat
        new_lng = lng + disp_lng

        # Check shoreline collision / beaching
        is_beached, shore_name = self.check_shoreline_collision(new_lat, new_lng)
        if is_beached:
            particle.lat = new_lat
            particle.lng = new_lng
            particle.status = "beached"
            particle.beached_shore = shore_name
            particle.beached_time_hours = round((elapsed_seconds + dt_seconds) / 3600.0, 2)
            particle.trajectory.append((round(new_lat, 5), round(new_lng, 5), particle.beached_time_hours))
            return particle

        # Check domain boundaries
        if not (self.min_lng <= new_lng <= self.max_lng and self.min_lat <= new_lat <= self.max_lat):
            particle.status = "exited_domain"
            return particle

        particle.lat = new_lat
        particle.lng = new_lng
        elapsed_hrs = round((elapsed_seconds + dt_seconds) / 3600.0, 2)
        particle.trajectory.append((round(new_lat, 5), round(new_lng, 5), elapsed_hrs))
        return particle

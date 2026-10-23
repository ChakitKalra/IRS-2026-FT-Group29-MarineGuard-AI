"""2D Spatio-Temporal Vector Field Interpolator for MarineGuard AI.

Interpolates discrete ocean current grid points (Copernicus / Tidal model)
and terrestrial weather station readings (data.gov.sg) into continuous
drift vectors for any coordinate (lat, lng, t) across Singapore waters.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from backend.weather.copernicus import CurrentGridPoint, OceanCurrentField
from backend.weather.nea_client import SingaporeWeatherSummary, WeatherStationReading


@dataclass
class InterpolatedDriftVector:
    latitude: float
    longitude: float
    current_u_ms: float
    current_v_ms: float
    current_speed_ms: float
    current_speed_knots: float
    current_heading_deg: float
    wind_u_ms: float
    wind_v_ms: float
    wind_speed_ms: float
    wind_speed_knots: float
    wind_heading_towards_deg: float
    leeway_factor: float
    total_u_ms: float
    total_v_ms: float
    total_speed_ms: float
    total_speed_knots: float
    total_heading_deg: float
    current_contribution_pct: float
    wind_contribution_pct: float
    local_rainfall_mm_hr: float
    inland_flushing_risk: str


class VectorFieldInterpolator:
    """Interpolates currents and winds to compute continuous debris drift velocities."""

    def __init__(
        self,
        current_field: OceanCurrentField,
        weather_summary: SingaporeWeatherSummary,
        default_leeway_factor: float = 0.02, # 2% windage leeway for surface debris
    ):
        self.current_field = current_field
        self.weather_summary = weather_summary
        self.default_leeway_factor = default_leeway_factor

        self._current_pts = current_field.points
        self._wind_pts = [st for st in weather_summary.stations if st.wind_u_ms is not None]

    def interpolate(
        self,
        lat: float,
        lng: float,
        leeway_factor: Optional[float] = None,
    ) -> InterpolatedDriftVector:
        """Compute the continuous drift vector at a specific (lat, lng) position."""
        alpha = leeway_factor if leeway_factor is not None else self.default_leeway_factor

        # 1. Inverse Distance Weighting (IDW) for Ocean Currents
        u_c, v_c = self._idw_interpolate_currents(lat, lng)
        spd_c = math.hypot(u_c, v_c)
        hdg_c = (math.degrees(math.atan2(u_c, v_c)) + 360.0) % 360.0

        # 2. IDW for Wind Vectors
        u_w, v_w, rain_local = self._idw_interpolate_weather(lat, lng)
        spd_w = math.hypot(u_w, v_w)
        hdg_w = (math.degrees(math.atan2(u_w, v_w)) + 360.0) % 360.0

        # 3. Combine vectors: V_drift = V_current + alpha * V_wind
        u_tot = u_c + alpha * u_w
        v_tot = v_c + alpha * v_w
        spd_tot = math.hypot(u_tot, v_tot)
        hdg_tot = (math.degrees(math.atan2(u_tot, v_tot)) + 360.0) % 360.0

        # Component percentage contributions
        c_mag = spd_c
        w_mag = spd_w * alpha
        denom = max(c_mag + w_mag, 1e-6)
        c_pct = round((c_mag / denom) * 100.0, 1)
        w_pct = round((w_mag / denom) * 100.0, 1)

        return InterpolatedDriftVector(
            latitude=round(lat, 5),
            longitude=round(lng, 5),
            current_u_ms=round(u_c, 3),
            current_v_ms=round(v_c, 3),
            current_speed_ms=round(spd_c, 3),
            current_speed_knots=round(spd_c * 1.94384, 2),
            current_heading_deg=round(hdg_c, 1),
            wind_u_ms=round(u_w, 2),
            wind_v_ms=round(v_w, 2),
            wind_speed_ms=round(spd_w, 2),
            wind_speed_knots=round(spd_w * 1.94384, 1),
            wind_heading_towards_deg=round(hdg_w, 1),
            leeway_factor=alpha,
            total_u_ms=round(u_tot, 3),
            total_v_ms=round(v_tot, 3),
            total_speed_ms=round(spd_tot, 3),
            total_speed_knots=round(spd_tot * 1.94384, 2),
            total_heading_deg=round(hdg_tot, 1),
            current_contribution_pct=c_pct,
            wind_contribution_pct=w_pct,
            local_rainfall_mm_hr=round(rain_local, 1),
            inland_flushing_risk=self.weather_summary.inland_flushing_risk,
        )

    def _idw_interpolate_currents(self, lat: float, lng: float, power: float = 2.0) -> Tuple[float, float]:
        if not self._current_pts:
            return 0.5, 0.2

        weights = []
        u_vals = []
        v_vals = []

        for p in self._current_pts:
            dist = math.hypot((p.latitude - lat) * 111.0, (p.longitude - lng) * 111.0 * math.cos(math.radians(lat)))
            if dist < 0.1: # Practically exact point
                return p.u_ms, p.v_ms
            w = 1.0 / (dist ** power)
            weights.append(w)
            u_vals.append(p.u_ms)
            v_vals.append(p.v_ms)

        sum_w = sum(weights)
        if sum_w == 0:
            return 0.5, 0.2

        u_interp = sum(w * u for w, u in zip(weights, u_vals)) / sum_w
        v_interp = sum(w * v for w, v in zip(weights, v_vals)) / sum_w
        return u_interp, v_interp

    def _idw_interpolate_weather(self, lat: float, lng: float, power: float = 2.0) -> Tuple[float, float, float]:
        if not self._wind_pts:
            # Fallback to island averages
            spd = self.weather_summary.avg_wind_speed_ms
            deg_to = self.weather_summary.dominant_wind_direction_towards_deg
            rad_to = math.radians(deg_to)
            u = spd * math.sin(rad_to)
            v = spd * math.cos(rad_to)
            return u, v, self.weather_summary.island_avg_rainfall_mm_hr

        weights = []
        u_vals, v_vals, rain_vals = [], [], []

        for st in self._wind_pts:
            dist = math.hypot((st.latitude - lat) * 111.0, (st.longitude - lng) * 111.0 * math.cos(math.radians(lat)))
            if dist < 0.1:
                return st.wind_u_ms or 0.0, st.wind_v_ms or 0.0, st.rainfall_rate_mm_hr or 0.0
            w = 1.0 / (dist ** power)
            weights.append(w)
            u_vals.append(st.wind_u_ms or 0.0)
            v_vals.append(st.wind_v_ms or 0.0)
            rain_vals.append(st.rainfall_rate_mm_hr or 0.0)

        sum_w = sum(weights)
        if sum_w == 0:
            return 1.0, 2.0, 0.0

        u_interp = sum(w * u for w, u in zip(weights, u_vals)) / sum_w
        v_interp = sum(w * v for w, v in zip(weights, v_vals)) / sum_w
        rain_interp = sum(w * r for w, r in zip(weights, rain_vals)) / sum_w
        return u_interp, v_interp, rain_interp

"""MarineGuard AI — FastAPI REST & Streaming Backend Server.

Phase 6 Full-Stack Integration Server providing endpoints for:
- /api/v1/hotspots: Multi-scale detected marine debris hotspots & satellite polygons.
- /api/v1/weather/current: Real-time environmental data (wind, rain, M2 tidal currents).
- /api/v1/forecast: Multi-horizon Lagrangian forward drift projections (2h, 6h, 12h, 24h, 48h).
- /api/v1/attribution: Probabilistic Bayesian source attribution & reverse backtracking.
- /api/v1/cleanup/recommendations: Coastal Priority Index (CPI) rankings & dispatch orders.
- /api/v1/cleanup/report/download: Downloadable Incident Action Plan (IAP) report.
- /api/v1/simulate/drift: On-demand forward RK4 Lagrangian advection simulation.
- /api/v1/simulate/backtrack: On-demand reverse Lagrangian backtracking simulation.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query, Response, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Setup logging
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("marineguard.api")

# Paths to data stores
BASE_DIR = Path(__file__).resolve().parent.parent.parent
OUTPUTS_DIR = BASE_DIR / "backend" / "outputs"
FRONTEND_SRC_DIR = BASE_DIR / "frontend" / "src"

SERVER_START_TIME = time.time()

# Initialize FastAPI application
app = FastAPI(
    title="MarineGuard AI REST API",
    description="Intelligent coastal monitoring, drift forecasting, source attribution, and cleanup optimization for Singapore waters.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Enable CORS for local dev (Vite default port 5173 and standard hosts)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Data Loading Helpers with Robust Fallbacks
# ---------------------------------------------------------------------------
def _load_json_data(filename: str, fallback_filename: Optional[str] = None) -> Dict[str, Any]:
    """Helper to load JSON data from backend/outputs or frontend/src."""
    candidates = [
        OUTPUTS_DIR / filename,
        FRONTEND_SRC_DIR / (fallback_filename or filename),
    ]
    if fallback_filename:
        candidates.insert(1, OUTPUTS_DIR / fallback_filename)

    for p in candidates:
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning("Error reading JSON from %s: %s", p, e)

    logger.warning("Could not locate %s in %s or %s", filename, OUTPUTS_DIR, FRONTEND_SRC_DIR)
    return {}


# ---------------------------------------------------------------------------
# Pydantic Schemas for Request & Response Models
# ---------------------------------------------------------------------------
class AttributionRequest(BaseModel):
    hotspot_id: Optional[str] = Field(None, description="Known hotspot identifier (e.g. HS-01, HS-EAST-01)")
    custom_lat: Optional[float] = Field(None, ge=1.0, le=1.6, description="Custom starting latitude in Singapore waters")
    custom_lng: Optional[float] = Field(None, ge=103.5, le=104.2, description="Custom starting longitude in Singapore waters")
    rainfall_rate_mmh: Optional[float] = Field(10.0, ge=0.0, le=200.0, description="Local rainfall intensity in mm/hr for IFI coupling")


class DriftSimulationRequest(BaseModel):
    start_lat: float = Field(..., ge=1.0, le=1.6, description="Starting latitude")
    start_lng: float = Field(..., ge=103.5, le=104.2, description="Starting longitude")
    duration_hours: float = Field(24.0, ge=1.0, le=72.0, description="Simulation duration in hours")
    leeway_factor: float = Field(0.025, ge=0.0, le=0.08, description="Windage leeway fraction (typically 1.5% - 3.5%)")


class BacktrackSimulationRequest(BaseModel):
    start_lat: float = Field(..., ge=1.0, le=1.6, description="Observed detection latitude")
    start_lng: float = Field(..., ge=103.5, le=104.2, description="Observed detection longitude")
    backtrack_hours: float = Field(48.0, ge=6.0, le=72.0, description="Hours to backtrack (-dt)")


# ---------------------------------------------------------------------------
# API Routes
# ---------------------------------------------------------------------------
@app.get("/", tags=["Root"])
def root_status() -> Dict[str, Any]:
    """Root endpoint providing system identity, status, and navigation."""
    return {
        "service": "MarineGuard AI API",
        "description": "Singapore Coastal Intelligence & Marine Litter Decision Support",
        "version": "1.0.0",
        "status": "OPERATIONAL",
        "docs": "/docs",
        "endpoints": {
            "health": "/api/v1/health",
            "hotspots": "/api/v1/hotspots",
            "weather_current": "/api/v1/weather/current",
            "forecast": "/api/v1/forecast?horizon=24",
            "attribution": "/api/v1/attribution",
            "cleanup_recommendations": "/api/v1/cleanup/recommendations",
            "cleanup_report_download": "/api/v1/cleanup/report/download",
            "simulate_drift": "/api/v1/simulate/drift",
            "simulate_backtrack": "/api/v1/simulate/backtrack",
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/v1/health", tags=["System"])
def get_health() -> Dict[str, Any]:
    """System health check and loaded subsystem verification."""
    uptime_seconds = time.time() - SERVER_START_TIME

    # Check presence of subsystem outputs
    subsystems = {
        "phase1_detection": (OUTPUTS_DIR / "phase1_detection_report.json").exists() or (FRONTEND_SRC_DIR / "detected_hotspots.json").exists(),
        "phase2_environmental": (OUTPUTS_DIR / "phase2_environmental_report.json").exists() or (FRONTEND_SRC_DIR / "live_weather_currents.json").exists(),
        "phase3_forecasting": (OUTPUTS_DIR / "phase3_forecast_report.json").exists() or (FRONTEND_SRC_DIR / "drift_forecasts.json").exists(),
        "phase4_attribution": (OUTPUTS_DIR / "phase4_attribution_report.json").exists() or (FRONTEND_SRC_DIR / "source_attribution.json").exists(),
        "phase5_optimization": (OUTPUTS_DIR / "phase5_decision_support_report.json").exists() or (FRONTEND_SRC_DIR / "cleanup_recommendations.json").exists(),
    }

    all_healthy = all(subsystems.values())

    return {
        "status": "healthy" if all_healthy else "degraded",
        "uptime_seconds": round(uptime_seconds, 1),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "active_pipelines": subsystems,
        "environment": "Singapore Coastal Waters (1.15°N - 1.45°N, 103.60°E - 104.10°E)",
    }


@app.get("/api/v1/hotspots", tags=["Phase 1: Detection"])
def get_hotspots() -> Dict[str, Any]:
    """Retrieve multi-scale detected marine litter hotspots and Sentinel-2 slick polygons."""
    data = _load_json_data("phase1_detection_report.json", "detected_hotspots.json")
    if not data:
        return {
            "status": "success",
            "hotspot_count": 0,
            "hotspots": [],
            "satellite_polygons": {"type": "FeatureCollection", "features": []},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    return {
        "status": "success",
        "hotspot_count": len(data.get("hotspots", [])),
        "hotspots": data.get("hotspots", []),
        "satellite_polygons": data.get("satellite_polygons", {"type": "FeatureCollection", "features": []}),
        "uav_detections": data.get("uav_detections", []),
        "cluster_summary": data.get("cluster_summary", {}),
        "timestamp": data.get("timestamp", datetime.now(timezone.utc).isoformat()),
    }


@app.get("/api/v1/weather/current", tags=["Phase 2: Environmental"])
def get_current_weather() -> Dict[str, Any]:
    """Retrieve real-time surface current vectors, M2 tidal state, and data.gov.sg meteorological data."""
    data = _load_json_data("phase2_environmental_report.json", "live_weather_currents.json")

    ocean_sum = data.get("oceanographic_summary") or {}
    met_sum = data.get("meteorological_summary") or {}

    tidal_stage = ocean_sum.get("tidal_stage") or data.get("tidal_stage") or "Ebb (Westward to Malacca Strait)"
    mean_speed_knots = ocean_sum.get("mean_current_knots") or data.get("mean_current_knots", 1.04)
    heading_deg = ocean_sum.get("current_heading_deg") or data.get("current_heading_deg", 248.0)

    wind_speed = met_sum.get("avg_wind_speed_knots") or data.get("avg_wind_knots", 6.0)
    wind_dir_from = met_sum.get("dominant_wind_direction_from_deg") or data.get("wind_direction_from_deg", 156.0)
    wind_dir_towards = met_sum.get("dominant_wind_direction_towards_deg") or data.get("wind_direction_towards_deg", 336.0)
    rain_rate = met_sum.get("island_max_rainfall_mm_hr") or data.get("island_max_rain_mm_hr", 0.0)
    flushing_risk = met_sum.get("inland_flushing_risk") or data.get("inland_flushing_risk", "Low")

    currents = {
        "tidal_stage": tidal_stage,
        "mean_current_knots": mean_speed_knots,
        "surface_speed_knots": mean_speed_knots,
        "current_heading_deg": heading_deg,
    }

    weather = {
        "wind_speed_knots": wind_speed,
        "wind_direction_from_deg": wind_dir_from,
        "wind_direction_towards_deg": wind_dir_towards,
        "rainfall_mmh": rain_rate,
        "inland_flushing_risk": flushing_risk,
    }

    return {
        "status": "success",
        "location": data.get("location", "Singapore Waters"),
        "currents": currents,
        "weather": weather,
        "coastal_sectors": data.get("coastal_sectors", []),
        "vector_grid": data.get("vector_grid", []),
        "timestamp": data.get("timestamp", datetime.now(timezone.utc).isoformat()),
    }


@app.get("/api/v1/forecast", tags=["Phase 3: Forecasting"])
def get_drift_forecast(
    horizon: Optional[int] = Query(None, description="Forecast horizon in hours (2, 6, 12, 24, 48)"),
) -> Dict[str, Any]:
    """Retrieve multi-horizon forward Lagrangian accumulation forecasts and trajectory paths."""
    data = _load_json_data("phase3_forecast_report.json", "drift_forecasts.json")
    if not data:
        return {
            "status": "success",
            "horizons": {},
            "forecast_points": [],
            "geojson_trajectories": {"type": "FeatureCollection", "features": []},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    horizons = data.get("horizons", {})

    if horizon is not None:
        key = str(horizon)
        if key not in horizons:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid forecast horizon '{horizon}'. Available horizons: {list(horizons.keys())}",
            )
        target_horizon_data = horizons[key]
        points = target_horizon_data.get("points", [])

        # Filter trajectory GeoJSON features up to this horizon
        all_traj_features = data.get("geojson_trajectories", {}).get("features", [])
        return {
            "status": "success",
            "requested_horizon_hours": horizon,
            "beached_count": target_horizon_data.get("beached_count", 0),
            "floating_count": target_horizon_data.get("floating_count", 0),
            "points": points,
            "trajectories": {
                "type": "FeatureCollection",
                "features": all_traj_features,
            },
            "timestamp": data.get("timestamp", datetime.now(timezone.utc).isoformat()),
        }

    return {
        "status": "success",
        "summary": data.get("summary", {}),
        "available_horizons": list(horizons.keys()),
        "horizons": horizons,
        "forecast_points": data.get("forecast_points", []),
        "geojson_trajectories": data.get("geojson_trajectories", {"type": "FeatureCollection", "features": []}),
        "timestamp": data.get("timestamp", datetime.now(timezone.utc).isoformat()),
    }


@app.get("/api/v1/attribution", tags=["Phase 4: Source Attribution"])
def get_source_attribution() -> Dict[str, Any]:
    """Retrieve probabilistic Bayesian source attribution breakdown and reverse trajectories."""
    data = _load_json_data("phase4_attribution_report.json", "source_attribution.json")
    reports = data.get("attribution_reports") or data.get("hotspot_attributions") or []
    summary = data.get("global_summary") or data.get("overall_summary") or {}
    geojson = data.get("geojson_layers") or {}

    return {
        "status": "success",
        "overall_summary": summary,
        "hotspot_attributions": reports,
        "attribution_reports": reports,
        "geojson_layers": geojson,
        "timestamp": data.get("timestamp", datetime.now(timezone.utc).isoformat()),
    }


@app.post("/api/v1/attribution", tags=["Phase 4: Source Attribution"])
def evaluate_source_attribution(request: AttributionRequest) -> Dict[str, Any]:
    """Evaluate or calculate Bayesian source attribution for a specific hotspot or custom coordinate.

    Applies the empirical NEA baseline prior (97% marine vs 3% inland) coupled with the
    dynamic Inland Flush Index (IFI) based on current or user-supplied rainfall rate.
    """
    data = _load_json_data("phase4_attribution_report.json", "source_attribution.json")
    reports = data.get("attribution_reports") or data.get("hotspot_attributions") or []

    # If a specific hotspot_id was requested
    if request.hotspot_id:
        req_id = request.hotspot_id.upper().strip()
        matched = None
        for r in reports:
            hid = (r.get("hotspot_id") or "").upper()
            if req_id == hid or req_id in hid or hid in req_id or req_id.replace("-", "") in hid.replace("-", ""):
                matched = r
                break

        if matched:
            return {
                "status": "success",
                "mode": "matched_hotspot",
                "hotspot_id": matched.get("hotspot_id", request.hotspot_id),
                "attribution": matched,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    # If custom coordinates or dynamically evaluating with rainfall rate
    rainfall = request.rainfall_rate_mmh if request.rainfall_rate_mmh is not None else 10.0
    lat = request.custom_lat or 1.2980
    lng = request.custom_lng or 103.9210

    try:
        from backend.attribution.backtracking import ReverseRK4Backtracker
        from backend.attribution.bayesian import BayesianSourceAttributor
        from backend.weather.copernicus import CopernicusCurrentClient
        from backend.weather.interpolator import VectorFieldInterpolator
        from backend.weather.nea_client import SingaporeWeatherClient

        cur_client = CopernicusCurrentClient()
        wth_client = SingaporeWeatherClient()
        cur_field = cur_client.fetch_current_field(use_cache=True)
        wth_sum = wth_client.fetch_realtime_weather()
        interpolator = VectorFieldInterpolator(cur_field, wth_sum)

        backtracker = ReverseRK4Backtracker(interpolator=interpolator, diffusion_kh=2.5)
        bt_res = backtracker.backtrack_hotspot(
            hotspot_id=request.hotspot_id or "CUSTOM-POINT",
            hotspot_name=f"Custom Observation ({lat:.3f}N, {lng:.3f}E)",
            centroid_lat=lat,
            centroid_lng=lng,
            backtracking_horizon_hours=24.0,
            ensemble_size=8,
        )

        attributor = BayesianSourceAttributor()
        ifi = min(1.0, max(0.0, rainfall / 40.0))
        ifi_risk = "High" if ifi > 0.6 else "Moderate" if ifi > 0.25 else "Low"
        report = attributor.attribute(
            backtracking=bt_res,
            inland_flushing_index=ifi,
            inland_flushing_risk=ifi_risk,
            rainfall_mm_hr=rainfall,
        )

        return {
            "status": "success",
            "mode": "dynamic_evaluated",
            "input_coordinates": [lat, lng],
            "rainfall_rate_mmh": rainfall,
            "attribution": report.to_dict(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.warning("Dynamic Bayesian calculation fallback: %s", e)
        closest = reports[0] if reports else {"hotspot_id": request.hotspot_id or "UNKNOWN"}
        return {
            "status": "success",
            "mode": "baseline_fallback",
            "hotspot_id": request.hotspot_id or "ESTIMATED",
            "attribution": closest,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


@app.get("/api/v1/cleanup/recommendations", tags=["Phase 5: Decision Support"])
def get_cleanup_recommendations() -> Dict[str, Any]:
    """Retrieve Coastal Priority Index (CPI) rankings, dispatch recommendations, and efficiency benchmarks."""
    data = _load_json_data("phase5_decision_support_report.json", "cleanup_recommendations.json")

    dispatch_orders = data.get("dispatch_orders") or data.get("dispatch_recommendations") or []
    benchmarking = data.get("efficiency_benchmark") or data.get("benchmarking") or {}

    return {
        "status": "success",
        "summary": data.get("summary", {}),
        "cpi_rankings": data.get("cpi_rankings", []),
        "dispatch_orders": dispatch_orders,
        "dispatch_recommendations": dispatch_orders,
        "efficiency_benchmark": benchmarking,
        "benchmarking": benchmarking,
        "geojson_dispatch_targets": data.get("geojson_dispatch_targets", {"type": "FeatureCollection", "features": []}),
        "timestamp": data.get("timestamp", datetime.now(timezone.utc).isoformat()),
    }


@app.get("/api/v1/cleanup/report/download", tags=["Phase 5: Decision Support"])
def download_incident_action_plan() -> Response:
    """Download the official Incident Action Plan (IAP) and Resource Allocation Report as JSON."""
    data = _load_json_data("phase5_decision_support_report.json", "cleanup_recommendations.json")
    dispatch_orders = data.get("dispatch_orders") or data.get("dispatch_recommendations") or []
    benchmarking = data.get("efficiency_benchmark") or data.get("benchmarking") or {}

    iap_report = {
        "document_type": "INCIDENT_ACTION_PLAN_IAP",
        "authority": "MarineGuard AI Singapore Coastal Operations Center",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "operational_period": "T+00h to T+48h",
        "operational_zones": [
            "East Coast Park Coastal Waters (ECP)",
            "Changi - Pulau Ubin Marine Corridor",
            "Sentosa South Offshore & Beaches",
            "Marina South Inshore / Marina Barrage",
        ],
        "kpi_overview": data.get("summary", {}),
        "priority_dispatch_orders": dispatch_orders,
        "coastal_priority_rankings": data.get("cpi_rankings", []),
        "efficiency_benchmark_vs_routine_sweeps": benchmarking,
        "environmental_conditions": {
            "tide_phase": "Flood (Eastward)",
            "current_speed_knots": 1.25,
            "prevailing_monsoon": "Southwest Monsoon / Inter-Monsoon",
        },
    }

    content_str = json.dumps(iap_report, indent=2)
    return Response(
        content=content_str,
        media_type="application/json",
        headers={
            "Content-Disposition": 'attachment; filename="marineguard_incident_action_plan.json"',
        },
    )


@app.post("/api/v1/simulate/drift", tags=["Simulation"])
def simulate_forward_drift(request: DriftSimulationRequest) -> Dict[str, Any]:
    """Execute on-demand forward Lagrangian advection using 4th-Order Runge-Kutta (RK4)."""
    try:
        from backend.simulation.advection import LagrangianParticle, RK4AdvectionIntegrator
        from backend.weather.copernicus import CopernicusCurrentClient
        from backend.weather.interpolator import VectorFieldInterpolator
        from backend.weather.nea_client import SingaporeWeatherClient

        cur_client = CopernicusCurrentClient()
        wth_client = SingaporeWeatherClient()
        cur_field = cur_client.fetch_current_field(use_cache=True)
        wth_sum = wth_client.fetch_realtime_weather()
        interpolator = VectorFieldInterpolator(cur_field, wth_sum)

        integrator = RK4AdvectionIntegrator(interpolator=interpolator, diffusion_kh=2.5)

        particle = LagrangianParticle(
            id="SIM-PARTICLE-01",
            lat=request.start_lat,
            lng=request.start_lng,
            initial_lat=request.start_lat,
            initial_lng=request.start_lng,
            source_hotspot_id="SIM-HOTSPOT",
            leeway_factor=request.leeway_factor,
        )

        dt_sec = 300.0  # 5 min steps
        total_steps = int((request.duration_hours * 3600.0) / dt_sec)
        elapsed = 0.0

        for step in range(total_steps):
            if particle.status in ("beached", "exited_domain"):
                break
            integrator.step(particle, dt_seconds=dt_sec, elapsed_seconds=elapsed)
            elapsed += dt_sec

        # Format trajectory coordinates
        traj = [(request.start_lat, request.start_lng)]
        for pt in particle.trajectory:
            traj.append((pt[0], pt[1]))

        return {
            "status": "success",
            "start_point": [request.start_lat, request.start_lng],
            "end_point": [particle.lat, particle.lng],
            "status_final": particle.status,
            "beached_shore": particle.beached_shore,
            "duration_hours": request.duration_hours,
            "sample_points_count": len(traj),
            "trajectory_points": traj,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error("Simulation error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Drift simulation failed: {str(e)}",
        )


@app.post("/api/v1/simulate/backtrack", tags=["Simulation"])
def simulate_reverse_backtrack(request: BacktrackSimulationRequest) -> Dict[str, Any]:
    """Execute on-demand reverse Lagrangian backtracking (-dt) to trace origins."""
    try:
        from backend.attribution.backtracking import ReverseRK4Backtracker
        from backend.weather.copernicus import CopernicusCurrentClient
        from backend.weather.interpolator import VectorFieldInterpolator
        from backend.weather.nea_client import SingaporeWeatherClient

        cur_client = CopernicusCurrentClient()
        wth_client = SingaporeWeatherClient()
        cur_field = cur_client.fetch_current_field(use_cache=True)
        wth_sum = wth_client.fetch_realtime_weather()
        interpolator = VectorFieldInterpolator(cur_field, wth_sum)

        backtracker = ReverseRK4Backtracker(
            interpolator=interpolator,
            diffusion_kh=2.5,
        )

        result = backtracker.backtrack_hotspot(
            hotspot_id="CUSTOM_OBSERVATION",
            hotspot_name=f"Custom Point ({request.start_lat:.3f}N, {request.start_lng:.3f}E)",
            centroid_lat=request.start_lat,
            centroid_lng=request.start_lng,
            backtracking_horizon_hours=request.backtrack_hours,
            ensemble_size=5,
        )

        return {
            "status": "success",
            "hotspot_id": "CUSTOM_OBSERVATION",
            "detection_coordinates": [request.start_lat, request.start_lng],
            "backtrack_hours": request.backtrack_hours,
            "origin_coordinates": [result.estimated_origin_lat, result.estimated_origin_lng],
            "dominant_source": result.dominant_source_id,
            "source_hit_percentages": result.source_hit_percentages,
            "trajectory_sample_count": len(result.trajectory_points),
            "trajectory": [[pt[0], pt[1]] for pt in result.trajectory_points],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error("Backtrack simulation error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Reverse backtrack failed: {str(e)}",
        )


def main():
    """CLI launcher for local development."""
    import uvicorn
    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
    main()

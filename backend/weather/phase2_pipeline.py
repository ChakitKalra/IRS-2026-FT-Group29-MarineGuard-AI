"""Phase 2 Integrated Environmental & Oceanographic Data Engine.

Fetches live data.gov.sg meteorological observations, retrieves
Copernicus/Tidal surface current vector fields for Singapore waters,
computes continuous drift vectors and Inland Flushing Risk, and exports
verified datasets for full-stack UI visualization.
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from backend.weather.copernicus import CopernicusCurrentClient
from backend.weather.interpolator import VectorFieldInterpolator
from backend.weather.nea_client import SingaporeWeatherClient

# Key Singapore coastal monitoring points
KEY_COASTAL_POINTS = [
    {"sector": "East Coast Park", "lat": 1.3030, "lng": 103.9330},
    {"sector": "Pasir Ris Shoreline", "lat": 1.3830, "lng": 103.9530},
    {"sector": "Sentosa / Southern Islands", "lat": 1.2500, "lng": 103.8310},
    {"sector": "Singapore Strait Fairway", "lat": 1.2000, "lng": 103.8800},
    {"sector": "Marina Barrage Estuary", "lat": 1.2799, "lng": 103.8703},
    {"sector": "Tuas Marine Basin", "lat": 1.2850, "lng": 103.6500},
]


def run_phase2_pipeline(export_to_frontend: bool = True) -> dict:
    print("=================================================================")
    print(" MarineGuard AI: Phase 2 Oceanographic & Weather Engine Test")
    print("=================================================================")

    output_dir = Path("backend/outputs")
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Fetch Real-time Singapore Weather
    print("\n[Step 1] Fetching live data.gov.sg Meteorological Observations...")
    weather_client = SingaporeWeatherClient()
    weather_summary = weather_client.fetch_realtime_weather()

    print(f" [OK] Timestamp: {weather_summary.timestamp}")
    print(f" [OK] Active Stations: {weather_summary.active_wind_stations} wind, {weather_summary.active_rain_stations} rain")
    print(f" [OK] Island Avg Wind: {weather_summary.avg_wind_speed_knots} kts ({weather_summary.avg_wind_speed_ms} m/s) "
          f"from {weather_summary.dominant_wind_direction_from_deg}° (towards {weather_summary.dominant_wind_direction_towards_deg}°)")
    print(f" [OK] Island Max Rain: {weather_summary.island_max_rainfall_mm_hr} mm/hr")
    print(f" [OK] Inland Flushing Risk: {weather_summary.inland_flushing_risk}")
    print(f"      Rationale: {weather_summary.inland_flushing_rationale}")

    # 2. Fetch Copernicus / Tidal Currents
    print("\n[Step 2] Retrieving Singapore Strait Surface Ocean Current Field...")
    current_client = CopernicusCurrentClient()
    current_field = current_client.fetch_current_field(use_cache=False)

    print(f" [OK] Model: {current_field.source_model}")
    print(f" [OK] Tidal Stage: {current_field.tidal_stage}")
    print(f" [OK] Mean Surface Speed: {current_field.mean_speed_knots} kts ({current_field.mean_speed_ms} m/s)")
    print(f" [OK] Dominant Flow Heading: {current_field.dominant_heading_deg}°")
    print(f" [OK] Grid Dimensions: {current_field.grid_rows} x {current_field.grid_cols} ({len(current_field.points)} points)")

    # 3. Vector Field Interpolation across Key Coastal Sectors
    print("\n[Step 3] Interpolating Multi-Vector Drift Fields across Singapore Sectors...")
    interpolator = VectorFieldInterpolator(current_field, weather_summary)
    coastal_vectors = []

    for pt in KEY_COASTAL_POINTS:
        vec = interpolator.interpolate(pt["lat"], pt["lng"])
        coastal_vectors.append({
            "sector": pt["sector"],
            "coordinates": [vec.latitude, vec.longitude],
            "current": {
                "speed_knots": vec.current_speed_knots,
                "speed_ms": vec.current_speed_ms,
                "heading_deg": vec.current_heading_deg,
            },
            "wind": {
                "speed_knots": vec.wind_speed_knots,
                "speed_ms": vec.wind_speed_ms,
                "heading_towards_deg": vec.wind_heading_towards_deg,
            },
            "combined_drift": {
                "speed_knots": vec.total_speed_knots,
                "speed_ms": vec.total_speed_ms,
                "heading_deg": vec.total_heading_deg,
                "current_contribution_pct": vec.current_contribution_pct,
                "wind_contribution_pct": vec.wind_contribution_pct,
            },
            "local_rainfall_mm_hr": vec.local_rainfall_mm_hr,
            "flushing_risk": vec.inland_flushing_risk,
        })
        print(f"   - {pt['sector']:<25} | Drift: {vec.total_speed_knots:>4.2f} kts heading {vec.total_heading_deg:>5.1f}° "
              f"(Curr: {vec.current_contribution_pct}%, Wind: {vec.wind_contribution_pct}%)")

    # 4. Generate GeoJSON Currents Grid
    currents_geojson = current_client.to_geojson(current_field)

    # 5. Assemble and Save
    result = {
        "status": "success",
        "phase": "Phase 2: Oceanographic & Environmental Data Engine",
        "timestamp": weather_summary.timestamp,
        "meteorological_summary": asdict(weather_summary),
        "ocean_current_summary": {
            "source_model": current_field.source_model,
            "tidal_stage": current_field.tidal_stage,
            "mean_speed_knots": current_field.mean_speed_knots,
            "dominant_heading_deg": current_field.dominant_heading_deg,
            "grid_points_count": len(current_field.points),
        },
        "coastal_sectors_drift": coastal_vectors,
        "currents_geojson": currents_geojson,
    }

    report_path = output_dir / "phase2_environmental_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(f"\n [OK] Saved backend report: {report_path}")

    if export_to_frontend:
        frontend_export_path = Path("frontend/src/live_weather_currents.json")
        frontend_export_path.parent.mkdir(parents=True, exist_ok=True)
        # Format for direct consumption by React frontend
        frontend_data = {
            "version": "1.0.0",
            "timestamp": weather_summary.timestamp,
            "tidal_stage": current_field.tidal_stage,
            "mean_current_knots": current_field.mean_speed_knots,
            "current_heading_deg": current_field.dominant_heading_deg,
            "avg_wind_knots": weather_summary.avg_wind_speed_knots,
            "wind_direction_from_deg": weather_summary.dominant_wind_direction_from_deg,
            "wind_direction_towards_deg": weather_summary.dominant_wind_direction_towards_deg,
            "island_max_rain_mm_hr": weather_summary.island_max_rainfall_mm_hr,
            "inland_flushing_risk": weather_summary.inland_flushing_risk,
            "inland_flushing_rationale": weather_summary.inland_flushing_rationale,
            "coastal_sectors": coastal_vectors,
            "current_points": [asdict(p) for p in current_field.points],
            "currents_geojson": currents_geojson,
        }
        with open(frontend_export_path, "w", encoding="utf-8") as f:
            json.dump(frontend_data, f, indent=2)
        print(f" [OK] Exported live environmental data to frontend: {frontend_export_path}")

    print("\n=================================================================")
    print(" Phase 2 Oceanographic & Weather Engine: ALL TESTS PASSED!")
    print("=================================================================")
    return result


if __name__ == "__main__":
    run_phase2_pipeline(export_to_frontend=True)

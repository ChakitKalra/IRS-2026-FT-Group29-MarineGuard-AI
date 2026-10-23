"""Phase 4 Integrated Probabilistic Source Attribution Pipeline.

Ingests Phase 1 detected hotspots and Phase 2 environmental fields,
executes reverse Lagrangian backtracking (-dt) using 4th-order Runge-Kutta integration,
evaluates trajectory intersections with candidate source domain polygons,
and applies Bayesian classification conditioned on the NEA 97%/3% prior and real-time IFI.
Exports verified source attribution datasets for the interactive dashboard.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from backend.attribution.backtracking import ReverseRK4Backtracker
from backend.attribution.bayesian import BayesianSourceAttributor
from backend.attribution.sources import SOURCE_DOMAINS, get_source_domains_geojson
from backend.weather.copernicus import CopernicusCurrentClient
from backend.weather.interpolator import VectorFieldInterpolator
from backend.weather.nea_client import SingaporeWeatherClient


def run_phase4_pipeline(export_to_frontend: bool = True) -> Dict[str, Any]:
    print("=================================================================")
    print(" MarineGuard AI: Phase 4 Probabilistic Source Attribution Engine")
    print("=================================================================")

    output_dir = Path("backend/outputs")
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Load Hotspots from Phase 1
    print("\n[Step 1] Loading Phase 1 Coastal Hotspots for Attribution...")
    hotspots_path = Path("frontend/src/detected_hotspots.json")
    if hotspots_path.exists():
        data = json.loads(hotspots_path.read_text(encoding="utf-8"))
        hotspots = data.get("hotspots", [])
    else:
        hotspots = [
            {"id": "HS-EAST-01", "name": "East Coast Marine Hotspot", "centroid_lat": 1.3050, "centroid_lng": 103.9420, "radius_meters": 150.0, "items_count": 324, "sector_id": "east_coast"},
            {"id": "HS-EAST-02", "name": "Bedok Coastal Hotspot", "centroid_lat": 1.3025, "centroid_lng": 103.9288, "radius_meters": 120.0, "items_count": 2, "sector_id": "east_coast"},
            {"id": "HS-PASI-03", "name": "Pasir Ris Beach Hotspot", "centroid_lat": 1.3815, "centroid_lng": 103.9532, "radius_meters": 120.0, "items_count": 4, "sector_id": "pasir_ris_changi"},
            {"id": "HS-SOUT-04", "name": "Sentosa Coastal Hotspot", "centroid_lat": 1.2512, "centroid_lng": 103.8290, "radius_meters": 120.0, "items_count": 2, "sector_id": "southern_islands"},
        ]
    print(f" [OK] Loaded {len(hotspots)} coastal hotspots to attribute.")

    # 2. Ingest Environmental Data from Phase 2
    print("\n[Step 2] Initializing Hydrodynamic & Meteorological Interpolator...")
    cur_client = CopernicusCurrentClient()
    wth_client = SingaporeWeatherClient()
    current_field = cur_client.fetch_current_field(use_cache=True)
    weather_summary = wth_client.fetch_realtime_weather()
    interpolator = VectorFieldInterpolator(current_field, weather_summary, default_leeway_factor=0.02)
    ifi_risk = weather_summary.inland_flushing_risk
    rain_rate = weather_summary.island_max_rainfall_mm_hr
    # Inland Flushing Index: normalized 0.0 to 1.0 based on rainfall intensity & risk level
    ifi = min(1.0, max(0.0, rain_rate / 20.0))
    if ifi_risk == "Severe":
        ifi = max(ifi, 0.85)
    elif ifi_risk == "High":
        ifi = max(ifi, 0.60)
    elif ifi_risk == "Moderate":
        ifi = max(ifi, 0.35)
    print(f" [OK] Environmental Context: IFI = {ifi:.2f} ({ifi_risk} Risk), Rain = {rain_rate:.1f} mm/hr")

    # 3. Initialize Backtracker and Bayesian Attributor
    print("\n[Step 3] Initializing Reverse Lagrangian Integrator & Bayesian Engine...")
    backtracker = ReverseRK4Backtracker(interpolator, diffusion_kh=2.5)
    attributor = BayesianSourceAttributor(base_marine_prior=0.97, base_inland_prior=0.03)

    attribution_reports: List[Dict[str, Any]] = []
    trajectory_features: List[Dict[str, Any]] = []
    origin_features: List[Dict[str, Any]] = []

    print("\n[Step 4] Running Reverse Backtracking (-48h) and Bayesian Classification...")
    for hs in hotspots:
        hs_id = hs.get("hotspot_id") or hs.get("id", "UNKNOWN")
        hs_name = hs.get("name", hs_id)
        c_lat = float(hs.get("centroid_lat", 1.30))
        c_lng = float(hs.get("centroid_lng", 103.85))

        # Run reverse ensemble backtracking
        bt_res = backtracker.backtrack_hotspot(
            hotspot_id=hs_id,
            hotspot_name=hs_name,
            centroid_lat=c_lat,
            centroid_lng=c_lng,
            backtracking_horizon_hours=48.0,
            ensemble_size=40,
            dt_seconds=300.0,
        )

        # Run Bayesian attribution
        report = attributor.attribute(
            backtracking=bt_res,
            inland_flushing_index=ifi,
            inland_flushing_risk=ifi_risk,
            rainfall_mm_hr=rain_rate,
        )

        report_dict = report.to_dict()
        attribution_reports.append(report_dict)
        trajectory_features.append(bt_res.geojson_trajectory)
        origin_features.append(bt_res.geojson_origin_marker)

        top_src = report.top_source_name
        top_pct = report.top_source_percentage
        print(f"   * [{hs_id}] {hs_name}")
        print(f"     Origin: ({report.estimated_origin_lat:.4f}, {report.estimated_origin_lng:.4f}) released ~{report.estimated_release_hours_ago:.1f}h ago")
        print(f"     Top Source: {top_src} ({top_pct}% | {report.top_source_confidence} Confidence)")
        print(f"     Split: {report.total_marine_transboundary_pct}% Marine vs {report.total_inland_local_pct}% Inland")

    # Aggregate global statistics across all hotspots
    global_source_totals: Dict[str, float] = {k: 0.0 for k in SOURCE_DOMAINS.keys()}
    for rep in attribution_reports:
        for b in rep["breakdown"]:
            global_source_totals[b["source_id"]] += b["percentage"]

    num_hs = max(len(attribution_reports), 1)
    global_source_averages = {
        k: round(v / num_hs, 1) for k, v in global_source_totals.items()
    }
    dominant_global_source_id = max(global_source_averages, key=global_source_averages.get)
    dominant_global_source_name = SOURCE_DOMAINS[dominant_global_source_id].name

    global_marine_avg = round(sum(
        rep["classification"]["total_marine_transboundary_pct"] for rep in attribution_reports
    ) / num_hs, 1)
    global_inland_avg = round(sum(
        rep["classification"]["total_inland_local_pct"] for rep in attribution_reports
    ) / num_hs, 1)

    # 5. Build GeoJSON Layers
    source_domains_geojson = get_source_domains_geojson()
    backtracking_trajectories_geojson = {
        "type": "FeatureCollection",
        "features": trajectory_features,
    }
    origin_markers_geojson = {
        "type": "FeatureCollection",
        "features": origin_features,
    }

    pipeline_result = {
        "status": "success",
        "phase": "Phase 4: Probabilistic Source Attribution Engine",
        "methodology": {
            "backtracking_integrator": "Reverse 4th-Order Runge-Kutta (-dt = -300s)",
            "ensemble_size_per_hotspot": 40,
            "backtracking_horizon_hours": 48.0,
            "prior_formulation": "Bayesian with NEA Baseline (97% Marine / 3% Inland) + Dynamic IFI Coupling",
            "candidate_source_domains": len(SOURCE_DOMAINS),
        },
        "environmental_context": {
            "inland_flushing_index": round(ifi, 3),
            "inland_flushing_risk": ifi_risk,
            "max_rainfall_rate_mm_hr": rain_rate,
        },
        "global_summary": {
            "total_hotspots_attributed": len(hotspots),
            "dominant_source_id": dominant_global_source_id,
            "dominant_source_name": dominant_global_source_name,
            "dominant_source_average_pct": global_source_averages[dominant_global_source_id],
            "average_marine_transboundary_pct": global_marine_avg,
            "average_inland_local_pct": global_inland_avg,
            "domain_averages": global_source_averages,
        },
        "attribution_reports": attribution_reports,
        "geojson_layers": {
            "source_domains": source_domains_geojson,
            "backtracking_trajectories": backtracking_trajectories_geojson,
            "origin_markers": origin_markers_geojson,
        },
    }

    # Save backend output
    report_path = output_dir / "phase4_attribution_report.json"
    report_path.write_text(json.dumps(pipeline_result, indent=2), encoding="utf-8")
    print(f"\n[Step 5] Backend attribution report saved to: {report_path}")

    # Export to frontend if requested
    if export_to_frontend:
        frontend_path = Path("frontend/src/source_attribution.json")
        frontend_path.write_text(json.dumps(pipeline_result, indent=2), encoding="utf-8")
        print(f" [OK] Exported source attribution dataset to: {frontend_path}")

    print("\n=================================================================")
    print(" [SUCCESS] Phase 4 Source Attribution Engine Completed Successfully!")
    print("=================================================================")
    return pipeline_result


if __name__ == "__main__":
    run_phase4_pipeline(export_to_frontend=True)

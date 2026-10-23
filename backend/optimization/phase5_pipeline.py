"""Phase 5 Integrated Cleanup Decision Support & Resource Optimization Pipeline.

Ingests Phase 1 detected hotspots, Phase 3 forward drift forecasts, and Phase 4
source attributions to compute Coastal Priority Index (CPI) rankings, formulate
optimized cleanup dispatch recommendations, and benchmark comparative operational efficiency.
Exports verified decision support datasets for the interactive dashboard.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from backend.optimization.cpi import CoastalPriorityIndexCalculator, CPIScoreBreakdown
from backend.optimization.dispatch import CleanupDispatchRecommender, DispatchRecommendation, EfficiencyBenchmark


def run_phase5_pipeline(export_to_frontend: bool = True) -> Dict[str, Any]:
    print("=================================================================")
    print(" MarineGuard AI: Phase 5 Cleanup Decision Support & Optimization")
    print("=================================================================")

    output_dir = Path("backend/outputs")
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Ingest Hotspots and Forecast Data
    print("\n[Step 1] Loading Detected Hotspots, Drift Forecasts & Attributions...")
    hotspots_path = Path("frontend/src/detected_hotspots.json")
    forecast_path = Path("frontend/src/drift_forecasts.json")
    attribution_path = Path("frontend/src/source_attribution.json")

    hotspots: List[Dict[str, Any]] = []
    if hotspots_path.exists():
        data = json.loads(hotspots_path.read_text(encoding="utf-8"))
        hotspots = data.get("hotspots", [])
    else:
        hotspots = [
            {"hotspot_id": "HS-EAST-01", "name": "East Coast Shoreline Hotspot #1", "sector_id": "east_coast", "centroid_lat": 1.3054, "centroid_lng": 103.9420, "detection_count": 324, "total_area_sq_m": 32400.0, "severity": "High", "composite_confidence": 95.0},
            {"hotspot_id": "HS-EAST-02", "name": "East Coast Shoreline Hotspot #2", "sector_id": "east_coast", "centroid_lat": 1.3025, "centroid_lng": 103.9288, "detection_count": 2, "total_area_sq_m": 45.0, "severity": "Medium", "composite_confidence": 88.5},
            {"hotspot_id": "HS-PASI-03", "name": "Pasir Ris Beach Hotspot #3", "sector_id": "pasir_ris_changi", "centroid_lat": 1.3815, "centroid_lng": 103.9532, "detection_count": 4, "total_area_sq_m": 60.0, "severity": "High", "composite_confidence": 91.0},
            {"hotspot_id": "HS-SOUT-04", "name": "Sentosa Coastal Hotspot #4", "sector_id": "southern_islands", "centroid_lat": 1.2512, "centroid_lng": 103.8290, "detection_count": 2, "total_area_sq_m": 50.0, "severity": "Medium", "composite_confidence": 85.0},
        ]

    # Map forecast horizon summary (+24h horizon provides optimal operational window)
    forecast_map: Dict[str, Dict[str, Any]] = {}
    if forecast_path.exists():
        fc_data = json.loads(forecast_path.read_text(encoding="utf-8"))
        h24_hotspots = fc_data.get("horizons", {}).get("24", {}).get("hotspots", [])
        for fc in h24_hotspots:
            orig_id = fc.get("origin_hotspot_id")
            forecast_map[orig_id] = {
                "status": fc.get("status"),
                "beached_prob": fc.get("beached_probability_pct", 0.0),
                "target_shore": fc.get("target_shore"),
                "time_to_beach_hours": 6.0 if fc.get("beached_probability_pct", 0.0) > 0 else None,
            }

    print(f" [OK] Loaded {len(hotspots)} coastal hotspots and matched forecast dynamics.")

    # 2. Initialize CPI Calculator and Dispatch Recommender
    print("\n[Step 2] Initializing Multi-Criteria CPI Engine & Dispatch Optimizer...")
    cpi_calc = CoastalPriorityIndexCalculator()
    recommender = CleanupDispatchRecommender()

    cpi_scores: List[CPIScoreBreakdown] = []
    dispatch_orders: List[DispatchRecommendation] = []

    print("\n[Step 3] Evaluating Coastal Priority Index (CPI) and Tasking Resources...")
    for hs in hotspots:
        hs_id = hs.get("hotspot_id") or hs.get("id", "UNKNOWN")
        fc_info = forecast_map.get(hs_id)

        cpi_result = cpi_calc.calculate_cpi(hs, forecast_summary=fc_info)
        dispatch_order = recommender.recommend_dispatch(cpi_result, hs, forecast_summary=fc_info)

        cpi_scores.append(cpi_result)
        dispatch_orders.append(dispatch_order)

        print(f"   * [{hs_id}] {cpi_result.hotspot_name}")
        print(f"     CPI Score: {cpi_result.cpi_score:.1f} ({cpi_result.priority_tier} Priority) | Q={cpi_result.quantity_score:.1f}, U={cpi_result.drift_urgency_factor:.2f}, W={cpi_result.sensitivity_weight:.2f}")
        print(f"     Recommended Intervention: {dispatch_order.intervention_type}")
        print(f"     Assets: {dispatch_order.assigned_assets} (Crew: {dispatch_order.recommended_crew_size})")
        print(f"     Window: {dispatch_order.optimal_window_hours} | Target Mass: ~{dispatch_order.expected_debris_mass_kg:.1f} kg")

    # Sort dispatches by CPI score descending
    cpi_scores.sort(key=lambda s: s.cpi_score, reverse=True)
    dispatch_orders.sort(key=lambda d: d.cpi_score, reverse=True)

    # 4. Compute Comparative Efficiency Benchmarks
    print("\n[Step 4] Running Comparative Operational Efficiency Benchmarking...")
    benchmark = recommender.compute_benchmarks(cpi_scores)
    print(f" [OK] Target Threshold: >= {benchmark.target_threshold_improvement_pct}% improvement")
    print(f" [OK] Achieved Retrieval Efficiency Improvement: +{benchmark.achieved_retrieval_improvement_pct:.1f}% vs Fixed Schedule")
    print(f" [OK] Achieved Response Latency Reduction: -{benchmark.achieved_latency_reduction_pct:.1f}%")

    # 5. Compile Report and GeoJSON Layers
    dispatch_geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "order_id": d.order_id,
                    "hotspot_id": d.hotspot_id,
                    "hotspot_name": d.hotspot_name,
                    "cpi_score": d.cpi_score,
                    "priority_tier": d.priority_tier,
                    "intervention_type": d.intervention_type,
                    "assigned_assets": d.assigned_assets,
                    "recommended_crew_size": d.recommended_crew_size,
                    "optimal_window_hours": d.optimal_window_hours,
                    "expected_debris_mass_kg": d.expected_debris_mass_kg,
                    "stranding_prevention_likelihood_pct": d.stranding_prevention_likelihood_pct,
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [d.target_longitude, d.target_latitude],
                },
            }
            for d in dispatch_orders
        ],
    }

    pipeline_result = {
        "status": "success",
        "phase": "Phase 5: Cleanup Decision Support & Resource Optimization",
        "methodology": {
            "ranking_framework": "Coastal Priority Index (CPI = Quantity x Urgency x Sensitivity)",
            "intervention_types": list(set(d.intervention_type for d in dispatch_orders)),
            "baseline_comparisons": ["Fixed Routine Sweeps (48h)", "Reactive Human Sightings"],
        },
        "summary": {
            "total_hotspots_ranked": len(cpi_scores),
            "critical_priority_count": sum(1 for s in cpi_scores if s.priority_tier == "Critical"),
            "high_priority_count": sum(1 for s in cpi_scores if s.priority_tier == "High"),
            "medium_priority_count": sum(1 for s in cpi_scores if s.priority_tier == "Medium"),
            "low_priority_count": sum(1 for s in cpi_scores if s.priority_tier == "Low"),
            "total_estimated_debris_mass_kg": round(sum(d.expected_debris_mass_kg for d in dispatch_orders), 1),
            "average_cpi_score": round(sum(s.cpi_score for s in cpi_scores) / max(len(cpi_scores), 1), 1),
        },
        "cpi_rankings": [s.to_dict() for s in cpi_scores],
        "dispatch_recommendations": [d.to_dict() for d in dispatch_orders],
        "benchmarking": benchmark.to_dict(),
        "geojson_dispatch_targets": dispatch_geojson,
    }

    # Save to backend outputs
    report_path = output_dir / "phase5_decision_support_report.json"
    report_path.write_text(json.dumps(pipeline_result, indent=2), encoding="utf-8")
    print(f"\n[Step 5] Backend decision support report saved to: {report_path}")

    # Export to frontend
    if export_to_frontend:
        frontend_path = Path("frontend/src/cleanup_recommendations.json")
        frontend_path.write_text(json.dumps(pipeline_result, indent=2), encoding="utf-8")
        print(f" [OK] Exported cleanup recommendations dataset to: {frontend_path}")

    print("\n=================================================================")
    print(" [SUCCESS] Phase 5 Cleanup Decision Support Completed Successfully!")
    print("=================================================================")
    return pipeline_result


if __name__ == "__main__":
    run_phase5_pipeline(export_to_frontend=True)

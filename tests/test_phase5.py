"""Unit and Integration Tests for Phase 5: Cleanup Decision Support & Resource Optimization."""

import unittest

from backend.optimization.cpi import CoastalPriorityIndexCalculator, SECTOR_SENSITIVITY_WEIGHTS
from backend.optimization.dispatch import (
    CleanupDispatchRecommender,
    InterventionType,
)


class TestPhase5CleanupOptimization(unittest.TestCase):
    def setUp(self):
        self.cpi_calc = CoastalPriorityIndexCalculator()
        self.recommender = CleanupDispatchRecommender()

    def test_cpi_calculation_components(self):
        """Test multi-criteria CPI components: Quantity, Urgency, and Sensitivity."""
        # 1. Quantity score test
        q_high = self.cpi_calc.compute_quantity_score(
            detection_count=324,
            total_area_sq_m=32400.0,
            composite_confidence=95.0,
            severity="High",
        )
        q_low = self.cpi_calc.compute_quantity_score(
            detection_count=2,
            total_area_sq_m=30.0,
            composite_confidence=75.0,
            severity="Low",
        )
        self.assertGreater(q_high, q_low)
        self.assertGreaterEqual(q_high, 50.0)

        # 2. Urgency multiplier test
        urg_imminent, dead_imminent = self.cpi_calc.compute_drift_urgency(
            beached_probability_pct=85.0,
            time_to_beach_hours=1.5,
        )
        urg_openwater, dead_openwater = self.cpi_calc.compute_drift_urgency(
            beached_probability_pct=5.0,
            time_to_beach_hours=None,
        )
        self.assertEqual(urg_imminent, 1.50)
        self.assertEqual(urg_openwater, 0.70)
        self.assertLess(dead_imminent, dead_openwater)

        # 3. Sensitivity weights
        self.assertEqual(SECTOR_SENSITIVITY_WEIGHTS["east_coast"]["weight"], 1.40)
        self.assertEqual(SECTOR_SENSITIVITY_WEIGHTS["pulau_ubin_sungei_buloh"]["weight"], 1.50)

        # 4. Full CPI calculation on sample hotspot
        sample_hs = {
            "hotspot_id": "TEST-ECP-01",
            "name": "East Coast Park Test Hotspot",
            "sector_id": "east_coast",
            "detection_count": 250,
            "total_area_sq_m": 25000.0,
            "composite_confidence": 92.0,
            "severity": "High",
        }
        fc_info = {
            "status": "Floating Plume",
            "beached_prob": 70.0,
            "target_shore": "East Coast Park (ECP)",
            "time_to_beach_hours": 3.0,
        }
        cpi_res = self.cpi_calc.calculate_cpi(sample_hs, forecast_summary=fc_info)
        self.assertGreaterEqual(cpi_res.cpi_score, 50.0)
        self.assertIn(cpi_res.priority_tier, ["Critical", "High"])
        self.assertEqual(cpi_res.sector_id, "east_coast")

    def test_dispatch_recommendation_logic(self):
        """Test dispatch recommender produces appropriate intervention types and resources."""
        # Case A: Imminent stranding / beached -> Beach Sweep Crew
        cpi_beached = self.cpi_calc.calculate_cpi(
            {
                "hotspot_id": "TEST-HS-BEACHED",
                "name": "Sentosa Beached Hotspot",
                "sector_id": "southern_islands",
                "detection_count": 80,
                "total_area_sq_m": 500.0,
            },
            forecast_summary={"status": "Beached Accumulation", "beached_prob": 90.0, "target_shore": "Sentosa Beach"},
        )
        dispatch_beached = self.recommender.recommend_dispatch(
            cpi_beached,
            {"centroid_lat": 1.250, "centroid_lng": 103.830, "detection_count": 80, "total_area_sq_m": 500.0},
        )
        self.assertEqual(dispatch_beached.intervention_type, InterventionType.BEACH_SWEEP_CREW.value)
        self.assertGreaterEqual(dispatch_beached.recommended_crew_size, 4)
        self.assertGreater(dispatch_beached.expected_debris_mass_kg, 10.0)

        # Case B: Floating in offshore fairway -> Scavenger Vessel Intercept
        cpi_floating = self.cpi_calc.calculate_cpi(
            {
                "hotspot_id": "TEST-HS-FLOAT",
                "name": "Singapore Strait Offshore Hotspot",
                "sector_id": "singapore_strait_deep",
                "detection_count": 150,
                "total_area_sq_m": 12000.0,
            },
            forecast_summary={"status": "Floating Plume", "beached_prob": 10.0},
        )
        dispatch_floating = self.recommender.recommend_dispatch(
            cpi_floating,
            {"centroid_lat": 1.180, "centroid_lng": 103.750, "detection_count": 150, "total_area_sq_m": 12000.0},
        )
        self.assertEqual(dispatch_floating.intervention_type, InterventionType.VESSEL_INTERCEPT.value)
        self.assertTrue(dispatch_floating.order_id.startswith("DSP-"))

    def test_comparative_efficiency_benchmarks(self):
        """Verify efficiency benchmark against fixed schedule and reactive baselines."""
        cpi_list = [
            self.cpi_calc.calculate_cpi({"hotspot_id": "HS-1", "detection_count": 100, "total_area_sq_m": 5000}),
            self.cpi_calc.calculate_cpi({"hotspot_id": "HS-2", "detection_count": 50, "total_area_sq_m": 2000}),
        ]
        benchmark = self.recommender.compute_benchmarks(cpi_list)

        # Must meet target threshold of >= 30% improvement over fixed schedule
        self.assertGreaterEqual(benchmark.achieved_retrieval_improvement_pct, 30.0)
        self.assertGreaterEqual(benchmark.achieved_latency_reduction_pct, 50.0)

        # Validate strategy comparison metrics
        ai_strat = benchmark.strategies["marineguard_ai"]
        fixed_strat = benchmark.strategies["baseline_fixed_schedule"]
        self.assertGreater(ai_strat.debris_retrieval_rate_kg_per_hour, fixed_strat.debris_retrieval_rate_kg_per_hour)
        self.assertLess(ai_strat.average_response_latency_hours, fixed_strat.average_response_latency_hours)


if __name__ == "__main__":
    unittest.main()

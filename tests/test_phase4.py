"""Unit and Integration Tests for Phase 4: Probabilistic Source Attribution Engine."""

import unittest
from shapely.geometry import Point

from backend.attribution.backtracking import ReverseRK4Backtracker, BackwardParticle
from backend.attribution.bayesian import BayesianSourceAttributor
from backend.attribution.sources import SOURCE_DOMAINS, find_containing_source, get_source_domains_geojson
from backend.weather.copernicus import CopernicusCurrentClient
from backend.weather.interpolator import VectorFieldInterpolator
from backend.weather.nea_client import SingaporeWeatherClient


class TestPhase4SourceAttribution(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Initialize environmental interpolator with cached hydrodynamic baseline
        cur_client = CopernicusCurrentClient()
        wth_client = SingaporeWeatherClient()
        cls.current_field = cur_client.fetch_current_field(use_cache=True)
        cls.weather_summary = wth_client.fetch_realtime_weather()
        cls.interpolator = VectorFieldInterpolator(cls.current_field, cls.weather_summary)

    def test_source_domain_geometry_and_boundaries(self):
        """Verify candidate source domain polygons and point containment."""
        self.assertEqual(len(SOURCE_DOMAINS), 5)

        # Check domain ids
        expected_ids = {"marine_traffic", "johor_strait", "transboundary_riau", "inland_canals", "recreational_beachgoers"}
        self.assertEqual(set(SOURCE_DOMAINS.keys()), expected_ids)

        # Test point in Singapore Strait shipping corridor
        shipping_pt = find_containing_source(1.160, 103.850)
        self.assertIsNotNone(shipping_pt)
        self.assertEqual(shipping_pt.id, "marine_traffic")

        # Test point in northern Johor Strait
        johor_pt = find_containing_source(1.440, 103.800)
        self.assertIsNotNone(johor_pt)
        self.assertEqual(johor_pt.id, "johor_strait")

        # Test point in southern Riau / Batam waters
        riau_pt = find_containing_source(1.100, 104.000)
        self.assertIsNotNone(riau_pt)
        self.assertEqual(riau_pt.id, "transboundary_riau")

        # Test GeoJSON serialization
        geojson = get_source_domains_geojson()
        self.assertEqual(geojson["type"], "FeatureCollection")
        self.assertEqual(len(geojson["features"]), 5)

    def test_reverse_rk4_backtracking_step(self):
        """Verify reverse RK4 velocity reversal and upstream displacement."""
        backtracker = ReverseRK4Backtracker(self.interpolator, diffusion_kh=0.0) # Zero diffusion for deterministic check

        test_lat, test_lng = 1.300, 103.920
        # Check forward velocity vs reverse velocity
        drift_fwd = self.interpolator.interpolate(test_lat, test_lng, leeway_factor=0.02)
        rev_u, rev_v = backtracker.get_reverse_velocity(test_lat, test_lng, leeway=0.02)

        self.assertAlmostEqual(drift_fwd.total_u_ms, -rev_u, places=3)
        self.assertAlmostEqual(drift_fwd.total_v_ms, -rev_v, places=3)

        # Step particle backward
        p = BackwardParticle(
            id="test_p1",
            lat=test_lat,
            lng=test_lng,
            initial_lat=test_lat,
            initial_lng=test_lng,
            leeway_factor=0.02,
        )
        stepped_p = backtracker.step_backward(p, dt_seconds=600.0, elapsed_seconds=0.0)

        # Should move in direction of (-u, -v)
        if drift_fwd.total_u_ms > 0:
            self.assertLess(stepped_p.lng, test_lng)
        elif drift_fwd.total_u_ms < 0:
            self.assertGreater(stepped_p.lng, test_lng)

    def test_hotspot_backtracking_and_bayesian_attribution(self):
        """Verify full backtracking ensemble and Bayesian attribution calculation."""
        backtracker = ReverseRK4Backtracker(self.interpolator, diffusion_kh=2.0)
        attributor = BayesianSourceAttributor(base_marine_prior=0.97, base_inland_prior=0.03)

        # 1. Test baseline priors in dry weather (IFI = 0.0)
        dry_priors = attributor.compute_priors(inland_flushing_index=0.0)
        marine_total = dry_priors["marine_traffic"] + dry_priors["transboundary_riau"] + dry_priors["johor_strait"]
        inland_total = dry_priors["inland_canals"] + dry_priors["recreational_beachgoers"]
        self.assertAlmostEqual(marine_total, 0.97, places=2)
        self.assertAlmostEqual(inland_total, 0.03, places=2)

        # 2. Test wet weather priors with heavy rainfall (IFI = 0.8)
        wet_priors = attributor.compute_priors(inland_flushing_index=0.8)
        self.assertGreater(wet_priors["inland_canals"], dry_priors["inland_canals"] * 5)

        # 3. Test ensemble backtracking of an East Coast hotspot
        bt_res = backtracker.backtrack_hotspot(
            hotspot_id="TEST-HS-ECP",
            hotspot_name="East Coast Test Hotspot",
            centroid_lat=1.305,
            centroid_lng=103.940,
            backtracking_horizon_hours=24.0,
            ensemble_size=20,
            dt_seconds=300.0,
        )

        self.assertEqual(bt_res.hotspot_id, "TEST-HS-ECP")
        self.assertEqual(bt_res.ensemble_size, 20)
        self.assertTrue(len(bt_res.trajectory_points) > 0)
        self.assertEqual(bt_res.geojson_trajectory["type"], "Feature")

        # 4. Attribute using Bayesian engine
        report = attributor.attribute(
            backtracking=bt_res,
            inland_flushing_index=0.05,
            inland_flushing_risk="Low",
            rainfall_mm_hr=0.0,
        )

        # Validate posterior normalization
        pct_sum = sum(e.percentage for e in report.attribution_breakdown)
        self.assertAlmostEqual(pct_sum, 100.0, delta=1.0)

        # Validate top source properties
        self.assertIn(report.top_source_id, SOURCE_DOMAINS)
        self.assertIn(report.top_source_confidence, ["High", "Moderate", "Fair"])
        self.assertTrue(len(report.operational_narrative) > 20)


if __name__ == "__main__":
    unittest.main()

"""Unit tests for MarineGuard AI Phase 3 Lagrangian Transport & Forecasting Engine."""

import unittest
from backend.simulation.advection import (
    LagrangianParticle,
    RK4AdvectionIntegrator,
    SINGAPORE_COASTAL_SHORES,
)
from backend.simulation.forecasting import DebrisDriftForecaster
from backend.weather.copernicus import CopernicusCurrentClient
from backend.weather.interpolator import VectorFieldInterpolator
from backend.weather.nea_client import SingaporeWeatherClient


class TestPhase3ForecastingEngine(unittest.TestCase):

    def setUp(self):
        cur_client = CopernicusCurrentClient()
        wth_client = SingaporeWeatherClient()
        self.current_field = cur_client.fetch_current_field()
        self.weather_summary = wth_client.fetch_realtime_weather()
        self.interpolator = VectorFieldInterpolator(self.current_field, self.weather_summary)

    def test_01_rk4_advection_step(self):
        """Test RK4 integrator single step advance and trajectory tracking."""
        integrator = RK4AdvectionIntegrator(self.interpolator, diffusion_kh=0.0)

        # Particle in deep open water (Singapore Strait Fairway: 1.20, 103.85)
        p = LagrangianParticle(
            id="TEST-P1",
            lat=1.2000,
            lng=103.8500,
            initial_lat=1.2000,
            initial_lng=103.8500,
            source_hotspot_id="TEST-HS",
            leeway_factor=0.02,
        )

        dt = 300.0 # 5 minutes
        p_stepped = integrator.step(p, dt_seconds=dt, elapsed_seconds=0.0)

        self.assertEqual(p_stepped.status, "active")
        self.assertGreater(len(p_stepped.trajectory), 0)
        # Verify displacement occurred
        self.assertTrue(p_stepped.lat != 1.2000 or p_stepped.lng != 103.8500)

    def test_02_shoreline_collision_and_beaching(self):
        """Test detection of shoreline stranding inside coastal polygons."""
        integrator = RK4AdvectionIntegrator(self.interpolator)

        # Check coordinate known to be inside East Coast Park Shoreline
        is_beached, shore = integrator.check_shoreline_collision(lat=1.310, lng=103.925)
        self.assertTrue(is_beached)
        self.assertIn("East Coast", shore)

        # Check deep marine point (should not be beached)
        is_beached_deep, shore_deep = integrator.check_shoreline_collision(lat=1.180, lng=103.850)
        self.assertFalse(is_beached_deep)
        self.assertIsNone(shore_deep)

    def test_03_debris_drift_forecaster_horizons(self):
        """Test particle seeding and multi-horizon accumulation forecasts."""
        forecaster = DebrisDriftForecaster(self.interpolator, particles_per_hotspot=10, time_step_seconds=300.0)

        hotspots = [
            {"id": "HS-EAST-01", "centroid_lat": 1.305, "centroid_lng": 103.942, "radius_meters": 100.0, "detection_count": 25, "sector_id": "east_coast"},
            {"id": "HS-SENT-02", "centroid_lat": 1.251, "centroid_lng": 103.829, "radius_meters": 100.0, "detection_count": 15, "sector_id": "southern_islands"},
        ]

        # Seed particles test
        particles = forecaster.seed_particles(hotspots)
        self.assertEqual(len(particles), 20)

        # Run forecast on 2h and 6h horizons
        forecasts = forecaster.run_forecast(hotspots, horizons_hours=[2, 6])
        self.assertIn(2, forecasts)
        self.assertIn(6, forecasts)

        summary_2h = forecasts[2]
        self.assertEqual(summary_2h.horizon_hours, 2)
        self.assertEqual(summary_2h.total_particles, 20)
        self.assertTrue(0.0 <= summary_2h.beached_percentage <= 100.0)
        self.assertEqual(len(summary_2h.accumulation_hotspots), 2)

        # Verify GeoJSON export
        geojson = forecaster.to_geojson(summary_2h)
        self.assertEqual(geojson["type"], "FeatureCollection")
        self.assertGreater(len(geojson["features"]), 0)
        # Should contain both Point (predicted hotspot) and LineString (drift trajectory)
        geom_types = {f["geometry"]["type"] for f in geojson["features"]}
        self.assertIn("Point", geom_types)
        self.assertIn("LineString", geom_types)


if __name__ == "__main__":
    unittest.main()

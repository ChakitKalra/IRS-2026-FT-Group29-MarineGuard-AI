"""Unit tests for MarineGuard AI Phase 2 Oceanographic & Environmental Data Engine."""

import unittest
from datetime import datetime, timezone
import math

from backend.weather.copernicus import CopernicusCurrentClient, STUDY_BOUNDS
from backend.weather.nea_client import SingaporeWeatherClient, WeatherStationReading
from backend.weather.interpolator import VectorFieldInterpolator


class TestPhase2EnvironmentalEngine(unittest.TestCase):

    def test_01_singapore_weather_client(self):
        """Test Singapore meteorological client (data.gov.sg ingestion & fallback)."""
        client = SingaporeWeatherClient(timeout_seconds=5)
        summary = client.fetch_realtime_weather()

        self.assertIsNotNone(summary.timestamp)
        self.assertGreater(summary.active_wind_stations, 0)
        self.assertGreaterEqual(summary.avg_wind_speed_knots, 0.0)
        self.assertTrue(0.0 <= summary.dominant_wind_direction_from_deg <= 360.0)
        self.assertTrue(0.0 <= summary.dominant_wind_direction_towards_deg <= 360.0)
        self.assertIn(summary.inland_flushing_risk, ["Low", "Moderate", "High"])

        # Check vector conversion relationship: towards = (from + 180) % 360
        expected_towards = (summary.dominant_wind_direction_from_deg + 180.0) % 360.0
        self.assertAlmostEqual(summary.dominant_wind_direction_towards_deg, expected_towards, delta=1.0)

    def test_02_copernicus_current_client(self):
        """Test Singapore Strait hydrodynamic surface current retrieval & tidal physics."""
        client = CopernicusCurrentClient()
        test_dt = datetime(2026, 10, 19, 12, 0, 0, tzinfo=timezone.utc)
        current_field = client.fetch_current_field(dt_utc=test_dt, use_cache=False)

        self.assertIn("Singapore Strait", current_field.source_model)
        self.assertGreater(len(current_field.points), 0)
        self.assertGreater(current_field.mean_speed_knots, 0.0)
        self.assertIn(current_field.tidal_stage.split()[0], ["Flood", "Ebb", "Slack"])

        # Check bounds
        for p in current_field.points:
            self.assertTrue(STUDY_BOUNDS[1] <= p.latitude <= STUDY_BOUNDS[3])
            self.assertTrue(STUDY_BOUNDS[0] <= p.longitude <= STUDY_BOUNDS[2])
            self.assertTrue(0.0 <= p.direction_towards_deg <= 360.0)
            self.assertAlmostEqual(p.speed_knots, p.speed_ms * 1.94384, delta=0.05)

        # Test GeoJSON conversion
        geojson = client.to_geojson(current_field)
        self.assertEqual(geojson["type"], "FeatureCollection")
        self.assertEqual(len(geojson["features"]), len(current_field.points))

    def test_03_vector_field_interpolator(self):
        """Test continuous 2D vector interpolation and Lagrangian drift equation."""
        client_cur = CopernicusCurrentClient()
        client_wth = SingaporeWeatherClient()
        current_field = client_cur.fetch_current_field()
        weather_summary = client_wth.fetch_realtime_weather()

        interpolator = VectorFieldInterpolator(current_field, weather_summary, default_leeway_factor=0.02)

        # Interpolate at East Coast Park
        vec = interpolator.interpolate(lat=1.303, lng=103.933, leeway_factor=0.02)

        self.assertAlmostEqual(vec.latitude, 1.303, places=3)
        self.assertAlmostEqual(vec.longitude, 103.933, places=3)
        self.assertGreater(vec.current_speed_knots, 0.0)
        self.assertGreater(vec.total_speed_knots, 0.0)
        self.assertTrue(0.0 <= vec.total_heading_deg <= 360.0)

        # Check that contributions sum to ~100%
        self.assertAlmostEqual(vec.current_contribution_pct + vec.wind_contribution_pct, 100.0, delta=0.5)

        # Verify drift equation: V_tot = V_c + alpha * V_w
        expected_u = vec.current_u_ms + 0.02 * vec.wind_u_ms
        expected_v = vec.current_v_ms + 0.02 * vec.wind_v_ms
        self.assertAlmostEqual(vec.total_u_ms, expected_u, delta=0.01)
        self.assertAlmostEqual(vec.total_v_ms, expected_v, delta=0.01)


if __name__ == "__main__":
    unittest.main()

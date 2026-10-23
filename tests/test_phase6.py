"""Unit tests for Phase 6: FastAPI REST API and Full-Stack Integration.

Tests all endpoints:
- GET /
- GET /api/v1/health
- GET /api/v1/hotspots
- GET /api/v1/weather/current
- GET /api/v1/forecast (with and without horizon param)
- GET /api/v1/attribution
- POST /api/v1/attribution (with hotspot_id and custom coordinates)
- GET /api/v1/cleanup/recommendations
- GET /api/v1/cleanup/report/download
- POST /api/v1/simulate/drift
- POST /api/v1/simulate/backtrack
"""

import json
import unittest
from fastapi.testclient import TestClient

from backend.app.main import app


class TestPhase6API(unittest.TestCase):
    """Test suite for MarineGuard AI FastAPI REST API."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_root_endpoint(self):
        """Verify root metadata endpoint returns 200 OK and endpoint directory."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("service"), "MarineGuard AI API")
        self.assertEqual(data.get("status"), "OPERATIONAL")
        self.assertIn("endpoints", data)
        self.assertIn("hotspots", data["endpoints"])
        self.assertIn("cleanup_recommendations", data["endpoints"])

    def test_health_check(self):
        """Verify /api/v1/health returns subsystem statuses and uptime."""
        response = self.client.get("/api/v1/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("status", data)
        self.assertIn("active_pipelines", data)
        pipelines = data["active_pipelines"]
        self.assertIn("phase1_detection", pipelines)
        self.assertIn("phase2_environmental", pipelines)
        self.assertIn("phase3_forecasting", pipelines)
        self.assertIn("phase4_attribution", pipelines)
        self.assertIn("phase5_optimization", pipelines)

    def test_get_hotspots(self):
        """Verify /api/v1/hotspots returns detected clusters and satellite polygons."""
        response = self.client.get("/api/v1/hotspots")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("status"), "success")
        self.assertIn("hotspots", data)
        self.assertIn("satellite_polygons", data)
        self.assertGreaterEqual(len(data["hotspots"]), 1)
        # Spot-check first hotspot
        hs1 = data["hotspots"][0]
        self.assertIn("hotspot_id", hs1)
        self.assertIn("centroid_lat", hs1)
        self.assertIn("centroid_lng", hs1)
        self.assertIn("severity", hs1)

    def test_get_weather_current(self):
        """Verify /api/v1/weather/current returns environmental conditions and vector grid."""
        response = self.client.get("/api/v1/weather/current")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("status"), "success")
        self.assertIn("currents", data)
        self.assertIn("weather", data)
        self.assertIn("vector_grid", data)
        self.assertIn("surface_speed_knots", data["currents"])
        self.assertIn("wind_speed_knots", data["weather"])

    def test_get_forecast_all_and_filtered(self):
        """Verify /api/v1/forecast returns all horizons or filters by horizon query param."""
        # 1. All horizons
        resp_all = self.client.get("/api/v1/forecast")
        self.assertEqual(resp_all.status_code, 200)
        data_all = resp_all.json()
        self.assertIn("horizons", data_all)
        self.assertIn("geojson_trajectories", data_all)

        # 2. Filtered horizon (+24h)
        resp_24 = self.client.get("/api/v1/forecast?horizon=24")
        self.assertEqual(resp_24.status_code, 200)
        data_24 = resp_24.json()
        self.assertEqual(data_24.get("requested_horizon_hours"), 24)
        self.assertIn("points", data_24)
        self.assertIn("trajectories", data_24)

        # 3. Invalid horizon
        resp_bad = self.client.get("/api/v1/forecast?horizon=99")
        self.assertEqual(resp_bad.status_code, 400)

    def test_source_attribution_get_and_post(self):
        """Verify GET and POST /api/v1/attribution endpoints."""
        # GET all attributions
        resp_get = self.client.get("/api/v1/attribution")
        self.assertEqual(resp_get.status_code, 200)
        data_get = resp_get.json()
        self.assertIn("hotspot_attributions", data_get)
        self.assertIn("geojson_layers", data_get)

        # POST evaluate specific hotspot (HS-01)
        resp_post = self.client.post(
            "/api/v1/attribution",
            json={"hotspot_id": "HS-01", "rainfall_rate_mmh": 15.0},
        )
        self.assertEqual(resp_post.status_code, 200)
        data_post = resp_post.json()
        self.assertEqual(data_post.get("status"), "success")
        self.assertIn("hotspot_id", data_post["attribution"])
        self.assertIn("HS", data_post["attribution"]["hotspot_id"])

        # POST evaluate custom point
        resp_custom = self.client.post(
            "/api/v1/attribution",
            json={"custom_lat": 1.2950, "custom_lng": 103.9100, "rainfall_rate_mmh": 25.0},
        )
        self.assertEqual(resp_custom.status_code, 200)
        data_custom = resp_custom.json()
        self.assertEqual(data_custom.get("status"), "success")
        self.assertIn("attribution", data_custom)

    def test_cleanup_recommendations_and_report_download(self):
        """Verify /api/v1/cleanup/recommendations and /api/v1/cleanup/report/download."""
        # 1. Recommendations & CPI rankings
        resp_recs = self.client.get("/api/v1/cleanup/recommendations")
        self.assertEqual(resp_recs.status_code, 200)
        data_recs = resp_recs.json()
        self.assertIn("cpi_rankings", data_recs)
        self.assertIn("dispatch_orders", data_recs)
        self.assertIn("efficiency_benchmark", data_recs)
        self.assertGreaterEqual(len(data_recs["dispatch_orders"]), 1)

        # 2. Downloadable IAP report
        resp_dl = self.client.get("/api/v1/cleanup/report/download")
        self.assertEqual(resp_dl.status_code, 200)
        self.assertEqual(resp_dl.headers.get("content-type"), "application/json")
        self.assertIn("attachment", resp_dl.headers.get("content-disposition", ""))
        self.assertIn("marineguard_incident_action_plan.json", resp_dl.headers.get("content-disposition", ""))
        iap = json.loads(resp_dl.content)
        self.assertEqual(iap.get("document_type"), "INCIDENT_ACTION_PLAN_IAP")
        self.assertIn("priority_dispatch_orders", iap)

    def test_simulation_endpoints(self):
        """Verify on-demand forward drift and reverse backtrack simulation endpoints."""
        # Forward drift
        resp_drift = self.client.post(
            "/api/v1/simulate/drift",
            json={"start_lat": 1.250, "start_lng": 103.820, "duration_hours": 6.0, "leeway_factor": 0.025},
        )
        self.assertEqual(resp_drift.status_code, 200)
        data_drift = resp_drift.json()
        self.assertEqual(data_drift.get("status"), "success")
        self.assertGreaterEqual(len(data_drift["trajectory_points"]), 2)

        # Reverse backtrack
        resp_backtrack = self.client.post(
            "/api/v1/simulate/backtrack",
            json={"start_lat": 1.2980, "start_lng": 103.9210, "backtrack_hours": 12.0},
        )
        self.assertEqual(resp_backtrack.status_code, 200)
        data_bt = resp_backtrack.json()
        self.assertEqual(data_bt.get("status"), "success")
        self.assertIn("origin_coordinates", data_bt)
        self.assertGreaterEqual(len(data_bt["trajectory"]), 2)


if __name__ == "__main__":
    unittest.main()

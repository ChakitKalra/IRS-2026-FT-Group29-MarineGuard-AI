"""Unit tests for MarineGuard AI Phase 1 Multi-Scale Detection Engine."""

import unittest
from pathlib import Path
import numpy as np

from backend.marida.inference import Sentinel2DebrisDetector
from backend.cv.detector import CoastalLitterDetector
from backend.analysis.hotspots import HotspotAggregator, assign_sector
from backend.cv.phase1_pipeline import generate_singapore_satellite_sample


class TestPhase1DetectionEngine(unittest.TestCase):

    def test_01_sentinel2_inference_pipeline(self):
        """Test Sentinel-2 11-band inference, water masking, and polygon generation."""
        detector = Sentinel2DebrisDetector()
        h, w = 60, 60
        bands = generate_singapore_satellite_sample(h=h, w=w, inject_debris=True)

        self.assertEqual(bands.shape, (11, h, w))
        water_mask, cloud_mask = detector.compute_water_and_cloud_mask(bands)
        self.assertEqual(water_mask.shape, (h, w))
        self.assertEqual(cloud_mask.shape, (h, w))

        # Detect raster
        bounds = (103.90, 1.28, 103.98, 1.34)
        result = detector.detect_raster(bands, bounds=bounds)

        self.assertEqual(result["type"], "FeatureCollection")
        self.assertIn("metadata", result)
        self.assertGreater(result["metadata"]["total_detections"], 0)

        # Verify feature properties
        feature = result["features"][0]
        self.assertEqual(feature["geometry"]["type"], "Polygon")
        props = feature["properties"]
        self.assertIn("centroid_lat", props)
        self.assertIn("centroid_lng", props)
        self.assertIn("area_sq_meters", props)
        self.assertIn("confidence", props)
        self.assertGreater(props["area_sq_meters"], 0)

    def test_02_uav_object_detector(self):
        """Test UAV / CCTV object detector on synthetic shoreline image."""
        detector = CoastalLitterDetector(weights_path="yolov8n.pt", conf_threshold=0.20)
        img = detector.create_synthetic_coastal_test_image()

        self.assertEqual(img.shape, (600, 800, 3))
        res = detector.detect(img, estimated_ground_area_sq_m=25.0)

        self.assertGreaterEqual(res.total_objects, 1)
        self.assertIn(res.severity, ["Low", "Medium", "High"])
        self.assertGreater(res.density_per_sq_meter, 0.0)
        self.assertIsInstance(res.counts_by_class, dict)

    def test_03_hotspot_spatial_clustering(self):
        """Test DBSCAN spatial aggregation and Singapore sector attribution."""
        aggregator = HotspotAggregator(cluster_eps_meters=800.0, min_samples=1)

        sample_detections = [
            {"id": "D1", "lat": 1.303, "lng": 103.929, "confidence": 85.0, "severity": "High", "source": "S2", "items_count": 50, "area_sq_m": 5000.0, "label": "Marine debris"},
            {"id": "D2", "lat": 1.304, "lng": 103.930, "confidence": 90.0, "severity": "High", "source": "UAV", "items_count": 3, "area_sq_m": 30.0, "label": "Plastic bottle"},
            {"id": "D3", "lat": 1.381, "lng": 103.953, "confidence": 80.0, "severity": "Medium", "source": "UAV", "items_count": 4, "area_sq_m": 40.0, "label": "Styrofoam"},
        ]

        hotspots = aggregator.aggregate(sample_detections)
        # Points D1 and D2 are within ~150 meters, should merge into 1 cluster; D3 is far away (~10 km)
        self.assertEqual(len(hotspots), 2)

        # First cluster should be East Coast
        self.assertEqual(hotspots[0].sector_id, "east_coast")
        self.assertEqual(hotspots[0].detection_count, 53)
        self.assertIn("S2", hotspots[0].sources)
        self.assertIn("UAV", hotspots[0].sources)

        # Second cluster should be Pasir Ris
        self.assertEqual(hotspots[1].sector_id, "pasir_ris_changi")

        geojson = aggregator.to_geojson(hotspots)
        self.assertEqual(geojson["type"], "FeatureCollection")
        self.assertEqual(len(geojson["features"]), 2)

    def test_04_sector_assignment(self):
        """Test coastal sector assignment for Singapore key landmarks."""
        sec_id, name = assign_sector(1.303, 103.933)  # East Coast
        self.assertEqual(sec_id, "east_coast")

        sec_id, name = assign_sector(1.383, 103.953)  # Pasir Ris
        self.assertEqual(sec_id, "pasir_ris_changi")

        sec_id, name = assign_sector(1.250, 103.830)  # Sentosa
        self.assertEqual(sec_id, "southern_islands")


if __name__ == "__main__":
    unittest.main()

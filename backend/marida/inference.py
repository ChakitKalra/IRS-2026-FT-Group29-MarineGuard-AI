"""Sentinel-2 Remote Sensing Inference Module for Marine Litter Hotspot Detection.

Ingests multi-spectral imagery (11 Sentinel-2 bands), computes water/cloud masks,
derives spectral indices (FDI, FAI, NDVI, NDWI), executes the trained MARIDA model
(or calibrated spectral baseline), and outputs georeferenced GeoJSON debris polygons.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

try:
    import rasterio
    from rasterio.transform import Affine
except ImportError:
    rasterio = None
    Affine = None

from backend.marida.features import ss_si_features

# Official MARIDA band centers in nanometers
BAND_NAMES = [
    "B01_440", "B02_490", "B03_560", "B04_665", "B05_705",
    "B06_740", "B07_783", "B08_842", "B8A_865", "B11_1600", "B12_2200"
]


@dataclass
class DetectionPolygon:
    id: str
    centroid_lat: float
    centroid_lng: float
    confidence: float
    severity: str
    area_sq_meters: float
    pixel_count: int
    geometry: Dict[str, Any]
    spectral_signature: Dict[str, float]


class Sentinel2DebrisDetector:
    """Detects floating marine debris from 11-band Sentinel-2 imagery."""

    def __init__(self, model_path: Optional[Path] = None):
        self.model_path = model_path
        self.classifier = None
        if model_path and Path(model_path).exists():
            try:
                from joblib import load
                self.classifier = load(model_path)
            except Exception as e:
                print(f"[Warning] Failed loading classifier at {model_path}: {e}")

    def compute_water_and_cloud_mask(self, bands: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Compute valid water mask and cloud mask.

        Parameters
        ----------
        bands : np.ndarray
            Shape (11, H, W) normalized surface reflectance [0.0, 1.0].

        Returns
        -------
        Tuple[np.ndarray, np.ndarray]
            (water_mask, cloud_mask) boolean masks of shape (H, W).
        """
        b2 = bands[1]  # Blue (490 nm)
        b3 = bands[2]  # Green (560 nm)
        b8 = bands[7]  # NIR (842 nm)
        b11 = bands[9] # SWIR-1 (1600 nm)

        with np.errstate(divide="ignore", invalid="ignore"):
            ndwi = (b3 - b8) / np.maximum(b3 + b8, 1e-6)

        # Clouds: elevated visible & SWIR reflectance
        cloud_mask = (b2 > 0.35) & (b11 > 0.20)

        # Water: high NDWI or low NIR/SWIR reflectance typical of ocean
        # Excludes dense land where NIR >> Green
        water_mask = ((ndwi > -0.05) | (b8 < 0.12)) & ~cloud_mask

        return water_mask, cloud_mask

    def predict_mask(self, bands: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Predict debris binary mask and confidence map.

        Returns
        -------
        Tuple[np.ndarray, np.ndarray]
            (binary_debris_mask, confidence_map)
        """
        c, h, w = bands.shape
        water_mask, cloud_mask = self.compute_water_and_cloud_mask(bands)
        features_19 = ss_si_features(bands)  # shape (19, H, W)

        binary_mask = np.zeros((h, w), dtype=np.uint8)
        confidence_map = np.zeros((h, w), dtype=np.float32)

        # Fallback spectral rule based on Kikaki et al. Floating Debris Index (FDI)
        # FDI = B8 - [B6 + (B11 - B6) * (833 - 740)/(1614 - 740) * 10]
        # Debris index is channel index 13 in ss_si_features (bands 0..10, ndvi 11, fai 12, fdi 13)
        fdi = features_19[13]
        ndvi = features_19[11]

        if self.classifier is not None:
            flat_features = features_19.reshape(19, -1).T
            flat_water = water_mask.ravel()
            valid_idx = np.where(flat_water & np.all(np.isfinite(flat_features), axis=1))[0]

            if len(valid_idx) > 0:
                try:
                    preds = self.classifier.predict(flat_features[valid_idx])
                    # Class 1 is Marine Debris in MARIDA
                    debris_pixels = (preds == 1)

                    if hasattr(self.classifier, "predict_proba"):
                        proba = self.classifier.predict_proba(flat_features[valid_idx])
                        # If class 1 is present in classes_
                        classes = list(self.classifier.classes_)
                        if 1 in classes:
                            cls_idx = classes.index(1)
                            confidence_map.ravel()[valid_idx] = proba[:, cls_idx]
                        else:
                            confidence_map.ravel()[valid_idx[debris_pixels]] = 0.85
                    else:
                        confidence_map.ravel()[valid_idx[debris_pixels]] = 0.85

                    binary_mask.ravel()[valid_idx[debris_pixels]] = 1
                except Exception as e:
                    print(f"[Warning] RF prediction failed ({e}), falling back to spectral FDI.")
                    debris_cond = water_mask & (fdi > 0.015) & (ndvi < 0.35)
                    binary_mask[debris_cond] = 1
                    confidence_map[debris_cond] = np.clip(fdi[debris_cond] * 20.0, 0.60, 0.95)
        else:
            # Calibrated physical baseline: FDI positive anomaly over water
            debris_cond = water_mask & (fdi > 0.012) & (ndvi < 0.40) & (ndvi > -0.20)
            binary_mask[debris_cond] = 1
            confidence_map[debris_cond] = np.clip(0.65 + fdi[debris_cond] * 15.0, 0.65, 0.95)

        return binary_mask, confidence_map

    def vectorize_detections(
        self,
        binary_mask: np.ndarray,
        confidence_map: np.ndarray,
        features_19: np.ndarray,
        transform_affine: Optional[Tuple[float, float, float, float, float, float]] = None,
        bounds: Optional[Tuple[float, float, float, float]] = None,
        min_pixels: int = 2,
    ) -> List[DetectionPolygon]:
        """Convert binary debris pixel clusters into georeferenced GeoJSON polygons.

        Parameters
        ----------
        binary_mask : np.ndarray
            (H, W) binary mask where 1 indicates marine debris.
        confidence_map : np.ndarray
            (H, W) confidence scores [0.0, 1.0].
        features_19 : np.ndarray
            (19, H, W) spectral bands and indices.
        bounds : tuple of float, optional
            (min_lon, min_lat, max_lon, max_lat) if transform_affine is not given.
        """
        h, w = binary_mask.shape
        contours, _ = cv2.findContours(binary_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Coordinate mapper: pixels (px, py) -> (lng, lat)
        def pixel_to_geo(px: float, py: float) -> Tuple[float, float]:
            if transform_affine is not None:
                a, b, c, d, e, f = transform_affine
                geo_x = c + px * a + py * b
                geo_y = f + px * d + py * e
                return geo_x, geo_y
            elif bounds is not None:
                min_lon, min_lat, max_lon, max_lat = bounds
                geo_x = min_lon + (px / max(w - 1, 1)) * (max_lon - min_lon)
                geo_y = max_lat - (py / max(h - 1, 1)) * (max_lat - min_lat)
                return geo_x, geo_y
            else:
                # Default to Singapore Strait coastal sample bounds
                # approx Singapore Southern waters: [103.80, 1.22, 103.96, 1.32]
                min_lon, min_lat, max_lon, max_lat = 103.80, 1.22, 103.96, 1.32
                geo_x = min_lon + (px / max(w - 1, 1)) * (max_lon - min_lon)
                geo_y = max_lat - (py / max(h - 1, 1)) * (max_lat - min_lat)
                return geo_x, geo_y

        detections: List[DetectionPolygon] = []
        for i, cnt in enumerate(contours):
            area_px = cv2.contourArea(cnt)
            if area_px < min_pixels and len(cnt) < 3:
                continue

            # Compute centroid
            m = cv2.moments(cnt)
            if m["m00"] != 0:
                cx_px = m["m10"] / m["m00"]
                cy_px = m["m01"] / m["m00"]
            else:
                cx_px, cy_px = cnt[0][0][0], cnt[0][0][1]

            c_lng, c_lat = pixel_to_geo(cx_px, cy_px)

            # Sample average confidence across the contour
            contour_mask = np.zeros((h, w), dtype=np.uint8)
            cv2.drawContours(contour_mask, [cnt], -1, 1, thickness=-1)
            cnt_pixels = contour_mask == 1
            avg_conf = float(np.mean(confidence_map[cnt_pixels])) if np.any(cnt_pixels) else 0.75
            pixel_count = int(np.sum(cnt_pixels))

            # Sentinel-2 has ~10m x 10m = 100m² per pixel
            area_sq_meters = float(pixel_count * 100.0)

            # Severity classification
            if area_sq_meters > 1000 or avg_conf > 0.85:
                severity = "High"
            elif area_sq_meters > 300 or avg_conf > 0.70:
                severity = "Medium"
            else:
                severity = "Low"

            # Spectral summary (mean FDI, NDVI, NDWI)
            mean_fdi = float(np.mean(features_19[13][cnt_pixels])) if np.any(cnt_pixels) else 0.0
            mean_ndvi = float(np.mean(features_19[11][cnt_pixels])) if np.any(cnt_pixels) else 0.0
            mean_ndwi = float(np.mean(features_19[15][cnt_pixels])) if np.any(cnt_pixels) else 0.0

            # GeoJSON coordinates: list of [lng, lat]
            poly_coords = []
            for pt in cnt:
                px, py = pt[0][0], pt[0][1]
                glng, glat = pixel_to_geo(px, py)
                poly_coords.append([round(glng, 6), round(glat, 6)])

            # Close polygon if needed
            if poly_coords and poly_coords[0] != poly_coords[-1]:
                poly_coords.append(poly_coords[0])

            geometry = {
                "type": "Polygon",
                "coordinates": [poly_coords]
            }

            detections.append(
                DetectionPolygon(
                    id=f"S2-LITTER-{i+1:03d}",
                    centroid_lat=round(c_lat, 6),
                    centroid_lng=round(c_lng, 6),
                    confidence=round(avg_conf * 100.0, 1),
                    severity=severity,
                    area_sq_meters=round(area_sq_meters, 1),
                    pixel_count=pixel_count,
                    geometry=geometry,
                    spectral_signature={
                        "mean_fdi": round(mean_fdi, 4),
                        "mean_ndvi": round(mean_ndvi, 4),
                        "mean_ndwi": round(mean_ndwi, 4),
                    }
                )
            )

        return detections

    def detect_raster(
        self,
        bands_11: np.ndarray,
        bounds: Optional[Tuple[float, float, float, float]] = None,
        transform_affine: Optional[Tuple[float, float, float, float, float, float]] = None,
    ) -> Dict[str, Any]:
        """Full inference pipeline on an 11-band raster.

        Returns GeoJSON FeatureCollection dictionary.
        """
        binary_mask, confidence_map = self.predict_mask(bands_11)
        features_19 = ss_si_features(bands_11)
        detections = self.vectorize_detections(
            binary_mask=binary_mask,
            confidence_map=confidence_map,
            features_19=features_19,
            transform_affine=transform_affine,
            bounds=bounds,
        )

        features = []
        for det in detections:
            features.append({
                "type": "Feature",
                "id": det.id,
                "geometry": det.geometry,
                "properties": {
                    "id": det.id,
                    "label": "Marine debris",
                    "source_type": "Sentinel-2 Satellite",
                    "centroid_lat": det.centroid_lat,
                    "centroid_lng": det.centroid_lng,
                    "confidence": det.confidence,
                    "severity": det.severity,
                    "area_sq_meters": det.area_sq_meters,
                    "pixel_count": det.pixel_count,
                    "spectral_signature": det.spectral_signature,
                }
            })

        return {
            "type": "FeatureCollection",
            "metadata": {
                "sensor": "Sentinel-2 MSI",
                "bands_processed": 11,
                "indices_derived": 8,
                "total_detections": len(detections),
                "total_area_sq_meters": sum(d.area_sq_meters for d in detections),
            },
            "features": features,
        }

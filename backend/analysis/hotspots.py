"""Spatial Hotspot Aggregation & Clustering Module for MarineGuard AI.

Groups heterogeneous detections (Sentinel-2 satellite slicks + UAV/CCTV object detections)
into cohesive geographic coastal hotspots using spatial clustering (DBSCAN / Haversine metric).
Associates clusters with named Singapore coastal management zones and computes density metrics.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from sklearn.cluster import DBSCAN

# Key Singapore coastal sectors for operational reporting
SINGAPORE_SECTORS = [
    {
        "id": "east_coast",
        "name": "East Coast Shoreline & Bedok Waters",
        "bounds": [1.28, 103.90, 1.34, 103.98],
        "center": [1.305, 103.935],
    },
    {
        "id": "pasir_ris_changi",
        "name": "Pasir Ris, Changi & Pulau Ubin",
        "bounds": [1.36, 103.94, 1.42, 104.02],
        "center": [1.385, 103.965],
    },
    {
        "id": "southern_islands",
        "name": "Sentosa, Labrador & Southern Islands",
        "bounds": [1.21, 103.78, 1.28, 103.86],
        "center": [1.255, 103.825],
    },
    {
        "id": "jurong_tuas",
        "name": "Jurong Coast & Tuas Industrial Basin",
        "bounds": [1.25, 103.62, 1.33, 103.75],
        "center": [1.285, 103.685],
    },
    {
        "id": "johor_strait_north",
        "name": "Johor Strait North & Sungei Buloh",
        "bounds": [1.41, 103.68, 1.47, 103.82],
        "center": [1.442, 103.745],
    },
    {
        "id": "singapore_strait_deep",
        "name": "Singapore Strait Commercial Traffic Lane",
        "bounds": [1.15, 103.75, 1.24, 104.05],
        "center": [1.200, 103.880],
    },
]


@dataclass
class HotspotCluster:
    hotspot_id: str
    name: str
    sector_id: str
    centroid_lat: float
    centroid_lng: float
    radius_meters: float
    severity: str
    composite_confidence: float
    detection_count: int
    total_area_sq_m: float
    sources: List[str]
    item_breakdown: Dict[str, int] = field(default_factory=dict)
    detection_ids: List[str] = field(default_factory=list)


def assign_sector(lat: float, lng: float) -> Tuple[str, str]:
    """Find the closest or containing Singapore coastal sector."""
    # Check bounding boxes first
    for sector in SINGAPORE_SECTORS:
        min_lat, min_lng, max_lat, max_lng = sector["bounds"]
        if min_lat <= lat <= max_lat and min_lng <= lng <= max_lng:
            return sector["id"], sector["name"]

    # Fallback to closest center by Euclidean distance in degrees
    best_dist = float("inf")
    best_sector = SINGAPORE_SECTORS[0]
    for sector in SINGAPORE_SECTORS:
        clat, clng = sector["center"]
        dist = math.hypot(lat - clat, lng - clng)
        if dist < best_dist:
            best_dist = dist
            best_sector = sector
    return best_sector["id"], best_sector["name"]


class HotspotAggregator:
    """Aggregates multi-source detections into hotspot clusters."""

    def __init__(self, cluster_eps_meters: float = 600.0, min_samples: int = 1):
        """
        Parameters
        ----------
        cluster_eps_meters : float
            Max distance between points to be considered in the same hotspot.
        min_samples : int
            Minimum points to form a cluster. 1 allows isolated high-confidence detections.
        """
        # Earth radius in meters ~ 6,371,000 m
        self.eps_radians = cluster_eps_meters / 6371000.0
        self.min_samples = min_samples

    def aggregate(self, detections: List[Dict[str, Any]]) -> List[HotspotCluster]:
        """Aggregate detection records into HotspotCluster objects.

        Each detection dict is expected to have:
        - 'lat': float
        - 'lng': float
        - 'confidence': float (0-100)
        - 'severity': 'High' | 'Medium' | 'Low'
        - 'source': 'Sentinel-2 Satellite' | 'UAV Drone' | 'CCTV' | etc.
        - 'id': str
        - Optional: 'area_sq_m', 'label', 'items_count'
        """
        if not detections:
            return []

        coords_deg = np.array([[d["lat"], d["lng"]] for d in detections])
        coords_rad = np.radians(coords_deg)

        # Cluster using Haversine distance
        clustering = DBSCAN(eps=self.eps_radians, min_samples=self.min_samples, metric="haversine")
        cluster_labels = clustering.fit_predict(coords_rad)

        hotspots: List[HotspotCluster] = []
        unique_labels = sorted(set(cluster_labels))

        for label_idx in unique_labels:
            mask = cluster_labels == label_idx
            sub_dets = [detections[i] for i in range(len(detections)) if mask[i]]
            sub_coords = coords_deg[mask]

            c_lat = float(np.mean(sub_coords[:, 0]))
            c_lng = float(np.mean(sub_coords[:, 1]))

            # Compute approximate cluster radius in meters
            if len(sub_coords) > 1:
                diffs_m = [
                    math.hypot((p[0] - c_lat) * 111000.0, (p[1] - c_lng) * 111000.0 * math.cos(math.radians(c_lat)))
                    for p in sub_coords
                ]
                radius_m = float(np.max(diffs_m))
            else:
                radius_m = 120.0

            # Aggregates
            total_items = sum(d.get("items_count", 1) for d in sub_dets)
            total_area = sum(d.get("area_sq_m", 100.0) for d in sub_dets)
            avg_conf = float(np.mean([d.get("confidence", 75.0) for d in sub_dets]))
            sources = sorted(list({d.get("source", "Satellite") for d in sub_dets}))

            # Breakdown by label
            item_breakdown: Dict[str, int] = {}
            for d in sub_dets:
                lbl = d.get("label", "Marine debris")
                cnt = d.get("items_count", 1)
                item_breakdown[lbl] = item_breakdown.get(lbl, 0) + cnt

            # Severity calculation
            if total_items >= 5 or total_area >= 800.0 or any(d.get("severity") == "High" for d in sub_dets):
                severity = "High"
            elif total_items >= 2 or total_area >= 250.0:
                severity = "Medium"
            else:
                severity = "Low"

            sector_id, sector_name = assign_sector(c_lat, c_lng)
            hs_id = f"HS-{sector_id.upper()[:4]}-{len(hotspots) + 1:02d}"

            hotspots.append(
                HotspotCluster(
                    hotspot_id=hs_id,
                    name=f"{sector_name} Hotspot #{len(hotspots) + 1}",
                    sector_id=sector_id,
                    centroid_lat=round(c_lat, 5),
                    centroid_lng=round(c_lng, 5),
                    radius_meters=round(radius_m, 1),
                    severity=severity,
                    composite_confidence=round(avg_conf, 1),
                    detection_count=total_items,
                    total_area_sq_m=round(total_area, 1),
                    sources=sources,
                    item_breakdown=item_breakdown,
                    detection_ids=[d.get("id", f"DET-{i}") for i, d in enumerate(sub_dets)],
                )
            )

        return hotspots

    def to_geojson(self, hotspots: List[HotspotCluster]) -> Dict[str, Any]:
        """Convert a list of HotspotClusters to standard GeoJSON FeatureCollection."""
        features = []
        for hs in hotspots:
            features.append({
                "type": "Feature",
                "id": hs.hotspot_id,
                "geometry": {
                    "type": "Point",
                    "coordinates": [hs.centroid_lng, hs.centroid_lat],
                },
                "properties": {
                    "id": hs.hotspot_id,
                    "name": hs.name,
                    "sector_id": hs.sector_id,
                    "severity": hs.severity,
                    "confidence": hs.composite_confidence,
                    "radius_meters": hs.radius_meters,
                    "detection_count": hs.detection_count,
                    "total_area_sq_m": hs.total_area_sq_m,
                    "sources": hs.sources,
                    "item_breakdown": hs.item_breakdown,
                    "detection_ids": hs.detection_ids,
                },
            })

        return {
            "type": "FeatureCollection",
            "metadata": {
                "total_hotspots": len(hotspots),
                "high_severity_count": sum(1 for h in hotspots if h.severity == "High"),
                "medium_severity_count": sum(1 for h in hotspots if h.severity == "Medium"),
                "low_severity_count": sum(1 for h in hotspots if h.severity == "Low"),
            },
            "features": features,
        }

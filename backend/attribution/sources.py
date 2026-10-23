"""Candidate Source Domains and Maritime Geographic Polygons for Singapore Waters.

Defines the spatial boundaries, metadata, and prior weights for the 5 primary
marine litter source domains in the Singapore coastal domain:
1. Singapore Strait Shipping Channel (Commercial Maritime Traffic / TSS)
2. Johor Strait / Cross-Border River Basin (Skudai, Tebrau, Johor River)
3. Riau Archipelago / Batam Waters (Indonesian Regional Transboundary Currents)
4. Local Inland Waterways & Canals (Marina Barrage, Kallang, Jurong River Sluices)
5. Recreational Shorelines & Beachgoers (Direct coastal visitor disposal)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from shapely.geometry import Point, Polygon, MultiPolygon
from shapely.ops import unary_union


@dataclass
class SourceDomain:
    id: str
    name: str
    category: str              # "marine_transboundary" | "inland_local"
    color: str                 # Hex color for UI
    description: str
    baseline_prior: float      # Empirical baseline prior (NEA study baseline)
    polygon: Polygon           # Shapely geometric boundary
    coordinates: List[List[float]] = field(default_factory=list) # [[lng, lat], ...]

    def to_geojson_feature(self) -> Dict[str, Any]:
        """Convert source domain to a GeoJSON Feature object for Leaflet rendering."""
        # Convert shapely polygon coords to geojson format [[lng, lat], ...]
        coords = list(self.polygon.exterior.coords)
        return {
            "type": "Feature",
            "properties": {
                "id": self.id,
                "name": self.name,
                "category": self.category,
                "color": self.color,
                "description": self.description,
                "baseline_prior": self.baseline_prior,
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [coords],
            },
        }

    def contains_point(self, lat: float, lng: float) -> bool:
        """Check if a coordinate point is within this source boundary."""
        return self.polygon.contains(Point(lng, lat))

    def distance_to_point_km(self, lat: float, lng: float) -> float:
        """Approximate distance in kilometers from point to source polygon boundary."""
        pt = Point(lng, lat)
        if self.polygon.contains(pt):
            return 0.0
        # 1 degree lat approx 111.14 km, lng approx 111.14 * cos(lat)
        dist_deg = self.polygon.distance(pt)
        return dist_deg * 111.14


# 1. Singapore Strait Shipping Channel
# Commercial TSS corridor south of mainland Singapore
SHIPPING_CHANNEL_POLYGON = Polygon([
    (103.580, 1.120),
    (104.180, 1.135),
    (104.220, 1.235),
    (104.050, 1.250),
    (103.840, 1.220),
    (103.680, 1.180),
    (103.580, 1.150),
])

# 2. Johor Strait & Cross-Border River Basins
# Northern channel separating Singapore and Malaysia
JOHOR_STRAIT_POLYGON = Polygon([
    (103.580, 1.390),
    (103.700, 1.420),
    (103.820, 1.430),
    (103.940, 1.395),
    (104.120, 1.400),
    (104.120, 1.485),
    (103.820, 1.495),
    (103.650, 1.470),
    (103.580, 1.445),
])

# 3. Riau Archipelago / Batam Waters
# Southern transboundary open waters (Indonesia / Batam / Bintan corridor)
RIAU_BATAM_POLYGON = Polygon([
    (103.750, 1.050),
    (104.250, 1.050),
    (104.250, 1.145),
    (103.950, 1.135),
    (103.750, 1.110),
])

# 4. Local Inland Waterways & Canal Outlets
# Coastal buffer around Marina Barrage, Kallang River, Singapore River, Jurong Canal, Bedok Canal
INLAND_CANALS_POLYGON = Polygon([
    (103.710, 1.285),
    (103.765, 1.285),
    (103.765, 1.325),
    (103.860, 1.275),
    (103.895, 1.275),
    (103.895, 1.315),
    (103.930, 1.300),
    (103.965, 1.300),
    (103.965, 1.335),
    (103.860, 1.325),
    (103.710, 1.325),
])

# 5. Recreational Shorelines & Beachgoers
# Direct shoreline recreational buffer (East Coast Park, Sentosa, Pasir Ris, Changi)
RECREATIONAL_SHORELINES_POLYGON = Polygon([
    (103.880, 1.295),
    (103.975, 1.305),
    (103.975, 1.335),
    (103.880, 1.320),
])

# Collection of all 5 source domains
SOURCE_DOMAINS: Dict[str, SourceDomain] = {
    "marine_traffic": SourceDomain(
        id="marine_traffic",
        name="Singapore Strait Shipping Channel",
        category="marine_transboundary",
        color="#f59e0b", # Amber
        description="Commercial maritime traffic, container transshipment anchorage zones, and offshore vessel discard along the Traffic Separation Scheme (TSS).",
        baseline_prior=0.55, # 55% of total marine baseline
        polygon=SHIPPING_CHANNEL_POLYGON,
    ),
    "johor_strait": SourceDomain(
        id="johor_strait",
        name="Johor Strait / Cross-Border Basin",
        category="marine_transboundary",
        color="#06b6d4", # Cyan
        description="Cross-border estuarine and river discharge from Sungei Skudai, Sungei Tebrau, and Johor River flushing through the Johor Strait.",
        baseline_prior=0.17, # 17% of total marine baseline
        polygon=JOHOR_STRAIT_POLYGON,
    ),
    "transboundary_riau": SourceDomain(
        id="transboundary_riau",
        name="Riau Archipelago / Batam Waters",
        category="marine_transboundary",
        color="#8b5cf6", # Purple
        description="Regional transboundary ocean currents entering Singapore waters from the Riau Archipelago, Batam, and Bintan straits.",
        baseline_prior=0.25, # 25% of total marine baseline
        polygon=RIAU_BATAM_POLYGON,
    ),
    "inland_canals": SourceDomain(
        id="inland_canals",
        name="Local Inland Waterways & Canals",
        category="inland_local",
        color="#ef4444", # Red
        description="Urban stormwater runoff, canal drainage flushes, and crest gate discharges (Marina Barrage, Kallang River, Jurong River).",
        baseline_prior=0.015, # 1.5% baseline (scales up dynamically during rain events)
        polygon=INLAND_CANALS_POLYGON,
    ),
    "recreational_beachgoers": SourceDomain(
        id="recreational_beachgoers",
        name="Recreational Shorelines & Beachgoers",
        category="inland_local",
        color="#10b981", # Emerald
        description="Direct shoreline recreation, beach visitors, park littering, and nearshore activities along public beaches (ECP, Sentosa, Pasir Ris).",
        baseline_prior=0.015, # 1.5% baseline
        polygon=RECREATIONAL_SHORELINES_POLYGON,
    ),
}


def get_source_domains_geojson() -> Dict[str, Any]:
    """Generate a FeatureCollection of all candidate source domains for map display."""
    features = [src.to_geojson_feature() for src in SOURCE_DOMAINS.values()]
    return {
        "type": "FeatureCollection",
        "features": features,
    }


def find_containing_source(lat: float, lng: float) -> Optional[SourceDomain]:
    """Identify which candidate source domain contains the given coordinate, if any."""
    pt = Point(lng, lat)
    for domain in SOURCE_DOMAINS.values():
        if domain.polygon.contains(pt):
            return domain
    return None

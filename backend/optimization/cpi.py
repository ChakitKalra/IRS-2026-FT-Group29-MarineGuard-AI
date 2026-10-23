"""Coastal Priority Index (CPI) Multi-Criteria Evaluation Engine.

Ranks marine litter hotspots and coastal segments using multi-attribute utility theory:
    CPI = Q_litter * U_drift * W_sensitivity
where:
    - Q_litter: Quantity, volume, and slick density score (0 to 100)
    - U_drift: Forward Lagrangian drift urgency and shoreline threat multiplier (0.6 to 1.5)
    - W_sensitivity: Ecological, recreational, and economic vulnerability weight (0.85 to 1.5)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# Sector sensitivity weights based on ecological, recreational, and infrastructure criticality
SECTOR_SENSITIVITY_WEIGHTS: Dict[str, Dict[str, Any]] = {
    "east_coast": {
        "name": "East Coast Park (ECP) Recreational Corridor",
        "weight": 1.40,
        "primary_concern": "High public beach footfall, coastal recreation, and camping amenities.",
        "vulnerability_type": "Recreational & Amenity",
    },
    "southern_islands": {
        "name": "Sentosa & Southern Islands Resort Enclave",
        "weight": 1.35,
        "primary_concern": "Tourism beaches (Siloso/Palawan), coral conservation, and resort lagoons.",
        "vulnerability_type": "Tourism & Marine Ecology",
    },
    "pulau_ubin_sungei_buloh": {
        "name": "Sungei Buloh & Pulau Ubin Wetland Sanctuary",
        "weight": 1.50,
        "primary_concern": "Pristine mangrove wetlands, migratory shorebird habitat, and Chek Jawa biodiversity.",
        "vulnerability_type": "Ecological Sanctuary (Critical)",
    },
    "pasir_ris_changi": {
        "name": "Pasir Ris & Changi Coastal Sector",
        "weight": 1.25,
        "primary_concern": "Estuarine mangrove fringes, recreational parks, and aquaculture kelongs.",
        "vulnerability_type": "Recreational & Aquaculture",
    },
    "jurong_tuas": {
        "name": "Jurong Island & Tuas Industrial Fairway",
        "weight": 1.10,
        "primary_concern": "Industrial water intake cooling channels, container terminals, and port logistics.",
        "vulnerability_type": "Critical Infrastructure",
    },
    "singapore_strait_deep": {
        "name": "Singapore Strait Commercial Traffic Separation Scheme",
        "weight": 0.90,
        "primary_concern": "Commercial maritime shipping navigation and anchorage buffer.",
        "vulnerability_type": "Navigation Fairway",
    },
}

DEFAULT_SECTOR_WEIGHT = 1.0


@dataclass
class CPIScoreBreakdown:
    hotspot_id: str
    hotspot_name: str
    sector_id: str
    sector_name: str
    cpi_score: float             # Final 0 - 100 scaled priority score
    priority_tier: str           # "Critical" | "High" | "Medium" | "Low"
    quantity_score: float        # 0 - 100
    drift_urgency_factor: float  # Multiplier (0.6 - 1.5)
    sensitivity_weight: float    # Multiplier (0.85 - 1.5)
    detection_count: int
    total_area_sq_m: float
    time_to_beach_hours: Optional[float]
    beached_probability_pct: float
    target_shore: Optional[str]
    vulnerability_rationale: str
    action_deadline_hours: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hotspot_id": self.hotspot_id,
            "hotspot_name": self.hotspot_name,
            "sector_id": self.sector_id,
            "sector_name": self.sector_name,
            "cpi_score": round(self.cpi_score, 1),
            "priority_tier": self.priority_tier,
            "quantity_score": round(self.quantity_score, 1),
            "drift_urgency_factor": round(self.drift_urgency_factor, 2),
            "sensitivity_weight": round(self.sensitivity_weight, 2),
            "detection_count": self.detection_count,
            "total_area_sq_m": self.total_area_sq_m,
            "time_to_beach_hours": self.time_to_beach_hours,
            "beached_probability_pct": round(self.beached_probability_pct, 1),
            "target_shore": self.target_shore,
            "vulnerability_rationale": self.vulnerability_rationale,
            "action_deadline_hours": self.action_deadline_hours,
        }


class CoastalPriorityIndexCalculator:
    """Calculates multi-criteria priority rankings for marine debris cleanup operations."""

    def compute_quantity_score(
        self,
        detection_count: int,
        total_area_sq_m: float,
        composite_confidence: float = 85.0,
        severity: str = "High",
    ) -> float:
        """Compute the debris volume/quantity factor on a 0 to 100 normalized scale."""
        # 1. Logarithmic count score (saturates near 500 items)
        norm_count = min(1.0, math.log1p(detection_count) / math.log1p(500))

        # 2. Area score (saturates near 35,000 m²)
        norm_area = min(1.0, total_area_sq_m / 35000.0)

        # 3. Severity baseline multiplier
        sev_mult = {"High": 1.0, "Medium": 0.75, "Low": 0.50}.get(severity, 0.75)

        # 4. Confidence factor
        conf_factor = max(0.5, composite_confidence / 100.0)

        # Blended quantity score
        q_raw = (0.50 * norm_count + 0.50 * norm_area) * sev_mult * conf_factor
        return round(q_raw * 100.0, 1)

    def compute_drift_urgency(
        self,
        beached_probability_pct: float,
        time_to_beach_hours: Optional[float],
        drift_speed_knots: float = 1.0,
    ) -> Tuple[float, float]:
        """Compute drift urgency multiplier (0.6 - 1.5) and action response deadline in hours."""
        prob = beached_probability_pct / 100.0

        if prob >= 0.50 and time_to_beach_hours is not None:
            # Imminent shoreline stranding threat
            if time_to_beach_hours <= 2.0:
                urgency = 1.50
                deadline = 2.0
            elif time_to_beach_hours <= 6.0:
                urgency = 1.35
                deadline = 4.0
            elif time_to_beach_hours <= 12.0:
                urgency = 1.20
                deadline = 8.0
            elif time_to_beach_hours <= 24.0:
                urgency = 1.05
                deadline = 16.0
            else:
                urgency = 0.90
                deadline = 24.0
        elif prob >= 0.20:
            # Moderate stranding probability
            urgency = 0.85
            deadline = 24.0
        else:
            # Debris drifting in open fairway or exiting domain
            urgency = 0.70
            deadline = 48.0

        # Small boost for high drift speeds
        if drift_speed_knots > 1.5:
            urgency = min(1.50, urgency * 1.05)

        return round(urgency, 2), deadline

    def get_sensitivity_info(self, sector_id: str) -> Tuple[float, str, str]:
        """Lookup sensitivity weight and rationale for a coastal sector."""
        if sector_id in SECTOR_SENSITIVITY_WEIGHTS:
            sec = SECTOR_SENSITIVITY_WEIGHTS[sector_id]
            return sec["weight"], sec["name"], sec["primary_concern"]
        return DEFAULT_SECTOR_WEIGHT, "General Coastal Sector", "Standard coastal monitoring area."

    def calculate_cpi(
        self,
        hotspot: Dict[str, Any],
        forecast_summary: Optional[Dict[str, Any]] = None,
    ) -> CPIScoreBreakdown:
        """Calculate complete CPI score and breakdown for a hotspot."""
        hs_id = hotspot.get("hotspot_id") or hotspot.get("id", "UNKNOWN")
        hs_name = hotspot.get("name", hs_id)
        sec_id = hotspot.get("sector_id", "east_coast")

        count = int(hotspot.get("detection_count") or hotspot.get("items_count", 1))
        area_sq_m = float(hotspot.get("total_area_sq_m", 100.0))
        confidence = float(hotspot.get("composite_confidence", 85.0))
        severity = hotspot.get("severity", "High")

        # Extract Phase 3 forecast dynamics if available
        beached_prob = 0.0
        t_beach: Optional[float] = None
        target_shore: Optional[str] = None
        drift_speed = 1.0

        if forecast_summary:
            beached_prob = float(forecast_summary.get("beached_prob", 0.0))
            target_shore = forecast_summary.get("target_shore")
            # If beached, estimate time from forecast horizon
            if beached_prob > 0.0:
                t_beach = float(forecast_summary.get("time_to_beach_hours", 6.0))

        # 1. Quantity Score Q
        q_score = self.compute_quantity_score(count, area_sq_m, confidence, severity)

        # 2. Urgency Factor U
        urgency_mult, deadline_hrs = self.compute_drift_urgency(beached_prob, t_beach, drift_speed)

        # 3. Sensitivity Weight W
        sens_weight, sec_name, rationale = self.get_sensitivity_info(sec_id)

        # Combined CPI score (normalized to 0 - 100)
        raw_cpi = (q_score / 100.0) * urgency_mult * sens_weight * 100.0
        cpi = min(100.0, max(5.0, raw_cpi))

        # Determine Priority Tier
        if cpi >= 70.0:
            tier = "Critical"
        elif cpi >= 45.0:
            tier = "High"
        elif cpi >= 25.0:
            tier = "Medium"
        else:
            tier = "Low"

        return CPIScoreBreakdown(
            hotspot_id=hs_id,
            hotspot_name=hs_name,
            sector_id=sec_id,
            sector_name=sec_name,
            cpi_score=round(cpi, 1),
            priority_tier=tier,
            quantity_score=q_score,
            drift_urgency_factor=urgency_mult,
            sensitivity_weight=sens_weight,
            detection_count=count,
            total_area_sq_m=area_sq_m,
            time_to_beach_hours=t_beach,
            beached_probability_pct=beached_prob,
            target_shore=target_shore,
            vulnerability_rationale=rationale,
            action_deadline_hours=deadline_hrs,
        )

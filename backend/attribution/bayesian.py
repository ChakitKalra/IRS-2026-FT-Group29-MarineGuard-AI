"""Bayesian Source Attribution Classifier with NEA Empirical Prior Conditioning.

Combines backward Lagrangian trajectory intersection likelihoods with empirical
priors from the Singapore National Environment Agency (NEA) marine litter baseline
study (97% offshore/transboundary vs. 3% inland waterways), dynamically modulated
by the real-time Inland Flushing Index (IFI) and rainfall conditions.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from backend.attribution.backtracking import BacktrackingResult
from backend.attribution.sources import SOURCE_DOMAINS, SourceDomain


@dataclass
class SourceAttributionEntry:
    source_id: str
    source_name: str
    category: str              # "marine_transboundary" | "inland_local"
    color: str
    prior_probability: float
    trajectory_likelihood: float
    posterior_probability: float
    percentage: float          # Posterior % (0 - 100)
    description: str


@dataclass
class AttributionReport:
    hotspot_id: str
    hotspot_name: str
    detection_lat: float
    detection_lng: float
    estimated_origin_lat: float
    estimated_origin_lng: float
    estimated_release_hours_ago: float
    inland_flushing_index: float
    inland_flushing_risk: str
    rainfall_mm_hr: float
    top_source_id: str
    top_source_name: str
    top_source_confidence: str # "High" | "Moderate" | "Fair"
    top_source_percentage: float
    runner_up_source_id: str
    runner_up_source_name: str
    runner_up_percentage: float
    total_marine_transboundary_pct: float
    total_inland_local_pct: float
    attribution_breakdown: List[SourceAttributionEntry]
    operational_narrative: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hotspot_id": self.hotspot_id,
            "hotspot_name": self.hotspot_name,
            "detection_coordinates": [self.detection_lat, self.detection_lng],
            "estimated_origin": {
                "latitude": self.estimated_origin_lat,
                "longitude": self.estimated_origin_lng,
                "release_hours_ago": self.estimated_release_hours_ago,
            },
            "environmental_context": {
                "inland_flushing_index": self.inland_flushing_index,
                "inland_flushing_risk": self.inland_flushing_risk,
                "rainfall_mm_hr": self.rainfall_mm_hr,
            },
            "classification": {
                "top_source_id": self.top_source_id,
                "top_source_name": self.top_source_name,
                "top_source_confidence": self.top_source_confidence,
                "top_source_percentage": self.top_source_percentage,
                "runner_up_source_id": self.runner_up_source_id,
                "runner_up_source_name": self.runner_up_source_name,
                "runner_up_percentage": self.runner_up_percentage,
                "total_marine_transboundary_pct": self.total_marine_transboundary_pct,
                "total_inland_local_pct": self.total_inland_local_pct,
            },
            "breakdown": [
                {
                    "source_id": e.source_id,
                    "source_name": e.source_name,
                    "category": e.category,
                    "color": e.color,
                    "prior_probability": round(e.prior_probability, 4),
                    "trajectory_likelihood": round(e.trajectory_likelihood, 4),
                    "posterior_probability": round(e.posterior_probability, 4),
                    "percentage": e.percentage,
                    "description": e.description,
                }
                for e in self.attribution_breakdown
            ],
            "operational_narrative": self.operational_narrative,
        }


class BayesianSourceAttributor:
    """Computes posterior attribution probabilities conditioned on physics & NEA baseline."""

    def __init__(
        self,
        base_marine_prior: float = 0.97,    # NEA Singapore study: 97% marine/transboundary
        base_inland_prior: float = 0.03,    # NEA Singapore study: 3% inland waterways
    ):
        self.base_marine_prior = base_marine_prior
        self.base_inland_prior = base_inland_prior

    def compute_priors(
        self,
        inland_flushing_index: float,
    ) -> Dict[str, float]:
        """Compute empirical prior distribution adjusted by real-time canal flushing."""
        # Normalize IFI between 0.0 and 1.0
        ifi = max(0.0, min(1.0, inland_flushing_index))

        # Under severe rain / canal flushes, inland prior scales up to 35%
        inland_boost = 0.35 * ifi
        adjusted_inland_total = min(0.40, self.base_inland_prior + inland_boost)
        adjusted_marine_total = 1.0 - adjusted_inland_total

        # Apportion among specific domains
        # Marine sub-domains proportioned by baseline weights (55:25:17)
        marine_norm = 0.55 + 0.25 + 0.17 # = 0.97
        p_shipping = adjusted_marine_total * (0.55 / marine_norm)
        p_riau = adjusted_marine_total * (0.25 / marine_norm)
        p_johor = adjusted_marine_total * (0.17 / marine_norm)

        # Inland sub-domains proportioned: canal gets boost from ifi, beachgoers stays baseline
        p_canals = adjusted_inland_total * 0.85
        p_beachgoers = adjusted_inland_total * 0.15

        priors = {
            "marine_traffic": p_shipping,
            "transboundary_riau": p_riau,
            "johor_strait": p_johor,
            "inland_canals": p_canals,
            "recreational_beachgoers": p_beachgoers,
        }

        # Normalize to ensure exact sum = 1.0
        total_p = sum(priors.values())
        return {k: v / total_p for k, v in priors.items()}

    def compute_likelihoods(
        self,
        backtracking: BacktrackingResult,
    ) -> Dict[str, float]:
        """Compute trajectory evidence likelihood P(Trajectory | Source Domain)."""
        likelihoods: Dict[str, float] = {}
        total_hits = max(sum(backtracking.source_hit_counts.values()), 1)

        for src_id, src_domain in SOURCE_DOMAINS.items():
            hit_freq = backtracking.source_hit_counts.get(src_id, 0) / float(total_hits)

            # Proximity kernel from estimated release origin to domain boundary
            dist_km = src_domain.distance_to_point_km(
                backtracking.estimated_origin_lat,
                backtracking.estimated_origin_lng,
            )
            # Gaussian kernel with sigma = 4.0 km
            prox_weight = math.exp(-(dist_km ** 2) / (2.0 * (4.0 ** 2)))

            # Combined likelihood with Laplace smoothing epsilon = 0.02
            raw_likelihood = 0.75 * hit_freq + 0.25 * prox_weight + 0.02
            likelihoods[src_id] = raw_likelihood

        # Normalize likelihoods across domains
        sum_l = sum(likelihoods.values())
        return {k: v / sum_l for k, v in likelihoods.items()}

    def attribute(
        self,
        backtracking: BacktrackingResult,
        inland_flushing_index: float = 0.0,
        inland_flushing_risk: str = "Low",
        rainfall_mm_hr: float = 0.0,
    ) -> AttributionReport:
        """Run Bayesian attribution combining backtracking evidence with NEA prior."""
        priors = self.compute_priors(inland_flushing_index)
        likelihoods = self.compute_likelihoods(backtracking)

        # Compute unnormalized posterior: P(S | D) ~ P(D | S) * P(S)
        unnorm_posteriors: Dict[str, float] = {}
        for src_id in SOURCE_DOMAINS.keys():
            unnorm_posteriors[src_id] = likelihoods[src_id] * priors[src_id]

        total_unnorm = max(sum(unnorm_posteriors.values()), 1e-9)
        posteriors = {k: v / total_unnorm for k, v in unnorm_posteriors.items()}

        # Build entry breakdown
        breakdown: List[SourceAttributionEntry] = []
        for src_id, p_post in sorted(posteriors.items(), key=lambda item: item[1], reverse=True):
            src_domain = SOURCE_DOMAINS[src_id]
            pct = round(p_post * 100.0, 1)
            breakdown.append(
                SourceAttributionEntry(
                    source_id=src_id,
                    source_name=src_domain.name,
                    category=src_domain.category,
                    color=src_domain.color,
                    prior_probability=priors[src_id],
                    trajectory_likelihood=likelihoods[src_id],
                    posterior_probability=p_post,
                    percentage=pct,
                    description=src_domain.description,
                )
            )

        top_entry = breakdown[0]
        runner_up = breakdown[1] if len(breakdown) > 1 else breakdown[0]

        # Confidence level heuristic
        if top_entry.percentage >= 60.0:
            confidence = "High"
        elif top_entry.percentage >= 40.0:
            confidence = "Moderate"
        else:
            confidence = "Fair"

        # Group totals
        marine_pct = round(
            sum(e.percentage for e in breakdown if e.category == "marine_transboundary"), 1
        )
        inland_pct = round(
            sum(e.percentage for e in breakdown if e.category == "inland_local"), 1
        )

        # Generate operational narrative
        narrative = self._generate_narrative(
            backtracking=backtracking,
            top_entry=top_entry,
            runner_up=runner_up,
            marine_pct=marine_pct,
            inland_pct=inland_pct,
            ifi=inland_flushing_index,
            rainfall=rainfall_mm_hr,
        )

        return AttributionReport(
            hotspot_id=backtracking.hotspot_id,
            hotspot_name=backtracking.hotspot_name,
            detection_lat=backtracking.detection_lat,
            detection_lng=backtracking.detection_lng,
            estimated_origin_lat=backtracking.estimated_origin_lat,
            estimated_origin_lng=backtracking.estimated_origin_lng,
            estimated_release_hours_ago=backtracking.estimated_release_hours_ago,
            inland_flushing_index=round(inland_flushing_index, 3),
            inland_flushing_risk=inland_flushing_risk,
            rainfall_mm_hr=round(rainfall_mm_hr, 1),
            top_source_id=top_entry.source_id,
            top_source_name=top_entry.source_name,
            top_source_confidence=confidence,
            top_source_percentage=top_entry.percentage,
            runner_up_source_id=runner_up.source_id,
            runner_up_source_name=runner_up.source_name,
            runner_up_percentage=runner_up.percentage,
            total_marine_transboundary_pct=marine_pct,
            total_inland_local_pct=inland_pct,
            attribution_breakdown=breakdown,
            operational_narrative=narrative,
        )

    def _generate_narrative(
        self,
        backtracking: BacktrackingResult,
        top_entry: SourceAttributionEntry,
        runner_up: SourceAttributionEntry,
        marine_pct: float,
        inland_pct: float,
        ifi: float,
        rainfall: float,
    ) -> str:
        """Formulate a concise operational narrative for maritime and coastal authorities."""
        t_hrs = backtracking.estimated_release_hours_ago
        src_name = top_entry.source_name
        pct = top_entry.percentage

        if ifi > 0.4:
            rain_ctx = f"Elevated canal runoff detected (IFI: {ifi:.2f}, Rain: {rainfall:.1f} mm/hr), contributing to inland sluice gate flushes."
        else:
            rain_ctx = "Dry weather conditions prevail; inland runoff minimal, aligning with NEA baseline marine dominance (97%)."

        return (
            f"Lagrangian reverse advection (-{t_hrs}h) indicates high attribution confidence to {src_name} "
            f"({pct}% posterior probability). Secondary influence from {runner_up.source_name} ({runner_up.percentage}%). "
            f"Overall split: {marine_pct}% Marine/Transboundary vs. {inland_pct}% Inland/Shoreline. {rain_ctx}"
        )

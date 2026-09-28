from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Mapping, Optional

from confidence_result import CONFIDENCE_DIMENSIONS


@dataclass(frozen=True)
class ConfidenceWeights:
    """
    Weights used to aggregate independently evaluated confidence
    dimensions.

    Equal weighting is intentionally used as the initial deterministic
    contract because the Module 09 specification does not prescribe
    domain-specific weights.
    """

    history_availability: float = 1.0
    candidate_completeness: float = 1.0
    behavioral_consistency: float = 1.0
    session_maturity: float = 1.0
    behavioral_stability: float = 1.0

    def as_dict(self) -> Dict[str, float]:
        return {
            "history_availability": self.history_availability,
            "candidate_completeness": self.candidate_completeness,
            "behavioral_consistency": self.behavioral_consistency,
            "session_maturity": self.session_maturity,
            "behavioral_stability": self.behavioral_stability,
        }

    def __post_init__(self) -> None:
        weights = self.as_dict()

        for name, weight in weights.items():
            if weight < 0.0:
                raise ValueError(
                    f"Confidence weight {name!r} cannot be negative"
                )

        if not any(weight > 0.0 for weight in weights.values()):
            raise ValueError(
                "At least one confidence weight must be positive"
            )


class ConfidenceCalculator:
    """
    Aggregates independently evaluated confidence dimensions.

    This class does not determine what confidence means for a particular
    Candidate Pattern. That responsibility belongs to ConfidenceEvaluator.
    """

    def __init__(
        self,
        weights: Optional[ConfidenceWeights] = None,
    ) -> None:
        self._weights = weights or ConfidenceWeights()

    @property
    def weights(self) -> ConfidenceWeights:
        return self._weights

    def calculate(
        self,
        dimension_scores: Mapping[
            str,
            Optional[float],
        ],
    ) -> float:
        score, _ = self.calculate_with_details(
            dimension_scores
        )
        return score

    def calculate_with_details(
        self,
        dimension_scores: Mapping[
            str,
            Optional[float],
        ],
    ) -> tuple[float, Dict[str, object]]:

        weights = self._weights.as_dict()

        weighted_total = 0.0
        active_weight = 0.0
        available_dimensions = []

        for dimension in CONFIDENCE_DIMENSIONS:
            value = dimension_scores.get(dimension)
            weight = weights[dimension]

            if value is None:
                continue

            if weight <= 0.0:
                continue

            if not 0.0 <= float(value) <= 1.0:
                raise ValueError(
                    f"Confidence dimension {dimension!r} "
                    "must be between 0.0 and 1.0"
                )

            weighted_total += float(value) * weight
            active_weight += weight
            available_dimensions.append(dimension)

        if active_weight == 0.0:
            return (
                0.0,
                {
                    "available_dimensions": [],
                    "active_weight": 0.0,
                    "weighted_total": 0.0,
                },
            )

        score = weighted_total / active_weight

        return (
            max(0.0, min(1.0, score)),
            {
                "available_dimensions": available_dimensions,
                "active_weight": active_weight,
                "weighted_total": weighted_total,
            },
        )

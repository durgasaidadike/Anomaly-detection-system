from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional


DRIFT_DIMENSIONS = (
    "behavioral_workflow",
    "operation_frequency",
    "temporal_characteristics",
    "working_rhythm",
    "behavioral_relationships",
    "session_characteristics",
    "contextual_behavior",
)


@dataclass(frozen=True)
class DriftWeights:
    """
    Weights used when aggregating dimension-level Drift values.

    All dimensions default to equal importance.
    """

    behavioral_workflow: float = 1.0
    operation_frequency: float = 1.0
    temporal_characteristics: float = 1.0
    working_rhythm: float = 1.0
    behavioral_relationships: float = 1.0
    session_characteristics: float = 1.0
    contextual_behavior: float = 1.0

    def __post_init__(self) -> None:
        for dimension in DRIFT_DIMENSIONS:
            weight = getattr(self, dimension)

            if weight < 0.0:
                raise ValueError(
                    f"Drift weight for '{dimension}' "
                    f"cannot be negative."
                )

    def as_dict(self) -> Dict[str, float]:
        return {
            dimension: getattr(self, dimension)
            for dimension in DRIFT_DIMENSIONS
        }


class DriftCalculator:
    """
    Aggregates dimension-level Drift measurements into
    one normalized Drift score.

    This class does not:
    - retrieve historical patterns
    - compare patterns itself
    - perform ML
    - calculate Similarity
    - calculate Confidence
    - make anomaly decisions
    """

    def __init__(
        self,
        weights: Optional[DriftWeights] = None,
    ) -> None:
        self._weights = weights or DriftWeights()

    @property
    def weights(self) -> DriftWeights:
        return self._weights

    def calculate(
        self,
        dimension_scores: Dict[str, Optional[float]],
    ) -> Optional[float]:
        """
        Calculate the weighted Drift score.

        None values represent unavailable dimensions and are
        excluded from the aggregation.

        Zero-weight dimensions are also excluded.

        Returns:
            A normalized score between 0.0 and 1.0,
            or None when no usable dimensions exist.
        """

        score, _ = self.calculate_with_details(
            dimension_scores
        )

        return score

    def calculate_with_details(
        self,
        dimension_scores: Dict[str, Optional[float]],
    ) -> tuple[
        Optional[float],
        Dict[str, object],
    ]:
        """
        Calculate Drift and return calculation metadata.
        """

        weights = self._weights.as_dict()

        weighted_sum = 0.0
        total_weight = 0.0

        available_dimensions = []
        unavailable_dimensions = []

        for dimension in DRIFT_DIMENSIONS:
            value = dimension_scores.get(dimension)

            if value is None:
                unavailable_dimensions.append(dimension)
                continue

            self._validate_score(dimension, value)

            weight = weights[dimension]

            if weight <= 0.0:
                unavailable_dimensions.append(
                    dimension
                )
                continue

            available_dimensions.append(dimension)

            weighted_sum += value * weight
            total_weight += weight

        if total_weight == 0.0:
            return (
                None,
                {
                    "available_dimensions": [],
                    "unavailable_dimensions": (
                        unavailable_dimensions
                    ),
                    "weights_used": {},
                },
            )

        score = weighted_sum / total_weight

        weights_used = {
            dimension: weights[dimension]
            for dimension in available_dimensions
        }

        return (
            score,
            {
                "available_dimensions": available_dimensions,
                "unavailable_dimensions": (
                    unavailable_dimensions
                ),
                "weights_used": weights_used,
            },
        )

    @staticmethod
    def _validate_score(
        dimension: str,
        value: float,
    ) -> None:
        if not 0.0 <= value <= 1.0:
            raise ValueError(
                f"Drift score for '{dimension}' "
                f"must be between 0.0 and 1.0."
            )

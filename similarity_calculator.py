from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class SimilarityWeights:
    """
    Explicit weights used to combine behavioral dimensions.

    Keeping the weights explicit makes the similarity calculation
    configurable and prevents hidden weighting decisions.
    """

    operational: float = 1.0
    temporal: float = 1.0
    sequential: float = 1.0
    contextual: float = 1.0
    relationship: float = 1.0
    session: float = 1.0

    def as_dict(self) -> Dict[str, float]:
        """
        Return the configured weights as a dictionary.
        """

        return {
            "operational": self.operational,
            "temporal": self.temporal,
            "sequential": self.sequential,
            "contextual": self.contextual,
            "relationship": self.relationship,
            "session": self.session,
        }


class SimilarityCalculator:
    """
    Aggregates dimension-level behavioral similarity scores
    into one normalized similarity metric.

    This class performs mathematical aggregation only.

    It does not:
    - retrieve patterns
    - access repositories
    - perform ML
    - detect anomalies
    - modify patterns
    """

    def __init__(
        self,
        weights: Optional[SimilarityWeights] = None,
    ) -> None:
        self._weights = weights or SimilarityWeights()
        self._validate_weights()

    @property
    def weights(self) -> SimilarityWeights:
        """
        Return the configured similarity weights.
        """

        return self._weights

    def calculate(
        self,
        dimension_scores: Dict[str, Optional[float]],
    ) -> Optional[float]:
        """
        Calculate the weighted similarity score.

        Dimensions with unavailable information (None) are excluded
        from the calculation.

        Returns:
            float -> normalized similarity score in [0.0, 1.0]
            None  -> insufficient behavioral information
        """

        if not dimension_scores:
            return None

        weights = self._weights.as_dict()

        weighted_sum = 0.0
        weight_sum = 0.0

        for dimension, score in dimension_scores.items():
            if dimension not in weights:
                continue

            if score is None:
                continue

            self._validate_score(
                dimension,
                score,
            )

            weight = weights[dimension]

            if weight <= 0.0:
                continue

            weighted_sum += score * weight
            weight_sum += weight

        if weight_sum == 0.0:
            return None

        result = weighted_sum / weight_sum

        return max(
            0.0,
            min(
                1.0,
                result,
            ),
        )

    def calculate_with_details(
        self,
        dimension_scores: Dict[str, Optional[float]],
    ) -> Dict[str, object]:
        """
        Calculate the similarity score and provide calculation
        metadata useful to downstream consumers.
        """

        score = self.calculate(dimension_scores)

        available_dimensions = [
            dimension
            for dimension, value in dimension_scores.items()
            if value is not None
            and dimension in self._weights.as_dict()
            and self._weights.as_dict()[dimension] > 0.0
        ]

        unavailable_dimensions = [
            dimension
            for dimension, value in dimension_scores.items()
            if value is None
        ]

        return {
            "score": score,
            "available_dimensions": available_dimensions,
            "unavailable_dimensions": unavailable_dimensions,
            "dimensions_used": len(available_dimensions),
            "weights": self._weights.as_dict(),
        }

    def _validate_weights(self) -> None:
        """
        Ensure every configured weight is finite and non-negative.
        """

        for dimension, weight in self._weights.as_dict().items():
            if weight < 0.0:
                raise ValueError(
                    f"Weight for '{dimension}' cannot be negative."
                )

    @staticmethod
    def _validate_score(
        dimension: str,
        score: float,
    ) -> None:
        """
        Validate a dimension-level similarity score.
        """

        if not 0.0 <= score <= 1.0:
            raise ValueError(
                f"Similarity score for '{dimension}' "
                "must be between 0.0 and 1.0."
            )

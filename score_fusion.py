from __future__ import annotations

import math
from collections.abc import Mapping, Sequence

from score_calibration import CalibratedModelScore


class WeightedScoreFusion:
    """
    Combines calibrated model scores using explicitly supplied weights.

    The fusion mechanism is intentionally independent from the choice
    of model weights. PRISM configuration supplies those weights.

    Fusion behavior:
        weighted mean =
            sum(score * weight) / sum(weight)

    Only models present in the supplied score collection participate.

    This class does not:
    - choose risk levels
    - apply decision thresholds
    - perform recovery
    - modify behavioral knowledge
    - train ML models
    """

    def __init__(
        self,
        weights: Mapping[str, float],
    ) -> None:
        self._weights = self._validate_weights(weights)

    @staticmethod
    def _validate_weights(
        weights: Mapping[str, float],
    ) -> dict[str, float]:
        if not isinstance(weights, Mapping):
            raise TypeError(
                "weights must be a mapping."
            )

        validated: dict[str, float] = {}

        for model_name, weight in weights.items():
            if not isinstance(model_name, str) or not model_name.strip():
                raise ValueError(
                    "Model names in fusion weights must be "
                    "non-empty strings."
                )

            if not isinstance(weight, (int, float)):
                raise ValueError(
                    f"Weight for model '{model_name}' "
                    "must be numerical."
                )

            numeric_weight = float(weight)

            if not math.isfinite(numeric_weight):
                raise ValueError(
                    f"Weight for model '{model_name}' "
                    "must be finite."
                )

            if numeric_weight <= 0.0:
                raise ValueError(
                    f"Weight for model '{model_name}' "
                    "must be greater than zero."
                )

            validated[model_name] = numeric_weight

        if not validated:
            raise ValueError(
                "At least one fusion weight is required."
            )

        return validated

    def combine(
        self,
        scores: Sequence[CalibratedModelScore],
    ) -> float:
        if not isinstance(scores, Sequence):
            raise TypeError(
                "scores must be a sequence."
            )

        if not scores:
            raise ValueError(
                "At least one calibrated model score is required."
            )

        weighted_total = 0.0
        weight_total = 0.0
        seen_models: set[str] = set()

        for score in scores:
            if not isinstance(
                score,
                CalibratedModelScore,
            ):
                raise TypeError(
                    "All fusion inputs must be "
                    "CalibratedModelScore instances."
                )

            if score.model_name in seen_models:
                raise ValueError(
                    f"Duplicate model score supplied for "
                    f"'{score.model_name}'."
                )

            seen_models.add(score.model_name)

            weight = self._weights.get(
                score.model_name
            )

            if weight is None:
                raise ValueError(
                    f"No fusion weight configured for "
                    f"model '{score.model_name}'."
                )

            weighted_total += (
                score.calibrated_score * weight
            )
            weight_total += weight

        if weight_total <= 0.0:
            raise ValueError(
                "Total fusion weight must be greater than zero."
            )

        result = (
            weighted_total / weight_total
        )

        if not math.isfinite(result):
            raise ValueError(
                "Fusion produced a non-finite result."
            )

        return float(result)

    def configured_models(self) -> tuple[str, ...]:
        return tuple(self._weights.keys())

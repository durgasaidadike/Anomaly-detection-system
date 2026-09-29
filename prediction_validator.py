from __future__ import annotations

import math


class PredictionValidator:
    """
    Validates raw numerical predictions produced by ML models.

    This validator does not assign anomaly meaning and does not
    transform model-specific scores. It only verifies that a
    prediction is structurally valid and safe to use.
    """

    @staticmethod
    def validate(
        *,
        model_name: str,
        prediction: float,
    ) -> float:
        if not isinstance(model_name, str) or not model_name.strip():
            raise ValueError(
                "model_name must be a non-empty string."
            )

        if not isinstance(prediction, (int, float)):
            raise ValueError(
                f"Prediction from model '{model_name}' "
                "must be numerical."
            )

        normalized_prediction = float(prediction)

        if not math.isfinite(normalized_prediction):
            raise ValueError(
                f"Prediction from model '{model_name}' "
                "must be finite."
            )

        return normalized_prediction

from __future__ import annotations

from dataclasses import dataclass

from prediction_validator import PredictionValidator
from score_semantics import (
    ScoreDirection,
    to_anomaly_direction,
)


@dataclass(frozen=True)
class ModelScore:
    """
    Validated numerical result produced by one ML model.
    """

    model_name: str
    score: float

    def __post_init__(self) -> None:
        validated_score = PredictionValidator.validate(
            model_name=self.model_name,
            prediction=self.score,
        )

        object.__setattr__(
            self,
            "score",
            validated_score,
        )

    def as_anomaly_score(
        self,
        direction: ScoreDirection,
    ) -> float:
        """
        Return the score using PRISM's canonical anomaly direction.

        Higher values indicate greater anomaly-oriented magnitude.

        The original raw score stored in this ModelScore is not
        modified.
        """

        return to_anomaly_direction(
            self.score,
            direction,
        )


@dataclass(frozen=True)
class ModelEvaluation:
    """
    Collection of validated model-level results for one
    behavioral evaluation.
    """

    pattern_id: str
    knowledge_id: str
    model_scores: tuple[ModelScore, ...]

    def model_count(self) -> int:
        """
        Return the number of model results contained
        in this evaluation.
        """
        return len(self.model_scores)

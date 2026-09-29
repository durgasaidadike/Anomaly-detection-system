from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelScore:
    """
    Result produced by one ML model.
    """

    model_name: str
    score: float


@dataclass(frozen=True)
class ModelEvaluation:
    """
    Collection of model-level results for one behavioral evaluation.
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

from __future__ import annotations

from dataclasses import dataclass

from ml_result_models import ModelEvaluation


@dataclass(frozen=True)
class ModelFailure:
    """
    Metadata describing a model that could not produce
    a valid prediction.
    """

    model_name: str
    error_type: str
    error_message: str


@dataclass(frozen=True)
class InferenceResult:
    """
    Complete result of one ML inference pass.

    Successful predictions are represented by ModelEvaluation.
    Failed models are represented separately so partial failure
    does not destroy valid model results.
    """

    evaluation: ModelEvaluation
    failures: tuple[ModelFailure, ...]

    def successful_model_count(self) -> int:
        return self.evaluation.model_count()

    def failed_model_count(self) -> int:
        return len(self.failures)

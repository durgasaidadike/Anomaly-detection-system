from __future__ import annotations

import logging

from feature_vector_models import FeatureVector
from ml_inference_results import (
    InferenceResult,
    ModelFailure,
)
from ml_model_registry import MLModelRegistry
from ml_result_models import (
    ModelEvaluation,
    ModelScore,
)

logger = logging.getLogger(__name__)


class MLInferenceEngine:
    """
    Coordinates model inference for one FeatureVector.

    Responsibilities:
    - validate the incoming FeatureVector boundary
    - invoke registered models
    - preserve valid model results
    - isolate individual model failures
    - produce inference metadata

    It does not:
    - normalize scores
    - fuse scores
    - make risk decisions
    - perform recovery
    - store behavioral knowledge
    """

    def __init__(
        self,
        registry: MLModelRegistry,
    ) -> None:
        if registry is None:
            raise ValueError(
                "Model registry cannot be None."
            )

        self._registry = registry

    def predict(
        self,
        vector: FeatureVector,
    ) -> InferenceResult:
        if not isinstance(vector, FeatureVector):
            raise TypeError(
                "MLInferenceEngine requires a FeatureVector."
            )

        if not vector.is_complete():
            raise ValueError(
                f"Feature vector for pattern "
                f"'{vector.pattern_id}' is incomplete."
            )

        scores: list[ModelScore] = []
        failures: list[ModelFailure] = []

        for model in self._registry:
            model_name = model.model_name

            try:
                raw_score = model.predict(vector)

                score = ModelScore(
                    model_name=model_name,
                    score=raw_score,
                )

                scores.append(score)

            except Exception as exc:
                failure = ModelFailure(
                    model_name=model_name,
                    error_type=type(exc).__name__,
                    error_message=str(exc),
                )

                failures.append(failure)

                logger.exception(
                    "ML model '%s' failed during inference.",
                    model_name,
                )

        evaluation = ModelEvaluation(
            pattern_id=vector.pattern_id,
            knowledge_id=vector.knowledge_id,
            model_scores=tuple(scores),
        )

        return InferenceResult(
            evaluation=evaluation,
            failures=tuple(failures),
        )

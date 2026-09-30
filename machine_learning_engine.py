from __future__ import annotations

from feature_vector_models import FeatureVector
from ml_inference_engine import MLInferenceEngine
from ml_model_registry import MLModelRegistry
from score_calibration import ScoreCalibrationEngine
from score_fusion import WeightedScoreFusion
from ensemble_result_models import EnsembleResult, MLMetadata


class MachineLearningEngine:
    """
    Public orchestration layer for PRISM Machine Learning inference.

    Coordinates:
        FeatureVector
            -> model inference
            -> score calibration
            -> weighted fusion
            -> EnsembleResult

    This component performs ML inference only.
    It does not perform risk classification, recovery, persistence,
    behavioral learning, or decision making.
    """

    def __init__(
        self,
        *,
        registry: MLModelRegistry,
        inference_engine: MLInferenceEngine,
        calibration_engine: ScoreCalibrationEngine,
        fusion_engine: WeightedScoreFusion,
    ) -> None:
        if not isinstance(registry, MLModelRegistry):
            raise TypeError("registry must be an MLModelRegistry")

        if not isinstance(inference_engine, MLInferenceEngine):
            raise TypeError(
                "inference_engine must be an MLInferenceEngine"
            )

        if not isinstance(
            calibration_engine,
            ScoreCalibrationEngine,
        ):
            raise TypeError(
                "calibration_engine must be a ScoreCalibrationEngine"
            )

        if not isinstance(
            fusion_engine,
            WeightedScoreFusion,
        ):
            raise TypeError(
                "fusion_engine must be a WeightedScoreFusion"
            )

        self._registry = registry
        self._inference_engine = inference_engine
        self._calibration_engine = calibration_engine
        self._fusion_engine = fusion_engine

    def predict(self, vector: FeatureVector) -> EnsembleResult:
        """
        Execute the complete PRISM ML inference pipeline
        for one FeatureVector.
        """

        if not isinstance(vector, FeatureVector):
            raise TypeError(
                "vector must be a FeatureVector"
            )

        if not vector.is_complete():
            raise ValueError(
                "FeatureVector must be complete"
            )

        inference_result = self._inference_engine.predict(vector)

        model_scores = inference_result.evaluation.model_scores

        if not model_scores:
            raise RuntimeError(
                "No model produced a valid prediction"
            )

        calibrated_scores = []

        for model_score in model_scores:
            model = self._registry.get(
                model_score.model_name
            )

            calibrated_score = self._calibration_engine.calibrate(
                model_score=model_score,
                direction=model.score_direction,
            )

            calibrated_scores.append(calibrated_score)

        calibrated_scores = tuple(calibrated_scores)

        anomaly_score = self._fusion_engine.combine(
            calibrated_scores
        )

        failures = inference_result.failures

        metadata = MLMetadata(
            configured_model_names=self._registry.names(),
            successful_model_names=tuple(
                score.model_name
                for score in model_scores
            ),
            failed_model_names=tuple(
                failure.model_name
                for failure in failures
            ),
        )

        return EnsembleResult(
            pattern_id=inference_result.evaluation.pattern_id,
            knowledge_id=inference_result.evaluation.knowledge_id,
            model_scores=tuple(model_scores),
            calibrated_scores=calibrated_scores,
            anomaly_score=anomaly_score,
            failures=tuple(failures),
            metadata=metadata,
        )

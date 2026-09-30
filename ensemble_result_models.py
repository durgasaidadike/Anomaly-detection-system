from __future__ import annotations

import math
from dataclasses import dataclass

from ml_inference_results import ModelFailure
from ml_result_models import ModelScore
from score_calibration import CalibratedModelScore


@dataclass(frozen=True)
class MLMetadata:
    configured_model_names: tuple[str, ...]
    successful_model_names: tuple[str, ...]
    failed_model_names: tuple[str, ...]

    def configured_model_count(self) -> int:
        return len(self.configured_model_names)

    def successful_model_count(self) -> int:
        return len(self.successful_model_names)

    def failed_model_count(self) -> int:
        return len(self.failed_model_names)


@dataclass(frozen=True)
class EnsembleResult:
    pattern_id: str
    knowledge_id: str
    model_scores: tuple[ModelScore, ...]
    calibrated_scores: tuple[CalibratedModelScore, ...]
    anomaly_score: float
    failures: tuple[ModelFailure, ...]
    metadata: MLMetadata

    def __post_init__(self) -> None:
        if not isinstance(self.pattern_id, str) or not self.pattern_id.strip():
            raise ValueError("pattern_id must be a non-empty string")

        if not isinstance(self.knowledge_id, str) or not self.knowledge_id.strip():
            raise ValueError("knowledge_id must be a non-empty string")

        if not self.model_scores:
            raise ValueError("model_scores must not be empty")

        if not self.calibrated_scores:
            raise ValueError("calibrated_scores must not be empty")

        if not isinstance(self.anomaly_score, (int, float)):
            raise ValueError("anomaly_score must be numeric")

        anomaly_score = float(self.anomaly_score)

        if not math.isfinite(anomaly_score):
            raise ValueError("anomaly_score must be finite")

        if not isinstance(self.metadata, MLMetadata):
            raise TypeError("metadata must be an MLMetadata instance")

        raw_model_names = tuple(
            score.model_name for score in self.model_scores
        )

        calibrated_model_names = tuple(
            score.model_name for score in self.calibrated_scores
        )

        if len(raw_model_names) != len(set(raw_model_names)):
            raise ValueError("model_scores must not contain duplicate model names")

        if len(calibrated_model_names) != len(set(calibrated_model_names)):
            raise ValueError(
                "calibrated_scores must not contain duplicate model names"
            )

        if set(raw_model_names) != set(calibrated_model_names):
            raise ValueError(
                "raw and calibrated scores must refer to the same models"
            )

        successful_names = set(self.metadata.successful_model_names)
        calibrated_names = set(calibrated_model_names)

        if successful_names != calibrated_names:
            raise ValueError(
                "metadata successful_model_names must match calibrated scores"
            )

        failed_names = set(self.metadata.failed_model_names)

        if successful_names & failed_names:
            raise ValueError(
                "a model cannot be both successful and failed"
            )

        failure_names = tuple(
            failure.model_name for failure in self.failures
        )

        if len(failure_names) != len(set(failure_names)):
            raise ValueError(
                "failures must not contain duplicate model names"
            )

        if set(failure_names) != failed_names:
            raise ValueError(
                "metadata failed_model_names must match failures"
            )

        configured_names = set(self.metadata.configured_model_names)

        if not successful_names.issubset(configured_names):
            raise ValueError(
                "successful models must be configured"
            )

        if not failed_names.issubset(configured_names):
            raise ValueError(
                "failed models must be configured"
            )

        object.__setattr__(self, "anomaly_score", anomaly_score)

    def model_count(self) -> int:
        return len(self.model_scores)

    def calibrated_model_count(self) -> int:
        return len(self.calibrated_scores)

    def successful_model_count(self) -> int:
        return self.metadata.successful_model_count()

    def failed_model_count(self) -> int:
        return self.metadata.failed_model_count()


from __future__ import annotations

import math
from dataclasses import dataclass

from ml_inference_results import ModelFailure
from ml_result_models import ModelScore
from score_calibration import CalibratedModelScore


@dataclass(frozen=True)
class MLMetadata:
    """
    Processing metadata describing the participating ML models.

    The metadata is derived from the inference result and does not
    contain behavioral history or persistent state.
    """

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
    """
    Complete statistical result for one FeatureVector evaluation.

    raw model scores:
        Original estimator outputs.

    calibrated scores:
        Model scores after score calibration.

    ensemble_score:
        Result produced by the configured fusion policy.

    failures:
        Models that could not provide a valid prediction.
    """

    pattern_id: str
    knowledge_id: str

    model_scores: tuple[ModelScore, ...]

    calibrated_scores: tuple[CalibratedModelScore, ...]

    ensemble_score: float

    failures: tuple[ModelFailure, ...]

    metadata: MLMetadata

    def __post_init__(self) -> None:
        if not isinstance(
            self.pattern_id,
            str,
        ) or not self.pattern_id.strip():
            raise ValueError(
                "pattern_id must be a non-empty string."
            )

        if not isinstance(
            self.knowledge_id,
            str,
        ) or not self.knowledge_id.strip():
            raise ValueError(
                "knowledge_id must be a non-empty string."
            )

        if not self.model_scores:
            raise ValueError(
                "At least one valid model score is required."
            )

        if not self.calibrated_scores:
            raise ValueError(
                "At least one calibrated model score is required."
            )

        numeric_score = float(
            self.ensemble_score
        )

        if not math.isfinite(numeric_score):
            raise ValueError(
                "ensemble_score must be finite."
            )

        raw_names = tuple(
            score.model_name
            for score in self.model_scores
        )

        calibrated_names = tuple(
            score.model_name
            for score in self.calibrated_scores
        )

        if len(raw_names) != len(
            set(raw_names)
        ):
            raise ValueError(
                "Model scores must contain unique model names."
            )

        if len(calibrated_names) != len(
            set(calibrated_names)
        ):
            raise ValueError(
                "Calibrated model scores must contain "
                "unique model names."
            )

        if set(raw_names) != set(
            calibrated_names
        ):
            raise ValueError(
                "Raw and calibrated model results "
                "must reference the same models."
            )

        metadata_successful = set(
            self.metadata.successful_model_names
        )

        calibrated_model_set = set(
            calibrated_names
        )

        if metadata_successful != (
            calibrated_model_set
        ):
            raise ValueError(
                "Metadata successful-model names must "
                "match calibrated model results."
            )

        failure_names = {
            failure.model_name
            for failure in self.failures
        }

        if failure_names.intersection(
            calibrated_model_set
        ):
            raise ValueError(
                "A model cannot be both successful "
                "and failed."
            )

        object.__setattr__(
            self,
            "ensemble_score",
            numeric_score,
        )

    def model_count(self) -> int:
        return len(self.model_scores)

    def calibrated_model_count(self) -> int:
        return len(self.calibrated_scores)

    def successful_model_count(self) -> int:
        return len(self.calibrated_scores)

    def failed_model_count(self) -> int:
        return len(self.failures)

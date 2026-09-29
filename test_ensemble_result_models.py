import pytest

from ensemble_result_models import (
    EnsembleResult,
    MLMetadata,
)
from ml_inference_results import ModelFailure
from ml_result_models import ModelScore
from score_calibration import CalibratedModelScore


def calibrated(
    model_name: str,
    score: float,
) -> CalibratedModelScore:
    return CalibratedModelScore(
        model_name=model_name,
        raw_score=score,
        canonical_score=score,
        calibrated_score=score,
    )


def build_result() -> EnsembleResult:
    return EnsembleResult(
        pattern_id="pattern-1",
        knowledge_id="knowledge-pattern-1",
        model_scores=(
            ModelScore(
                model_name="IsolationForest",
                score=-0.2,
            ),
            ModelScore(
                model_name="LocalOutlierFactor",
                score=-1.1,
            ),
        ),
        calibrated_scores=(
            calibrated(
                "IsolationForest",
                0.8,
            ),
            calibrated(
                "LocalOutlierFactor",
                0.6,
            ),
        ),
        ensemble_score=0.72,
        failures=(),
        metadata=MLMetadata(
            configured_model_names=(
                "IsolationForest",
                "LocalOutlierFactor",
            ),
            successful_model_names=(
                "IsolationForest",
                "LocalOutlierFactor",
            ),
            failed_model_names=(),
        ),
    )


def test_metadata_counts_models():
    metadata = MLMetadata(
        configured_model_names=(
            "IsolationForest",
            "LocalOutlierFactor",
            "OneClassSVM",
            "EllipticEnvelope",
        ),
        successful_model_names=(
            "IsolationForest",
            "LocalOutlierFactor",
            "EllipticEnvelope",
        ),
        failed_model_names=(
            "OneClassSVM",
        ),
    )

    assert metadata.configured_model_count() == 4
    assert metadata.successful_model_count() == 3
    assert metadata.failed_model_count() == 1


def test_ensemble_result_preserves_identity():
    result = build_result()

    assert result.pattern_id == "pattern-1"
    assert result.knowledge_id == (
        "knowledge-pattern-1"
    )


def test_ensemble_result_preserves_raw_scores():
    result = build_result()

    assert result.model_scores[0].score == -0.2
    assert result.model_scores[1].score == -1.1


def test_ensemble_result_preserves_calibrated_scores():
    result = build_result()

    assert (
        result.calibrated_scores[0].calibrated_score
        == 0.8
    )

    assert (
        result.calibrated_scores[1].calibrated_score
        == 0.6
    )


def test_ensemble_result_preserves_final_score():
    result = build_result()

    assert result.ensemble_score == 0.72


def test_ensemble_result_counts_models():
    result = build_result()

    assert result.model_count() == 2
    assert result.calibrated_model_count() == 2
    assert result.successful_model_count() == 2
    assert result.failed_model_count() == 0


def test_partial_failure_is_preserved():
    result = EnsembleResult(
        pattern_id="pattern-1",
        knowledge_id="knowledge-pattern-1",
        model_scores=(
            ModelScore(
                model_name="IsolationForest",
                score=-0.2,
            ),
            ModelScore(
                model_name="EllipticEnvelope",
                score=0.4,
            ),
        ),
        calibrated_scores=(
            calibrated(
                "IsolationForest",
                0.8,
            ),
            calibrated(
                "EllipticEnvelope",
                0.3,
            ),
        ),
        ensemble_score=0.55,
        failures=(
            ModelFailure(
                model_name="OneClassSVM",
                error_type="RuntimeError",
                error_message="Model unavailable",
            ),
        ),
        metadata=MLMetadata(
            configured_model_names=(
                "IsolationForest",
                "EllipticEnvelope",
                "OneClassSVM",
            ),
            successful_model_names=(
                "IsolationForest",
                "EllipticEnvelope",
            ),
            failed_model_names=(
                "OneClassSVM",
            ),
        ),
    )

    assert result.successful_model_count() == 2
    assert result.failed_model_count() == 1
    assert (
        result.failures[0].model_name
        == "OneClassSVM"
    )


def test_non_finite_ensemble_score_is_rejected():
    with pytest.raises(ValueError):
        result = build_result()

        EnsembleResult(
            pattern_id=result.pattern_id,
            knowledge_id=result.knowledge_id,
            model_scores=result.model_scores,
            calibrated_scores=result.calibrated_scores,
            ensemble_score=float("nan"),
            failures=result.failures,
            metadata=result.metadata,
        )


def test_empty_model_scores_are_rejected():
    with pytest.raises(ValueError):
        result = build_result()

        EnsembleResult(
            pattern_id=result.pattern_id,
            knowledge_id=result.knowledge_id,
            model_scores=(),
            calibrated_scores=result.calibrated_scores,
            ensemble_score=0.5,
            failures=result.failures,
            metadata=result.metadata,
        )


def test_empty_calibrated_scores_are_rejected():
    with pytest.raises(ValueError):
        result = build_result()

        EnsembleResult(
            pattern_id=result.pattern_id,
            knowledge_id=result.knowledge_id,
            model_scores=result.model_scores,
            calibrated_scores=(),
            ensemble_score=0.5,
            failures=result.failures,
            metadata=result.metadata,
        )


def test_raw_and_calibrated_model_sets_must_match():
    result = build_result()

    with pytest.raises(ValueError):
        EnsembleResult(
            pattern_id=result.pattern_id,
            knowledge_id=result.knowledge_id,
            model_scores=result.model_scores,
            calibrated_scores=(
                calibrated(
                    "IsolationForest",
                    0.8,
                ),
                calibrated(
                    "OneClassSVM",
                    0.5,
                ),
            ),
            ensemble_score=0.5,
            failures=result.failures,
            metadata=result.metadata,
        )


def test_success_metadata_must_match_calibrated_results():
    result = build_result()

    with pytest.raises(ValueError):
        EnsembleResult(
            pattern_id=result.pattern_id,
            knowledge_id=result.knowledge_id,
            model_scores=result.model_scores,
            calibrated_scores=result.calibrated_scores,
            ensemble_score=0.5,
            failures=result.failures,
            metadata=MLMetadata(
                configured_model_names=(
                    "IsolationForest",
                    "LocalOutlierFactor",
                ),
                successful_model_names=(
                    "IsolationForest",
                ),
                failed_model_names=(
                    "LocalOutlierFactor",
                ),
            ),
        )


def test_successful_and_failed_model_cannot_overlap():
    result = build_result()

    with pytest.raises(ValueError):
        EnsembleResult(
            pattern_id=result.pattern_id,
            knowledge_id=result.knowledge_id,
            model_scores=result.model_scores,
            calibrated_scores=result.calibrated_scores,
            ensemble_score=0.5,
            failures=(
                ModelFailure(
                    model_name="IsolationForest",
                    error_type="RuntimeError",
                    error_message="failure",
                ),
            ),
            metadata=MLMetadata(
                configured_model_names=(
                    "IsolationForest",
                    "LocalOutlierFactor",
                ),
                successful_model_names=(
                    "IsolationForest",
                    "LocalOutlierFactor",
                ),
                failed_model_names=(),
            ),
        )


def test_ensemble_result_is_immutable():
    result = build_result()

    with pytest.raises(AttributeError):
        result.ensemble_score = 0.9

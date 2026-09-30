import pytest

from ensemble_result_models import EnsembleResult, MLMetadata
from ml_inference_results import ModelFailure
from ml_result_models import ModelScore
from score_calibration import CalibratedModelScore


def make_raw_scores():
    return (
        ModelScore("isolation_forest", -0.2),
        ModelScore("lof", -0.4),
    )


def make_calibrated_scores():
    return (
        CalibratedModelScore(
            model_name="isolation_forest",
            raw_score=-0.2,
            canonical_score=0.2,
            calibrated_score=0.3,
        ),
        CalibratedModelScore(
            model_name="lof",
            raw_score=-0.4,
            canonical_score=0.4,
            calibrated_score=0.5,
        ),
    )


def make_metadata():
    return MLMetadata(
        configured_model_names=(
            "isolation_forest",
            "lof",
        ),
        successful_model_names=(
            "isolation_forest",
            "lof",
        ),
        failed_model_names=(),
    )


def make_result():
    return EnsembleResult(
        pattern_id="pattern-1",
        knowledge_id="knowledge-1",
        model_scores=make_raw_scores(),
        calibrated_scores=make_calibrated_scores(),
        anomaly_score=0.4,
        failures=(),
        metadata=make_metadata(),
    )


def test_metadata_counts():
    metadata = make_metadata()

    assert metadata.configured_model_count() == 2
    assert metadata.successful_model_count() == 2
    assert metadata.failed_model_count() == 0


def test_result_preserves_pattern_identity():
    result = make_result()

    assert result.pattern_id == "pattern-1"
    assert result.knowledge_id == "knowledge-1"


def test_result_preserves_raw_model_scores():
    result = make_result()

    assert result.model_scores == make_raw_scores()


def test_result_preserves_calibrated_scores():
    result = make_result()

    assert result.calibrated_scores == make_calibrated_scores()


def test_result_preserves_anomaly_score():
    result = make_result()

    assert result.anomaly_score == pytest.approx(0.4)


def test_result_model_counts():
    result = make_result()

    assert result.model_count() == 2
    assert result.calibrated_model_count() == 2
    assert result.successful_model_count() == 2
    assert result.failed_model_count() == 0


def test_partial_model_failure_is_represented():
    result = EnsembleResult(
        pattern_id="pattern-1",
        knowledge_id="knowledge-1",
        model_scores=(
            ModelScore("isolation_forest", -0.2),
            ModelScore("lof", -0.4),
        ),
        calibrated_scores=(
            CalibratedModelScore(
                model_name="isolation_forest",
                raw_score=-0.2,
                canonical_score=0.2,
                calibrated_score=0.3,
            ),
            CalibratedModelScore(
                model_name="lof",
                raw_score=-0.4,
                canonical_score=0.4,
                calibrated_score=0.5,
            ),
        ),
        anomaly_score=0.4,
        failures=(
            ModelFailure(
                model_name="one_class_svm",
                error_type="RuntimeError",
                error_message="model unavailable",
            ),
        ),
        metadata=MLMetadata(
            configured_model_names=(
                "isolation_forest",
                "lof",
                "one_class_svm",
            ),
            successful_model_names=(
                "isolation_forest",
                "lof",
            ),
            failed_model_names=(
                "one_class_svm",
            ),
        ),
    )

    assert result.successful_model_count() == 2
    assert result.failed_model_count() == 1
    assert result.failures[0].model_name == "one_class_svm"


def test_nonfinite_anomaly_score_is_rejected():
    with pytest.raises(ValueError):
        EnsembleResult(
            pattern_id="pattern-1",
            knowledge_id="knowledge-1",
            model_scores=make_raw_scores(),
            calibrated_scores=make_calibrated_scores(),
            anomaly_score=float("nan"),
            failures=(),
            metadata=make_metadata(),
        )


def test_empty_raw_scores_are_rejected():
    with pytest.raises(ValueError):
        EnsembleResult(
            pattern_id="pattern-1",
            knowledge_id="knowledge-1",
            model_scores=(),
            calibrated_scores=make_calibrated_scores(),
            anomaly_score=0.4,
            failures=(),
            metadata=make_metadata(),
        )


def test_empty_calibrated_scores_are_rejected():
    with pytest.raises(ValueError):
        EnsembleResult(
            pattern_id="pattern-1",
            knowledge_id="knowledge-1",
            model_scores=make_raw_scores(),
            calibrated_scores=(),
            anomaly_score=0.4,
            failures=(),
            metadata=make_metadata(),
        )


def test_raw_and_calibrated_model_sets_must_match():
    with pytest.raises(ValueError):
        EnsembleResult(
            pattern_id="pattern-1",
            knowledge_id="knowledge-1",
            model_scores=(
                ModelScore("isolation_forest", -0.2),
                ModelScore("lof", -0.4),
            ),
            calibrated_scores=(
                CalibratedModelScore(
                    model_name="isolation_forest",
                    raw_score=-0.2,
                    canonical_score=0.2,
                    calibrated_score=0.3,
                ),
            ),
            anomaly_score=0.3,
            failures=(),
            metadata=make_metadata(),
        )


def test_successful_metadata_must_match_calibrated_models():
    with pytest.raises(ValueError):
        EnsembleResult(
            pattern_id="pattern-1",
            knowledge_id="knowledge-1",
            model_scores=make_raw_scores(),
            calibrated_scores=make_calibrated_scores(),
            anomaly_score=0.4,
            failures=(),
            metadata=MLMetadata(
                configured_model_names=(
                    "isolation_forest",
                    "lof",
                ),
                successful_model_names=(
                    "isolation_forest",
                ),
                failed_model_names=(),
            ),
        )


def test_failed_metadata_must_match_failures():
    with pytest.raises(ValueError):
        EnsembleResult(
            pattern_id="pattern-1",
            knowledge_id="knowledge-1",
            model_scores=make_raw_scores(),
            calibrated_scores=make_calibrated_scores(),
            anomaly_score=0.4,
            failures=(),
            metadata=MLMetadata(
                configured_model_names=(
                    "isolation_forest",
                    "lof",
                    "one_class_svm",
                ),
                successful_model_names=(
                    "isolation_forest",
                    "lof",
                ),
                failed_model_names=(
                    "one_class_svm",
                ),
            ),
        )


def test_successful_and_failed_models_cannot_overlap():
    with pytest.raises(ValueError):
        EnsembleResult(
            pattern_id="pattern-1",
            knowledge_id="knowledge-1",
            model_scores=make_raw_scores(),
            calibrated_scores=make_calibrated_scores(),
            anomaly_score=0.4,
            failures=(),
            metadata=MLMetadata(
                configured_model_names=(
                    "isolation_forest",
                    "lof",
                ),
                successful_model_names=(
                    "isolation_forest",
                    "lof",
                ),
                failed_model_names=(
                    "lof",
                ),
            ),
        )


def test_failure_names_must_be_unique():
    failure = ModelFailure(
        model_name="one_class_svm",
        error_type="RuntimeError",
        error_message="model unavailable",
    )

    with pytest.raises(ValueError):
        EnsembleResult(
            pattern_id="pattern-1",
            knowledge_id="knowledge-1",
            model_scores=make_raw_scores(),
            calibrated_scores=make_calibrated_scores(),
            anomaly_score=0.4,
            failures=(failure, failure),
            metadata=MLMetadata(
                configured_model_names=(
                    "isolation_forest",
                    "lof",
                    "one_class_svm",
                ),
                successful_model_names=(
                    "isolation_forest",
                    "lof",
                ),
                failed_model_names=(
                    "one_class_svm",
                ),
            ),
        )


def test_result_is_immutable():
    result = make_result()

    with pytest.raises(AttributeError):
        result.anomaly_score = 0.8

def test_metadata_rejects_duplicate_configured_models():
    with pytest.raises(ValueError):
        MLMetadata(
            configured_model_names=(
                "model_a",
                "model_a",
            ),
            successful_model_names=(
                "model_a",
            ),
            failed_model_names=(),
        )


def test_metadata_rejects_empty_configured_models():
    with pytest.raises(ValueError):
        MLMetadata(
            configured_model_names=(),
            successful_model_names=(),
            failed_model_names=(),
        )


def test_metadata_rejects_unclassified_configured_model():
    with pytest.raises(ValueError):
        MLMetadata(
            configured_model_names=(
                "model_a",
                "model_b",
                "model_c",
            ),
            successful_model_names=(
                "model_a",
            ),
            failed_model_names=(
                "model_b",
            ),
        )


def test_metadata_rejects_empty_model_name():
    with pytest.raises(ValueError):
        MLMetadata(
            configured_model_names=(
                "model_a",
                "",
            ),
            successful_model_names=(
                "model_a",
                "",
            ),
            failed_model_names=(),
        )


def test_metadata_requires_complete_success_failure_coverage():
    metadata = MLMetadata(
        configured_model_names=(
            "model_a",
            "model_b",
            "model_c",
        ),
        successful_model_names=(
            "model_a",
            "model_c",
        ),
        failed_model_names=(
            "model_b",
        ),
    )

    assert metadata.configured_model_count() == 3
    assert metadata.successful_model_count() == 2
    assert metadata.failed_model_count() == 1


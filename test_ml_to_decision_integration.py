from decision_engine import DecisionEngine
from decision_models import (
    DecisionConfiguration,
    RiskLevel,
)
from test_ml_engine_four_model_integration import (
    build_engine,
    decision_configuration,
    make_feature_vector,
)


def test_real_ml_result_reaches_decision_engine():
    engine, _ = build_engine()

    result = engine.predict(
        make_feature_vector()
    )

    original_score = result.anomaly_score
    original_metadata = result.metadata
    original_model_scores = result.model_scores

    decision_engine = DecisionEngine(
        decision_configuration()
    )

    decision = decision_engine.make_decision_from_ensemble(
        result
    )

    assert decision.metadata.evaluated_from_score == (
        original_score
    )

    assert decision.metadata.model_metadata is (
        original_metadata
    )

    assert result.anomaly_score == original_score
    assert result.metadata is original_metadata
    assert result.model_scores == original_model_scores

    assert decision.risk_level in (
        RiskLevel.NORMAL,
        RiskLevel.SUSPICIOUS,
        RiskLevel.HIGH_RISK,
        RiskLevel.CRITICAL,
    )
def test_partial_model_failure_handoff_preserves_metadata():
    from ml_inference_results import ModelFailure
    from ml_result_models import ModelScore
    from score_calibration import CalibratedModelScore
    from ensemble_result_models import EnsembleResult, MLMetadata

    metadata = MLMetadata(
        configured_model_names=(
            "isolation_forest",
            "local_outlier_factor",
            "one_class_svm",
            "elliptic_envelope",
        ),
        successful_model_names=(
            "isolation_forest",
            "local_outlier_factor",
            "elliptic_envelope",
        ),
        failed_model_names=(
            "one_class_svm",
        ),
    )

    result = EnsembleResult(
        pattern_id="pattern-partial",
        knowledge_id="knowledge-partial",
        model_scores=(
            ModelScore(
                model_name="isolation_forest",
                score=0.8,
            ),
            ModelScore(
                model_name="local_outlier_factor",
                score=0.7,
            ),
            ModelScore(
                model_name="elliptic_envelope",
                score=0.9,
            ),
        ),
        calibrated_scores=tuple(
            CalibratedModelScore(
                model_name=name,
                raw_score=score,
                canonical_score=score,
                calibrated_score=score,
            )
            for name, score in (
                ("isolation_forest", 0.8),
                ("local_outlier_factor", 0.7),
                ("elliptic_envelope", 0.9),
            )
        ),
        anomaly_score=2.2,
        failures=(
            ModelFailure(
                model_name="one_class_svm",
                error_type="RuntimeError",
                error_message="controlled failure",
            ),
        ),
        metadata=metadata,
    )

    decision = DecisionEngine(
        decision_configuration()
    ).make_decision_from_ensemble(
        result
    )

    assert (
        decision.metadata.model_metadata.failed_model_names
        == result.metadata.failed_model_names
    )

    assert (
        decision.metadata.model_metadata.successful_model_names
        == result.metadata.successful_model_names
    )


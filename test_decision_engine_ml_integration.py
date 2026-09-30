from decision_engine import DecisionEngine
from decision_models import (
    DecisionConfiguration,
    RiskLevel,
    DecisionStatus,
)
from ensemble_result_models import (
    EnsembleResult,
    MLMetadata,
)
from ml_inference_results import ModelFailure
from ml_result_models import ModelScore
from score_calibration import CalibratedModelScore


def configuration():
    return DecisionConfiguration(
        thresholds={
            RiskLevel.NORMAL: 0.0,
            RiskLevel.SUSPICIOUS: 1.0,
            RiskLevel.HIGH_RISK: 2.0,
            RiskLevel.CRITICAL: 3.0,
        },
        decisions={
            RiskLevel.NORMAL: "ALLOW",
            RiskLevel.SUSPICIOUS: "WARN",
            RiskLevel.HIGH_RISK: "INTERVENE",
            RiskLevel.CRITICAL: "BLOCK",
        },
        actions={
            RiskLevel.NORMAL: "NO_ACTION",
            RiskLevel.SUSPICIOUS: "WARNING",
            RiskLevel.HIGH_RISK: "PROTECT",
            RiskLevel.CRITICAL: "ESCALATE",
        },
        safe_default_risk_level=RiskLevel.HIGH_RISK,
    )


def calibrated_scores(names_scores):
    return tuple(
        CalibratedModelScore(
            model_name=name,
            raw_score=score,
            canonical_score=score,
            calibrated_score=score,
        )
        for name, score in names_scores
    )


def ensemble_result():
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
            "one_class_svm",
            "elliptic_envelope",
        ),
        failed_model_names=(),
    )

    return EnsembleResult(
        pattern_id="pattern-001",
        knowledge_id="knowledge-001",
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
                model_name="one_class_svm",
                score=0.6,
            ),
            ModelScore(
                model_name="elliptic_envelope",
                score=0.9,
            ),
        ),
        calibrated_scores=calibrated_scores(
            (
                ("isolation_forest", 0.8),
                ("local_outlier_factor", 0.7),
                ("one_class_svm", 0.6),
                ("elliptic_envelope", 0.9),
            )
        ),
        anomaly_score=2.5,
        failures=(),
        metadata=metadata,
    )


def test_module_11_ensemble_result_reaches_decision_engine():
    result = ensemble_result()

    engine = DecisionEngine(
        configuration()
    )

    decision = engine.make_decision_from_ensemble(
        result
    )

    assert decision.risk_level == RiskLevel.HIGH_RISK
    assert decision.decision == "INTERVENE"
    assert decision.recommended_action == "PROTECT"

    assert (
        decision.metadata.evaluated_from_score
        == 2.5
    )

    assert (
        decision.metadata.model_metadata
        is result.metadata
    )

    assert (
        decision.metadata.status
        == DecisionStatus.SUCCESS
    )
def test_partial_ml_failure_is_preserved():
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
        pattern_id="pattern-002",
        knowledge_id="knowledge-002",
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
        calibrated_scores=calibrated_scores(
            (
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

    engine = DecisionEngine(
        configuration()
    )

    decision = engine.make_decision_from_ensemble(
        result
    )

    assert decision.risk_level == RiskLevel.HIGH_RISK

    assert (
        decision.metadata.model_metadata
        is metadata
    )

    assert (
        decision.metadata.model_metadata.failed_model_names
        == ("one_class_svm",)
    )


def test_invalid_ensemble_result_is_rejected():
    engine = DecisionEngine(
        configuration()
    )

    try:
        engine.make_decision_from_ensemble(
            object()
        )
    except TypeError:
        return

    raise AssertionError(
        "invalid ensemble result must be rejected"
    )


def test_ensemble_result_is_not_mutated():
    result = ensemble_result()

    original_score = result.anomaly_score
    original_metadata = result.metadata
    original_model_scores = result.model_scores

    engine = DecisionEngine(
        configuration()
    )

    engine.make_decision_from_ensemble(
        result
    )

    assert result.anomaly_score == original_score
    assert result.metadata is original_metadata
    assert result.model_scores == original_model_scores


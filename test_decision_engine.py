import pytest

from decision_engine import DecisionEngine
from decision_models import (
    DecisionConfiguration,
    DecisionStatus,
    RiskLevel,
)
from ensemble_result_models import MLMetadata


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


def model_metadata():
    return MLMetadata(
        configured_model_names=(
            "model_a",
            "model_b",
            "model_c",
            "model_d",
        ),
        successful_model_names=(
            "model_a",
            "model_b",
            "model_c",
            "model_d",
        ),
        failed_model_names=(),
    )


def test_engine_classifies_normal_score():
    engine = DecisionEngine(configuration())

    assert (
        engine.classify_risk(-0.5)
        == RiskLevel.NORMAL
    )


def test_engine_classifies_suspicious_score():
    engine = DecisionEngine(configuration())

    assert (
        engine.classify_risk(1.5)
        == RiskLevel.SUSPICIOUS
    )


def test_engine_classifies_high_risk_score():
    engine = DecisionEngine(configuration())

    assert (
        engine.classify_risk(2.5)
        == RiskLevel.HIGH_RISK
    )


def test_engine_classifies_critical_score():
    engine = DecisionEngine(configuration())

    assert (
        engine.classify_risk(3.0)
        == RiskLevel.CRITICAL
    )
def test_engine_determines_configured_action():
    engine = DecisionEngine(configuration())

    assert (
        engine.determine_action(
            RiskLevel.HIGH_RISK
        )
        == "PROTECT"
    )


def test_make_decision_produces_complete_result():
    metadata = model_metadata()
    engine = DecisionEngine(configuration())

    result = engine.make_decision(
        2.25,
        metadata,
    )

    assert result.decision == "INTERVENE"
    assert result.risk_level == RiskLevel.HIGH_RISK
    assert result.recommended_action == "PROTECT"

    assert (
        result.metadata.evaluated_from_score
        == 2.25
    )

    assert (
        result.metadata.model_metadata is metadata
    )


def test_make_decision_preserves_ml_metadata():
    metadata = model_metadata()
    engine = DecisionEngine(configuration())

    result = engine.make_decision(
        1.5,
        metadata,
    )

    assert (
        result.metadata.model_metadata
        == metadata
    )


def test_make_decision_rejects_invalid_model_metadata():
    engine = DecisionEngine(configuration())

    with pytest.raises(TypeError):
        engine.make_decision(
            1.5,
            object(),
        )


def test_engine_does_not_mutate_configuration():
    config = configuration()
    original_thresholds = dict(
        config.thresholds
    )
    original_decisions = dict(
        config.decisions
    )
    original_actions = dict(
        config.actions
    )

    engine = DecisionEngine(config)

    engine.make_decision(
        2.5,
        model_metadata(),
    )

    assert dict(config.thresholds) == original_thresholds
    assert dict(config.decisions) == original_decisions
    assert dict(config.actions) == original_actions


def test_decision_engine_uses_anomaly_score_as_received():
    engine = DecisionEngine(configuration())

    metadata = model_metadata()

    result = engine.make_decision(
        3.0,
        metadata,
    )

    assert (
        result.metadata.evaluated_from_score
        == 3.0
    )


def test_decision_engine_does_not_change_model_metadata():
    metadata = model_metadata()

    original_configured = (
        metadata.configured_model_names
    )
    original_successful = (
        metadata.successful_model_names
    )
    original_failed = (
        metadata.failed_model_names
    )

    engine = DecisionEngine(configuration())

    engine.make_decision(
        2.0,
        metadata,
    )

    assert (
        metadata.configured_model_names
        == original_configured
    )
    assert (
        metadata.successful_model_names
        == original_successful
    )
    assert (
        metadata.failed_model_names
        == original_failed
    )

def test_missing_anomaly_score_uses_safe_default():
    engine = DecisionEngine(configuration())
    metadata = model_metadata()

    result = engine.make_decision(
        None,
        metadata,
    )

    assert (
        result.risk_level
        == RiskLevel.HIGH_RISK
    )

    assert (
        result.metadata.status
        == DecisionStatus.SAFE_DEFAULT
    )

    assert (
        result.metadata.evaluated_from_score
        is None
    )

    assert (
        result.metadata.failure_reason
        == "missing anomaly score"
    )


def test_invalid_anomaly_score_uses_safe_default():
    engine = DecisionEngine(configuration())
    metadata = model_metadata()

    result = engine.make_decision(
        "invalid",
        metadata,
    )

    assert (
        result.metadata.status
        == DecisionStatus.SAFE_DEFAULT
    )

    assert (
        result.metadata.failure_reason
        == "invalid anomaly score"
    )


def test_nan_anomaly_score_uses_safe_default():
    engine = DecisionEngine(configuration())
    metadata = model_metadata()

    result = engine.make_decision(
        float("nan"),
        metadata,
    )

    assert (
        result.metadata.status
        == DecisionStatus.SAFE_DEFAULT
    )

    assert (
        result.metadata.failure_reason
        == "non-finite anomaly score"
    )


def test_infinite_anomaly_score_uses_safe_default():
    engine = DecisionEngine(configuration())
    metadata = model_metadata()

    result = engine.make_decision(
        float("inf"),
        metadata,
    )

    assert (
        result.metadata.status
        == DecisionStatus.SAFE_DEFAULT
    )

    assert (
        result.metadata.failure_reason
        == "non-finite anomaly score"
    )


def test_successful_decision_has_no_failure_reason():
    engine = DecisionEngine(configuration())
    metadata = model_metadata()

    result = engine.make_decision(
        2.5,
        metadata,
    )

    assert (
        result.metadata.status
        == DecisionStatus.SUCCESS
    )

    assert result.metadata.failure_reason is None
    assert result.metadata.evaluated_from_score == 2.5


def test_safe_default_preserves_model_metadata():
    engine = DecisionEngine(configuration())
    metadata = model_metadata()

    result = engine.make_decision(
        None,
        metadata,
    )

    assert (
        result.metadata.model_metadata
        is metadata
    )


def test_boolean_anomaly_score_uses_safe_default():
    engine = DecisionEngine(configuration())
    metadata = model_metadata()

    result = engine.make_decision(
        True,
        metadata,
    )

    assert (
        result.metadata.status
        == DecisionStatus.SAFE_DEFAULT
    )


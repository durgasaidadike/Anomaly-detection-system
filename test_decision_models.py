import pytest

from decision_models import (
    DecisionConfiguration,
    DecisionMetadata,
    DecisionResult,
    DecisionStatus,
    RiskLevel,
)


def valid_configuration():
    return DecisionConfiguration(
        thresholds={
            RiskLevel.NORMAL: 0.0,
            RiskLevel.SUSPICIOUS: 1.0,
            RiskLevel.HIGH_RISK: 2.0,
            RiskLevel.CRITICAL: 3.0,
        },
        decisions={
            RiskLevel.NORMAL: "DECISION_NORMAL",
            RiskLevel.SUSPICIOUS: "DECISION_SUSPICIOUS",
            RiskLevel.HIGH_RISK: "DECISION_HIGH_RISK",
            RiskLevel.CRITICAL: "DECISION_CRITICAL",
        },
        actions={
            RiskLevel.NORMAL: "ACTION_NORMAL",
            RiskLevel.SUSPICIOUS: "ACTION_SUSPICIOUS",
            RiskLevel.HIGH_RISK: "ACTION_HIGH_RISK",
            RiskLevel.CRITICAL: "ACTION_CRITICAL",
        },
        safe_default_risk_level=RiskLevel.HIGH_RISK,
    )


def test_risk_levels_are_defined():
    assert RiskLevel.NORMAL.value == "NORMAL"
    assert RiskLevel.SUSPICIOUS.value == "SUSPICIOUS"
    assert RiskLevel.HIGH_RISK.value == "HIGH_RISK"
    assert RiskLevel.CRITICAL.value == "CRITICAL"


def test_valid_decision_configuration_is_accepted():
    configuration = valid_configuration()

    assert len(configuration.thresholds) == 4
    assert len(configuration.decisions) == 4
    assert len(configuration.actions) == 4


def test_configuration_requires_all_risk_levels():
    with pytest.raises(ValueError):
        DecisionConfiguration(
            thresholds={
                RiskLevel.NORMAL: 0.0,
            },
            decisions={
                RiskLevel.NORMAL: "NORMAL",
            },
            actions={
                RiskLevel.NORMAL: "ACTION",
            },
            safe_default_risk_level=RiskLevel.HIGH_RISK,
        )
def test_configuration_rejects_duplicate_threshold_values():
    with pytest.raises(ValueError):
        DecisionConfiguration(
            thresholds={
                RiskLevel.NORMAL: 0.0,
                RiskLevel.SUSPICIOUS: 1.0,
                RiskLevel.HIGH_RISK: 1.0,
                RiskLevel.CRITICAL: 3.0,
            },
            decisions={
                RiskLevel.NORMAL: "NORMAL",
                RiskLevel.SUSPICIOUS: "SUSPICIOUS",
                RiskLevel.HIGH_RISK: "HIGH",
                RiskLevel.CRITICAL: "CRITICAL",
            },
            actions={
                RiskLevel.NORMAL: "ACTION_NORMAL",
                RiskLevel.SUSPICIOUS: "ACTION_SUSPICIOUS",
                RiskLevel.HIGH_RISK: "ACTION_HIGH",
                RiskLevel.CRITICAL: "ACTION_CRITICAL",
            },
            safe_default_risk_level=RiskLevel.HIGH_RISK,
        )


def test_configuration_rejects_non_finite_threshold():
    with pytest.raises(ValueError):
        DecisionConfiguration(
            thresholds={
                RiskLevel.NORMAL: 0.0,
                RiskLevel.SUSPICIOUS: float("inf"),
                RiskLevel.HIGH_RISK: 2.0,
                RiskLevel.CRITICAL: 3.0,
            },
            decisions={
                RiskLevel.NORMAL: "NORMAL",
                RiskLevel.SUSPICIOUS: "SUSPICIOUS",
                RiskLevel.HIGH_RISK: "HIGH",
                RiskLevel.CRITICAL: "CRITICAL",
            },
            actions={
                RiskLevel.NORMAL: "ACTION_NORMAL",
                RiskLevel.SUSPICIOUS: "ACTION_SUSPICIOUS",
                RiskLevel.HIGH_RISK: "ACTION_HIGH",
                RiskLevel.CRITICAL: "ACTION_CRITICAL",
            },
            safe_default_risk_level=RiskLevel.HIGH_RISK,
        )


def test_configuration_rejects_empty_decision():
    with pytest.raises(ValueError):
        DecisionConfiguration(
            thresholds={
                RiskLevel.NORMAL: 0.0,
                RiskLevel.SUSPICIOUS: 1.0,
                RiskLevel.HIGH_RISK: 2.0,
                RiskLevel.CRITICAL: 3.0,
            },
            decisions={
                RiskLevel.NORMAL: "",
                RiskLevel.SUSPICIOUS: "SUSPICIOUS",
                RiskLevel.HIGH_RISK: "HIGH",
                RiskLevel.CRITICAL: "CRITICAL",
            },
            actions={
                RiskLevel.NORMAL: "ACTION_NORMAL",
                RiskLevel.SUSPICIOUS: "ACTION_SUSPICIOUS",
                RiskLevel.HIGH_RISK: "ACTION_HIGH",
                RiskLevel.CRITICAL: "ACTION_CRITICAL",
            },
            safe_default_risk_level=RiskLevel.HIGH_RISK,
        )


def valid_model_metadata():
    from ensemble_result_models import MLMetadata

    return MLMetadata(
        configured_model_names=(
            "model_a",
            "model_b",
        ),
        successful_model_names=(
            "model_a",
            "model_b",
        ),
        failed_model_names=(),
    )


def test_decision_metadata_validates_score():
    metadata = DecisionMetadata(
        configured_risk_levels=(
            "NORMAL",
            "SUSPICIOUS",
            "HIGH_RISK",
            "CRITICAL",
        ),
        evaluated_from_score=1.25,
        model_metadata=valid_model_metadata(),
        status=DecisionStatus.SUCCESS,
        failure_reason=None,
    )

    assert metadata.evaluated_from_score == 1.25


def test_decision_metadata_rejects_non_finite_score():
    from ensemble_result_models import MLMetadata

    with pytest.raises(ValueError):
        DecisionMetadata(
            configured_risk_levels=("NORMAL",),
            evaluated_from_score=float("nan"),
            model_metadata=MLMetadata(
                configured_model_names=("model_a",),
                successful_model_names=("model_a",),
                failed_model_names=(),
            ),
            status=DecisionStatus.SUCCESS,
            failure_reason=None,
        )


def test_decision_result_accepts_valid_contract():
    result = DecisionResult(
        decision="DECISION_HIGH",
        risk_level=RiskLevel.HIGH_RISK,
        recommended_action="ACTION_HIGH",
        metadata=DecisionMetadata(
            configured_risk_levels=(
                "NORMAL",
                "SUSPICIOUS",
                "HIGH_RISK",
                "CRITICAL",
            ),
            evaluated_from_score=2.5,
            model_metadata=valid_model_metadata(),
            status=DecisionStatus.SUCCESS,
            failure_reason=None,
        ),
    )

    assert result.risk_level == RiskLevel.HIGH_RISK
    assert result.decision == "DECISION_HIGH"
    assert result.recommended_action == "ACTION_HIGH"


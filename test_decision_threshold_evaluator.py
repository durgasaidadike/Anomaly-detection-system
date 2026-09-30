import pytest

from decision_models import (
    DecisionConfiguration,
    RiskLevel,
)
from decision_threshold_evaluator import (
    DecisionThresholdEvaluator,
)


def configuration():
    return DecisionConfiguration(
        thresholds={
            RiskLevel.NORMAL: 0.0,
            RiskLevel.SUSPICIOUS: 1.0,
            RiskLevel.HIGH_RISK: 2.0,
            RiskLevel.CRITICAL: 3.0,
        },
        decisions={
            RiskLevel.NORMAL: "NORMAL_DECISION",
            RiskLevel.SUSPICIOUS: "SUSPICIOUS_DECISION",
            RiskLevel.HIGH_RISK: "HIGH_RISK_DECISION",
            RiskLevel.CRITICAL: "CRITICAL_DECISION",
        },
        actions={
            RiskLevel.NORMAL: "NORMAL_ACTION",
            RiskLevel.SUSPICIOUS: "SUSPICIOUS_ACTION",
            RiskLevel.HIGH_RISK: "HIGH_RISK_ACTION",
            RiskLevel.CRITICAL: "CRITICAL_ACTION",
        },
        safe_default_risk_level=RiskLevel.HIGH_RISK,
    )


def test_score_below_normal_threshold_returns_normal():
    evaluator = DecisionThresholdEvaluator(
        configuration()
    )

    assert evaluator.evaluate(-1.0) == RiskLevel.NORMAL


def test_score_at_normal_threshold_returns_normal():
    evaluator = DecisionThresholdEvaluator(
        configuration()
    )

    assert evaluator.evaluate(0.0) == RiskLevel.NORMAL


def test_score_below_suspicious_returns_normal():
    evaluator = DecisionThresholdEvaluator(
        configuration()
    )

    assert evaluator.evaluate(0.99) == RiskLevel.NORMAL
def test_score_at_suspicious_threshold_returns_suspicious():
    evaluator = DecisionThresholdEvaluator(
        configuration()
    )

    assert evaluator.evaluate(1.0) == RiskLevel.SUSPICIOUS


def test_score_at_high_risk_threshold_returns_high_risk():
    evaluator = DecisionThresholdEvaluator(
        configuration()
    )

    assert evaluator.evaluate(2.0) == RiskLevel.HIGH_RISK


def test_score_at_critical_threshold_returns_critical():
    evaluator = DecisionThresholdEvaluator(
        configuration()
    )

    assert evaluator.evaluate(3.0) == RiskLevel.CRITICAL


def test_score_between_thresholds_selects_correct_level():
    evaluator = DecisionThresholdEvaluator(
        configuration()
    )

    assert evaluator.evaluate(1.5) == RiskLevel.SUSPICIOUS
    assert evaluator.evaluate(2.5) == RiskLevel.HIGH_RISK
    assert evaluator.evaluate(10.0) == RiskLevel.CRITICAL


def test_non_numeric_score_is_rejected():
    evaluator = DecisionThresholdEvaluator(
        configuration()
    )

    with pytest.raises(ValueError):
        evaluator.evaluate("1.0")


def test_nan_score_is_rejected():
    evaluator = DecisionThresholdEvaluator(
        configuration()
    )

    with pytest.raises(ValueError):
        evaluator.evaluate(float("nan"))


def test_infinite_score_is_rejected():
    evaluator = DecisionThresholdEvaluator(
        configuration()
    )

    with pytest.raises(ValueError):
        evaluator.evaluate(float("inf"))


def test_thresholds_must_increase_by_risk_level():
    with pytest.raises(ValueError):
        DecisionConfiguration(
            thresholds={
                RiskLevel.NORMAL: 0.0,
                RiskLevel.SUSPICIOUS: 2.0,
                RiskLevel.HIGH_RISK: 1.0,
                RiskLevel.CRITICAL: 3.0,
            },
            decisions={
                RiskLevel.NORMAL: "N",
                RiskLevel.SUSPICIOUS: "S",
                RiskLevel.HIGH_RISK: "H",
                RiskLevel.CRITICAL: "C",
            },
            actions={
                RiskLevel.NORMAL: "N",
                RiskLevel.SUSPICIOUS: "S",
                RiskLevel.HIGH_RISK: "H",
                RiskLevel.CRITICAL: "C",
            },
            safe_default_risk_level=RiskLevel.HIGH_RISK,
        )


def test_configuration_mappings_are_immutable():
    config = configuration()

    with pytest.raises(TypeError):
        config.thresholds[RiskLevel.NORMAL] = 99.0


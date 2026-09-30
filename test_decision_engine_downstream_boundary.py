import pytest

from decision_engine import DecisionEngine
from decision_models import (
    DecisionConfiguration,
    RiskLevel,
    DecisionStatus,
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


def metadata():
    return MLMetadata(
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


def test_decision_result_contains_downstream_decision_information():
    engine = DecisionEngine(configuration())

    result = engine.make_decision(
        2.5,
        metadata(),
    )

    assert result.decision == "INTERVENE"
    assert result.risk_level == RiskLevel.HIGH_RISK
    assert result.recommended_action == "PROTECT"

    assert result.metadata is not None
    assert (
        result.metadata.status
        == DecisionStatus.SUCCESS
    )


def test_decision_result_can_be_consumed_without_recalculation():
    engine = DecisionEngine(configuration())

    decision_result = engine.make_decision(
        2.5,
        metadata(),
    )

    received = {
        "decision": decision_result.decision,
        "risk_level": decision_result.risk_level,
        "recommended_action": (
            decision_result.recommended_action
        ),
        "decision_metadata": (
            decision_result.metadata
        ),
    }

    assert received["decision"] == "INTERVENE"

    assert (
        received["risk_level"]
        == RiskLevel.HIGH_RISK
    )

    assert (
        received["recommended_action"]
        == "PROTECT"
    )

    assert received["decision_metadata"] is (
        decision_result.metadata
    )
def test_downstream_consumer_cannot_mutate_decision_result():
    engine = DecisionEngine(configuration())

    result = engine.make_decision(
        2.5,
        metadata(),
    )

    try:
        result.decision = "CHANGED"
    except AttributeError:
        pass
    else:
        raise AssertionError(
            "DecisionResult must be immutable"
        )


def test_decision_metadata_is_immutable():
    engine = DecisionEngine(configuration())

    result = engine.make_decision(
        2.5,
        metadata(),
    )

    try:
        result.metadata = None
    except AttributeError:
        pass
    else:
        raise AssertionError(
            "DecisionResult metadata must be immutable"
        )


def test_decision_engine_does_not_import_recovery_implementation():
    import decision_engine

    source = (
        decision_engine.__file__
    )

    with open(
        source,
        "r",
        encoding="utf-8",
    ) as handle:
        content = handle.read().lower()

    forbidden = (
        "recoverymanager",
        "backupmanager",
        "restoremanager",
        "execute_recovery",
        "restore_file",
        "quarantine_file",
    )

    for symbol in forbidden:
        assert symbol not in content


def test_decision_engine_does_not_own_persistence():
    import decision_engine

    source = (
        decision_engine.__file__
    )

    with open(
        source,
        "r",
        encoding="utf-8",
    ) as handle:
        content = handle.read().lower()

    forbidden = (
        "pymongo",
        "motor",
        "sqlite3",
        "sqlalchemy",
        "mongodb",
        "insert_one",
        "update_one",
        "find_one",
    )

    for symbol in forbidden:
        assert symbol not in content


def test_threshold_conflict_is_rejected_before_decision():
    from decision_models import DecisionConfiguration

    with pytest.raises(ValueError):
        DecisionConfiguration(
            thresholds={
                RiskLevel.NORMAL: 0.0,
                RiskLevel.SUSPICIOUS: 3.0,
                RiskLevel.HIGH_RISK: 2.0,
                RiskLevel.CRITICAL: 4.0,
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


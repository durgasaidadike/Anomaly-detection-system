import pytest

from decision_models import (
    DecisionMetadata,
    DecisionResult,
    DecisionStatus,
    RiskLevel,
)
from ensemble_result_models import MLMetadata
from recovery_manager import RecoveryManager
from recovery_models import (
    BackupReference,
    FileMetadata,
    RecoveryAction,
    RecoveryPolicy,
    RecoveryRequest,
    RecoveryResult,
)


def build_decision_result() -> DecisionResult:
    model_metadata = MLMetadata(
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
    decision_metadata = DecisionMetadata(
        configured_risk_levels=(
            "NORMAL",
            "SUSPICIOUS",
            "HIGH_RISK",
            "CRITICAL",
        ),
        evaluated_from_score=2.5,
        model_metadata=model_metadata,
        status=DecisionStatus.SUCCESS,
        failure_reason=None,
    )
    return DecisionResult(
        decision="INTERVENE",
        risk_level=RiskLevel.HIGH_RISK,
        recommended_action="PROTECT",
        metadata=decision_metadata,
    )


def build_file_metadata() -> FileMetadata:
    return FileMetadata(
        file_name="report.docx",
        file_extension=".docx",
        file_path="/data/docs/report.docx",
        directory="/data/docs",
        file_size=15000,
    )


def build_request(
    action: RecoveryAction = RecoveryAction.RESTORE_PREVIOUS_VERSION,
) -> RecoveryRequest:
    return RecoveryRequest(
        decision_result=build_decision_result(),
        recovery_policy=RecoveryPolicy(
            policy_id="policy-001",
            action=action,
        ),
        file_metadata=build_file_metadata(),
        backup_reference=BackupReference(
            backup_id="backup-001",
            backup_path="/backups/report.docx.bak",
        ),
    )


def build_result(action_name: str = "restore") -> RecoveryResult:
    return RecoveryResult(
        status="COMPLETED",
        report="Recovery workflow completed.",
        action_metadata={"action": action_name},
        recovery_log=("Recovery completed.",),
    )


def test_manager_dispatches_to_registered_handler():
    received = {}

    def handler(request: RecoveryRequest) -> RecoveryResult:
        received["request"] = request
        return build_result()

    manager = RecoveryManager(
        action_handlers={
            RecoveryAction.RESTORE_PREVIOUS_VERSION: handler,
        },
    )
    request = build_request(
        action=RecoveryAction.RESTORE_PREVIOUS_VERSION,
    )
    result = manager.execute(request)

    assert result.status == "COMPLETED"
    assert received["request"] is request


def test_manager_selects_handler_by_action():
    def restore_handler(request: RecoveryRequest) -> RecoveryResult:
        return build_result(action_name="restore")

    def quarantine_handler(request: RecoveryRequest) -> RecoveryResult:
        return build_result(action_name="quarantine")

    manager = RecoveryManager(
        action_handlers={
            RecoveryAction.RESTORE_PREVIOUS_VERSION: restore_handler,
            RecoveryAction.TEMPORARY_QUARANTINE: quarantine_handler,
        },
    )
    request = build_request(
        action=RecoveryAction.TEMPORARY_QUARANTINE,
    )
    result = manager.execute(request)

    assert result.action_metadata["action"] == "quarantine"


def test_manager_rejects_unregistered_action():
    manager = RecoveryManager(
        action_handlers={
            RecoveryAction.NO_ACTION: lambda request: build_result(),
        },
    )
    request = build_request(
        action=RecoveryAction.TEMPORARY_QUARANTINE,
    )
    with pytest.raises(KeyError):
        manager.execute(request)


def test_manager_rejects_invalid_request_type():
    manager = RecoveryManager(
        action_handlers={
            RecoveryAction.NO_ACTION: lambda request: build_result(),
        },
    )
    with pytest.raises(TypeError):
        manager.execute("not-a-request")


def test_manager_rejects_empty_handlers():
    with pytest.raises(ValueError):
        RecoveryManager(action_handlers={})


def test_manager_rejects_non_mapping_handlers():
    with pytest.raises(TypeError):
        RecoveryManager(action_handlers=[1, 2, 3])


def test_manager_rejects_non_action_key():
    with pytest.raises(TypeError):
        RecoveryManager(
            action_handlers={"RESTORE": lambda request: build_result()},
        )


def test_manager_rejects_non_callable_handler():
    with pytest.raises(TypeError):
        RecoveryManager(
            action_handlers={
                RecoveryAction.NO_ACTION: "not-callable",
            },
        )


def test_manager_rejects_handler_returning_wrong_type():
    manager = RecoveryManager(
        action_handlers={
            RecoveryAction.NO_ACTION: lambda request: "done",
        },
    )
    request = build_request(action=RecoveryAction.NO_ACTION)
    with pytest.raises(TypeError):
        manager.execute(request)


def test_registered_actions_reports_configured_actions():
    manager = RecoveryManager(
        action_handlers={
            RecoveryAction.NO_ACTION: lambda request: build_result(),
            RecoveryAction.TEMPORARY_QUARANTINE: (
                lambda request: build_result()
            ),
        },
    )
    assert set(manager.registered_actions) == {
        RecoveryAction.NO_ACTION,
        RecoveryAction.TEMPORARY_QUARANTINE,
    }
    assert manager.has_handler(RecoveryAction.NO_ACTION) is True
    assert (
        manager.has_handler(
            RecoveryAction.RESTORE_PREVIOUS_VERSION,
        )
        is False
    )


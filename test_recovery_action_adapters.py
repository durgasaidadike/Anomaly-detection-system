import pytest

from decision_models import (
    DecisionMetadata,
    DecisionResult,
    DecisionStatus,
    RiskLevel,
)
from ensemble_result_models import MLMetadata
from recovery_action_adapters import (
    make_quarantine_handler,
    make_restore_previous_version_handler,
)
from recovery_filesystem_port import RecoveryFilesystemPort
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
        file_name="sample.txt",
        file_extension=".txt",
        file_path=r"C:\watched\sample.txt",
        directory=r"C:\watched",
        file_size=100,
    )


def build_backup_reference() -> BackupReference:
    return BackupReference(
        backup_id="backup-001",
        backup_path=r"C:\backups\sample.txt.bak",
    )


def build_restore_request() -> RecoveryRequest:
    return RecoveryRequest(
        decision_result=build_decision_result(),
        recovery_policy=RecoveryPolicy(
            policy_id="restore-policy",
            action=RecoveryAction.RESTORE_PREVIOUS_VERSION,
        ),
        file_metadata=build_file_metadata(),
        backup_reference=build_backup_reference(),
    )


def build_quarantine_request() -> RecoveryRequest:
    return RecoveryRequest(
        decision_result=build_decision_result(),
        recovery_policy=RecoveryPolicy(
            policy_id="quarantine-policy",
            action=RecoveryAction.TEMPORARY_QUARANTINE,
        ),
        file_metadata=build_file_metadata(),
    )


def build_recovery_result() -> RecoveryResult:
    return RecoveryResult(
        status="COMPLETED",
        report="Recovery workflow completed.",
        action_metadata={"action": "restore"},
        recovery_log=("Recovery completed.",),
    )


class FakeBackupManager:
    def __init__(self):
        self.calls = []

    def verify_backup(self, backup_reference):
        self.calls.append(
            ("verify", backup_reference)
        )
        return True

    def restore_backup(
        self,
        backup_reference,
        file_metadata,
    ):
        self.calls.append(
            (
                "restore",
                backup_reference,
                file_metadata,
            )
        )
        return True

    def create_backup(
        self,
        file_metadata,
        recovery_policy,
    ):
        self.calls.append(
            (
                "create",
                file_metadata,
                recovery_policy,
            )
        )
        return build_backup_reference()


class FakeFilesystem:
    def __init__(self):
        self.calls = []

    def quarantine_file(self, file_metadata):
        self.calls.append(file_metadata)


def test_restore_adapter_verifies_before_restore():
    backup_manager = FakeBackupManager()
    result = build_recovery_result()
    result_factory = lambda request: result
    handler = make_restore_previous_version_handler(
        backup_manager,
        result_factory,
    )
    request = build_restore_request()
    returned = handler(request)
    assert returned is result
    assert [
        call[0]
        for call in backup_manager.calls
    ] == [
        "verify",
        "restore",
    ]


def test_restore_adapter_rejects_failed_backup_verification():
    backup_manager = FakeBackupManager()
    backup_manager.verify_backup = (
        lambda backup_reference: False
    )
    handler = make_restore_previous_version_handler(
        backup_manager,
        lambda request: build_recovery_result(),
    )
    with pytest.raises(
        RuntimeError,
        match="backup verification failed",
    ):
        handler(build_restore_request())
    assert backup_manager.calls == []


def test_restore_handler_rejects_wrong_action():
    backup_manager = FakeBackupManager()
    handler = make_restore_previous_version_handler(
        backup_manager,
        lambda request: build_recovery_result(),
    )
    with pytest.raises(
        ValueError,
        match="requires RESTORE_PREVIOUS_VERSION",
    ):
        handler(build_quarantine_request())
    assert backup_manager.calls == []


def test_quarantine_adapter_delegates_to_filesystem():
    filesystem = FakeFilesystem()
    result = build_recovery_result()
    result_factory = lambda request: result
    handler = make_quarantine_handler(
        filesystem,
        result_factory,
    )
    request = build_quarantine_request()
    returned = handler(request)
    assert returned is result
    assert filesystem.calls == [
        request.file_metadata
    ]


def test_quarantine_handler_rejects_wrong_action():
    filesystem = FakeFilesystem()
    handler = make_quarantine_handler(
        filesystem,
        lambda request: build_recovery_result(),
    )
    with pytest.raises(
        ValueError,
        match="requires TEMPORARY_QUARANTINE",
    ):
        handler(build_restore_request())
    assert filesystem.calls == []


def test_adapters_propagate_execution_failure_to_manager():
    filesystem = FakeFilesystem()

    def exploding_quarantine(file_metadata):
        raise OSError("quarantine failed")

    filesystem.quarantine_file = exploding_quarantine
    failure_calls = []

    def failure_handler(request, error):
        failure_calls.append(error)
        return RecoveryResult(
            status="FAILED",
            report="Recovery action failed.",
            action_metadata={
                "failure_type": type(error).__name__,
            },
            recovery_log=("Recovery action failed.",),
        )

    quarantine_handler = make_quarantine_handler(
        filesystem,
        lambda request: build_recovery_result(),
    )
    manager = RecoveryManager(
        {RecoveryAction.TEMPORARY_QUARANTINE: quarantine_handler},
        failure_handler,
        lambda request, result: True,
    )
    result = manager.execute(build_quarantine_request())
    assert result.status == "FAILED"
    assert len(failure_calls) == 1
    assert isinstance(failure_calls[0], OSError)


def test_adapters_wired_into_manager_registry():
    backup_manager = FakeBackupManager()
    filesystem = FakeFilesystem()
    result = build_recovery_result()
    result_factory = lambda request: result

    handlers = {
        RecoveryAction.RESTORE_PREVIOUS_VERSION:
            make_restore_previous_version_handler(
                backup_manager,
                result_factory,
            ),
        RecoveryAction.TEMPORARY_QUARANTINE:
            make_quarantine_handler(
                filesystem,
                result_factory,
            ),
    }
    manager = RecoveryManager(
        action_handlers=handlers,
        failure_handler=lambda request, error: RecoveryResult(
            status="FAILED",
            report="Recovery action failed.",
            action_metadata={
                "failure_type": type(error).__name__,
            },
            recovery_log=("Recovery action failed.",),
        ),
        verification_handler=lambda request, result: True,
    )
    restore_result = manager.execute(build_restore_request())
    quarantine_result = manager.execute(build_quarantine_request())
    assert restore_result is result
    assert quarantine_result is result
    assert filesystem.calls == [
        build_quarantine_request().file_metadata
    ]




import ast
from pathlib import Path

import pytest

from backup_failure import (
    BoundedRetryPolicy,
)
from backup_security import (
    BackupSecurityContext,
)
from test_backup_security import (
    AllowAllAccessController,
    RecordingEncryptionProvider,
    RecordingSecureDeletionProvider,
)
from backup_manager import BackupManager
from backup_manager_port import BackupManagerPort
from filesystem_backup_storage import (
    FilesystemBackupStorage,
)
from recovery_action_adapters import (
    RecoveryResultFactory,
)
from recovery_backup_integration import (
    build_backup_recovery_handlers,
)
from recovery_manager import RecoveryManager
from decision_models import (
    DecisionMetadata,
    DecisionResult,
    DecisionStatus,
    RiskLevel,
)
from ensemble_result_models import MLMetadata
from recovery_models import (
    FileMetadata,
    RecoveryAction,
    RecoveryPolicy,
    RecoveryRequest,
    RecoveryResult,
)


class SelectiveRetentionEvaluator:
    """Test-only retention rule: a record is expired
    when its backup_id has been marked."""

    def __init__(self) -> None:
        self.expired_ids: set[str] = set()

    def is_expired(self, record) -> bool:
        return (
            record.reference.backup_id
            in self.expired_ids
        )


class RecordingFailureLogger:
    """Test-only logger that records every failure context."""

    def __init__(self):
        self.events = []

    def log_failure(self, context):
        self.events.append(context)


class RecordingRecoveryManagerNotifier:
    """Test-only notifier that records terminal failures."""

    def __init__(self):
        self.events = []

    def notify_failure(self, context):
        self.events.append(context)


def build_file_metadata(
    source: Path,
) -> FileMetadata:
    return FileMetadata(
        file_name=source.name,
        file_extension=source.suffix,
        file_path=str(source),
        directory=str(source.parent),
        file_size=source.stat().st_size,
    )


def build_real_manager(
    tmp_path: Path,
) -> BackupManager:
    secure_deleter = RecordingSecureDeletionProvider()
    return BackupManager(
        FilesystemBackupStorage(
            tmp_path / "backups",
            secure_deleter,
        ),
        SelectiveRetentionEvaluator(),
        BoundedRetryPolicy(
            max_attempts=1
        ),
        RecordingFailureLogger(),
        RecordingRecoveryManagerNotifier(),
        BackupSecurityContext(
            AllowAllAccessController(),
            RecordingEncryptionProvider(),
            secure_deleter,
        ),
    )


def build_decision_result() -> DecisionResult:
    model_metadata = MLMetadata(
        configured_model_names=(
            "isolation_forest",
            "local_outlier_factor",
            "one_class_svm",
        ),
        successful_model_names=(
            "isolation_forest",
            "local_outlier_factor",
            "one_class_svm",
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


def build_recovery_result() -> RecoveryResult:
    return RecoveryResult(
        status="COMPLETED",
        report="Recovery workflow completed.",
        action_metadata={
            "action": "restore",
        },
        recovery_log=(
            "Recovery completed.",
        ),
    )


def test_concrete_backup_manager_satisfies_port(
    tmp_path: Path,
):
    manager = build_real_manager(tmp_path)

    assert isinstance(
        manager,
        BackupManagerPort,
    )


def test_real_backup_manager_is_wired_into_recovery_manager(
    tmp_path: Path,
):
    manager = build_real_manager(
        tmp_path
    )

    source = tmp_path / "important.txt"

    source.write_text(
        "legitimate original",
        encoding="utf-8",
    )

    file_metadata = FileMetadata(
        file_name=source.name,
        file_extension=source.suffix,
        file_path=str(source),
        directory=str(source.parent),
        file_size=source.stat().st_size,
    )

    policy = RecoveryPolicy(
        policy_id="restore-policy",
        action=RecoveryAction.RESTORE_PREVIOUS_VERSION,
    )

    backup_reference = manager.create_backup(
        file_metadata,
        policy,
    )

    source.write_text(
        "modified content",
        encoding="utf-8",
    )

    request = RecoveryRequest(
        decision_result=build_decision_result(),
        recovery_policy=policy,
        file_metadata=build_file_metadata(source),
        backup_reference=backup_reference,
    )

    handlers = build_backup_recovery_handlers(
        manager,
        lambda request: build_recovery_result(),
    )

    recovery_manager = RecoveryManager(
        action_handlers=handlers,
        failure_handler=lambda request, error: RecoveryResult(
            status="FAILED",
            report="Recovery failed.",
            action_metadata={
                "failure_type": type(error).__name__,
            },
            recovery_log=(
                "Recovery failed.",
            ),
        ),
        verification_handler=lambda request, result: True,
    )

    result = recovery_manager.execute(
        request
    )

    assert result.status == "COMPLETED"

    assert source.read_text(
        encoding="utf-8"
    ) == "legitimate original"


class RecordingBackupManager:
    def __init__(
        self,
        delegate: BackupManager,
    ):
        self._delegate = delegate
        self.calls = []

    def verify_backup(
        self,
        backup_reference,
    ):
        self.calls.append(
            "verify"
        )

        return self._delegate.verify_backup(
            backup_reference
        )

    def restore_backup(
        self,
        backup_reference,
        file_metadata,
    ):
        self.calls.append(
            "restore"
        )

        return self._delegate.restore_backup(
            backup_reference,
            file_metadata,
        )

    def create_backup(
        self,
        file_metadata,
        recovery_policy,
    ):
        return self._delegate.create_backup(
            file_metadata,
            recovery_policy,
        )


def test_recovery_handler_verifies_before_restoring(
    tmp_path: Path,
):
    real_manager = build_real_manager(
        tmp_path
    )

    source = tmp_path / "ordered.txt"

    source.write_text(
        "original",
        encoding="utf-8",
    )

    file_metadata = build_file_metadata(
        source
    )

    policy = RecoveryPolicy(
        policy_id="restore-policy",
        action=RecoveryAction.RESTORE_PREVIOUS_VERSION,
    )

    reference = real_manager.create_backup(
        file_metadata,
        policy,
    )

    source.write_text(
        "changed",
        encoding="utf-8",
    )

    recording_manager = RecordingBackupManager(
        real_manager
    )

    handlers = build_backup_recovery_handlers(
        recording_manager,
        lambda request: build_recovery_result(),
    )

    recovery_manager = RecoveryManager(
        handlers,
        lambda request, error: RecoveryResult(
            status="FAILED",
            report="Recovery failed.",
            action_metadata={
                "failure_type": type(error).__name__,
            },
            recovery_log=(
                "Recovery failed.",
            ),
        ),
        lambda request, result: True,
    )

    request = RecoveryRequest(
        decision_result=build_decision_result(),
        recovery_policy=policy,
        file_metadata=build_file_metadata(source),
        backup_reference=reference,
    )

    recovery_manager.execute(
        request
    )

    assert recording_manager.calls == [
        "verify",
        "restore",
    ]


def test_recovery_manager_rejects_corrupted_backup(
    tmp_path: Path,
):
    manager = build_real_manager(
        tmp_path
    )

    source = tmp_path / "corrupted.txt"

    source.write_text(
        "original",
        encoding="utf-8",
    )

    file_metadata = build_file_metadata(
        source
    )

    policy = RecoveryPolicy(
        policy_id="restore-policy",
        action=RecoveryAction.RESTORE_PREVIOUS_VERSION,
    )

    reference = manager.create_backup(
        file_metadata,
        policy,
    )

    source.write_text(
        "current",
        encoding="utf-8",
    )

    Path(
        reference.backup_path
    ).write_text(
        "CORRUPTED",
        encoding="utf-8",
    )

    handlers = build_backup_recovery_handlers(
        manager,
        lambda request: build_recovery_result(),
    )

    failure_calls = []

    recovery_manager = RecoveryManager(
        handlers,
        lambda request, error: (
            failure_calls.append(error)
            or RecoveryResult(
                status="FAILED",
                report="Recovery failed.",
                action_metadata={
                    "failure_type": type(error).__name__,
                },
                recovery_log=(
                    "Recovery failed.",
                ),
            )
        ),
        lambda request, result: True,
    )

    result = recovery_manager.execute(
        RecoveryRequest(
            decision_result=build_decision_result(),
            recovery_policy=policy,
            file_metadata=file_metadata,
            backup_reference=reference,
        )
    )

    assert result.status == "FAILED"
    assert len(failure_calls) == 1

    assert source.read_text(
        encoding="utf-8"
    ) == "current"


def test_restore_recovery_requires_backup_reference(
    tmp_path: Path,
):
    manager = build_real_manager(
        tmp_path
    )

    handlers = build_backup_recovery_handlers(
        manager,
        lambda request: build_recovery_result(),
    )

    recovery_manager = RecoveryManager(
        handlers,
        lambda request, error: build_recovery_result(),
        lambda request, result: True,
    )

    source = tmp_path / "missing-reference.txt"

    source.write_text(
        "content",
        encoding="utf-8",
    )

    policy = RecoveryPolicy(
        policy_id="restore-policy",
        action=RecoveryAction.RESTORE_PREVIOUS_VERSION,
    )

    request = RecoveryRequest(
        decision_result=build_decision_result(),
        recovery_policy=policy,
        file_metadata=build_file_metadata(
            source
        ),
        backup_reference=None,
    )

    with pytest.raises(
        ValueError,
        match="requires a valid BackupReference",
    ):
        recovery_manager.execute(
            request
        )


def test_backup_manager_port_contract_remains_unchanged():
    source = (
        Path(__file__).parent
        / "backup_manager_port.py"
    )

    content = source.read_text(
        encoding="utf-8"
    )

    assert "def create_backup(" in content
    assert "def restore_backup(" in content
    assert "def verify_backup(" in content


def test_recovery_backup_integration_depends_on_port_and_recovery_adapter():
    source = (
        Path(__file__).parent
        / "recovery_backup_integration.py"
    )

    content = source.read_text(
        encoding="utf-8"
    )

    assert "BackupManagerPort" in content
    assert "make_restore_previous_version_handler" in content


def test_recovery_backup_integration_has_no_ml_or_behavioral_dependencies():
    source = (
        Path(__file__).parent
        / "recovery_backup_integration.py"
    )

    tree = ast.parse(
        source.read_text(
            encoding="utf-8"
        )
    )

    imported_modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_modules.add(
                    alias.name.split(".")[0].lower()
                )
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported_modules.add(
                    node.module.split(".")[0].lower()
                )

    forbidden = {
        "decision_engine",
        "machine_learning_engine",
        "pattern_repository",
        "behavior_analyzer",
        "sklearn",
        "numpy",
        "torch",
    }

    assert imported_modules.isdisjoint(
        forbidden
    ), f"Found forbidden imports: {imported_modules & forbidden}"

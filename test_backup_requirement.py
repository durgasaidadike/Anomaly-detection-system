import pytest

from backup_requirement import (
    BackupRequirementContext,
    ExplicitOperationBackupPolicy,
    FileOperation,
)
from decision_models import (
    DecisionMetadata,
    DecisionStatus,
)
from ensemble_result_models import MLMetadata
from recovery_models import (
    FileMetadata,
    RecoveryAction,
    RecoveryPolicy,
)


def build_file_metadata() -> FileMetadata:
    return FileMetadata(
        file_name="sample.txt",
        file_extension=".txt",
        file_path=r"C:\data\sample.txt",
        directory=r"C:\data",
        file_size=128,
    )


def build_recovery_policy() -> RecoveryPolicy:
    return RecoveryPolicy(
        policy_id="policy-001",
        action=RecoveryAction.ROLLBACK_OPERATION,
    )


def build_decision_metadata() -> DecisionMetadata:
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
    return DecisionMetadata(
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


def build_context(
    operation: FileOperation = FileOperation.MODIFY,
    storage_available: bool = True,
) -> BackupRequirementContext:
    return BackupRequirementContext(
        file_metadata=build_file_metadata(),
        recovery_policy=build_recovery_policy(),
        decision_metadata=build_decision_metadata(),
        operation=operation,
        file_importance="NORMAL",
        storage_available=storage_available,
    )


def test_delete_requires_backup():
    policy = ExplicitOperationBackupPolicy()
    assert policy.requires_backup(
        build_context(operation=FileOperation.DELETE)
    ) is True


def test_modify_requires_backup():
    policy = ExplicitOperationBackupPolicy()
    assert policy.requires_backup(
        build_context(operation=FileOperation.MODIFY)
    ) is True


def test_read_does_not_require_backup():
    policy = ExplicitOperationBackupPolicy()
    assert policy.requires_backup(
        build_context(operation=FileOperation.READ)
    ) is False


def test_temporary_file_does_not_require_backup():
    policy = ExplicitOperationBackupPolicy()
    assert policy.requires_backup(
        build_context(operation=FileOperation.TEMPORARY_FILE)
    ) is False


def test_unavailable_storage_never_requires_backup():
    policy = ExplicitOperationBackupPolicy()
    for operation in FileOperation:
        assert policy.requires_backup(
            build_context(
                operation=operation,
                storage_available=False,
            )
        ) is False


def test_context_is_immutable():
    context = build_context()
    with pytest.raises(AttributeError):
        context.operation = FileOperation.READ


def test_context_rejects_invalid_operation():
    with pytest.raises(TypeError):
        BackupRequirementContext(
            file_metadata=build_file_metadata(),
            recovery_policy=build_recovery_policy(),
            decision_metadata=build_decision_metadata(),
            operation="DELETE",
            file_importance="NORMAL",
            storage_available=True,
        )


def test_context_rejects_invalid_file_metadata():
    with pytest.raises(TypeError):
        BackupRequirementContext(
            file_metadata=None,
            recovery_policy=build_recovery_policy(),
            decision_metadata=build_decision_metadata(),
            operation=FileOperation.DELETE,
            file_importance="NORMAL",
            storage_available=True,
        )


def test_policy_rejects_invalid_context():
    policy = ExplicitOperationBackupPolicy()
    with pytest.raises(TypeError):
        policy.requires_backup("not-a-context")

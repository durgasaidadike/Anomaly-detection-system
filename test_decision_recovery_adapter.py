import pytest

from decision_models import (
    DecisionMetadata,
    DecisionResult,
    DecisionStatus,
    RiskLevel,
)
from decision_recovery_adapter import build_recovery_request
from ensemble_result_models import MLMetadata
from recovery_models import (
    BackupReference,
    FileMetadata,
    RecoveryAction,
    RecoveryPolicy,
    RecoveryRequest,
)


def build_decision() -> DecisionResult:
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


def build_policy(
    action: RecoveryAction = RecoveryAction.NO_ACTION,
) -> RecoveryPolicy:
    return RecoveryPolicy(
        policy_id="policy-001",
        action=action,
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


def test_build_recovery_request_preserves_decision():
    decision = build_decision()
    policy = RecoveryPolicy(
        policy_id="policy-1",
        action=RecoveryAction.NO_ACTION,
    )
    file_metadata = FileMetadata(
        file_name="sample.txt",
        file_extension=".txt",
        file_path=r"C:\watched\sample.txt",
        directory=r"C:\watched",
        file_size=100,
    )
    request = build_recovery_request(
        decision=decision,
        recovery_policy=policy,
        file_metadata=file_metadata,
    )
    assert isinstance(request, RecoveryRequest)
    assert request.decision_result is decision
    assert request.recovery_policy is policy
    assert request.file_metadata is file_metadata
    assert request.backup_reference is None


def test_build_recovery_request_preserves_backup_reference():
    decision = build_decision()
    policy = RecoveryPolicy(
        policy_id="restore-policy",
        action=RecoveryAction.RESTORE_PREVIOUS_VERSION,
    )
    file_metadata = build_file_metadata()
    backup_reference = build_backup_reference()
    request = build_recovery_request(
        decision=decision,
        recovery_policy=policy,
        file_metadata=file_metadata,
        backup_reference=backup_reference,
    )
    assert request.decision_result is decision
    assert request.recovery_policy is policy
    assert request.file_metadata is file_metadata
    assert request.backup_reference is backup_reference


def test_rejects_invalid_decision():
    with pytest.raises(TypeError, match="decision"):
        build_recovery_request(
            decision=None,
            recovery_policy=build_policy(),
            file_metadata=build_file_metadata(),
        )


def test_rejects_invalid_recovery_policy():
    with pytest.raises(TypeError, match="recovery_policy"):
        build_recovery_request(
            decision=build_decision(),
            recovery_policy=None,
            file_metadata=build_file_metadata(),
        )


def test_rejects_invalid_file_metadata():
    with pytest.raises(TypeError, match="file_metadata"):
        build_recovery_request(
            decision=build_decision(),
            recovery_policy=build_policy(),
            file_metadata=None,
        )


def test_rejects_invalid_backup_reference():
    with pytest.raises(TypeError, match="backup_reference"):
        build_recovery_request(
            decision=build_decision(),
            recovery_policy=build_policy(),
            file_metadata=build_file_metadata(),
            backup_reference="invalid-reference",
        )


def test_adapter_end_to_end_with_recovery_manager():
    from recovery_manager import RecoveryManager
    from recovery_verification import RecoveryVerificationError

    decision = build_decision()
    request = build_recovery_request(
        decision=decision,
        recovery_policy=build_policy(
            action=RecoveryAction.TEMPORARY_QUARANTINE,
        ),
        file_metadata=build_file_metadata(),
    )

    def handler(recovery_request):
        from recovery_models import RecoveryResult
        assert recovery_request is request
        return RecoveryResult(
            status="COMPLETED",
            report="Quarantined.",
            action_metadata={
                "action": (
                    recovery_request.recovery_policy.action.value
                ),
            },
            recovery_log=("Quarantined.",),
        )

    manager = RecoveryManager(
        {RecoveryAction.TEMPORARY_QUARANTINE: handler},
        lambda req, err: (_ for _ in ()).throw(err),
        lambda req, res: True,
    )
    result = manager.execute(request)
    assert result.status == "COMPLETED"
    assert request.decision_result is decision

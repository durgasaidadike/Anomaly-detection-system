import pytest

from decision_models import (
    DecisionMetadata,
    DecisionResult,
    DecisionStatus,
    RiskLevel,
)
from ensemble_result_models import MLMetadata
from recovery_models import (
    BackupReference,
    FileMetadata,
    RecoveryPolicy,
    RecoveryRequest,
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


def build_policy() -> RecoveryPolicy:
    return RecoveryPolicy(
        policy_name="QUARANTINE_AND_RESTORE",
    )


def build_backup_reference() -> BackupReference:
    return BackupReference(
        backup_id="backup-001",
        backup_path="/backups/report.docx.bak",
    )


def test_file_metadata_accepts_valid_contract():
    metadata = build_file_metadata()
    assert metadata.file_name == "report.docx"
    assert metadata.file_extension == ".docx"
    assert metadata.file_path == "/data/docs/report.docx"
    assert metadata.directory == "/data/docs"
    assert metadata.file_size == 15000


def test_file_metadata_rejects_empty_text_field():
    with pytest.raises(ValueError):
        FileMetadata(
            file_name="",
            file_extension=".docx",
            file_path="/data/docs/report.docx",
            directory="/data/docs",
            file_size=15000,
        )


def test_file_metadata_rejects_whitespace_text_field():
    with pytest.raises(ValueError):
        FileMetadata(
            file_name="report.docx",
            file_extension="   ",
            file_path="/data/docs/report.docx",
            directory="/data/docs",
            file_size=15000,
        )


def test_file_metadata_rejects_non_string_text_field():
    with pytest.raises(ValueError):
        FileMetadata(
            file_name="report.docx",
            file_extension=".docx",
            file_path=None,
            directory="/data/docs",
            file_size=15000,
        )


def test_file_metadata_rejects_negative_file_size():
    with pytest.raises(ValueError):
        FileMetadata(
            file_name="report.docx",
            file_extension=".docx",
            file_path="/data/docs/report.docx",
            directory="/data/docs",
            file_size=-1,
        )


def test_file_metadata_rejects_bool_file_size():
    with pytest.raises(ValueError):
        FileMetadata(
            file_name="report.docx",
            file_extension=".docx",
            file_path="/data/docs/report.docx",
            directory="/data/docs",
            file_size=True,
        )


def test_file_metadata_rejects_non_integer_file_size():
    with pytest.raises(ValueError):
        FileMetadata(
            file_name="report.docx",
            file_extension=".docx",
            file_path="/data/docs/report.docx",
            directory="/data/docs",
            file_size=15.5,
        )


def test_file_metadata_is_immutable():
    metadata = build_file_metadata()
    with pytest.raises(AttributeError):
        metadata.file_size = 999


def test_recovery_policy_accepts_valid_contract():
    policy = build_policy()
    assert policy.policy_name == "QUARANTINE_AND_RESTORE"


def test_recovery_policy_rejects_empty_policy_name():
    with pytest.raises(ValueError):
        RecoveryPolicy(policy_name="")


def test_recovery_policy_rejects_whitespace_policy_name():
    with pytest.raises(ValueError):
        RecoveryPolicy(policy_name="   ")


def test_recovery_policy_rejects_non_string_policy_name():
    with pytest.raises(ValueError):
        RecoveryPolicy(policy_name=None)


def test_recovery_policy_is_immutable():
    policy = build_policy()
    with pytest.raises(AttributeError):
        policy.policy_name = "OTHER"


def test_backup_reference_accepts_valid_contract():
    reference = build_backup_reference()
    assert reference.backup_id == "backup-001"
    assert reference.backup_path == "/backups/report.docx.bak"


def test_backup_reference_rejects_empty_backup_id():
    with pytest.raises(ValueError):
        BackupReference(
            backup_id="",
            backup_path="/backups/report.docx.bak",
        )


def test_backup_reference_rejects_empty_backup_path():
    with pytest.raises(ValueError):
        BackupReference(
            backup_id="backup-001",
            backup_path="   ",
        )


def test_backup_reference_is_immutable():
    reference = build_backup_reference()
    with pytest.raises(AttributeError):
        reference.backup_id = "changed"


def test_recovery_request_accepts_valid_contract():
    request = RecoveryRequest(
        decision_result=build_decision_result(),
        recovery_policy=build_policy(),
        file_metadata=build_file_metadata(),
        backup_reference=build_backup_reference(),
    )
    assert request.decision_result.decision == "INTERVENE"
    assert request.decision_result.risk_level == RiskLevel.HIGH_RISK
    assert request.recovery_policy.policy_name == "QUARANTINE_AND_RESTORE"
    assert request.file_metadata.file_name == "report.docx"
    assert request.backup_reference.backup_id == "backup-001"


def test_recovery_request_backup_reference_is_optional():
    request = RecoveryRequest(
        decision_result=build_decision_result(),
        recovery_policy=build_policy(),
        file_metadata=build_file_metadata(),
        backup_reference=None,
    )
    assert request.backup_reference is None


def test_recovery_request_defaults_backup_reference_to_none():
    request = RecoveryRequest(
        decision_result=build_decision_result(),
        recovery_policy=build_policy(),
        file_metadata=build_file_metadata(),
    )
    assert request.backup_reference is None


def test_recovery_request_rejects_invalid_decision_result():
    with pytest.raises(ValueError):
        RecoveryRequest(
            decision_result="INTERVENE",
            recovery_policy=build_policy(),
            file_metadata=build_file_metadata(),
            backup_reference=build_backup_reference(),
        )


def test_recovery_request_rejects_invalid_recovery_policy():
    with pytest.raises(ValueError):
        RecoveryRequest(
            decision_result=build_decision_result(),
            recovery_policy="QUARANTINE_AND_RESTORE",
            file_metadata=build_file_metadata(),
            backup_reference=build_backup_reference(),
        )


def test_recovery_request_rejects_invalid_file_metadata():
    with pytest.raises(ValueError):
        RecoveryRequest(
            decision_result=build_decision_result(),
            recovery_policy=build_policy(),
            file_metadata="report.docx",
            backup_reference=build_backup_reference(),
        )


def test_recovery_request_rejects_invalid_backup_reference():
    with pytest.raises(ValueError):
        RecoveryRequest(
            decision_result=build_decision_result(),
            recovery_policy=build_policy(),
            file_metadata=build_file_metadata(),
            backup_reference="backup-001",
        )


def test_recovery_request_is_immutable():
    request = RecoveryRequest(
        decision_result=build_decision_result(),
        recovery_policy=build_policy(),
        file_metadata=build_file_metadata(),
        backup_reference=build_backup_reference(),
    )
    with pytest.raises(AttributeError):
        request.recovery_policy = build_policy()



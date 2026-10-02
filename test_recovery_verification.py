import pytest

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
from recovery_verification import (
    RecoveryVerificationError,
    verify_recovery,
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
    action: RecoveryAction = RecoveryAction.NO_ACTION,
) -> RecoveryRequest:
    return RecoveryRequest(
        decision_result=build_decision_result(),
        recovery_policy=RecoveryPolicy(
            policy_id="policy-001",
            action=action,
        ),
        file_metadata=build_file_metadata(),
    )


def test_verify_recovery_accepts_true():
    request = build_request(
        RecoveryAction.NO_ACTION
    )
    result = RecoveryResult(
        status="COMPLETED",
        report="Recovery completed.",
        action_metadata={
            "action": RecoveryAction.NO_ACTION.value,
        },
        recovery_log=("verified",),
    )
    verified = verify_recovery(
        request,
        result,
        lambda request, result: True,
    )
    assert verified is result


def test_verify_recovery_rejects_false():
    request = build_request(
        RecoveryAction.NO_ACTION
    )
    result = RecoveryResult(
        status="COMPLETED",
        report="Recovery completed.",
        action_metadata={
            "action": RecoveryAction.NO_ACTION.value,
        },
        recovery_log=("verification pending",),
    )
    with pytest.raises(
        RecoveryVerificationError
    ):
        verify_recovery(
            request,
            result,
            lambda request, result: False,
        )


def test_verify_recovery_rejects_invalid_request():
    result = RecoveryResult(
        status="COMPLETED",
        report="Recovery completed.",
        action_metadata={
            "action": RecoveryAction.NO_ACTION.value,
        },
        recovery_log=("verified",),
    )
    with pytest.raises(TypeError):
        verify_recovery(
            "not-a-request",
            result,
            lambda request, result: True,
        )


def test_verify_recovery_rejects_invalid_result():
    request = build_request(
        RecoveryAction.NO_ACTION
    )
    with pytest.raises(TypeError):
        verify_recovery(
            request,
            "not-a-result",
            lambda request, result: True,
        )


def test_verify_recovery_rejects_non_callable_verifier():
    request = build_request(
        RecoveryAction.NO_ACTION
    )
    result = RecoveryResult(
        status="COMPLETED",
        report="Recovery completed.",
        action_metadata={
            "action": RecoveryAction.NO_ACTION.value,
        },
        recovery_log=("verified",),
    )
    with pytest.raises(TypeError):
        verify_recovery(
            request,
            result,
            "not-callable",
        )


def test_verify_recovery_rejects_non_bool_verdict():
    request = build_request(
        RecoveryAction.NO_ACTION
    )
    result = RecoveryResult(
        status="COMPLETED",
        report="Recovery completed.",
        action_metadata={
            "action": RecoveryAction.NO_ACTION.value,
        },
        recovery_log=("verified",),
    )
    with pytest.raises(TypeError):
        verify_recovery(
            request,
            result,
            lambda request, result: "verified",
        )


def test_verification_error_is_runtime_error():
    assert issubclass(
        RecoveryVerificationError, RuntimeError
    )

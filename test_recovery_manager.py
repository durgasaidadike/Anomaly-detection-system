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
from recovery_verification import (
    RecoveryVerificationError,
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


def default_failure_handler(request, error) -> RecoveryResult:
    return RecoveryResult(
        status="FAILED",
        report="Recovery action failed.",
        action_metadata={
            "action": request.recovery_policy.action.value,
            "failure_type": type(error).__name__,
        },
        recovery_log=("Recovery action failed.",),
    )


def successful_verifier(
    request,
    result,
):
    return True


def build_handlers(calls):
    def handler(request):
        calls.append(request.recovery_policy.action)
        return build_result(
            request.recovery_policy.action.value
        )
    return {
        action: handler
        for action in RecoveryAction
    }


def build_failure_result(calls,):
    def failure_handler(
        request,
        error,
    ):
        calls.append(
            (
                request.recovery_policy.action,
                type(error).__name__,
            )
        )
        return RecoveryResult(
            status="FAILED",
            report="Recovery action failed.",
            action_metadata={
                "action": (
                    request.recovery_policy.action.value
                ),
                "failure_type": (
                    type(error).__name__
                ),
            },
            recovery_log=(
                "Recovery action failed.",
            ),
        )
    return failure_handler


def test_manager_dispatches_to_registered_handler():
    received = {}

    def handler(request: RecoveryRequest) -> RecoveryResult:
        received["request"] = request
        return build_result()

    manager = RecoveryManager(
        action_handlers={
            RecoveryAction.RESTORE_PREVIOUS_VERSION: handler,
        },
        failure_handler=default_failure_handler,
        verification_handler=successful_verifier,
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
        failure_handler=default_failure_handler,
        verification_handler=successful_verifier,
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
        failure_handler=default_failure_handler,
        verification_handler=successful_verifier,
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
        failure_handler=default_failure_handler,
        verification_handler=successful_verifier,
    )
    with pytest.raises(TypeError):
        manager.execute("not-a-request")


def test_manager_rejects_empty_handlers():
    with pytest.raises(ValueError):
        RecoveryManager(
            action_handlers={},
            failure_handler=default_failure_handler,
            verification_handler=successful_verifier,
        )


def test_manager_rejects_non_mapping_handlers():
    with pytest.raises(TypeError):
        RecoveryManager(
            action_handlers=[1, 2, 3],
            failure_handler=default_failure_handler,
            verification_handler=successful_verifier,
        )


def test_manager_rejects_non_action_key():
    with pytest.raises(TypeError):
        RecoveryManager(
            action_handlers={"RESTORE": lambda request: build_result()},
            failure_handler=default_failure_handler,
            verification_handler=successful_verifier,
        )


def test_manager_rejects_non_callable_handler():
    with pytest.raises(TypeError):
        RecoveryManager(
            action_handlers={
                RecoveryAction.NO_ACTION: "not-callable",
            },
            failure_handler=default_failure_handler,
            verification_handler=successful_verifier,
        )


def test_manager_rejects_handler_returning_wrong_type():
    manager = RecoveryManager(
        action_handlers={
            RecoveryAction.NO_ACTION: lambda request: "done",
        },
        failure_handler=default_failure_handler,
        verification_handler=successful_verifier,
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
        failure_handler=default_failure_handler,
        verification_handler=successful_verifier,
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



def test_recovery_failure_is_captured_without_retry():
    calls = []
    failure_calls = []

    def failing_handler(request):
        calls.append("attempt")
        raise RuntimeError("restore failed")

    def failure_handler(request, error):
        failure_calls.append(
            (request, error)
        )
        return RecoveryResult(
            status="FAILED",
            report="Recovery action failed.",
            action_metadata={
                "action": (
                    request.recovery_policy.action.value
                ),
                "failure_type": type(error).__name__,
            },
            recovery_log=(
                "Recovery action failed.",
            ),
        )

    handlers = {
        action: failing_handler
        for action in RecoveryAction
    }
    manager = RecoveryManager(
        handlers,
        failure_handler,
        successful_verifier,
    )
    request = build_request(
        RecoveryAction.RESTORE_PREVIOUS_VERSION,
    )
    result = manager.execute(request)

    assert result.status == "FAILED"
    assert result.action_metadata["failure_type"] == "RuntimeError"
    assert calls == ["attempt"]
    assert len(failure_calls) == 1
    assert failure_calls[0][0] is request
    assert isinstance(failure_calls[0][1], RuntimeError)


def test_recovery_failure_is_not_retried():
    attempts = []

    def failing_handler(request):
        attempts.append(1)
        raise RuntimeError("recovery failed")

    def failure_handler(request, error):
        return RecoveryResult(
            status="FAILED",
            report="Failure handled.",
            action_metadata={
                "failure_type": type(error).__name__,
            },
            recovery_log=(
                "Recovery failed once.",
            ),
        )

    handlers = {
        action: failing_handler
        for action in RecoveryAction
    }
    manager = RecoveryManager(
        handlers,
        failure_handler,
        successful_verifier,
    )
    result = manager.execute(
        build_request(
            RecoveryAction.TEMPORARY_QUARANTINE
        )
    )
    assert result.status == "FAILED"
    assert attempts == [1]


def test_invalid_failure_handler_is_rejected():
    with pytest.raises(TypeError):
        RecoveryManager(
            {
                action: (
                    lambda request: build_result(
                        action.value
                    )
                )
                for action in RecoveryAction
            },
            failure_handler="invalid",
            verification_handler=successful_verifier,
        )


def test_invalid_verification_handler_is_rejected():
    with pytest.raises(TypeError):
        RecoveryManager(
            {
                action: (
                    lambda request: build_result(
                        action.value
                    )
                )
                for action in RecoveryAction
            },
            failure_handler=default_failure_handler,
            verification_handler="invalid",
        )


def test_failure_handler_must_return_recovery_result():
    def failing_handler(request):
        raise RuntimeError("controlled failure")

    def invalid_failure_handler(
        request,
        error,
    ):
        return "invalid"

    manager = RecoveryManager(
        {
            action: failing_handler
            for action in RecoveryAction
        },
        invalid_failure_handler,
        successful_verifier,
    )
    with pytest.raises(TypeError):
        manager.execute(
            build_request(
                RecoveryAction.RESTORE_PREVIOUS_VERSION
            )
        )


def test_failure_path_records_action_and_error_type():
    calls = []
    manager = RecoveryManager(
        {
            action: (
                lambda request: (_ for _ in ()).throw(
                    RuntimeError("boom")
                )
            )
            for action in RecoveryAction
        },
        build_failure_result(calls),
        successful_verifier,
    )
    result = manager.execute(
        build_request(RecoveryAction.TEMPORARY_QUARANTINE)
    )
    assert result.status == "FAILED"
    assert calls == [
        (RecoveryAction.TEMPORARY_QUARANTINE, "RuntimeError")
    ]


def test_successful_recovery_is_verified():
    calls = []
    verification_calls = []

    def verifier(
        request,
        result,
    ):
        verification_calls.append(
            (request, result)
        )
        return True

    manager = RecoveryManager(
        build_handlers(calls),
        build_failure_result(calls),
        verifier,
    )
    request = build_request(
        RecoveryAction.RESTORE_PREVIOUS_VERSION
    )
    result = manager.execute(request)
    assert result.status == "COMPLETED"
    assert len(verification_calls) == 1
    assert verification_calls[0][0] is request
    assert verification_calls[0][1] is result


def test_failed_verification_enters_failure_boundary():
    calls = []
    failure_calls = []

    def verifier(
        request,
        result,
    ):
        return False

    def failure_handler(
        request,
        error,
    ):
        failure_calls.append(
            (request, error)
        )
        return RecoveryResult(
            status="FAILED",
            report="Verification failed.",
            action_metadata={
                "failure_type": type(error).__name__,
            },
            recovery_log=(
                "Recovery verification failed.",
            ),
        )

    manager = RecoveryManager(
        build_handlers(calls),
        failure_handler,
        verifier,
    )
    request = build_request(
        RecoveryAction.RESTORE_PREVIOUS_VERSION
    )
    result = manager.execute(request)

    assert result.status == "FAILED"
    assert result.report == "Verification failed."
    assert len(failure_calls) == 1
    assert failure_calls[0][0] is request
    assert isinstance(
        failure_calls[0][1], RecoveryVerificationError
    )


def test_verifier_must_return_bool():
    def invalid_verifier(
        request,
        result,
    ):
        return "verified"

    manager = RecoveryManager(
        build_handlers([]),
        build_failure_result([]),
        invalid_verifier,
    )
    with pytest.raises(TypeError):
        manager.execute(
            build_request(
                RecoveryAction.NO_ACTION
            )
        )


def test_verification_failure_is_not_retried():
    attempts = []

    def verifier(
        request,
        result,
    ):
        attempts.append(1)
        return False

    failure_calls = []

    def failure_handler(
        request,
        error,
    ):
        failure_calls.append(1)
        return RecoveryResult(
            status="FAILED",
            report="Verification failure.",
            action_metadata={
                "failure_type": type(error).__name__,
            },
            recovery_log=(
                "Verification failed.",
            ),
        )

    manager = RecoveryManager(
        build_handlers([]),
        failure_handler,
        verifier,
    )
    result = manager.execute(
        build_request(
            RecoveryAction.RESTORE_PREVIOUS_VERSION
        )
    )
    assert result.status == "FAILED"
    assert attempts == [1]
    assert failure_calls == [1]


def test_restore_requires_backup_reference():
    manager = RecoveryManager(
        build_handlers([]),
        build_failure_result([]),
        successful_verifier,
    )
    request = RecoveryRequest(
        decision_result=build_decision_result(),
        recovery_policy=RecoveryPolicy(
            policy_id="policy-restore",
            action=RecoveryAction.RESTORE_PREVIOUS_VERSION,
        ),
        file_metadata=build_file_metadata(),
        backup_reference=None,
    )
    with pytest.raises(ValueError):
        manager.execute(request)


def test_rollback_requires_backup_reference():
    manager = RecoveryManager(
        build_handlers([]),
        build_failure_result([]),
        successful_verifier,
    )
    request = RecoveryRequest(
        decision_result=build_decision_result(),
        recovery_policy=RecoveryPolicy(
            policy_id="policy-rollback",
            action=RecoveryAction.ROLLBACK_OPERATION,
        ),
        file_metadata=build_file_metadata(),
        backup_reference=None,
    )
    with pytest.raises(ValueError):
        manager.execute(request)


def test_quarantine_does_not_require_backup_reference():
    manager = RecoveryManager(
        build_handlers([]),
        build_failure_result([]),
        successful_verifier,
    )
    request = RecoveryRequest(
        decision_result=build_decision_result(),
        recovery_policy=RecoveryPolicy(
            policy_id="policy-quarantine",
            action=RecoveryAction.TEMPORARY_QUARANTINE,
        ),
        file_metadata=build_file_metadata(),
        backup_reference=None,
    )
    result = manager.execute(request)
    assert result.status == "COMPLETED"


def test_no_action_does_not_require_backup_reference():
    manager = RecoveryManager(
        build_handlers([]),
        build_failure_result([]),
        successful_verifier,
    )
    request = RecoveryRequest(
        decision_result=build_decision_result(),
        recovery_policy=RecoveryPolicy(
            policy_id="policy-noop",
            action=RecoveryAction.NO_ACTION,
        ),
        file_metadata=build_file_metadata(),
        backup_reference=None,
    )
    result = manager.execute(request)
    assert result.status == "COMPLETED"


def test_missing_backup_does_not_invoke_action_handler():
    invoked = []

    def guarded_handler(request):
        invoked.append(request)
        return build_result("restore")

    manager = RecoveryManager(
        {
            RecoveryAction.RESTORE_PREVIOUS_VERSION: guarded_handler,
        },
        default_failure_handler,
        successful_verifier,
    )
    request = RecoveryRequest(
        decision_result=build_decision_result(),
        recovery_policy=RecoveryPolicy(
            policy_id="policy-restore",
            action=RecoveryAction.RESTORE_PREVIOUS_VERSION,
        ),
        file_metadata=build_file_metadata(),
        backup_reference=None,
    )
    with pytest.raises(ValueError):
        manager.execute(request)
    assert invoked == []



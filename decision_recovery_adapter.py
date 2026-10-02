from decision_models import DecisionResult
from recovery_models import (
    BackupReference,
    FileMetadata,
    RecoveryPolicy,
    RecoveryRequest,
)


def build_recovery_request(
    decision: DecisionResult,
    recovery_policy: RecoveryPolicy,
    file_metadata: FileMetadata,
    backup_reference: BackupReference | None = None,
) -> RecoveryRequest:
    """Construct the Recovery Manager input from an already-evaluated decision.

    This adapter does not evaluate risk or thresholds,
    nor does it assess recovery necessity.
    The supplied DecisionResult remains the authoritative decision output.
    """
    if not isinstance(decision, DecisionResult):
        raise TypeError("decision must be a DecisionResult")
    if not isinstance(recovery_policy, RecoveryPolicy):
        raise TypeError("recovery_policy must be a RecoveryPolicy")
    if not isinstance(file_metadata, FileMetadata):
        raise TypeError("file_metadata must be a FileMetadata")
    if (
        backup_reference is not None
        and not isinstance(backup_reference, BackupReference)
    ):
        raise TypeError(
            "backup_reference must be a BackupReference or None"
        )
    return RecoveryRequest(
        decision_result=decision,
        recovery_policy=recovery_policy,
        file_metadata=file_metadata,
        backup_reference=backup_reference,
    )

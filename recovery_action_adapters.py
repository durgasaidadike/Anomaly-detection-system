from typing import Callable

from backup_manager_port import BackupManagerPort
from recovery_filesystem_port import RecoveryFilesystemPort
from recovery_models import (
    RecoveryAction,
    RecoveryRequest,
    RecoveryResult,
)

RecoveryResultFactory = Callable[
    [RecoveryRequest],
    RecoveryResult,
]


def make_restore_previous_version_handler(
    backup_manager: BackupManagerPort,
    result_factory: RecoveryResultFactory,
):
    if not isinstance(backup_manager, BackupManagerPort):
        raise TypeError(
            "backup_manager must satisfy BackupManagerPort"
        )
    if not callable(result_factory):
        raise TypeError("result_factory must be callable")

    def handler(request: RecoveryRequest) -> RecoveryResult:
        if not isinstance(request, RecoveryRequest):
            raise TypeError(
                "request must be a RecoveryRequest"
            )
        if (
            request.recovery_policy.action
            is not RecoveryAction.RESTORE_PREVIOUS_VERSION
        ):
            raise ValueError(
                "handler requires RESTORE_PREVIOUS_VERSION"
            )
        if request.backup_reference is None:
            raise ValueError(
                "RESTORE_PREVIOUS_VERSION requires "
                "a valid BackupReference"
            )
        verified = backup_manager.verify_backup(
            request.backup_reference,
        )
        if not verified:
            raise RuntimeError(
                "backup verification failed"
            )
        restored = backup_manager.restore_backup(
            request.backup_reference,
            request.file_metadata,
        )
        if not restored:
            raise RuntimeError(
                "backup restore failed"
            )
        result = result_factory(request)
        if not isinstance(result, RecoveryResult):
            raise TypeError(
                "result_factory must return RecoveryResult"
            )
        return result

    return handler


def make_quarantine_handler(
    filesystem: RecoveryFilesystemPort,
    result_factory: RecoveryResultFactory,
):
    if not isinstance(filesystem, RecoveryFilesystemPort):
        raise TypeError(
            "filesystem must satisfy RecoveryFilesystemPort"
        )
    if not callable(result_factory):
        raise TypeError("result_factory must be callable")

    def handler(request: RecoveryRequest) -> RecoveryResult:
        if not isinstance(request, RecoveryRequest):
            raise TypeError(
                "request must be a RecoveryRequest"
            )
        if (
            request.recovery_policy.action
            is not RecoveryAction.TEMPORARY_QUARANTINE
        ):
            raise ValueError(
                "handler requires TEMPORARY_QUARANTINE"
            )
        filesystem.quarantine_file(
            request.file_metadata,
        )
        result = result_factory(request)
        if not isinstance(result, RecoveryResult):
            raise TypeError(
                "result_factory must return RecoveryResult"
            )
        return result

    return handler

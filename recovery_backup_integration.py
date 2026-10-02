from __future__ import annotations

from collections.abc import Callable

from backup_manager_port import BackupManagerPort
from recovery_action_adapters import (
    RecoveryResultFactory,
    make_restore_previous_version_handler,
)
from recovery_models import (
    RecoveryAction,
    RecoveryResult,
)


def build_backup_recovery_handlers(
    backup_manager: BackupManagerPort,
    result_factory: RecoveryResultFactory,
) -> dict[
    RecoveryAction,
    Callable,
]:
    """
    Build Recovery Manager handlers backed by the concrete
    Backup Manager implementation.

    This function performs composition only. It does not alter
    Recovery Manager policy or implement backup mechanics.
    """
    if not isinstance(
        backup_manager,
        BackupManagerPort,
    ):
        raise TypeError(
            "backup_manager must satisfy BackupManagerPort"
        )

    if not callable(result_factory):
        raise TypeError(
            "result_factory must be callable"
        )

    return {
        RecoveryAction.RESTORE_PREVIOUS_VERSION:
            make_restore_previous_version_handler(
                backup_manager,
                result_factory,
            ),
    }

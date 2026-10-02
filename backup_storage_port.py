from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from recovery_models import BackupReference


@runtime_checkable
class BackupStoragePort(Protocol):
    """
    Boundary between Backup Manager and physical backup storage.

    Storage owns the mechanics of physically storing a backup.
    Backup Manager owns the lifecycle/orchestration.

    BackupStoragePort does not decide:
    - whether a backup is needed
    - risk level
    - anomaly status
    - recovery policy
    - ML results

    It only provides the storage operation.
    """

    def store(
        self,
        source_path: Path,
        backup_id: str,
    ) -> BackupReference:
        """
        Store a recoverable copy of source_path and return
        an opaque reference to the stored backup.
        """
        ...

    def restore(
        self,
        backup_reference: BackupReference,
        destination_path: Path,
    ) -> None:
        """
        Restore the referenced backup to destination_path.

        The storage layer owns physical file copying.
        Backup Manager owns validation and recovery coordination.
        """
        ...

    def delete(
        self,
        backup_reference: BackupReference,
    ) -> None:
        """
        Permanently remove the referenced backup from storage.

        Storage owns the physical deletion operation.
        """
        ...
from __future__ import annotations

from typing import Protocol, runtime_checkable

from recovery_models import (
    BackupReference,
    FileMetadata,
    RecoveryPolicy,
)


@runtime_checkable
class BackupManagerPort(Protocol):
    """Contract used by Recovery Manager to communicate
    with the future Backup Manager implementation.

    This is only an interface boundary.
    It does not implement:
    - backup storage,
    - filesystem copying,
    - restoration,
    - cleanup,
    - persistence.
    """

    def create_backup(
        self,
        file_metadata: FileMetadata,
        recovery_policy: RecoveryPolicy,
    ) -> BackupReference:
        """Create a recovery point and return its reference."""
        ...

    def restore_backup(
        self,
        backup_reference: BackupReference,
        file_metadata: FileMetadata,
    ) -> bool:
        """Restore a previous backup for the given file."""
        ...

    def verify_backup(
        self,
        backup_reference: BackupReference,
    ) -> bool:
        """Verify that a backup reference remains usable."""
        ...

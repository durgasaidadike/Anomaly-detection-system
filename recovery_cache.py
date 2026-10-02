from __future__ import annotations

from recovery_models import BackupReference


class RecoveryCache:
    """
    Lightweight temporary cache used to accelerate recovery
    lookup.

    The cache stores only the BackupReference associated
    with a source file path. Full backup metadata remains
    owned by BackupManager's backup-record state.
    """

    def __init__(self) -> None:
        self._entries: dict[
            str,
            BackupReference,
        ] = {}

    @property
    def size(self) -> int:
        return len(self._entries)

    def put(
        self,
        file_path: str,
        backup_reference: BackupReference,
    ) -> None:
        if (
            not isinstance(file_path, str)
            or not file_path.strip()
        ):
            raise ValueError(
                "file_path must be a non-empty string"
            )
        if not isinstance(
            backup_reference,
            BackupReference,
        ):
            raise TypeError(
                "backup_reference must be BackupReference"
            )
        self._entries[file_path] = backup_reference

    def get(
        self,
        file_path: str,
    ) -> BackupReference | None:
        if (
            not isinstance(file_path, str)
            or not file_path.strip()
        ):
            raise ValueError(
                "file_path must be a non-empty string"
            )
        return self._entries.get(file_path)

    def remove(
        self,
        file_path: str,
    ) -> None:
        if (
            not isinstance(file_path, str)
            or not file_path.strip()
        ):
            raise ValueError(
                "file_path must be a non-empty string"
            )
        self._entries.pop(file_path, None)

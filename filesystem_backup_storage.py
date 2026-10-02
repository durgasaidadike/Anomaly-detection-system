from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

from backup_security import SecureDeletionProvider
from backup_storage_port import BackupStoragePort
from recovery_models import BackupReference


class FilesystemBackupStorage(BackupStoragePort):
    """
    Concrete filesystem-backed Backup Storage.

    A storage root is injected by the caller. The implementation
    creates the actual backup file beneath that root.

    The copy is written to a temporary file inside the storage
    root first and only moved into its final destination once
    the copy has completed. A BackupReference is therefore never
    returned for a half-written or missing backup file, which is
    how invalid backup references are prevented.

    Restoration reuses the same mechanism: the restore copy is
    completed in a temporary file beside the target and only
    then atomically replaces the target, so a failed or
    incomplete copy does not leave a partially written target.
    """

    def __init__(
        self,
        storage_root: Path,
        secure_deletion_provider: SecureDeletionProvider,
    ) -> None:
        if not isinstance(storage_root, Path):
            raise TypeError(
                "storage_root must be Path"
            )
        if not isinstance(
            secure_deletion_provider,
            SecureDeletionProvider,
        ):
            raise TypeError(
                "secure_deletion_provider must implement "
                "SecureDeletionProvider"
            )
        self._storage_root = storage_root
        self._secure_deletion_provider = (
            secure_deletion_provider
        )
        self._storage_root.mkdir(
            parents=True,
            exist_ok=True,
        )

    @property
    def storage_root(self) -> Path:
        return self._storage_root

    def store(
        self,
        source_path: Path,
        backup_id: str,
    ) -> BackupReference:
        self._validate_arguments(
            source_path,
            backup_id,
        )
        if not source_path.is_file():
            raise FileNotFoundError(
                f"source file does not exist: {source_path}"
            )

        destination = self._destination_for(
            source_path,
            backup_id,
        )
        if destination.exists():
            raise FileExistsError(
                f"backup already exists: {destination}"
            )

        self._storage_root.mkdir(
            parents=True,
            exist_ok=True,
        )
        temporary_path = self._reserve_temporary_path(
            backup_id
        )
        try:
            shutil.copy2(
                source_path,
                temporary_path,
            )
            os.replace(
                temporary_path,
                destination,
            )
        except BaseException:
            temporary_path.unlink(missing_ok=True)
            raise

        self._confirm_stored(
            source_path,
            destination,
        )
        return BackupReference(
            backup_id=backup_id,
            backup_path=str(destination),
        )

    def restore(
        self,
        backup_reference: BackupReference,
        destination_path: Path,
    ) -> None:
        if not isinstance(
            backup_reference, BackupReference
        ):
            raise TypeError(
                "backup_reference must be BackupReference"
            )
        if not isinstance(destination_path, Path):
            raise TypeError(
                "destination_path must be Path"
            )

        backup_path = Path(
            backup_reference.backup_path
        ).resolve()
        destination_path = destination_path.resolve()

        if not backup_path.exists():
            raise FileNotFoundError(
                f"backup file does not exist: "
                f"{backup_path}"
            )
        if not backup_path.is_file():
            raise ValueError(
                f"backup path is not a file: "
                f"{backup_path}"
            )
        if backup_path == destination_path:
            raise ValueError(
                "backup path and destination path "
                "must differ"
            )

        destination_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        temporary_path = self._reserve_restore_path(
            destination_path
        )
        try:
            shutil.copy2(
                backup_path,
                temporary_path,
            )
            self._confirm_stored(
                backup_path,
                temporary_path,
            )
            os.replace(
                temporary_path,
                destination_path,
            )
        except BaseException:
            temporary_path.unlink(missing_ok=True)
            raise

    def delete(
        self,
        backup_reference: BackupReference,
    ) -> None:
        if not isinstance(
            backup_reference, BackupReference
        ):
            raise TypeError(
                "backup_reference must be BackupReference"
            )

        backup_path = Path(
            backup_reference.backup_path
        ).resolve()
        if not backup_path.exists():
            raise FileNotFoundError(
                f"backup file does not exist: "
                f"{backup_path}"
            )
        if not backup_path.is_file():
            raise ValueError(
                f"backup path is not a regular file: "
                f"{backup_path}"
            )
        self._secure_deletion_provider.secure_delete(
            backup_path
        )
        if backup_path.exists():
            raise IOError(
                "secure deletion provider reported "
                "success but backup still exists"
            )

    @staticmethod
    def _validate_arguments(
        source_path: Path,
        backup_id: str,
    ) -> None:
        if not isinstance(source_path, Path):
            raise TypeError(
                "source_path must be Path"
            )
        if (
            not isinstance(backup_id, str)
            or not backup_id.strip()
        ):
            raise ValueError(
                "backup_id must be a non-empty string"
            )
        if (
            "/" in backup_id
            or "\\" in backup_id
            or backup_id in (".", "..")
        ):
            raise ValueError(
                "backup_id must not contain path separators"
            )

    def _destination_for(
        self,
        source_path: Path,
        backup_id: str,
    ) -> Path:
        return (
            self._storage_root
            / f"{backup_id}{source_path.suffix}"
        )

    def _reserve_temporary_path(
        self,
        backup_id: str,
    ) -> Path:
        handle, name = tempfile.mkstemp(
            dir=str(self._storage_root),
            prefix=f".{backup_id}-",
            suffix=".tmp",
        )
        os.close(handle)
        return Path(name)

    @staticmethod
    def _reserve_restore_path(
        destination_path: Path,
    ) -> Path:
        """Reserve the temporary restore file beside the
        target so the final replacement stays atomic."""
        handle, name = tempfile.mkstemp(
            dir=str(destination_path.parent),
            prefix=f".{destination_path.name}-",
            suffix=".tmp",
        )
        os.close(handle)
        return Path(name)

    def _confirm_stored(
        self,
        source_path: Path,
        destination: Path,
    ) -> None:
        if not destination.is_file():
            raise OSError(
                "backup destination does not exist "
                "after the copy completed"
            )
        if (
            destination.stat().st_size
            != source_path.stat().st_size
        ):
            try:
                # A stored artifact that does not match its
                # source is removed through the injected
                # secure-deletion boundary, never by a
                # direct unlink.
                self._secure_deletion_provider.secure_delete(
                    destination
                )
            except Exception:
                # Cleanup failure must not hide the size
                # mismatch error.
                pass
            raise OSError(
                "stored backup size does not match "
                "the source file"
            )
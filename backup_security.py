from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Protocol, runtime_checkable

from recovery_models import (
    BackupReference,
    FileMetadata,
)


class BackupSecurityOperation(str, Enum):
    CREATE = "CREATE"
    VERIFY = "VERIFY"
    RESTORE = "RESTORE"
    DELETE = "DELETE"


class BackupSecurityError(RuntimeError):
    """Base error for Backup Manager security failures."""


class BackupAccessDeniedError(BackupSecurityError):
    """Raised when a security policy denies an operation."""


@runtime_checkable
class BackupEncryptionProvider(Protocol):
    """
    Encryption/decryption boundary.

    The cryptographic algorithm and key-management mechanism are
    deliberately external because Module 14 does not prescribe
    either one.
    """

    def encrypt_backup(
        self,
        source_path: Path,
        destination_path: Path,
    ) -> None:
        """Encrypt a backup file at source_path to destination_path."""
        ...

    def decrypt_backup(
        self,
        encrypted_path: Path,
        destination_path: Path,
    ) -> None:
        """Decrypt a backup file at encrypted_path to destination_path."""
        ...


@runtime_checkable
class BackupAccessController(Protocol):
    """
    Access control boundary.

    The authorization model (RBAC, ABAC, etc.) is deliberately
    external because Module 14 does not prescribe one.
    """

    def authorize(
        self,
        operation: BackupSecurityOperation,
        file_metadata: FileMetadata,
        backup_reference: BackupReference | None = None,
    ) -> None:
        """
        Authorize a backup operation.

        Raises BackupAccessDeniedError if the operation is not permitted.
        """
        ...


@runtime_checkable
class SecureDeletionProvider(Protocol):
    """
    Secure deletion boundary.

    The exact secure deletion algorithm (overwrite counts, DoD
    standards, etc.) is deliberately external because Module 14
    does not prescribe one.
    """

    def secure_delete(self, file_path: Path) -> None:
        """
        Securely delete a file.

        After this call, the file must not exist.
        """
        ...


class BackupSecurityContext:
    """
    Groups the security providers required by Backup Manager.

    No security policy is inferred from absence/presence of
    arbitrary configuration.
    """

    def __init__(
        self,
        access_controller: BackupAccessController,
        encryption_provider: BackupEncryptionProvider,
        secure_deletion_provider: SecureDeletionProvider,
    ) -> None:
        if not isinstance(
            access_controller,
            BackupAccessController,
        ):
            raise TypeError(
                "access_controller must implement "
                "BackupAccessController"
            )
        if not isinstance(
            encryption_provider,
            BackupEncryptionProvider,
        ):
            raise TypeError(
                "encryption_provider must implement "
                "BackupEncryptionProvider"
            )
        if not isinstance(
            secure_deletion_provider,
            SecureDeletionProvider,
        ):
            raise TypeError(
                "secure_deletion_provider must implement "
                "SecureDeletionProvider"
            )

        self._access_controller = access_controller
        self._encryption_provider = encryption_provider
        self._secure_deletion_provider = (
            secure_deletion_provider
        )

    @property
    def access_controller(self) -> BackupAccessController:
        return self._access_controller

    @property
    def encryption_provider(self) -> BackupEncryptionProvider:
        return self._encryption_provider

    @property
    def secure_deletion_provider(self) -> SecureDeletionProvider:
        return self._secure_deletion_provider

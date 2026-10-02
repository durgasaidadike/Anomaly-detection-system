from __future__ import annotations

from dataclasses import dataclass

from decision_models import DecisionResult


@dataclass(frozen=True)
class FileMetadata:
    """
    Immutable filesystem metadata required by the
    Recovery Manager.
    """

    file_name: str
    file_extension: str
    file_path: str
    directory: str
    file_size: int

    def __post_init__(self) -> None:
        text_fields = (
            ("file_name", self.file_name),
            ("file_extension", self.file_extension),
            ("file_path", self.file_path),
            ("directory", self.directory),
        )
        for field_name, value in text_fields:
            if (
                not isinstance(value, str)
                or not value.strip()
            ):
                raise ValueError(
                    f"{field_name} must be a non-empty string"
                )
        if (
            isinstance(self.file_size, bool)
            or not isinstance(self.file_size, int)
        ):
            raise ValueError(
                "file_size must be an integer"
            )
        if self.file_size < 0:
            raise ValueError(
                "file_size must not be negative"
            )


@dataclass(frozen=True)
class RecoveryPolicy:
    """
    Identifies the recovery policy to be applied.

    Policy behavior itself is intentionally outside
    this contract and will be implemented later.
    """

    policy_name: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.policy_name, str)
            or not self.policy_name.strip()
        ):
            raise ValueError(
                "policy_name must be a non-empty string"
            )


@dataclass(frozen=True)
class BackupReference:
    """
    Opaque reference to a backup owned by the Backup Manager.

    Recovery Manager only coordinates with this reference.
    Backup storage, versioning, and restore mechanics remain
    owned by the Backup Manager.
    """

    backup_id: str
    backup_path: str

    def __post_init__(self) -> None:
        text_fields = (
            ("backup_id", self.backup_id),
            ("backup_path", self.backup_path),
        )
        for field_name, value in text_fields:
            if (
                not isinstance(value, str)
                or not value.strip()
            ):
                raise ValueError(
                    f"{field_name} must be a non-empty string"
                )


@dataclass(frozen=True)
class RecoveryRequest:
    """
    Immutable input boundary for the Recovery Manager.

    Composed from:
        DecisionResult + RecoveryPolicy + FileMetadata + BackupReference.

    This contract carries inputs only. It performs no recovery,
    no backup/restore I/O, and no policy execution.
    """

    decision_result: DecisionResult
    recovery_policy: RecoveryPolicy
    file_metadata: FileMetadata
    backup_reference: BackupReference | None = None

    def __post_init__(self) -> None:
        if not isinstance(
            self.decision_result,
            DecisionResult,
        ):
            raise ValueError(
                "decision_result must be DecisionResult"
            )
        if not isinstance(
            self.recovery_policy,
            RecoveryPolicy,
        ):
            raise ValueError(
                "recovery_policy must be RecoveryPolicy"
            )
        if not isinstance(
            self.file_metadata,
            FileMetadata,
        ):
            raise ValueError(
                "file_metadata must be FileMetadata"
            )
        if self.backup_reference is not None and not isinstance(
            self.backup_reference,
            BackupReference,
        ):
            raise ValueError(
                "backup_reference must be BackupReference or None"
            )

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from decision_models import DecisionMetadata
from recovery_models import (
    FileMetadata,
    RecoveryPolicy,
)


class FileOperation(str, Enum):
    """Filesystem operation categories explicitly referenced by
    the Module 14 backup philosophy examples.

    These values do not imply that this is the complete PRISM
    operation taxonomy.
    """

    DELETE = "DELETE"
    MODIFY = "MODIFY"
    READ = "READ"
    TEMPORARY_FILE = "TEMPORARY_FILE"


@dataclass(frozen=True)
class BackupRequirementContext:
    """Explicit context required to evaluate whether a backup
    should be created.

    Module 14 states that backup selection depends on:
    - file importance
    - risk level / decision metadata
    - operation type
    - recovery policy
    - storage availability

    The specification does not define the exact representation
    or thresholds for every factor, so this context keeps those
    inputs explicit rather than inventing semantics.
    """

    file_metadata: FileMetadata
    recovery_policy: RecoveryPolicy
    decision_metadata: DecisionMetadata
    operation: FileOperation
    file_importance: str
    storage_available: bool

    def __post_init__(self) -> None:
        if not isinstance(
            self.file_metadata,
            FileMetadata,
        ):
            raise TypeError(
                "file_metadata must be FileMetadata"
            )
        if not isinstance(
            self.recovery_policy,
            RecoveryPolicy,
        ):
            raise TypeError(
                "recovery_policy must be RecoveryPolicy"
            )
        if not isinstance(
            self.decision_metadata,
            DecisionMetadata,
        ):
            raise TypeError(
                "decision_metadata must be DecisionMetadata"
            )
        if not isinstance(
            self.operation,
            FileOperation,
        ):
            raise TypeError(
                "operation must be FileOperation"
            )
        if (
            not isinstance(self.file_importance, str)
            or not self.file_importance.strip()
        ):
            raise ValueError(
                "file_importance must be a non-empty string"
            )
        if not isinstance(self.storage_available, bool):
            raise TypeError(
                "storage_available must be a bool"
            )


class BackupRequirementEvaluator(Protocol):
    """Evaluates whether a backup should be created."""

    def requires_backup(
        self,
        context: BackupRequirementContext,
    ) -> bool:
        ...


class ExplicitOperationBackupPolicy:
    """Minimal policy based only on the operation examples
    explicitly stated by Module 14.

    DELETE and MODIFY require a backup.
    READ and TEMPORARY_FILE do not.
    Storage availability is respected because a backup cannot
    be created when the required storage is unavailable.
    Other factors remain explicit in the context but are not
    assigned invented semantics here.
    """

    _BACKUP_REQUIRED_OPERATIONS = frozenset(
        {
            FileOperation.DELETE,
            FileOperation.MODIFY,
        }
    )

    def requires_backup(
        self,
        context: BackupRequirementContext,
    ) -> bool:
        if not isinstance(
            context,
            BackupRequirementContext,
        ):
            raise TypeError(
                "context must be BackupRequirementContext"
            )
        if not context.storage_available:
            return False
        return (
            context.operation
            in self._BACKUP_REQUIRED_OPERATIONS
        )

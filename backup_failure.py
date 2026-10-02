from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from recovery_models import FileMetadata


@dataclass(frozen=True)
class BackupFailureContext:
    """
    Immutable information describing a failed backup operation.

    Built once per failed attempt so logging and Recovery
    Manager notification observe the same facts.
    """

    operation: str
    file_metadata: FileMetadata
    attempt: int
    error_type: str
    error_message: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.operation, str)
            or not self.operation.strip()
        ):
            raise ValueError(
                "operation must be a non-empty string"
            )

        if not isinstance(
            self.file_metadata,
            FileMetadata,
        ):
            raise TypeError(
                "file_metadata must be FileMetadata"
            )

        if (
            isinstance(self.attempt, bool)
            or not isinstance(self.attempt, int)
            or self.attempt < 1
        ):
            raise ValueError(
                "attempt must be a positive integer"
            )

        if (
            not isinstance(self.error_type, str)
            or not self.error_type.strip()
        ):
            raise ValueError(
                "error_type must be a non-empty string"
            )

        if (
            not isinstance(self.error_message, str)
            or not self.error_message.strip()
        ):
            raise ValueError(
                "error_message must be a non-empty string"
            )


@runtime_checkable
class BackupRetryPolicy(Protocol):
    """
    Decides whether a failed backup attempt may be retried.

    Retry count and backoff semantics remain externally
    configurable; Module 14 does not prescribe a default
    retry count, so no value is invented here.
    """

    def should_retry(
        self,
        attempt: int,
        error: BaseException,
    ) -> bool:
        ...


@runtime_checkable
class BackupFailureLogger(Protocol):
    """
    Logging boundary for backup failures.
    """

    def log_failure(
        self,
        context: BackupFailureContext,
    ) -> None:
        ...


@runtime_checkable
class RecoveryManagerNotifier(Protocol):
    """
    Notification boundary used to report terminal backup
    failures to the Recovery Manager layer.
    """

    def notify_failure(
        self,
        context: BackupFailureContext,
    ) -> None:
        ...


class BackupCreationError(RuntimeError):
    """
    Raised when backup creation fails after the configured
    retry policy has been exhausted.

    Callers receive a stable failure type instead of whatever
    low-level filesystem exception occurred, and the original
    context remains available via .context / .__cause__.
    """

    def __init__(
        self,
        context: BackupFailureContext,
    ) -> None:
        self.context = context

        super().__init__(
            "backup creation failed after "
            f"attempt {context.attempt}: "
            f"{context.error_message}"
        )


class BoundedRetryPolicy:
    """
    Retry policy with an explicitly supplied maximum number
    of attempts.

    No default retry count is prescribed by Module 14; the
    application/composition layer decides the bound.
    """

    def __init__(
        self,
        max_attempts: int,
    ) -> None:
        if (
            isinstance(max_attempts, bool)
            or not isinstance(max_attempts, int)
            or max_attempts < 1
        ):
            raise ValueError(
                "max_attempts must be a positive integer"
            )

        self._max_attempts = max_attempts

    def should_retry(
        self,
        attempt: int,
        error: BaseException,
    ) -> bool:
        if (
            isinstance(attempt, bool)
            or not isinstance(attempt, int)
            or attempt < 1
        ):
            raise ValueError(
                "attempt must be a positive integer"
            )

        if not isinstance(
            error,
            BaseException,
        ):
            raise TypeError(
                "error must be BaseException"
            )

        return attempt < self._max_attempts

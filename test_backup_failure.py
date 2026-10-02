import dataclasses
import logging

import pytest

from backup_failure import (
    BackupCreationError,
    BackupFailureContext,
    BackupFailureLogger,
    BackupRetryPolicy,
    BoundedRetryPolicy,
    RecoveryManagerNotifier,
)
from backup_failure_logging import LoggingBackupFailureLogger
from recovery_models import FileMetadata


def build_file_metadata() -> FileMetadata:
    return FileMetadata(
        file_name="important.txt",
        file_extension=".txt",
        file_path="C:/data/important.txt",
        directory="C:/data",
        file_size=1024,
    )


def build_context() -> BackupFailureContext:
    return BackupFailureContext(
        operation="CREATE_BACKUP",
        file_metadata=build_file_metadata(),
        attempt=1,
        error_type="OSError",
        error_message="disk failure",
    )


def test_backup_failure_context_preserves_values():
    context = build_context()
    assert context.operation == "CREATE_BACKUP"
    assert (
        context.file_metadata.file_name == "important.txt"
    )
    assert context.attempt == 1
    assert context.error_type == "OSError"
    assert context.error_message == "disk failure"


def test_backup_failure_context_is_immutable():
    context = build_context()
    with pytest.raises(dataclasses.FrozenInstanceError):
        context.attempt = 2


def test_backup_failure_context_rejects_blank_operation():
    with pytest.raises(ValueError, match="operation"):
        BackupFailureContext(
            operation="   ",
            file_metadata=build_file_metadata(),
            attempt=1,
            error_type="OSError",
            error_message="disk failure",
        )


def test_backup_failure_context_rejects_invalid_file_metadata():
    with pytest.raises(TypeError, match="file_metadata"):
        BackupFailureContext(
            operation="CREATE_BACKUP",
            file_metadata=object(),
            attempt=1,
            error_type="OSError",
            error_message="disk failure",
        )


@pytest.mark.parametrize(
    "attempt",
    [0, -1, True, "1"],
)
def test_backup_failure_context_rejects_invalid_attempt(
    attempt,
):
    with pytest.raises(ValueError, match="attempt"):
        BackupFailureContext(
            operation="CREATE_BACKUP",
            file_metadata=build_file_metadata(),
            attempt=attempt,
            error_type="OSError",
            error_message="disk failure",
        )


def test_backup_failure_context_rejects_blank_error_fields():
    with pytest.raises(ValueError, match="error_type"):
        BackupFailureContext(
            operation="CREATE_BACKUP",
            file_metadata=build_file_metadata(),
            attempt=1,
            error_type=" ",
            error_message="disk failure",
        )
    with pytest.raises(ValueError, match="error_message"):
        BackupFailureContext(
            operation="CREATE_BACKUP",
            file_metadata=build_file_metadata(),
            attempt=1,
            error_type="OSError",
            error_message="",
        )


def test_backup_creation_error_carries_context_and_message():
    context = build_context()
    error = BackupCreationError(context)
    assert error.context == context
    assert isinstance(error, RuntimeError)
    assert "attempt 1" in str(error)
    assert "disk failure" in str(error)


def test_bounded_retry_policy_rejects_invalid_max_attempts():
    for max_attempts in (0, -1, True, "3"):
        with pytest.raises(
            ValueError,
            match="max_attempts",
        ):
            BoundedRetryPolicy(
                max_attempts=max_attempts,
            )


def test_bounded_retry_policy_allows_attempts_below_max():
    policy = BoundedRetryPolicy(max_attempts=3)
    error = OSError("boom")
    assert policy.should_retry(1, error) is True
    assert policy.should_retry(2, error) is True
    assert policy.should_retry(3, error) is False


def test_bounded_retry_policy_stops_after_single_attempt():
    policy = BoundedRetryPolicy(max_attempts=1)
    assert (
        policy.should_retry(1, OSError("boom")) is False
    )


def test_bounded_retry_policy_validates_arguments():
    policy = BoundedRetryPolicy(max_attempts=2)
    with pytest.raises(ValueError, match="attempt"):
        policy.should_retry(0, OSError("boom"))
    with pytest.raises(TypeError, match="error"):
        policy.should_retry(1, "not-an-exception")


def test_failure_boundaries_accept_structural_implementations():
    class RecordingNotifier:
        def notify_failure(self, context):
            self.events = []

    adapter = LoggingBackupFailureLogger(
        logging.getLogger("backup.failure.test")
    )
    assert isinstance(adapter, BackupFailureLogger)
    assert isinstance(
        BoundedRetryPolicy(max_attempts=2),
        BackupRetryPolicy,
    )
    assert isinstance(
        RecordingNotifier(),
        RecoveryManagerNotifier,
    )


def test_logging_failure_logger_requires_logger_instance():
    with pytest.raises(TypeError, match="logger"):
        LoggingBackupFailureLogger(object())


def test_logging_failure_logger_emits_error_record(caplog):
    logger = logging.getLogger("backup.failure.test")
    adapter = LoggingBackupFailureLogger(logger)
    context = build_context()

    with caplog.at_level(
        logging.ERROR,
        logger="backup.failure.test",
    ):
        adapter.log_failure(context)

    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert record.levelno == logging.ERROR
    message = record.getMessage()
    assert "CREATE_BACKUP" in message
    assert "C:/data/important.txt" in message
    assert "attempt=1" in message
    assert "OSError" in message
    assert "disk failure" in message

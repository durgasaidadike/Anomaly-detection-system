from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Lock
import time

import pytest

from backup_failure import (
    BackupCreationError,
    BoundedRetryPolicy,
)
from backup_security import (
    BackupAccessDeniedError,
    BackupSecurityContext,
    SecureDeletionProvider,
)
from backup_integrity import (
    INTEGRITY_ALGORITHM,
    calculate_file_digest,
)
from backup_manager import BackupManager
from backup_models import (
    BackupMetadata,
    BackupRecord,
)
from filesystem_backup_storage import (
    FilesystemBackupStorage,
)
from recovery_models import (
    BackupReference,
    FileMetadata,
    RecoveryAction,
    RecoveryPolicy,
)
from test_backup_security import (
    AllowAllAccessController,
    DenyingAccessController,
    RecordingEncryptionProvider,
    RecordingSecureDeletionProvider,
)


def build_file_metadata(
    source: Path,
) -> FileMetadata:
    return FileMetadata(
        file_name=source.name,
        file_extension=source.suffix,
        file_path=str(source),
        directory=str(source.parent),
        file_size=source.stat().st_size,
    )


def build_policy() -> RecoveryPolicy:
    return RecoveryPolicy(
        policy_id="policy-001",
        action=RecoveryAction.ROLLBACK_OPERATION,
    )


def build_security_context() -> BackupSecurityContext:
    """Test-only security context that always allows
    operations and records no side effects."""
    return BackupSecurityContext(
        AllowAllAccessController(),
        RecordingEncryptionProvider(),
        RecordingSecureDeletionProvider(),
    )


class SelectiveRetentionEvaluator:
    """Test-only retention rule: a record is expired
    when its backup_id has been marked."""

    def __init__(self) -> None:
        self.expired_ids: set[str] = set()

    def is_expired(self, record) -> bool:
        return (
            record.reference.backup_id
            in self.expired_ids
        )


class FailingRetentionEvaluator:
    """Test-only evaluator that always fails."""

    def is_expired(self, record) -> bool:
        raise RuntimeError(
            "simulated evaluator failure"
        )


def build_manager(
    tmp_path: Path,
    *,
    retry_policy=None,
    failure_logger=None,
    notifier=None,
    security_context=None,
):
    secure_deleter = RecordingSecureDeletionProvider()
    storage = FilesystemBackupStorage(
        tmp_path / "backups",
        secure_deleter,
    )
    retention_evaluator = SelectiveRetentionEvaluator()
    retry_policy = (
        retry_policy
        or BoundedRetryPolicy(max_attempts=1)
    )
    failure_logger = (
        failure_logger
        or RecordingFailureLogger()
    )
    notifier = (
        notifier
        or RecordingRecoveryManagerNotifier()
    )
    if security_context is None:
        security_context = BackupSecurityContext(
            AllowAllAccessController(),
            RecordingEncryptionProvider(),
            secure_deleter,
        )
    manager = BackupManager(
        storage,
        retention_evaluator,
        retry_policy,
        failure_logger,
        notifier,
        security_context,
    )
    return (
        manager,
        retention_evaluator,
        failure_logger,
        notifier,
    )


def build_source(
    tmp_path: Path,
    content: str = "important data",
) -> Path:
    source = tmp_path / "important.txt"
    source.write_text(content, encoding="utf-8")
    return source


class FailingStorage:
    def store(
        self,
        source_path,
        backup_id,
    ):
        raise OSError(
            "simulated storage failure"
        )

    def restore(
        self,
        backup_reference,
        destination_path,
    ):
        raise AssertionError(
            "restore should not be called"
        )

    def delete(
        self,
        backup_reference,
    ):
        raise AssertionError(
            "delete should not be called"
        )


class EmptyReferenceStorage:
    """Returns a reference that points to no file."""

    def store(
        self,
        source_path,
        backup_id,
    ) -> BackupReference:
        return BackupReference(
            backup_id=backup_id,
            backup_path=str(
                source_path.parent / "missing.bak"
            ),
        )

    def restore(
        self,
        backup_reference,
        destination_path,
    ):
        raise AssertionError(
            "restore should not be called"
        )

    def delete(
        self,
        backup_reference,
    ):
        raise AssertionError(
            "delete should not be called"
        )


class FailingRestoreStorage:
    """Test-only storage: backup is valid but the
    restore operation itself fails."""

    def store(
        self,
        source_path,
        backup_id,
    ):
        raise AssertionError(
            "store should not be called"
        )

    def restore(
        self,
        backup_reference,
        destination_path,
    ):
        raise OSError(
            "simulated restore failure"
        )

    def delete(
        self,
        backup_reference,
    ):
        raise AssertionError(
            "delete should not be called"
        )


class FailingDeleteStorage:
    """Test-only storage: every operation is
    delegated except deletion, which fails."""

    def __init__(
        self,
        delegate: FilesystemBackupStorage,
    ) -> None:
        self._delegate = delegate

    def store(
        self,
        source_path,
        backup_id,
    ):
        return self._delegate.store(
            source_path,
            backup_id,
        )

    def restore(
        self,
        backup_reference,
        destination_path,
    ):
        return self._delegate.restore(
            backup_reference,
            destination_path,
        )

    def delete(
        self,
        backup_reference,
    ):
        raise OSError(
            "simulated deletion failure"
        )


class RecordingFailureLogger:
    """Test-only logger that records every failure context."""

    def __init__(self):
        self.events = []

    def log_failure(self, context):
        self.events.append(context)


class RecordingRecoveryManagerNotifier:
    """Test-only notifier that records terminal failures."""

    def __init__(self):
        self.events = []

    def notify_failure(self, context):
        self.events.append(context)


class FailOnceStorage:
    """Test-only storage: the first store() fails, later
    attempts delegate to a real filesystem storage."""

    def __init__(
        self,
        delegate: FilesystemBackupStorage,
    ):
        self._delegate = delegate
        self.calls = 0

    def store(
        self,
        source_path,
        backup_id,
    ):
        self.calls += 1
        if self.calls == 1:
            raise OSError(
                "transient storage failure"
            )
        return self._delegate.store(
            source_path,
            backup_id,
        )

    def restore(
        self,
        backup_reference,
        destination_path,
    ):
        return self._delegate.restore(
            backup_reference,
            destination_path,
        )

    def delete(
        self,
        backup_reference,
    ):
        return self._delegate.delete(
            backup_reference,
        )


class AlwaysFailingStorage:
    """Test-only storage: every operation fails."""

    def store(
        self,
        source_path,
        backup_id,
    ):
        raise OSError(
            "permanent storage failure"
        )

    def restore(
        self,
        backup_reference,
        destination_path,
    ):
        raise AssertionError(
            "restore should not be called"
        )

    def delete(
        self,
        backup_reference,
    ):
        raise AssertionError(
            "delete should not be called"
        )


class FailingRetryPolicy:
    """Test-only retry policy that always fails."""

    def should_retry(
        self,
        attempt,
        error,
    ):
        raise RuntimeError(
            "retry policy failure"
        )


def test_backup_manager_starts_with_no_backup_references(
    tmp_path: Path,
):
    manager, *_ = build_manager(tmp_path)
    assert manager.backup_references == ()


def test_backup_manager_starts_with_empty_recovery_cache(
    tmp_path: Path,
):
    manager, *_ = build_manager(tmp_path)
    assert manager.recovery_cache_size == 0


def test_backup_references_are_returned_as_a_tuple(
    tmp_path: Path,
):
    manager, *_ = build_manager(tmp_path)
    references = manager.backup_references
    assert isinstance(references, tuple)


def test_backup_manager_starts_with_zero_count(
    tmp_path: Path,
):
    manager, *_ = build_manager(tmp_path)
    assert manager.backup_count == 0


def test_backup_manager_returns_none_for_unknown_record(
    tmp_path: Path,
):
    manager, *_ = build_manager(tmp_path)
    assert manager.get_record("missing") is None


def test_backup_manager_requires_storage_port(
    tmp_path: Path,
):
    with pytest.raises(TypeError, match="storage"):
        BackupManager(
            object(),
            SelectiveRetentionEvaluator(),
            BoundedRetryPolicy(max_attempts=1),
            RecordingFailureLogger(),
            RecordingRecoveryManagerNotifier(),
            build_security_context(),
        )


def test_create_backup_creates_real_recoverable_file(
    tmp_path: Path,
):
    source = build_source(tmp_path)
    manager, *_ = build_manager(tmp_path)

    reference = manager.create_backup(
        build_file_metadata(source),
        build_policy(),
    )

    assert isinstance(
        reference,
        BackupReference,
    )
    backup_file = Path(reference.backup_path)
    assert backup_file.is_file()
    assert backup_file.read_text(
        encoding="utf-8"
    ) == "important data"
    assert tmp_path / "backups" in backup_file.parents
    assert source.is_file()


def test_create_backup_registers_the_reference(
    tmp_path: Path,
):
    source = build_source(tmp_path)
    manager, *_ = build_manager(tmp_path)

    reference = manager.create_backup(
        build_file_metadata(source),
        build_policy(),
    )

    assert manager.backup_count == 1
    assert reference in manager.backup_references

    record = manager.get_record(reference.backup_id)
    assert isinstance(record, BackupRecord)
    assert record.reference == reference
    assert record.status == "CREATED"
    assert (
        record.metadata.values["source_path"]
        == str(source)
    )
    assert (
        record.metadata.values["policy_id"]
        == "policy-001"
    )
    assert (
        record.metadata.values["recovery_action"]
        == "ROLLBACK_OPERATION"
    )


def test_create_backup_preserves_source_content(
    tmp_path: Path,
):
    source = build_source(
        tmp_path,
        content="before backup",
    )
    manager, *_ = build_manager(tmp_path)

    reference = manager.create_backup(
        build_file_metadata(source),
        build_policy(),
    )
    source.write_text(
        "after backup",
        encoding="utf-8",
    )

    assert Path(reference.backup_path).read_text(
        encoding="utf-8"
    ) == "before backup"


def test_create_backup_generates_unique_references(
    tmp_path: Path,
):
    source = build_source(tmp_path)
    manager, *_ = build_manager(tmp_path)

    first = manager.create_backup(
        build_file_metadata(source),
        build_policy(),
    )
    second = manager.create_backup(
        build_file_metadata(source),
        build_policy(),
    )

    assert first.backup_id != second.backup_id
    assert manager.backup_count == 2
    assert first.backup_path != second.backup_path


def test_storage_failure_does_not_register_reference(
    tmp_path: Path,
):
    source = tmp_path / "sample.txt"
    source.write_text("data", encoding="utf-8")
    manager = BackupManager(
        FailingStorage(),
        SelectiveRetentionEvaluator(),
        BoundedRetryPolicy(max_attempts=1),
        RecordingFailureLogger(),
        RecordingRecoveryManagerNotifier(),
        build_security_context(),
    )

    with pytest.raises(
        BackupCreationError,
        match="simulated storage failure",
    ):
        manager.create_backup(
            build_file_metadata(source),
            build_policy(),
        )

    assert manager.backup_count == 0
    assert manager.backup_references == ()


def test_invalid_reference_from_storage_is_rejected(
    tmp_path: Path,
):
    source = build_source(tmp_path)
    manager = BackupManager(
        EmptyReferenceStorage(),
        SelectiveRetentionEvaluator(),
        BoundedRetryPolicy(max_attempts=1),
        RecordingFailureLogger(),
        RecordingRecoveryManagerNotifier(),
        build_security_context(),
    )

    with pytest.raises(
        BackupCreationError,
        match="storage returned an invalid backup reference",
    ):
        manager.create_backup(
            build_file_metadata(source),
            build_policy(),
        )

    assert manager.backup_count == 0
    assert manager.backup_references == ()


def test_create_backup_rejects_invalid_file_metadata(
    tmp_path: Path,
):
    manager, *_ = build_manager(tmp_path)
    with pytest.raises(TypeError, match="file_metadata"):
        manager.create_backup(
            "sample.txt",
            build_policy(),
        )


def test_create_backup_rejects_invalid_recovery_policy(
    tmp_path: Path,
):
    source = build_source(tmp_path)
    manager, *_ = build_manager(tmp_path)
    with pytest.raises(
        TypeError, match="recovery_policy"
    ):
        manager.create_backup(
            build_file_metadata(source),
            "policy-001",
        )


def test_backup_record_contains_reference_metadata_and_status(
    tmp_path: Path,
):
    source = tmp_path / "important.txt"
    source.write_text(
        "PRISM backup",
        encoding="utf-8",
    )
    manager, *_ = build_manager(tmp_path)
    reference = manager.create_backup(
        build_file_metadata(source),
        build_policy(),
    )
    record = manager.get_backup_record(reference)
    assert record.reference == reference
    assert isinstance(
        record.metadata,
        BackupMetadata,
    )
    assert record.status == "CREATED"


def test_backup_metadata_is_retrievable(
    tmp_path: Path,
):
    source = tmp_path / "important.txt"
    source.write_text(
        "PRISM metadata test",
        encoding="utf-8",
    )
    manager, *_ = build_manager(tmp_path)
    reference = manager.create_backup(
        build_file_metadata(source),
        build_policy(),
    )
    metadata = manager.get_backup_metadata(reference)
    assert metadata.values[
        "source_path"
    ] == str(source)
    assert metadata.values[
        "backup_path"
    ] == reference.backup_path
    assert metadata.values[
        "policy_id"
    ] == "policy-001"


def test_backup_status_is_retrievable(
    tmp_path: Path,
):
    source = tmp_path / "status.txt"
    source.write_text(
        "status test",
        encoding="utf-8",
    )
    manager, *_ = build_manager(tmp_path)
    reference = manager.create_backup(
        build_file_metadata(source),
        build_policy(),
    )
    assert (
        manager.get_backup_status(reference)
        == "CREATED"
    )


def test_unknown_backup_reference_is_rejected(
    tmp_path: Path,
):
    source = tmp_path / "source.txt"
    source.write_text(
        "data",
        encoding="utf-8",
    )
    manager, *_ = build_manager(tmp_path)
    manager.create_backup(
        build_file_metadata(source),
        build_policy(),
    )
    unknown_reference = BackupReference(
        backup_id="unknown-backup",
        backup_path=str(
            tmp_path / "backups" / "unknown.backup"
        ),
    )
    with pytest.raises(
        KeyError,
        match="backup reference not found",
    ):
        manager.get_backup_record(
            unknown_reference
        )


def test_reference_with_existing_id_but_wrong_path_is_rejected(
    tmp_path: Path,
):
    source = tmp_path / "source.txt"
    source.write_text(
        "data",
        encoding="utf-8",
    )
    manager, *_ = build_manager(tmp_path)
    reference = manager.create_backup(
        build_file_metadata(source),
        build_policy(),
    )
    forged_reference = BackupReference(
        backup_id=reference.backup_id,
        backup_path=str(
            tmp_path / "backups" / "wrong.backup"
        ),
    )
    with pytest.raises(
        KeyError,
        match="backup reference mismatch",
    ):
        manager.get_backup_record(
            forged_reference
        )


def test_get_backup_record_rejects_invalid_reference(
    tmp_path: Path,
):
    manager, *_ = build_manager(tmp_path)
    with pytest.raises(
        TypeError, match="backup_reference"
    ):
        manager.get_backup_record("backup-001")


def test_backup_record_is_immutable(
    tmp_path: Path,
):
    source = tmp_path / "immutable.txt"
    source.write_text(
        "immutable",
        encoding="utf-8",
    )
    manager, *_ = build_manager(tmp_path)
    reference = manager.create_backup(
        build_file_metadata(source),
        build_policy(),
    )
    record = manager.get_backup_record(reference)
    with pytest.raises(
        AttributeError,
    ):
        record.status = "CHANGED"


def test_backup_metadata_cannot_be_mutated_through_record(
    tmp_path: Path,
):
    source = tmp_path / "metadata.txt"
    source.write_text(
        "metadata",
        encoding="utf-8",
    )
    manager, *_ = build_manager(tmp_path)
    reference = manager.create_backup(
        build_file_metadata(source),
        build_policy(),
    )
    record = manager.get_backup_record(reference)
    with pytest.raises(
        TypeError,
    ):
        record.metadata.values[
            "source_path"
        ] = "tampered"


def test_create_backup_stores_integrity_metadata(
    tmp_path: Path,
):
    source = tmp_path / "important.txt"
    source.write_text(
        "integrity protected data",
        encoding="utf-8",
    )
    manager, *_ = build_manager(tmp_path)
    reference = manager.create_backup(
        build_file_metadata(source),
        build_policy(),
    )
    metadata = manager.get_backup_metadata(reference)
    backup_path = Path(reference.backup_path)
    assert (
        metadata.values["integrity_algorithm"]
        == INTEGRITY_ALGORITHM
    )
    assert metadata.values[
        "integrity_digest"
    ] == calculate_file_digest(backup_path)


def test_verify_backup_returns_true_for_intact_backup(
    tmp_path: Path,
):
    source = tmp_path / "important.txt"
    source.write_text(
        "original backup content",
        encoding="utf-8",
    )
    manager, *_ = build_manager(tmp_path)
    reference = manager.create_backup(
        build_file_metadata(source),
        build_policy(),
    )
    assert manager.verify_backup(reference) is True


def test_verify_backup_detects_corruption(
    tmp_path: Path,
):
    source = tmp_path / "important.txt"
    source.write_text(
        "original content",
        encoding="utf-8",
    )
    manager, *_ = build_manager(tmp_path)
    reference = manager.create_backup(
        build_file_metadata(source),
        build_policy(),
    )
    backup_path = Path(reference.backup_path)
    backup_path.write_text(
        "CORRUPTED CONTENT",
        encoding="utf-8",
    )
    assert manager.verify_backup(reference) is False


def test_verify_backup_detects_content_with_same_size(
    tmp_path: Path,
):
    """Byte-for-byte comparison: same size, different
    content must still be flagged as corrupted."""
    source = tmp_path / "important.txt"
    source.write_text(
        "AAAAAAAAAA",
        encoding="utf-8",
    )
    manager, *_ = build_manager(tmp_path)
    reference = manager.create_backup(
        build_file_metadata(source),
        build_policy(),
    )
    backup_path = Path(reference.backup_path)
    backup_path.write_text(
        "BBBBBBBBBB",
        encoding="utf-8",
    )
    assert (
        backup_path.stat().st_size
        == source.stat().st_size
    )
    assert manager.verify_backup(reference) is False


def test_verify_backup_returns_false_when_backup_is_missing(
    tmp_path: Path,
):
    source = tmp_path / "important.txt"
    source.write_text(
        "original content",
        encoding="utf-8",
    )
    manager, *_ = build_manager(tmp_path)
    reference = manager.create_backup(
        build_file_metadata(source),
        build_policy(),
    )
    backup_path = Path(reference.backup_path)
    backup_path.unlink()
    assert manager.verify_backup(reference) is False


def test_verify_backup_returns_false_for_unknown_reference(
    tmp_path: Path,
):
    manager, *_ = build_manager(tmp_path)
    reference = BackupReference(
        backup_id="unknown-backup",
        backup_path=str(
            tmp_path / "backups" / "unknown.backup"
        ),
    )
    assert manager.verify_backup(reference) is False


def test_duplicate_backup_request_creates_unique_backups(
    tmp_path: Path,
):
    manager = build_manager(tmp_path)[0]
    source = tmp_path / "duplicate.txt"
    source.write_text(
        "same content",
        encoding="utf-8",
    )
    file_metadata = build_file_metadata(
        source
    )
    first = manager.create_backup(
        file_metadata,
        build_policy(),
    )
    second = manager.create_backup(
        file_metadata,
        build_policy(),
    )
    assert first != second
    assert len(
        manager.backup_references
    ) == 2


def test_duplicate_backup_requests_create_unique_physical_backups(
    tmp_path: Path,
):
    manager = build_manager(tmp_path)[0]
    source = tmp_path / "physical-duplicate.txt"
    source.write_text(
        "one physical backup",
        encoding="utf-8",
    )
    file_metadata = build_file_metadata(
        source
    )
    first = manager.create_backup(
        file_metadata,
        build_policy(),
    )
    second = manager.create_backup(
        file_metadata,
        build_policy(),
    )
    assert first != second
    assert len(
        manager.backup_references
    ) == 2
    backup_directory = (
        tmp_path / "backups"
    )
    assert backup_directory.exists()
    backup_files = list(backup_directory.iterdir())
    assert len(backup_files) >= 2


def test_changed_source_content_creates_new_backup(
    tmp_path: Path,
):
    manager = build_manager(tmp_path)[0]
    source = tmp_path / "changed.txt"
    source.write_text(
        "version one",
        encoding="utf-8",
    )
    first_metadata = build_file_metadata(
        source
    )
    first = manager.create_backup(
        first_metadata,
        build_policy(),
    )
    source.write_text(
        "version two",
        encoding="utf-8",
    )
    second_metadata = build_file_metadata(
        source
    )
    second = manager.create_backup(
        second_metadata,
        build_policy(),
    )
    assert first != second
    assert len(
        manager.backup_references
    ) == 2


def test_changed_source_preserves_both_backup_versions(
    tmp_path: Path,
):
    manager = build_manager(tmp_path)[0]
    source = tmp_path / "versions.txt"
    source.write_text(
        "version one",
        encoding="utf-8",
    )
    metadata = build_file_metadata(
        source
    )
    first = manager.create_backup(
        metadata,
        build_policy(),
    )
    source.write_text(
        "version two",
        encoding="utf-8",
    )
    metadata = build_file_metadata(
        source
    )
    second = manager.create_backup(
        metadata,
        build_policy(),
    )
    assert first != second
    assert len(
        manager.backup_references
    ) == 2
    assert manager.verify_backup(first)
    assert manager.verify_backup(second)


def test_same_content_different_files_create_separate_backups(
    tmp_path: Path,
):
    manager = build_manager(tmp_path)[0]
    first_source = tmp_path / "one.txt"
    second_source = tmp_path / "two.txt"
    first_source.write_text(
        "identical",
        encoding="utf-8",
    )
    second_source.write_text(
        "identical",
        encoding="utf-8",
    )
    first = manager.create_backup(
        build_file_metadata(first_source),
        build_policy(),
    )
    second = manager.create_backup(
        build_file_metadata(second_source),
        build_policy(),
    )
    assert first != second
    assert len(
        manager.backup_references
    ) == 2


class CountingStorage:
    def __init__(
        self,
        delegate,
    ):
        self._delegate = delegate
        self._lock = Lock()
        self.store_calls = 0

    def store(
        self,
        source_path,
        backup_id,
    ):
        with self._lock:
            self.store_calls += 1
        time.sleep(0.05)
        return self._delegate.store(
            source_path,
            backup_id,
        )

    def restore(
        self,
        backup_reference,
        destination_path,
    ):
        return self._delegate.restore(
            backup_reference,
            destination_path,
        )

    def delete(
        self,
        backup_reference,
    ):
        return self._delegate.delete(
            backup_reference,
        )


def test_concurrent_backup_requests_create_unique_backups(
    tmp_path: Path,
):
    real_storage = FilesystemBackupStorage(
        tmp_path / "backups",
        RecordingSecureDeletionProvider(),
    )
    storage = CountingStorage(
        real_storage
    )
    manager = BackupManager(
        storage,
        SelectiveRetentionEvaluator(),
        BoundedRetryPolicy(
            max_attempts=1
        ),
        RecordingFailureLogger(),
        RecordingRecoveryManagerNotifier(),
        build_security_context(),
    )
    source = tmp_path / "concurrent.txt"
    source.write_text(
        "concurrent backup",
        encoding="utf-8",
    )
    metadata = build_file_metadata(
        source
    )

    def create():
        return manager.create_backup(
            metadata,
            build_policy(),
        )

    with ThreadPoolExecutor(
        max_workers=8
    ) as executor:
        results = list(
            executor.map(
                lambda _: create(),
                range(8),
            )
        )

    assert storage.store_calls == 8
    assert len(set(results)) == 8
    assert len(
        manager.backup_references
    ) == 8


class BlockingCountingStorage:
    def __init__(
        self,
        delegate,
    ):
        self._delegate = delegate
        self._lock = Lock()
        self.active = 0
        self.max_active = 0

    def store(
        self,
        source_path,
        backup_id,
    ):
        with self._lock:
            self.active += 1
            self.max_active = max(
                self.max_active,
                self.active,
            )
        try:
            time.sleep(0.1)
            return self._delegate.store(
                source_path,
                backup_id,
            )
        finally:
            with self._lock:
                self.active -= 1

    def restore(
        self,
        backup_reference,
        destination_path,
    ):
        return self._delegate.restore(
            backup_reference,
            destination_path,
        )

    def delete(
        self,
        backup_reference,
    ):
        return self._delegate.delete(
            backup_reference,
        )


def test_different_sources_are_not_globally_serialized(
    tmp_path: Path,
):
    real_storage = FilesystemBackupStorage(
        tmp_path / "backups",
        RecordingSecureDeletionProvider(),
    )
    storage = BlockingCountingStorage(
        real_storage
    )
    manager = BackupManager(
        storage,
        SelectiveRetentionEvaluator(),
        BoundedRetryPolicy(
            max_attempts=1
        ),
        RecordingFailureLogger(),
        RecordingRecoveryManagerNotifier(),
        build_security_context(),
    )
    first_source = tmp_path / "first.txt"
    second_source = tmp_path / "second.txt"
    first_source.write_text(
        "first",
        encoding="utf-8",
    )
    second_source.write_text(
        "second",
        encoding="utf-8",
    )
    first_metadata = build_file_metadata(
        first_source
    )
    second_metadata = build_file_metadata(
        second_source
    )

    def create_first():
        return manager.create_backup(
            first_metadata,
            build_policy(),
        )

    def create_second():
        return manager.create_backup(
            second_metadata,
            build_policy(),
        )

    with ThreadPoolExecutor(
        max_workers=2
    ) as executor:
        futures = [
            executor.submit(
                create_first
            ),
            executor.submit(
                create_second
            ),
        ]
        results = [
            f.result()
            for f in futures
        ]

    assert storage.max_active >= 2
    assert len(results) == 2
    assert results[0] != results[1]


def test_verify_backup_rejects_unsupported_integrity_algorithm(
    tmp_path: Path,
):
    source = tmp_path / "important.txt"
    source.write_text(
        "protected content",
        encoding="utf-8",
    )
    manager, *_ = build_manager(tmp_path)
    reference = manager.create_backup(
        build_file_metadata(source),
        build_policy(),
    )
    original_record = manager.get_backup_record(
        reference
    )
    tampered_metadata = BackupMetadata(
        values={
            **dict(original_record.metadata.values),
            "integrity_algorithm": "UNKNOWN",
        }
    )
    # Defensive-behavior test only: production code
    # must never mutate manager internals this way.
    manager._backup_records[
        reference.backup_id
    ] = BackupRecord(
        reference=original_record.reference,
        metadata=tampered_metadata,
        status=original_record.status,
        file_metadata=original_record.file_metadata,
    )
    assert manager.verify_backup(reference) is False


def test_verify_backup_rejects_missing_digest_metadata(
    tmp_path: Path,
):
    source = tmp_path / "important.txt"
    source.write_text(
        "protected content",
        encoding="utf-8",
    )
    manager, *_ = build_manager(tmp_path)
    reference = manager.create_backup(
        build_file_metadata(source),
        build_policy(),
    )
    original_record = manager.get_backup_record(
        reference
    )
    tampered_values = dict(
        original_record.metadata.values
    )
    del tampered_values["integrity_digest"]
    manager._backup_records[
        reference.backup_id
    ] = BackupRecord(
        reference=original_record.reference,
        metadata=BackupMetadata(
            values=tampered_values
        ),
        status=original_record.status,
        file_metadata=original_record.file_metadata,
    )
    assert manager.verify_backup(reference) is False


def test_verify_backup_rejects_invalid_reference(
    tmp_path: Path,
):
    manager, *_ = build_manager(tmp_path)
    with pytest.raises(
        TypeError, match="backup_reference"
    ):
        manager.verify_backup("backup-001")


def test_restore_backup_restores_original_content(
    tmp_path: Path,
):
    source = tmp_path / "important.txt"
    source.write_text(
        "original legitimate content",
        encoding="utf-8",
    )
    manager, *_ = build_manager(tmp_path)
    file_metadata = build_file_metadata(source)
    reference = manager.create_backup(
        file_metadata,
        build_policy(),
    )
    source.write_text(
        "changed suspicious content",
        encoding="utf-8",
    )
    result = manager.restore_backup(
        reference,
        file_metadata,
    )
    assert result is True
    assert source.read_text(
        encoding="utf-8"
    ) == "original legitimate content"


def test_restore_backup_rejects_corrupted_backup_without_modifying_target(
    tmp_path: Path,
):
    source = tmp_path / "important.txt"
    source.write_text(
        "original legitimate content",
        encoding="utf-8",
    )
    manager, *_ = build_manager(tmp_path)
    file_metadata = build_file_metadata(source)
    reference = manager.create_backup(
        file_metadata,
        build_policy(),
    )
    source.write_text(
        "current target content",
        encoding="utf-8",
    )
    backup_path = Path(reference.backup_path)
    backup_path.write_text(
        "CORRUPTED BACKUP",
        encoding="utf-8",
    )

    # corrupted backup
    #       |
    #       v
    # verify_backup() -> False
    #       |
    #       v
    # restore NOT attempted
    #       |
    #       v
    # target unchanged
    assert manager.verify_backup(reference) is False
    result = manager.restore_backup(
        reference,
        file_metadata,
    )
    assert result is False
    assert source.read_text(
        encoding="utf-8"
    ) == "current target content"


def test_restore_backup_returns_false_for_missing_backup(
    tmp_path: Path,
):
    source = tmp_path / "important.txt"
    source.write_text(
        "original content",
        encoding="utf-8",
    )
    manager, *_ = build_manager(tmp_path)
    file_metadata = build_file_metadata(source)
    reference = manager.create_backup(
        file_metadata,
        build_policy(),
    )
    source.write_text(
        "current content",
        encoding="utf-8",
    )
    Path(reference.backup_path).unlink()
    result = manager.restore_backup(
        reference,
        file_metadata,
    )
    assert result is False
    assert source.read_text(
        encoding="utf-8"
    ) == "current content"


def test_restore_backup_returns_false_for_unknown_reference(
    tmp_path: Path,
):
    source = tmp_path / "important.txt"
    source.write_text(
        "current content",
        encoding="utf-8",
    )
    manager, *_ = build_manager(tmp_path)
    unknown_reference = BackupReference(
        backup_id="unknown",
        backup_path=str(
            tmp_path
            / "backups"
            / "unknown.backup"
        ),
    )
    result = manager.restore_backup(
        unknown_reference,
        build_file_metadata(source),
    )
    assert result is False
    assert source.read_text(
        encoding="utf-8"
    ) == "current content"


def test_restore_backup_rejects_invalid_reference(
    tmp_path: Path,
):
    manager, *_ = build_manager(tmp_path)
    file_path = tmp_path / "file.txt"
    file_path.write_text(
        "data",
        encoding="utf-8",
    )
    with pytest.raises(
        TypeError,
        match="BackupReference",
    ):
        manager.restore_backup(
            None,
            build_file_metadata(file_path),
        )


def test_restore_backup_rejects_invalid_file_metadata(
    tmp_path: Path,
):
    manager, *_ = build_manager(tmp_path)
    file_path = tmp_path / "file.txt"
    file_path.write_text(
        "data",
        encoding="utf-8",
    )
    reference = BackupReference(
        backup_id="backup-001",
        backup_path=str(
            tmp_path
            / "backups"
            / "backup-001.txt"
        ),
    )
    with pytest.raises(
        TypeError,
        match="FileMetadata",
    ):
        manager.restore_backup(
            reference,
            None,
        )


def test_restore_backup_returns_false_when_storage_restore_fails(
    tmp_path: Path,
):
    source = tmp_path / "important.txt"
    source.write_text(
        "original",
        encoding="utf-8",
    )
    real_storage = FilesystemBackupStorage(
        tmp_path / "backups",
        RecordingSecureDeletionProvider(),
    )
    manager = BackupManager(
        real_storage,
        SelectiveRetentionEvaluator(),
        BoundedRetryPolicy(max_attempts=1),
        RecordingFailureLogger(),
        RecordingRecoveryManagerNotifier(),
        build_security_context(),
    )
    file_metadata = build_file_metadata(source)
    reference = manager.create_backup(
        file_metadata,
        build_policy(),
    )
    source.write_text(
        "current",
        encoding="utf-8",
    )
    # Direct private-state mutation is test-only:
    # production code never reassigns _storage.
    manager._storage = FailingRestoreStorage()

    result = manager.restore_backup(
        reference,
        file_metadata,
    )
    assert result is False
    assert source.read_text(
        encoding="utf-8"
    ) == "current"


def test_manager_satisfies_backup_manager_port(
    tmp_path: Path,
):
    from backup_manager_port import BackupManagerPort

    manager, *_ = build_manager(tmp_path)
    assert isinstance(manager, BackupManagerPort)


def test_backup_manager_rejects_invalid_retention_evaluator(
    tmp_path: Path,
):
    storage = FilesystemBackupStorage(
        tmp_path / "backups",
        RecordingSecureDeletionProvider(),
    )
    with pytest.raises(
        TypeError,
        match="retention_evaluator",
    ):
        BackupManager(
            storage,
            object(),
            BoundedRetryPolicy(max_attempts=1),
            RecordingFailureLogger(),
            RecordingRecoveryManagerNotifier(),
            build_security_context(),
        )


def test_cleanup_retains_non_expired_backup(
    tmp_path: Path,
):
    manager, *_ = build_manager(tmp_path)
    source = tmp_path / "sample.txt"
    source.write_text(
        "keep this backup",
        encoding="utf-8",
    )
    reference = manager.create_backup(
        build_file_metadata(source),
        build_policy(),
    )
    backup_path = Path(reference.backup_path)

    manager.cleanup_backups()

    assert backup_path.exists()
    assert reference in manager.backup_references


def test_cleanup_removes_expired_backup(
    tmp_path: Path,
):
    manager, evaluator, *_ = build_manager(tmp_path)
    source = tmp_path / "sample.txt"
    source.write_text(
        "remove this backup",
        encoding="utf-8",
    )
    reference = manager.create_backup(
        build_file_metadata(source),
        build_policy(),
    )
    evaluator.expired_ids.add(reference.backup_id)
    backup_path = Path(reference.backup_path)

    manager.cleanup_backups()

    assert not backup_path.exists()
    assert reference not in manager.backup_references


def test_cleanup_keeps_record_when_storage_delete_fails(
    tmp_path: Path,
):
    real_storage = FilesystemBackupStorage(
        tmp_path / "backups",
        RecordingSecureDeletionProvider(),
    )
    storage = FailingDeleteStorage(real_storage)
    evaluator = SelectiveRetentionEvaluator()
    manager = BackupManager(
        storage,
        evaluator,
        BoundedRetryPolicy(max_attempts=1),
        RecordingFailureLogger(),
        RecordingRecoveryManagerNotifier(),
        build_security_context(),
    )
    source = tmp_path / "sample.txt"
    source.write_text(
        "retain when deletion fails",
        encoding="utf-8",
    )
    reference = manager.create_backup(
        build_file_metadata(source),
        build_policy(),
    )
    evaluator.expired_ids.add(reference.backup_id)
    backup_path = Path(reference.backup_path)

    manager.cleanup_backups()

    # Physical cleanup failed, so both the backup file and
    # the manager's record of it must survive.
    assert backup_path.exists()
    assert reference in manager.backup_references


def test_cleanup_removes_stale_record_when_backup_already_missing(
    tmp_path: Path,
):
    manager, evaluator, *_ = build_manager(tmp_path)
    source = tmp_path / "sample.txt"
    source.write_text(
        "stale backup",
        encoding="utf-8",
    )
    reference = manager.create_backup(
        build_file_metadata(source),
        build_policy(),
    )
    evaluator.expired_ids.add(reference.backup_id)
    Path(reference.backup_path).unlink()

    manager.cleanup_backups()

    assert reference not in manager.backup_references


def test_cleanup_does_not_delete_when_retention_evaluation_fails(
    tmp_path: Path,
):
    storage = FilesystemBackupStorage(
        tmp_path / "backups",
        RecordingSecureDeletionProvider(),
    )
    manager = BackupManager(
        storage,
        FailingRetentionEvaluator(),
        BoundedRetryPolicy(max_attempts=1),
        RecordingFailureLogger(),
        RecordingRecoveryManagerNotifier(),
        build_security_context(),
    )
    source = tmp_path / "sample.txt"
    source.write_text(
        "must remain safe",
        encoding="utf-8",
    )
    reference = manager.create_backup(
        build_file_metadata(source),
        build_policy(),
    )
    backup_path = Path(reference.backup_path)

    manager.cleanup_backups()

    assert backup_path.exists()
    assert reference in manager.backup_references


def test_create_backup_populates_recovery_cache(
    tmp_path: Path,
):
    manager, *_ = build_manager(tmp_path)
    source = tmp_path / "cached.txt"
    source.write_text(
        "cache me",
        encoding="utf-8",
    )
    file_metadata = build_file_metadata(source)

    reference = manager.create_backup(
        file_metadata,
        build_policy(),
    )

    cached_reference = (
        manager.get_cached_backup_reference(
            file_metadata
        )
    )
    assert cached_reference == reference
    assert manager.recovery_cache_size == 1


def test_get_cached_backup_reference_returns_none_for_unknown_file(
    tmp_path: Path,
):
    manager, *_ = build_manager(tmp_path)
    source = tmp_path / "unknown.txt"
    source.write_text(
        "unknown",
        encoding="utf-8",
    )
    file_metadata = build_file_metadata(source)

    assert (
        manager.get_cached_backup_reference(
            file_metadata
        )
        is None
    )


def test_cleanup_retains_cache_for_non_expired_backup(
    tmp_path: Path,
):
    manager, *_ = build_manager(tmp_path)
    source = tmp_path / "retained.txt"
    source.write_text(
        "retain",
        encoding="utf-8",
    )
    file_metadata = build_file_metadata(source)

    reference = manager.create_backup(
        file_metadata,
        build_policy(),
    )

    manager.cleanup_backups()

    assert (
        manager.get_cached_backup_reference(
            file_metadata
        )
        == reference
    )
    assert manager.recovery_cache_size == 1


def test_cleanup_removes_cache_for_expired_backup(
    tmp_path: Path,
):
    manager, evaluator, *_ = build_manager(tmp_path)
    source = tmp_path / "expired.txt"
    source.write_text(
        "expire me",
        encoding="utf-8",
    )
    file_metadata = build_file_metadata(source)

    reference = manager.create_backup(
        file_metadata,
        build_policy(),
    )
    assert (
        manager.get_cached_backup_reference(
            file_metadata
        )
        == reference
    )
    evaluator.expired_ids.add(
        reference.backup_id
    )

    manager.cleanup_backups()

    assert (
        manager.get_cached_backup_reference(
            file_metadata
        )
        is None
    )
    assert manager.recovery_cache_size == 0


def test_stale_cache_entry_is_removed(
    tmp_path: Path,
):
    manager, *_ = build_manager(tmp_path)
    source = tmp_path / "stale.txt"
    source.write_text(
        "stale",
        encoding="utf-8",
    )
    file_metadata = build_file_metadata(source)

    reference = manager.create_backup(
        file_metadata,
        build_policy(),
    )
    assert (
        manager.get_cached_backup_reference(
            file_metadata
        )
        == reference
    )

    # Test-only internal mutation: simulates an
    # inconsistent state where a cache entry outlived the
    # record that should authorize it.
    manager._backup_records.pop(
        reference.backup_id,
        None,
    )

    assert (
        manager.get_cached_backup_reference(
            file_metadata
        )
        is None
    )
    assert manager.recovery_cache_size == 0


def test_create_backup_retries_transient_failure(
    tmp_path: Path,
):
    real_storage = FilesystemBackupStorage(
        tmp_path / "backups",
        RecordingSecureDeletionProvider(),
    )
    storage = FailOnceStorage(real_storage)
    logger = RecordingFailureLogger()
    notifier = RecordingRecoveryManagerNotifier()
    manager = BackupManager(
        storage,
        SelectiveRetentionEvaluator(),
        BoundedRetryPolicy(max_attempts=2),
        logger,
        notifier,
        build_security_context(),
    )
    source = tmp_path / "retry.txt"
    source.write_text(
        "retry succeeds",
        encoding="utf-8",
    )

    reference = manager.create_backup(
        build_file_metadata(source),
        build_policy(),
    )

    assert reference is not None
    assert storage.calls == 2
    # The transient failure is logged exactly once, and a
    # successful retry is never reported to Recovery Manager.
    assert len(logger.events) == 1
    assert len(notifier.events) == 0


def test_terminal_backup_failure_is_logged_and_notified(
    tmp_path: Path,
):
    logger = RecordingFailureLogger()
    notifier = RecordingRecoveryManagerNotifier()
    manager = BackupManager(
        AlwaysFailingStorage(),
        SelectiveRetentionEvaluator(),
        BoundedRetryPolicy(max_attempts=2),
        logger,
        notifier,
        build_security_context(),
    )
    source = tmp_path / "failure.txt"
    source.write_text(
        "failure",
        encoding="utf-8",
    )

    with pytest.raises(BackupCreationError):
        manager.create_backup(
            build_file_metadata(source),
            build_policy(),
        )

    assert len(logger.events) == 2
    assert len(notifier.events) == 1

    notification = notifier.events[0]
    assert notification.operation == "CREATE_BACKUP"
    assert notification.attempt == 2
    assert notification.error_type == "OSError"


def test_terminal_backup_failure_registers_no_reference(
    tmp_path: Path,
):
    manager = BackupManager(
        AlwaysFailingStorage(),
        SelectiveRetentionEvaluator(),
        BoundedRetryPolicy(max_attempts=3),
        RecordingFailureLogger(),
        RecordingRecoveryManagerNotifier(),
        build_security_context(),
    )
    source = tmp_path / "no-reference.txt"
    source.write_text(
        "must not become a reference",
        encoding="utf-8",
    )

    with pytest.raises(BackupCreationError):
        manager.create_backup(
            build_file_metadata(source),
            build_policy(),
        )

    # A terminal failure must never leave an invalid or
    # unmanaged reference behind.
    assert manager.backup_references == ()
    assert manager.recovery_cache_size == 0


def test_failed_post_storage_attempt_is_cleaned_before_retry(
    tmp_path: Path,
    monkeypatch,
):
    real_storage = FilesystemBackupStorage(
        tmp_path / "backups",
        RecordingSecureDeletionProvider(),
    )
    manager = BackupManager(
        real_storage,
        SelectiveRetentionEvaluator(),
        BoundedRetryPolicy(max_attempts=1),
        RecordingFailureLogger(),
        RecordingRecoveryManagerNotifier(),
        build_security_context(),
    )
    source = tmp_path / "digest-failure.txt"
    source.write_text(
        "cleanup orphan",
        encoding="utf-8",
    )

    import backup_manager as module

    def fail_digest(path):
        raise OSError(
            "digest calculation failure"
        )

    monkeypatch.setattr(
        module,
        "calculate_file_digest",
        fail_digest,
    )

    with pytest.raises(BackupCreationError):
        manager.create_backup(
            build_file_metadata(source),
            build_policy(),
        )

    backups = list(
        (tmp_path / "backups").glob("*")
    )

    # The physical backup existed when the digest failed, so
    # the failed attempt must have deleted it before the
    # terminal failure surfaced.
    assert backups == []
    assert manager.backup_references == ()
    assert manager.recovery_cache_size == 0


def test_retry_policy_failure_is_logged_and_notified(
    tmp_path: Path,
):
    logger = RecordingFailureLogger()
    notifier = RecordingRecoveryManagerNotifier()
    manager = BackupManager(
        AlwaysFailingStorage(),
        SelectiveRetentionEvaluator(),
        FailingRetryPolicy(),
        logger,
        notifier,
        build_security_context(),
    )
    source = tmp_path / "retry-policy.txt"
    source.write_text(
        "data",
        encoding="utf-8",
    )

    with pytest.raises(BackupCreationError):
        manager.create_backup(
            build_file_metadata(source),
            build_policy(),
        )

    # One event for the attempt failure and one for the
    # retry-policy failure itself; Recovery Manager is
    # notified exactly once, with the policy failure.
    assert len(logger.events) == 2
    assert len(notifier.events) == 1
    assert (
        notifier.events[0].error_type == "RuntimeError"
    )


class ExplodingStorage:
    """Test-only storage: any store() call means the
    access-control boundary failed to stop the operation."""

    def store(
        self,
        source_path,
        backup_id,
    ):
        raise AssertionError(
            "storage must not be called"
        )

    def restore(
        self,
        backup_reference,
        destination_path,
    ):
        raise AssertionError(
            "restore must not be called"
        )

    def delete(
        self,
        backup_reference,
    ):
        raise AssertionError(
            "delete must not be called"
        )


class SwitchableAccessController:
    """Test-only access controller whose verdict can be
    flipped between operations."""

    def __init__(self, allow: bool = True):
        self.allow = allow

    def authorize(
        self,
        operation,
        file_metadata,
        backup_reference=None,
    ):
        if not self.allow:
            raise BackupAccessDeniedError(
                "operation denied"
            )


class ExplodingRestoreStorage:
    """Test-only storage: store/delete delegate to a real
    filesystem storage, but restore must never be reached
    once access is denied."""

    def __init__(self, delegate) -> None:
        self._delegate = delegate

    def store(
        self,
        source_path,
        backup_id,
    ):
        return self._delegate.store(
            source_path,
            backup_id,
        )

    def restore(
        self,
        backup_reference,
        destination_path,
    ):
        raise AssertionError(
            "restore must not be called"
        )

    def delete(
        self,
        backup_reference,
    ):
        return self._delegate.delete(backup_reference)


def test_backup_manager_requires_security_context(
    tmp_path: Path,
):
    real_storage = FilesystemBackupStorage(
        tmp_path / "backups",
        RecordingSecureDeletionProvider(),
    )
    with pytest.raises(
        TypeError,
        match="security_context",
    ):
        BackupManager(
            real_storage,
            SelectiveRetentionEvaluator(),
            BoundedRetryPolicy(max_attempts=1),
            RecordingFailureLogger(),
            RecordingRecoveryManagerNotifier(),
            object(),
        )


def test_denied_create_does_not_reach_storage(
    tmp_path: Path,
):
    logger = RecordingFailureLogger()
    notifier = RecordingRecoveryManagerNotifier()
    security = BackupSecurityContext(
        DenyingAccessController(),
        RecordingEncryptionProvider(),
        RecordingSecureDeletionProvider(),
    )
    manager = BackupManager(
        ExplodingStorage(),
        SelectiveRetentionEvaluator(),
        BoundedRetryPolicy(max_attempts=1),
        logger,
        notifier,
        security,
    )
    source = tmp_path / "denied.txt"
    source.write_text(
        "secret",
        encoding="utf-8",
    )

    with pytest.raises(BackupAccessDeniedError):
        manager.create_backup(
            build_file_metadata(source),
            build_policy(),
        )

    # Denial is a security event, not a failed attempt:
    # nothing is logged, notified, or stored.
    assert manager.backup_count == 0
    assert logger.events == []
    assert notifier.events == []


def test_denied_restore_does_not_reach_storage(
    tmp_path: Path,
):
    controller = SwitchableAccessController()
    secure_deleter = RecordingSecureDeletionProvider()
    real_storage = FilesystemBackupStorage(
        tmp_path / "backups",
        secure_deleter,
    )
    manager = BackupManager(
        ExplodingRestoreStorage(real_storage),
        SelectiveRetentionEvaluator(),
        BoundedRetryPolicy(max_attempts=1),
        RecordingFailureLogger(),
        RecordingRecoveryManagerNotifier(),
        BackupSecurityContext(
            controller,
            RecordingEncryptionProvider(),
            secure_deleter,
        ),
    )
    source = build_source(tmp_path)
    reference = manager.create_backup(
        build_file_metadata(source),
        build_policy(),
    )

    controller.allow = False

    with pytest.raises(BackupAccessDeniedError):
        manager.restore_backup(
            reference,
            build_file_metadata(source),
        )


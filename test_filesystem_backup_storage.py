from pathlib import Path

import pytest
import shutil

from backup_security import SecureDeletionProvider
from backup_storage_port import BackupStoragePort
from filesystem_backup_storage import (
    FilesystemBackupStorage,
)
from recovery_models import BackupReference


class RecordingSecureDeletionProvider:
    def __init__(self):
        self.calls = []

    def secure_delete(self, file_path):
        self.calls.append(file_path)
        file_path.unlink()


def build_source(
    tmp_path: Path,
    content: str = "PRISM real backup test",
) -> Path:
    source = tmp_path / "source.txt"
    source.write_text(content, encoding="utf-8")
    return source


def build_storage(
    tmp_path: Path,
) -> FilesystemBackupStorage:
    return FilesystemBackupStorage(
        tmp_path / "backups",
        RecordingSecureDeletionProvider(),
    )


def test_store_creates_real_backup_copy(
    tmp_path: Path,
):
    source = tmp_path / "source.txt"
    storage_root = tmp_path / "backups"
    content = "PRISM real backup test"
    source.write_text(
        content,
        encoding="utf-8",
    )
    storage = build_storage(tmp_path)
    reference = storage.store(
        source,
        "backup-001",
    )
    assert isinstance(
        reference,
        BackupReference,
    )


def test_stored_backup_matches_source_content(
    tmp_path: Path,
):
    source = build_source(tmp_path)
    storage_root = tmp_path / "backups"
    storage = FilesystemBackupStorage(
        storage_root,
        RecordingSecureDeletionProvider(),
    )
    reference = storage.store(
        source,
        "backup-002",
    )
    backup_file = Path(reference.backup_path)
    assert backup_file.is_file()
    assert backup_file.read_text(
        encoding="utf-8"
    ) == source.read_text(encoding="utf-8")


def test_stored_backup_lives_beneath_storage_root(
    tmp_path: Path,
):
    source = build_source(tmp_path)
    storage_root = tmp_path / "backups"
    storage = FilesystemBackupStorage(
        storage_root,
        RecordingSecureDeletionProvider(),
    )
    reference = storage.store(
        source,
        "backup-003",
    )
    backup_file = Path(reference.backup_path)
    assert storage_root in backup_file.parents
    assert reference.backup_id == "backup-003"


def test_stored_backup_is_independent_of_source(
    tmp_path: Path,
):
    source = build_source(
        tmp_path,
        content="original",
    )
    storage_root = tmp_path / "backups"
    storage = FilesystemBackupStorage(
        storage_root,
        RecordingSecureDeletionProvider(),
    )
    reference = storage.store(
        source,
        "backup-004",
    )
    source.write_text(
        "modified",
        encoding="utf-8",
    )
    assert Path(reference.backup_path).read_text(
        encoding="utf-8"
    ) == "original"


def test_store_rejects_missing_source_file(
    tmp_path: Path,
):
    storage = FilesystemBackupStorage(
        tmp_path / "backups",
        RecordingSecureDeletionProvider(),
    )
    with pytest.raises(FileNotFoundError):
        storage.store(
            tmp_path / "missing.txt",
            "backup-005",
        )


def test_store_rejects_invalid_source_type(
    tmp_path: Path,
):
    storage = FilesystemBackupStorage(
        tmp_path / "backups",
        RecordingSecureDeletionProvider(),
    )
    with pytest.raises(TypeError):
        storage.store(
            "source.txt",
            "backup-006",
        )


def test_store_rejects_invalid_backup_id(
    tmp_path: Path,
):
    source = build_source(tmp_path)
    storage = FilesystemBackupStorage(
        tmp_path / "backups",
        RecordingSecureDeletionProvider(),
    )
    with pytest.raises(ValueError):
        storage.store(source, "   ")


def test_store_rejects_backup_id_with_separator(
    tmp_path: Path,
):
    source = build_source(tmp_path)
    storage = FilesystemBackupStorage(
        tmp_path / "backups",
        RecordingSecureDeletionProvider(),
    )
    with pytest.raises(ValueError):
        storage.store(source, "../escape")


def test_store_rejects_duplicate_backup_id(
    tmp_path: Path,
):
    source = build_source(tmp_path)
    storage = FilesystemBackupStorage(
        tmp_path / "backups",
        RecordingSecureDeletionProvider(),
    )
    storage.store(source, "backup-007")
    with pytest.raises(FileExistsError):
        storage.store(source, "backup-007")


def test_store_leaves_no_temporary_files(
    tmp_path: Path,
):
    source = build_source(tmp_path)
    storage_root = tmp_path / "backups"
    storage = FilesystemBackupStorage(
        storage_root,
        RecordingSecureDeletionProvider(),
    )
    storage.store(
        source,
        "backup-008",
    )
    leftovers = list(storage_root.iterdir())
    assert len(leftovers) == 1
    assert leftovers[0].name == "backup-008.txt"


def test_failed_copy_leaves_no_partial_backup(
    tmp_path: Path,
    monkeypatch,
):
    source = build_source(tmp_path)
    storage_root = tmp_path / "backups"
    storage = FilesystemBackupStorage(
        storage_root,
        RecordingSecureDeletionProvider(),
    )

    def failing_copy(*args, **kwargs):
        raise OSError("simulated copy failure")

    monkeypatch.setattr(shutil, "copy2", failing_copy)

    with pytest.raises(
        OSError,
        match="simulated copy failure",
    ):
        storage.store(
            source,
            "backup-009",
        )

    assert not (
        storage_root / "backup-009.txt"
    ).exists()
    assert list(storage_root.iterdir()) == []


def test_storage_root_is_created_on_init(
    tmp_path: Path,
):
    storage_root = tmp_path / "nested" / "backups"
    FilesystemBackupStorage(
        storage_root,
        RecordingSecureDeletionProvider(),
    )
    assert storage_root.is_dir()


def test_constructor_rejects_non_path_root(
    tmp_path: Path,
):
    with pytest.raises(TypeError):
        FilesystemBackupStorage(
            str(tmp_path),
            RecordingSecureDeletionProvider(),
        )


def test_storage_satisfies_backup_storage_port(
    tmp_path: Path,
):
    storage = FilesystemBackupStorage(
        tmp_path / "backups",
        RecordingSecureDeletionProvider(),
    )
    assert isinstance(storage, BackupStoragePort)


def test_restore_replaces_target_with_backup_contents(
    tmp_path: Path,
):
    source = tmp_path / "source.txt"
    target = tmp_path / "target.txt"
    source.write_text(
        "original important data",
        encoding="utf-8",
    )
    target.write_text(
        "modified malicious data",
        encoding="utf-8",
    )
    storage = FilesystemBackupStorage(
        tmp_path / "backups",
        RecordingSecureDeletionProvider(),
    )
    reference = storage.store(
        source,
        "backup-restore-001",
    )
    storage.restore(
        reference,
        target,
    )
    assert target.read_text(
        encoding="utf-8"
    ) == "original important data"


def test_restore_creates_missing_target(
    tmp_path: Path,
):
    source = tmp_path / "source.txt"
    target = tmp_path / "restored.txt"
    source.write_text(
        "recoverable content",
        encoding="utf-8",
    )
    storage = FilesystemBackupStorage(
        tmp_path / "backups",
        RecordingSecureDeletionProvider(),
    )
    reference = storage.store(
        source,
        "backup-restore-002",
    )
    assert not target.exists()
    storage.restore(
        reference,
        target,
    )
    assert target.exists()
    assert target.read_text(
        encoding="utf-8"
    ) == "recoverable content"


def test_restore_rejects_missing_backup(
    tmp_path: Path,
):
    storage = FilesystemBackupStorage(
        tmp_path / "backups",
        RecordingSecureDeletionProvider(),
    )
    reference = BackupReference(
        backup_id="missing",
        backup_path=str(
            tmp_path
            / "backups"
            / "missing.backup"
        ),
    )
    target = tmp_path / "target.txt"
    with pytest.raises(FileNotFoundError):
        storage.restore(
            reference,
            target,
        )
    assert not target.exists()


def test_restore_rejects_same_backup_and_target(
    tmp_path: Path,
):
    source = tmp_path / "source.txt"
    source.write_text(
        "data",
        encoding="utf-8",
    )
    storage = FilesystemBackupStorage(
        tmp_path / "backups",
        RecordingSecureDeletionProvider(),
    )
    reference = storage.store(
        source,
        "backup-same-path",
    )
    backup_path = Path(reference.backup_path)
    with pytest.raises(
        ValueError,
        match="must differ",
    ):
        storage.restore(
            reference,
            backup_path,
        )


def test_restore_rejects_invalid_reference_type(
    tmp_path: Path,
):
    storage = FilesystemBackupStorage(
        tmp_path / "backups",
        RecordingSecureDeletionProvider(),
    )
    with pytest.raises(TypeError):
        storage.restore(
            "backup-001",
            tmp_path / "target.txt",
        )


def test_restore_rejects_invalid_destination_type(
    tmp_path: Path,
):
    source = build_source(tmp_path)
    storage = FilesystemBackupStorage(
        tmp_path / "backups",
        RecordingSecureDeletionProvider(),
    )
    reference = storage.store(
        source,
        "backup-restore-003",
    )
    with pytest.raises(TypeError):
        storage.restore(
            reference,
            str(tmp_path / "target.txt"),
        )


def test_failed_restore_leaves_target_unchanged(
    tmp_path: Path,
    monkeypatch,
):
    source = tmp_path / "source.txt"
    target = tmp_path / "target.txt"
    source.write_text(
        "backup content",
        encoding="utf-8",
    )
    target.write_text(
        "existing target content",
        encoding="utf-8",
    )
    storage = FilesystemBackupStorage(
        tmp_path / "backups",
        RecordingSecureDeletionProvider(),
    )
    reference = storage.store(
        source,
        "backup-restore-004",
    )

    def failing_copy(*args, **kwargs):
        raise OSError("simulated copy failure")

    monkeypatch.setattr(shutil, "copy2", failing_copy)

    with pytest.raises(
        OSError,
        match="simulated copy failure",
    ):
        storage.restore(
            reference,
            target,
        )

    assert target.read_text(
        encoding="utf-8"
    ) == "existing target content"
    assert list(tmp_path.glob(".*.tmp")) == []


def test_restore_leaves_no_temporary_files(
    tmp_path: Path,
):
    source = build_source(tmp_path)
    target = tmp_path / "restored.txt"
    storage = FilesystemBackupStorage(
        tmp_path / "backups",
        RecordingSecureDeletionProvider(),
    )
    reference = storage.store(
        source,
        "backup-restore-005",
    )
    storage.restore(
        reference,
        target,
    )
    leftovers = [
        path
        for path in tmp_path.iterdir()
        if path.name.endswith(".tmp")
    ]
    assert leftovers == []


def test_delete_removes_backup_file(tmp_path: Path):
    source = tmp_path / "source.txt"
    source.write_text("delete me", encoding="utf-8")
    storage = FilesystemBackupStorage(
        tmp_path / "backups",
        RecordingSecureDeletionProvider(),
    )
    reference = storage.store(
        source,
        "delete-test",
    )
    backup_path = Path(reference.backup_path)

    storage.delete(reference)

    assert not backup_path.exists()


def test_delete_rejects_missing_backup(tmp_path: Path):
    storage = FilesystemBackupStorage(
        tmp_path / "backups",
        RecordingSecureDeletionProvider(),
    )
    reference = BackupReference(
        backup_id="missing",
        backup_path=str(
            tmp_path / "backups" / "missing.backup"
        ),
    )
    with pytest.raises(FileNotFoundError):
        storage.delete(reference)


def test_delete_rejects_invalid_reference(
    tmp_path: Path,
):
    storage = FilesystemBackupStorage(
        tmp_path / "backups",
        RecordingSecureDeletionProvider(),
    )
    with pytest.raises(
        TypeError, match="BackupReference"
    ):
        storage.delete(None)

def test_storage_delegates_delete_to_secure_deletion_provider(
    tmp_path: Path,
):
    source = tmp_path / "source.txt"
    source.write_text(
        "delete me",
        encoding="utf-8",
    )

    secure_deleter = RecordingSecureDeletionProvider()

    storage = FilesystemBackupStorage(
        tmp_path / "backups",
        secure_deleter,
    )

    reference = storage.store(
        source,
        "secure-delete-test",
    )

    storage.delete(reference)

    assert secure_deleter.calls == [
        Path(reference.backup_path).resolve()
    ]


def test_delete_fails_when_provider_leaves_backup(
    tmp_path: Path,
):
    class NonDeletingProvider:
        """Test-only provider that records the request
        but does not actually remove the file."""

        def secure_delete(self, file_path):
            return None

    source = tmp_path / "source.txt"
    source.write_text(
        "still here",
        encoding="utf-8",
    )
    storage = FilesystemBackupStorage(
        tmp_path / "backups",
        NonDeletingProvider(),
    )
    reference = storage.store(
        source,
        "provider-noop-test",
    )

    with pytest.raises(
        IOError,
        match="still exists",
    ):
        storage.delete(reference)


def test_size_mismatch_removes_backup_through_secure_deletion(
    tmp_path: Path,
    monkeypatch,
):
    source = tmp_path / "source.txt"
    source.write_text(
        "full source content",
        encoding="utf-8",
    )
    storage_root = tmp_path / "backups"
    secure_deleter = RecordingSecureDeletionProvider()
    storage = FilesystemBackupStorage(
        storage_root,
        secure_deleter,
    )

    def truncated_copy(src, dst):
        Path(dst).write_text(
            "short",
            encoding="utf-8",
        )

    monkeypatch.setattr(
        shutil,
        "copy2",
        truncated_copy,
    )

    with pytest.raises(
        OSError,
        match="size does not match",
    ):
        storage.store(source, "bad-size-test")

    expected = storage_root / "bad-size-test.txt"
    assert not expected.exists()
    assert secure_deleter.calls == [expected]
    assert list(storage_root.iterdir()) == []

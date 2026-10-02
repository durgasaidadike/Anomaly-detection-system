import pytest

from backup_models import (
    BackupMetadata,
    BackupRecord,
)
from recovery_models import (
    BackupReference,
    FileMetadata,
)


def build_reference() -> BackupReference:
    return BackupReference(
        backup_id="backup-001",
        backup_path=r"C:\backups\sample.txt.bak",
    )


def build_metadata() -> BackupMetadata:
    return BackupMetadata(
        values={
            "source": r"C:\watched\sample.txt",
        }
    )


def build_file_metadata() -> FileMetadata:
    return FileMetadata(
        file_name="sample.txt",
        file_extension=".txt",
        file_path=r"C:\watched\sample.txt",
        directory=r"C:\watched",
        file_size=100,
    )


def test_backup_metadata_accepts_mapping():
    metadata = BackupMetadata(
        values={
            "source": r"C:\watched\sample.txt",
        }
    )
    assert metadata.values["source"] == (
        r"C:\watched\sample.txt"
    )


def test_backup_metadata_is_immutable():
    metadata = BackupMetadata(
        values={
            "source": r"C:\watched\sample.txt",
        }
    )
    with pytest.raises(TypeError):
        metadata.values["source"] = "changed"


def test_backup_metadata_rejects_non_mapping():
    with pytest.raises(TypeError):
        BackupMetadata(values="not-a-mapping")


def test_backup_metadata_rejects_empty_key():
    with pytest.raises(ValueError):
        BackupMetadata(values={"   ": "value"})


def test_backup_record_accepts_valid_contract():
    record = BackupRecord(
        reference=build_reference(),
        metadata=build_metadata(),
        status="PENDING",
        file_metadata=build_file_metadata(),
    )
    assert record.reference.backup_id == "backup-001"
    assert record.status == "PENDING"


def test_backup_record_is_immutable():
    record = BackupRecord(
        reference=build_reference(),
        metadata=build_metadata(),
        status="PENDING",
        file_metadata=build_file_metadata(),
    )
    with pytest.raises(AttributeError):
        record.status = "CHANGED"


def test_backup_record_rejects_invalid_reference():
    with pytest.raises(TypeError):
        BackupRecord(
            reference="backup-001",
            metadata=build_metadata(),
            status="PENDING",
            file_metadata=build_file_metadata(),
        )


def test_backup_record_rejects_invalid_metadata():
    with pytest.raises(TypeError):
        BackupRecord(
            reference=build_reference(),
            metadata={"source": "x"},
            status="PENDING",
            file_metadata=build_file_metadata(),
        )


def test_backup_record_rejects_empty_status():
    with pytest.raises(ValueError):
        BackupRecord(
            reference=build_reference(),
            metadata=build_metadata(),
            status="   ",
            file_metadata=build_file_metadata(),
        )


def test_backup_record_rejects_invalid_file_metadata():
    with pytest.raises(TypeError):
        BackupRecord(
            reference=build_reference(),
            metadata=build_metadata(),
            status="PENDING",
            file_metadata="not-a-file-metadata",
        )

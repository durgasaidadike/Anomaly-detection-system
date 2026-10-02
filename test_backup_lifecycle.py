from backup_lifecycle import (
    BackupRetentionEvaluator,
)
from backup_models import (
    BackupMetadata,
    BackupRecord,
)
from recovery_models import (
    BackupReference,
    FileMetadata,
)


def build_record(
    backup_id: str = "backup-001",
) -> BackupRecord:
    return BackupRecord(
        reference=BackupReference(
            backup_id=backup_id,
            backup_path=f"/backups/{backup_id}.backup",
        ),
        metadata=BackupMetadata(values={}),
        status="CREATED",
        file_metadata=FileMetadata(
            file_name="sample.txt",
            file_extension=".txt",
            file_path="/data/sample.txt",
            directory="/data",
            file_size=100,
        ),
    )


class FixedRetentionEvaluator:
    def __init__(self, expired_ids: set[str]) -> None:
        self._expired_ids = expired_ids

    def is_expired(self, record: BackupRecord) -> bool:
        return (
            record.reference.backup_id
            in self._expired_ids
        )


def test_evaluator_implementations_satisfy_protocol():
    evaluator = FixedRetentionEvaluator(
        {"backup-001"}
    )
    assert isinstance(
        evaluator, BackupRetentionEvaluator
    )


def test_object_without_is_expired_is_not_accepted():
    assert not isinstance(
        object(), BackupRetentionEvaluator
    )


def test_is_expired_only_reports_listed_ids():
    evaluator = FixedRetentionEvaluator(
        {"backup-001"}
    )
    expired = build_record("backup-001")
    kept = build_record("backup-002")
    assert evaluator.is_expired(expired) is True
    assert evaluator.is_expired(kept) is False
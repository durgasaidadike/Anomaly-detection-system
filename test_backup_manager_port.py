import pytest

from backup_manager_port import BackupManagerPort
from recovery_models import (
    BackupReference,
    FileMetadata,
    RecoveryAction,
    RecoveryPolicy,
)


def build_file_metadata() -> FileMetadata:
    return FileMetadata(
        file_name="report.docx",
        file_extension=".docx",
        file_path="/data/docs/report.docx",
        directory="/data/docs",
        file_size=15000,
    )


def build_policy(
    action: RecoveryAction = RecoveryAction.RESTORE_PREVIOUS_VERSION,
) -> RecoveryPolicy:
    return RecoveryPolicy(
        policy_id="policy-001",
        action=action,
    )


class FakeBackupManager:
    """Test-only implementation of BackupManagerPort."""

    def __init__(self) -> None:
        self.created = False
        self.restored = False
        self.verified = False

    def create_backup(
        self,
        file_metadata,
        recovery_policy,
    ):
        self.created = True
        return BackupReference(
            backup_id="backup-test-001",
            backup_path="/backups/report.docx.bak",
        )

    def restore_backup(
        self,
        backup_reference,
        file_metadata,
    ):
        self.restored = True
        return True

    def verify_backup(
        self,
        backup_reference,
    ):
        self.verified = True
        return True


def test_fake_backup_manager_satisfies_port():
    fake = FakeBackupManager()
    assert isinstance(fake, BackupManagerPort)


def test_create_backup_returns_backup_reference():
    fake = FakeBackupManager()
    reference = fake.create_backup(
        build_file_metadata(),
        build_policy(),
    )
    assert fake.created is True
    assert isinstance(reference, BackupReference)
    assert reference.backup_id == "backup-test-001"


def test_restore_backup_returns_bool():
    fake = FakeBackupManager()
    reference = BackupReference(
        backup_id="backup-test-001",
        backup_path="/backups/report.docx.bak",
    )
    outcome = fake.restore_backup(
        reference,
        build_file_metadata(),
    )
    assert outcome is True
    assert fake.restored is True


def test_verify_backup_returns_bool():
    fake = FakeBackupManager()
    reference = BackupReference(
        backup_id="backup-test-001",
        backup_path="/backups/report.docx.bak",
    )
    outcome = fake.verify_backup(reference)
    assert outcome is True
    assert fake.verified is True


def test_port_does_not_implement_storage():
    import backup_manager_port

    source_path = backup_manager_port.__file__
    with open(source_path, "r", encoding="utf-8") as handle:
        content = handle.read().lower()
    for token in (
        "shutil",
        "open(",
        "os.remove",
        "os.rename",
        "sqlite",
        "pymongo",
        "path.unlink",
    ):
        assert token not in content


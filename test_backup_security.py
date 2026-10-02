from pathlib import Path

import pytest

from backup_security import (
    BackupAccessController,
    BackupAccessDeniedError,
    BackupEncryptionProvider,
    BackupSecurityContext,
    BackupSecurityOperation,
    SecureDeletionProvider,
)
from recovery_models import (
    BackupReference,
    FileMetadata,
)


class AllowAllAccessController:
    def authorize(
        self,
        operation,
        file_metadata,
        backup_reference=None,
    ):
        return None


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


class RecordingEncryptionProvider:
    def __init__(self):
        self.encrypt_calls = []
        self.decrypt_calls = []

    def encrypt_backup(
        self,
        source_path,
        destination_path,
    ):
        self.encrypt_calls.append(
            (source_path, destination_path)
        )

    def decrypt_backup(
        self,
        encrypted_path,
        destination_path,
    ):
        self.decrypt_calls.append(
            (encrypted_path, destination_path)
        )


class RecordingSecureDeletionProvider:
    def __init__(self):
        self.calls = []

    def secure_delete(self, file_path):
        self.calls.append(file_path)
        file_path.unlink()


class DenyingAccessController:
    def authorize(
        self,
        operation,
        file_metadata,
        backup_reference=None,
    ):
        raise BackupAccessDeniedError(
            "operation denied"
        )


def test_access_denial_is_explicit(tmp_path: Path):
    source = tmp_path / "test.txt"
    source.write_text("test", encoding="utf-8")
    controller = DenyingAccessController()
    with pytest.raises(
        BackupAccessDeniedError,
        match="operation denied",
    ):
        controller.authorize(
            BackupSecurityOperation.CREATE,
            build_file_metadata(source),
        )


def test_security_context_validates_providers():
    access_controller = AllowAllAccessController()
    encryption_provider = (
        RecordingEncryptionProvider()
    )
    secure_deletion_provider = (
        RecordingSecureDeletionProvider()
    )

    context = BackupSecurityContext(
        access_controller,
        encryption_provider,
        secure_deletion_provider,
    )

    assert (
        context.access_controller is access_controller
    )
    assert (
        context.encryption_provider
        is encryption_provider
    )
    assert (
        context.secure_deletion_provider
        is secure_deletion_provider
    )


def test_security_context_rejects_invalid_access_controller():
    with pytest.raises(
        TypeError,
        match="access_controller must implement",
    ):
        BackupSecurityContext(
            object(),
            RecordingEncryptionProvider(),
            RecordingSecureDeletionProvider(),
        )


def test_security_context_rejects_invalid_encryption_provider():
    with pytest.raises(
        TypeError,
        match="encryption_provider must implement",
    ):
        BackupSecurityContext(
            AllowAllAccessController(),
            object(),
            RecordingSecureDeletionProvider(),
        )


def test_security_context_rejects_invalid_secure_deletion_provider():
    with pytest.raises(
        TypeError,
        match="secure_deletion_provider must implement",
    ):
        BackupSecurityContext(
            AllowAllAccessController(),
            RecordingEncryptionProvider(),
            object(),
        )

def test_security_protocols_are_runtime_checkable():
    assert isinstance(
        AllowAllAccessController(),
        BackupAccessController,
    )
    assert isinstance(
        RecordingEncryptionProvider(),
        BackupEncryptionProvider,
    )
    assert isinstance(
        RecordingSecureDeletionProvider(),
        SecureDeletionProvider,
    )


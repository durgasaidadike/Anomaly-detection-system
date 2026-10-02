from recovery_filesystem_port import RecoveryFilesystemPort
from recovery_models import FileMetadata


class FakeRecoveryFilesystem:
    def __init__(self):
        self.quarantined = []

    def quarantine_file(
        self,
        file_metadata: FileMetadata,
    ) -> None:
        self.quarantined.append(file_metadata)


def build_file_metadata() -> FileMetadata:
    return FileMetadata(
        file_name="sample.txt",
        file_extension=".txt",
        file_path=r"C:\watched\sample.txt",
        directory=r"C:\watched",
        file_size=100,
    )


def test_fake_filesystem_satisfies_protocol():
    filesystem = FakeRecoveryFilesystem()
    assert isinstance(
        filesystem,
        RecoveryFilesystemPort,
    )


def test_quarantine_file_receives_file_metadata():
    filesystem = FakeRecoveryFilesystem()
    metadata = build_file_metadata()
    result = filesystem.quarantine_file(metadata)
    assert result is None
    assert filesystem.quarantined == [metadata]

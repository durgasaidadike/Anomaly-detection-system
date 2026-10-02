from typing import Protocol, runtime_checkable

from recovery_models import FileMetadata


@runtime_checkable
class RecoveryFilesystemPort(Protocol):
    """Filesystem capability required by recovery workflows.

    This chunk requires quarantine only. This is a port,
    not a filesystem implementation.
    """

    def quarantine_file(
        self,
        file_metadata: FileMetadata,
    ) -> None:
        ...

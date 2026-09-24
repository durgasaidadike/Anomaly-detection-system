from __future__ import annotations

from typing import Optional, Protocol

from repository_snapshot import (
    RepositorySnapshot,
)


class RepositoryPersistence(Protocol):
    """
    Physical persistence boundary for repository recovery.

    Module 06 defines only this boundary. Physical serialization and any
    storage technology (MongoDB, files, or another store) are implemented
    behind it, outside the repository's logical responsibilities.
    """

    def save(
        self,
        snapshot: RepositorySnapshot,
    ) -> bool:
        ...

    def load(
        self,
    ) -> Optional[RepositorySnapshot]:
        ...

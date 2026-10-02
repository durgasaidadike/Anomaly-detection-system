from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from recovery_models import (
    BackupReference,
    FileMetadata,
)


@dataclass(frozen=True)
class BackupMetadata:
    """Immutable metadata associated with a backup.

    Module 14 defines Backup Metadata as part of the
    Backup Manager state/output contract, but does not
    prescribe a fixed field schema. Metadata is therefore
    represented as an immutable mapping until later
    backup-storage/integrity chunks define the exact
    metadata produced by the implementation.
    """

    values: Mapping[str, object]

    def __post_init__(self) -> None:
        if not isinstance(self.values, Mapping):
            raise TypeError(
                "values must be a mapping"
            )
        values = dict(self.values)
        for key in values:
            if (
                not isinstance(key, str)
                or not key.strip()
            ):
                raise ValueError(
                    "metadata keys must be non-empty strings"
                )
        object.__setattr__(
            self,
            "values",
            MappingProxyType(values),
        )


@dataclass(frozen=True)
class BackupRecord:
    """Immutable record pairing a backup reference with metadata.

    Status is intentionally a free-form non-empty string: the
    specification requires Backup Status without defining an
    official status vocabulary, so no status enum is introduced
    in this chunk.
    """

    reference: BackupReference
    metadata: BackupMetadata
    status: str
    file_metadata: FileMetadata

    def __post_init__(self) -> None:
        if not isinstance(
            self.reference,
            BackupReference,
        ):
            raise TypeError(
                "reference must be a BackupReference"
            )
        if not isinstance(
            self.metadata,
            BackupMetadata,
        ):
            raise TypeError(
                "metadata must be a BackupMetadata"
            )
        if (
            not isinstance(self.status, str)
            or not self.status.strip()
        ):
            raise ValueError(
                "status must be a non-empty string"
            )
        if not isinstance(
            self.file_metadata,
            FileMetadata,
        ):
            raise TypeError(
                "file_metadata must be FileMetadata"
            )

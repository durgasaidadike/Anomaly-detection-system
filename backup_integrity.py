from __future__ import annotations

from hashlib import sha256
from pathlib import Path

CHUNK_SIZE = 64 * 1024

INTEGRITY_ALGORITHM = "sha256"


def calculate_file_digest(
    file_path: Path,
) -> str:
    """
    Calculate the integrity digest of a file.

    The file is processed incrementally so large backups do not
    need to be loaded entirely into memory.
    """
    if not isinstance(file_path, Path):
        raise TypeError(
            "file_path must be Path"
        )
    if not file_path.exists():
        raise FileNotFoundError(
            f"file does not exist: {file_path}"
        )
    if not file_path.is_file():
        raise ValueError(
            f"path is not a regular file: {file_path}"
        )

    digest = sha256()
    with file_path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(CHUNK_SIZE),
            b"",
        ):
            digest.update(chunk)
    return digest.hexdigest()
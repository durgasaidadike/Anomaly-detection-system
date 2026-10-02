from hashlib import sha256
from pathlib import Path

import pytest

from backup_integrity import (
    CHUNK_SIZE,
    INTEGRITY_ALGORITHM,
    calculate_file_digest,
)


def test_calculate_file_digest_is_deterministic(
    tmp_path: Path,
):
    file_path = tmp_path / "sample.txt"
    file_path.write_text(
        "PRISM integrity",
        encoding="utf-8",
    )
    first = calculate_file_digest(file_path)
    second = calculate_file_digest(file_path)
    assert first == second


def test_different_contents_produce_different_digests(
    tmp_path: Path,
):
    first_file = tmp_path / "first.txt"
    second_file = tmp_path / "second.txt"
    first_file.write_text(
        "first content",
        encoding="utf-8",
    )
    second_file.write_text(
        "second content",
        encoding="utf-8",
    )
    assert calculate_file_digest(
        first_file
    ) != calculate_file_digest(second_file)


def test_digest_matches_hashlib_reference(
    tmp_path: Path,
):
    content = "PRISM digest reference"
    file_path = tmp_path / "reference.txt"
    file_path.write_text(content, encoding="utf-8")
    expected = sha256(
        content.encode("utf-8")
    ).hexdigest()
    assert calculate_file_digest(
        file_path
    ) == expected


def test_digest_is_stable_across_chunked_reads(
    tmp_path: Path,
):
    """A file larger than CHUNK_SIZE must digest
    identically to a whole-file hash, proving the
    streaming loop does not lose or duplicate bytes."""
    payload = bytes(range(256)) * (
        (CHUNK_SIZE // 256) + 4
    )
    file_path = tmp_path / "large.bin"
    file_path.write_bytes(payload)
    assert file_path.stat().st_size > CHUNK_SIZE
    assert calculate_file_digest(
        file_path
    ) == sha256(payload).hexdigest()


def test_digest_rejects_non_path_argument(
    tmp_path: Path,
):
    file_path = tmp_path / "sample.txt"
    file_path.write_text("data", encoding="utf-8")
    with pytest.raises(
        TypeError, match="file_path must be Path"
    ):
        calculate_file_digest(str(file_path))


def test_digest_rejects_missing_file(
    tmp_path: Path,
):
    with pytest.raises(
        FileNotFoundError,
        match="file does not exist",
    ):
        calculate_file_digest(
            tmp_path / "absent.txt"
        )


def test_digest_rejects_directory(
    tmp_path: Path,
):
    with pytest.raises(
        ValueError,
        match="not a regular file",
    ):
        calculate_file_digest(tmp_path)


def test_integrity_algorithm_is_a_label():
    """The algorithm is a stored metadata label, not an
    architectural rule; only that it is a non-empty
    string is guaranteed."""
    assert isinstance(INTEGRITY_ALGORITHM, str)
    assert INTEGRITY_ALGORITHM.strip()
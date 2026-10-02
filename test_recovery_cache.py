import pytest

from recovery_cache import RecoveryCache
from recovery_models import BackupReference


def build_reference(
    backup_id: str = "backup-001",
) -> BackupReference:
    return BackupReference(
        backup_id=backup_id,
        backup_path=r"C:\backups\backup-001.backup",
    )


def test_cache_starts_empty():
    cache = RecoveryCache()
    assert cache.size == 0


def test_put_and_get_reference():
    cache = RecoveryCache()
    reference = build_reference()
    cache.put(
        r"C:\data\sample.txt",
        reference,
    )
    assert (
        cache.get(
            r"C:\data\sample.txt"
        )
        == reference
    )


def test_get_returns_none_for_unknown_path():
    cache = RecoveryCache()
    assert (
        cache.get(r"C:\data\missing.txt") is None
    )
    assert cache.size == 0


def test_put_rejects_empty_file_path():
    cache = RecoveryCache()
    with pytest.raises(
        ValueError, match="file_path"
    ):
        cache.put(
            "",
            build_reference(),
        )


def test_put_rejects_invalid_reference():
    cache = RecoveryCache()
    with pytest.raises(
        TypeError, match="BackupReference"
    ):
        cache.put(
            r"C:\data\sample.txt",
            None,
        )


def test_put_replaces_existing_entry():
    cache = RecoveryCache()
    first = build_reference("backup-001")
    second = build_reference("backup-002")
    cache.put(
        r"C:\data\sample.txt",
        first,
    )
    cache.put(
        r"C:\data\sample.txt",
        second,
    )
    assert cache.size == 1
    assert (
        cache.get(r"C:\data\sample.txt") == second
    )


def test_remove_drops_entry_and_is_idempotent():
    cache = RecoveryCache()
    cache.put(
        r"C:\data\sample.txt",
        build_reference(),
    )

    cache.remove(r"C:\data\sample.txt")
    cache.remove(r"C:\data\sample.txt")

    assert (
        cache.get(r"C:\data\sample.txt") is None
    )
    assert cache.size == 0

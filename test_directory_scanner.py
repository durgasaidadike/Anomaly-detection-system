import os
import tempfile
from pathlib import Path

from directory_scanner import DirectoryScanner
from persistence_port import PersistencePort


class FakePersistence(PersistencePort):
    """Test-only implementation of PersistencePort."""

    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail
        self.saved_entries = []

    def save_event(self, event_data):
        pass

    def save_baseline_entry(self, entry_data):
        if self.should_fail:
            raise RuntimeError("Simulated database failure")
        self.saved_entries.append(entry_data)
        return "test-id"

    def save_directory_snapshot(self, snapshot_data):
        pass

    def save_validation_result(self, validation_data):
        pass

    def save_watcher_registration(self, registration_data):
        pass


def test_metadata_creation_failure_skips_file():
    """When metadata creation fails, scan error is logged and file is not counted."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a directory with one file
        test_file = Path(tmpdir) / "test.txt"
        test_file.write_text("content")

        scanner = DirectoryScanner([tmpdir], persistence=None)

        # Mock build_entry_metadata to raise OSError
        original_build = DirectoryScanner.build_entry_metadata
        def failing_build(self, *args, **kwargs):
            raise OSError("Permission denied")
        DirectoryScanner.build_entry_metadata = failing_build

        try:
            result = scanner.scan_directory(tmpdir)

            # File should not be counted
            assert result["total_files"] == 0
            assert len(result["entries"]) == 0

            # Filesystem scan error should be logged
            assert any("FILESYSTEM_SCAN_FAILED" in error for error in result["scan_errors"])
        finally:
            DirectoryScanner.build_entry_metadata = original_build


def test_persistence_failure_logs_error_and_keeps_file_in_snapshot():
    """When persistence fails, error is logged but file remains in snapshot."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test.txt"
        test_file.write_text("content")

        persistence = FakePersistence(should_fail=True)
        scanner = DirectoryScanner([tmpdir], persistence=persistence)

        result = scanner.scan_directory(tmpdir)

        # File should be counted and in snapshot
        assert result["total_files"] == 1
        assert len(result["entries"]) == 1

        # Persistence error should be logged
        assert any("BASELINE_PERSISTENCE_FAILED" in error for error in result["scan_errors"])


def test_first_file_persistence_failure_allows_second_file_processing():
    """When first file persistence fails, second file is still processed."""
    with tempfile.TemporaryDirectory() as tmpdir:
        file1 = Path(tmpdir) / "file1.txt"
        file2 = Path(tmpdir) / "file2.txt"
        file1.write_text("content1")
        file2.write_text("content2")

        # Persistence fails on all calls
        persistence = FakePersistence(should_fail=True)
        scanner = DirectoryScanner([tmpdir], persistence=persistence)

        result = scanner.scan_directory(tmpdir)

        # Both files should be counted
        assert result["total_files"] == 2
        assert len(result["entries"]) == 2

        # Both should have persistence errors
        persistence_errors = [e for e in result["scan_errors"] if "BASELINE_PERSISTENCE_FAILED" in e]
        assert len(persistence_errors) == 2


def test_persistence_absent_continues_scanning():
    """When persistence is absent, scanning continues without claiming successful persistence."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test.txt"
        test_file.write_text("content")

        scanner = DirectoryScanner([tmpdir], persistence=None)

        result = scanner.scan_directory(tmpdir)

        # File should be counted
        assert result["total_files"] == 1
        assert len(result["entries"]) == 1

        # No persistence errors
        persistence_errors = [e for e in result["scan_errors"] if "BASELINE_PERSISTENCE_FAILED" in e]
        assert len(persistence_errors) == 0


def test_persistence_succeeds_saves_baseline():
    """When persistence succeeds, baseline is saved and success is logged."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test.txt"
        test_file.write_text("content")

        persistence = FakePersistence(should_fail=False)
        scanner = DirectoryScanner([tmpdir], persistence=persistence)

        result = scanner.scan_directory(tmpdir)

        # File should be counted
        assert result["total_files"] == 1
        assert len(result["entries"]) == 1

        # Baseline should be saved
        assert len(persistence.saved_entries) == 1

        # No persistence errors
        persistence_errors = [e for e in result["scan_errors"] if "BASELINE_PERSISTENCE_FAILED" in e]
        assert len(persistence_errors) == 0

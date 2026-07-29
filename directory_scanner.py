import logging
import os
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple, TypedDict

from database import save_baseline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

logger = logging.getLogger(__name__)


class EntryMetadata(TypedDict):
    entry_name: str
    absolute_path: str
    relative_path: str
    parent_directory: str
    entry_type: str
    extension: str
    size: int
    created_time: str
    modified_time: str
    accessed_time: str
    is_symlink: bool
    baseline: bool
    sha256: Optional[str]


class DirectoryScanner:
    """
    PRISM Module 002.xx
    Directory Scanner

    Responsible for:
    - Directory validation
    - Recursive filesystem discovery
    - Metadata collection
    - Initial snapshot generation

    This module performs initialization only.
    It does not monitor live filesystem changes.
    """

    def __init__(self, directories: Optional[List[str]] = None):
        self.directories = directories or []
        self.snapshot = []
        self.valid_directories = set()
        self.invalid_directories = set()
        self.total_files = 0
        self.total_directories = 0

    @staticmethod
    def calculate_hash(file_path: str) -> Optional[str]:
        sha256 = hashlib.sha256()

        try:
            with open(file_path, "rb") as file:
                while chunk := file.read(4096):
                    sha256.update(chunk)

            return sha256.hexdigest()

        except (OSError, PermissionError):
            return None

    def validate_directory(
        self,
        directory_path: str
    ) -> Tuple[bool, str, str]:
        """
        Validate a directory before scanning.

        Returns:
            (is_valid, status, normalized_path)
        """
        normalized = os.path.abspath(directory_path)

        if normalized in self.valid_directories:
            return False, "DUPLICATE_DIRECTORY", normalized

        if not os.path.exists(normalized):
            return False, "DIRECTORY_NOT_FOUND", normalized

        if not os.path.isdir(normalized):
            return False, "NOT_A_DIRECTORY", normalized

        if not os.access(normalized, os.R_OK):
            return False, "PERMISSION_DENIED", normalized

        self.valid_directories.add(normalized)

        return True, "VALID", normalized

    def build_entry_metadata(
        self,
        root_path: str,
        full_path: str,
        is_directory: bool
    ) -> EntryMetadata:
        """
        Build metadata for a filesystem entry.
        """
        stats = os.stat(full_path, follow_symlinks=False)
        path_obj = Path(full_path)

        return {
            "entry_name": path_obj.name,
            "absolute_path": str(path_obj.resolve(strict=False)),
            "relative_path": os.path.relpath(full_path, root_path),
            "parent_directory": str(path_obj.parent),
            "entry_type": "DIRECTORY" if is_directory else "FILE",
            "extension": "" if is_directory else path_obj.suffix.lower(),
            "size": 0 if is_directory else stats.st_size,
            "created_time": datetime.fromtimestamp(
                stats.st_ctime,
                tz=timezone.utc
            ).isoformat(),
            "modified_time": datetime.fromtimestamp(
                stats.st_mtime,
                tz=timezone.utc
            ).isoformat(),
            "accessed_time": datetime.fromtimestamp(
                stats.st_atime,
                tz=timezone.utc
            ).isoformat(),
            "is_symlink": os.path.islink(full_path),
            "baseline": True,
            "sha256": (
                None
                if is_directory
                else self.calculate_hash(full_path)
            )
        }

    def scan_directory(
        self,
        directory_path: str
    ) -> Dict:
        """
        Recursively scan a directory and build its snapshot.
        """
        is_valid, status, normalized_path = self.validate_directory(directory_path)

        snapshot = {
            "root_directory": normalized_path,
            "validation_status": status,
            "scan_timestamp": datetime.now(timezone.utc).isoformat(),
            "entries": [],
            "total_files": 0,
            "total_directories": 0,
            "scan_errors": [],
            "validation_results": {},
            "watcher_registration": {
                "directory": normalized_path,
                "registered": False,
                "registration_time": None
            },
            "initialization_complete": False
        }

        if not is_valid:
            self.invalid_directories.add(normalized_path)
            return snapshot

        for root, dirs, files in os.walk(normalized_path):
            for directory_name in dirs:
                full_path = os.path.join(root, directory_name)

                try:
                    metadata = self.build_entry_metadata(
                        normalized_path,
                        full_path,
                        True
                    )
                    snapshot["entries"].append(metadata)
                    snapshot["total_directories"] += 1
                    self.total_directories += 1

                except Exception as e:
                    logger.error(f"Failed to scan directory '{directory_name}': {e}")

            for file_name in files:
                full_path = os.path.join(root, file_name)

                try:
                    metadata = self.build_entry_metadata(
                        normalized_path,
                        full_path,
                        False
                    )
                    snapshot["entries"].append(metadata)
                    snapshot["total_files"] += 1
                    self.total_files += 1
                    save_baseline(metadata)
                    logger.info(f"Baseline created for file: {file_name}")

                except Exception as e:
                    logger.error(f"Failed to scan file '{file_name}': {e}")

        self.snapshot.append(snapshot)
        return snapshot

    def scan(self) -> List[Dict]:
        """
        Scan every configured directory.
        """
        results = []

        for directory in self.directories:
            result = self.scan_directory(directory)
            results.append(result)

        return results

    def get_statistics(self) -> Dict:
        """
        Return overall scan statistics.
        """
        return {
            "directories_scanned": len(self.valid_directories),
            "invalid_directories": len(self.invalid_directories),
            "total_files": self.total_files,
            "total_directories": self.total_directories,
            "total_snapshots": len(self.snapshot)
        }


if __name__ == "__main__":
    WATCHED_FOLDERS = [
        r"C:\projects\watched-folder"
    ]

    scanner = DirectoryScanner(WATCHED_FOLDERS)
    scanner.scan()

    stats = scanner.get_statistics()

    print("\n========== PRISM DIRECTORY SCANNER ==========\n")
    print(f"Directories Scanned : {stats['directories_scanned']}")
    print(f"Invalid Directories : {stats['invalid_directories']}")
    print(f"Total Directories   : {stats['total_directories']}")
    print(f"Total Files         : {stats['total_files']}")
    print(f"Snapshots Created   : {stats['total_snapshots']}")
    print("\n=============================================\n")
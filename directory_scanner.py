import os
import hashlib
from datetime import datetime

from database import save_baseline

WATCHED_FOLDER = r"C:\projects\watched-folder"


def calculate_hash(file_path):

    sha256 = hashlib.sha256()

    try:
        with open(file_path, "rb") as file:

            while chunk := file.read(4096):
                sha256.update(chunk)

        return sha256.hexdigest()

    except Exception as e:
        print(f"Hash Error: {e}")
        return None


def scan_directory(folder_path):

    total_files = 0

    for root, dirs, files in os.walk(folder_path):

        for file in files:

            try:

                full_path = os.path.join(root, file)

                stats = os.stat(full_path)

                file_metadata = {

                    "file_name": file,

                    "file_path": full_path,

                    "file_size": stats.st_size,

                    "created_time":
                    datetime.fromtimestamp(
                        stats.st_ctime
                    ).isoformat(),

                    "modified_time":
                    datetime.fromtimestamp(
                        stats.st_mtime
                    ).isoformat(),

                    "sha256":
                    calculate_hash(full_path),

                    "baseline": True

                }

                save_baseline(file_metadata)

                total_files += 1

                print(f"[BASELINE] {file}")

            except Exception as e:

                print(
                    f"Error scanning {file}: {str(e)}"
                )

    print("\n================================")
    print(f"Baseline Created: {total_files}")
    print("================================")


if __name__ == "__main__":

    if not os.path.exists(WATCHED_FOLDER):

        print("Watched folder not found.")
        exit()

    scan_directory(WATCHED_FOLDER)
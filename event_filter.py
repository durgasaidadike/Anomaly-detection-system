import os
from datetime import datetime


IGNORED_EXTENSIONS = {
    ".tmp"
}


IGNORED_FILES = {
    "desktop.ini",
    "thumbs.db"
}


def should_ignore(file_path):

    file_name = os.path.basename(file_path)

    if file_name.lower() in IGNORED_FILES:
        return True

    if file_name.startswith("~"):
        return True

    extension = os.path.splitext(file_name)[1].lower()

    if extension in IGNORED_EXTENSIONS:
        return True

    return False


def build_event(event_type, file_path):

    file_name = os.path.basename(file_path)

    file_extension = os.path.splitext(file_name)[1]

    event = {

        "event_type": event_type,

        "file_name": file_name,

        "file_extension": file_extension,

        "file_path": file_path,

        "event_timestamp": datetime.utcnow().isoformat(),

        "valid_event": True

    }

    return event
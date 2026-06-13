import uuid
import os
from datetime import datetime, timezone


def create_log_record(event):
    file_path = event["file_path"]
    processed_time = datetime.now(timezone.utc)

    try:
        if os.path.exists(file_path) and os.path.isfile(file_path):
            file_size = os.path.getsize(file_path)
        else:
            file_size = 0
    except OSError:
        file_size = 0

    directory = os.path.dirname(file_path)

    record = {
        "record_id": str(uuid.uuid4()),
        "source_module": "WATCHER",
        "event_type": event["event_type"],
        "file_name": event["file_name"],
        "file_extension": event["file_extension"].lower(),
        "file_path": file_path,
        "directory": directory,
        "file_size": file_size,
        "event_timestamp": event["event_timestamp"],
        "processed_timestamp": processed_time.isoformat(),
        "event_hour": processed_time.hour,
        "is_unusual_time": processed_time.hour < 6 or processed_time.hour > 22,
        "record_status": "READY_FOR_PATTERN_ANALYSIS"
    }

    return record
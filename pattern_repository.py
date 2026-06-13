from collections import deque

# =====================================
# Repository Limits
# =====================================

EVENT_SEQUENCE_MAX = 100
GLOBAL_HISTORY_MAX = 1000
OPERATION_HISTORY_MAX = 500


# =====================================
# Event Sequence Storage
# =====================================

event_sequence = deque(maxlen=EVENT_SEQUENCE_MAX)


# =====================================
# Operation Statistics
# =====================================

operation_stats = {
    "CREATED": 0,
    "MODIFIED": 0,
    "DELETED": 0,
    "MOVED": 0,
    "COPIED": 0
}


# =====================================
# Behavioral Histories
# =====================================

create_history = deque(maxlen=OPERATION_HISTORY_MAX)
modify_history = deque(maxlen=OPERATION_HISTORY_MAX)
delete_history = deque(maxlen=OPERATION_HISTORY_MAX)
move_history = deque(maxlen=OPERATION_HISTORY_MAX)
copy_history = deque(maxlen=OPERATION_HISTORY_MAX)

extension_history = deque(maxlen=GLOBAL_HISTORY_MAX)
directory_history = deque(maxlen=GLOBAL_HISTORY_MAX)
access_hour_history = deque(maxlen=GLOBAL_HISTORY_MAX)
file_size_history = deque(maxlen=GLOBAL_HISTORY_MAX)


# =====================================
# Store Pattern
# =====================================

def store_pattern(log_record):
    event_type = log_record.get("event_type", "UNKNOWN")
    extension = log_record.get("file_extension", "").lower()
    directory = log_record.get("directory", "")
    hour = log_record.get("event_hour", 0)
    size = log_record.get("file_size", 0)

    # ---------------------------------
    # Event Sequence
    # ---------------------------------

    event_sequence.append(event_type)

    # ---------------------------------
    # Operation Stats
    # ---------------------------------

    if event_type in operation_stats:
        operation_stats[event_type] += 1

    # ---------------------------------
    # Global Histories
    # ---------------------------------

    extension_history.append(extension)
    directory_history.append(directory)
    access_hour_history.append(hour)
    file_size_history.append(size)

    # ---------------------------------
    # Contextual Record
    # ---------------------------------

    behavior_record = {
        "event_type": event_type,
        "extension": extension,
        "directory": directory,
        "hour": hour,
        "size": size
    }

    # ---------------------------------
    # Operation Specific Histories
    # ---------------------------------

    if event_type == "CREATED":
        create_history.append(behavior_record)

    elif event_type == "MODIFIED":
        modify_history.append(behavior_record)

    elif event_type == "DELETED":
        delete_history.append(behavior_record)

    elif event_type == "MOVED":
        move_history.append(behavior_record)

    elif event_type == "COPIED":
        copy_history.append(behavior_record)


# =====================================
# Get Repository Summary
# =====================================

def get_pattern_summary():
    return {
        "event_sequence": list(event_sequence),
        "operation_stats": dict(operation_stats),
        "create_history": list(create_history),
        "modify_history": list(modify_history),
        "delete_history": list(delete_history),
        "move_history": list(move_history),
        "copy_history": list(copy_history),
        "extension_history": list(extension_history),
        "directory_history": list(directory_history),
        "access_hour_history": list(access_hour_history),
        "file_size_history": list(file_size_history)
    }


# =====================================
# Reset Repository
# =====================================

def reset_patterns():
    event_sequence.clear()

    for key in operation_stats:
        operation_stats[key] = 0

    create_history.clear()
    modify_history.clear()
    delete_history.clear()
    move_history.clear()
    copy_history.clear()

    extension_history.clear()
    directory_history.clear()
    access_hour_history.clear()
    file_size_history.clear()
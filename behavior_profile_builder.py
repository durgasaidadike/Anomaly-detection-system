from collections import Counter
from pattern_store import load_patterns


def build_behavior_profile():
    data = load_patterns()

    extension_history = data.get("extension_history", [])
    directory_history = data.get("directory_history", [])
    access_hour_history = data.get("access_hour_history", [])
    file_size_history = data.get("file_size_history", [])

    create_history = data.get("create_history", [])
    modify_history = data.get("modify_history", [])
    delete_history = data.get("delete_history", [])
    move_history = data.get("move_history", [])
    copy_history = data.get("copy_history", [])

    operation_stats = data.get("operation_stats", {})

    extension_counter = Counter(extension_history)
    directory_counter = Counter(directory_history)
    hour_counter = Counter(access_hour_history)

    profile = {
        "common_extensions": extension_counter.most_common(5),
        "common_directories": directory_counter.most_common(5),
        "common_hours": hour_counter.most_common(5),

        "average_file_size": (
            sum(file_size_history) / len(file_size_history)
            if file_size_history else 0
        ),
        "min_file_size": (
            min(file_size_history)
            if file_size_history else 0
        ),
        "max_file_size": (
            max(file_size_history)
            if file_size_history else 0
        ),

        "total_operations": sum(operation_stats.values()),
        "operation_stats": operation_stats,

        "create_count": len(create_history),
        "modify_count": len(modify_history),
        "delete_count": len(delete_history),
        "move_count": len(move_history),
        "copy_count": len(copy_history)
    }

    return profile
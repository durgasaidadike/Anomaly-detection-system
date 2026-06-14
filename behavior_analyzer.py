from behavior_profile_builder import build_behavior_profile


def analyze_behavior(log_record, operation_frequency=0):
    profile = build_behavior_profile()

    risk_score = 0

    results = {
        "extension_anomaly": False,
        "directory_anomaly": False,
        "time_anomaly": False,
        "size_anomaly": False,
        "delete_burst_anomaly": False,
        "modify_burst_anomaly": False,
        "operation_frequency_anomaly": False
    }

    current_event_type = log_record.get("event_type", "")
    current_extension = log_record.get("file_extension", "").lower()
    current_directory = log_record.get("directory", "")
    current_hour = log_record.get("event_hour", 0)
    current_size = log_record.get("file_size", 0)

    # -------------------------
    # Extension Check
    # -------------------------

    common_extensions = [
        ext for ext, count
        in profile.get("common_extensions", [])
    ]

    if common_extensions and current_extension not in common_extensions:
        results["extension_anomaly"] = True
        risk_score += 25

    # -------------------------
    # Directory Check
    # -------------------------

    common_directories = [
        directory for directory, count
        in profile.get("common_directories", [])
    ]

    if common_directories and current_directory not in common_directories:
        results["directory_anomaly"] = True
        risk_score += 25

    # -------------------------
    # Time Check
    # -------------------------

    common_hours = [
        hour for hour, count
        in profile.get("common_hours", [])
    ]

    if common_hours and current_hour not in common_hours:
        results["time_anomaly"] = True
        risk_score += 25

    # -------------------------
    # Size Check
    # -------------------------

    max_size = profile.get("max_file_size", 0)

    if max_size > 0 and current_size > max_size:
        results["size_anomaly"] = True
        risk_score += 25

    # -------------------------
    # Delete Burst Check
    # -------------------------

    delete_count = profile.get("delete_count", 0)

    if current_event_type == "DELETED" and delete_count > 0:
        if operation_frequency > (delete_count * 2):
            results["delete_burst_anomaly"] = True
            risk_score += 20

    # -------------------------
    # Modify Burst Check
    # -------------------------

    modify_count = profile.get("modify_count", 0)

    if current_event_type == "MODIFIED" and modify_count > 0:
        if operation_frequency > (modify_count * 2):
            results["modify_burst_anomaly"] = True
            risk_score += 20

    # -------------------------
    # Operation Frequency Check
    # -------------------------

    total_operations = profile.get("total_operations", 0)

    if total_operations > 0:
        if operation_frequency > (total_operations * 2):
            results["operation_frequency_anomaly"] = True
            risk_score += 20

    results["risk_score"] = risk_score

    return results
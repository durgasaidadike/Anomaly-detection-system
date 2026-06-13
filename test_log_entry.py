from log_entry import create_log_record


sample_event = {
    "event_type": "MODIFIED",

    "file_name": "salary.xlsx",

    "file_extension": ".xlsx",

    "file_path":
        r"C:\projects\watched-folder\salary.xlsx",

    "event_timestamp":
        "2026-06-13T20:00:00",

    "valid_event": True
}


record = create_log_record(sample_event)

print("\n========== LOG RECORD ==========\n")

for key, value in record.items():
    print(f"{key}: {value}")
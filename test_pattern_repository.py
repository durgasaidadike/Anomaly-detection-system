from pattern_repository import (
    store_pattern,
    get_pattern_summary,
    reset_patterns
)

reset_patterns()

sample_records = [
    {
        "event_type": "CREATED",
        "file_extension": ".txt",
        "directory": "Documents",
        "event_hour": 10,
        "file_size": 1000
    },
    {
        "event_type": "MODIFIED",
        "file_extension": ".docx",
        "directory": "Projects",
        "event_hour": 12,
        "file_size": 5000
    },
    {
        "event_type": "DELETED",
        "file_extension": ".xlsx",
        "directory": "Downloads",
        "event_hour": 14,
        "file_size": 2500
    },
    {
        "event_type": "MOVED",
        "file_extension": ".pdf",
        "directory": "Archive",
        "event_hour": 16,
        "file_size": 8000
    },
    {
        "event_type": "COPIED",
        "file_extension": ".zip",
        "directory": "Backups",
        "event_hour": 18,
        "file_size": 15000
    }
]

for record in sample_records:
    store_pattern(record)

summary = get_pattern_summary()

print("\n===== PATTERN REPOSITORY V2 =====\n")

for key, value in summary.items():
    print(f"{key}:")
    print(value)
    print()
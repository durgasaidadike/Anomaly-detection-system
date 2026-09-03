from pattern_repository import (
    get_pattern_summary,
    reset_patterns,
    store_pattern,
)


def test_pattern_repository_stores_sample_records(monkeypatch):
    saved_snapshots = []

    monkeypatch.setattr(
        "pattern_repository.save_patterns",
        lambda snapshot: saved_snapshots.append(snapshot.copy()),
    )

    reset_patterns()

    sample_records = [
        {
            "event_type": "CREATED",
            "file_extension": ".txt",
            "directory": "Documents",
            "event_hour": 10,
            "file_size": 1000,
        },
        {
            "event_type": "MODIFIED",
            "file_extension": ".docx",
            "directory": "Projects",
            "event_hour": 12,
            "file_size": 5000,
        },
        {
            "event_type": "DELETED",
            "file_extension": ".xlsx",
            "directory": "Downloads",
            "event_hour": 14,
            "file_size": 2500,
        },
        {
            "event_type": "MOVED",
            "file_extension": ".pdf",
            "directory": "Archive",
            "event_hour": 16,
            "file_size": 8000,
        },
        {
            "event_type": "COPIED",
            "file_extension": ".zip",
            "directory": "Backups",
            "event_hour": 18,
            "file_size": 15000,
        },
    ]

    for record in sample_records:
        store_pattern(record)

    summary = get_pattern_summary()

    assert summary["event_sequence"] == [
        "CREATED",
        "MODIFIED",
        "DELETED",
        "MOVED",
        "COPIED",
    ]

    assert summary["operation_stats"] == {
        "CREATED": 1,
        "MODIFIED": 1,
        "DELETED": 1,
        "MOVED": 1,
        "RENAMED": 0,
        "EXTENSION_CHANGED": 0,
        "COPIED": 1,
    }

    assert len(summary["create_history"]) == 1
    assert len(summary["modify_history"]) == 1
    assert len(summary["delete_history"]) == 1
    assert len(summary["move_history"]) == 1
    assert len(summary["copy_history"]) == 1

    assert len(saved_snapshots) == len(sample_records)
from datetime import datetime

from candidate_pattern_manager import CandidatePatternManager
from final_pattern_repository_adapter import (
    FinalPatternRepositoryAdapter,
)


def test_completed_pattern_reaches_repository_with_normalized_operations(
    monkeypatch,
):
    stored_records = []

    monkeypatch.setattr(
        "final_pattern_repository_adapter.store_pattern",
        lambda record: stored_records.append(record),
    )

    adapter = FinalPatternRepositoryAdapter()

    manager = CandidatePatternManager(
        final_pattern_handler=adapter.store,
    )

    manager.createPattern(
        "session-1",
        user_id="user-1",
        session_start_time=datetime(
            2026,
            1,
            1,
            10,
            0,
        ),
    )

    observations = [
        {
            "operation_type": "CREATE",
            "timestamp": datetime(2026, 1, 1, 10, 0),
            "file_extension": ".txt",
            "directory": "Documents",
            "event_hour": 10,
            "file_size": 1000,
        },
        {
            "operation_type": "MODIFY",
            "timestamp": datetime(2026, 1, 1, 10, 5),
            "file_extension": ".docx",
            "directory": "Projects",
            "event_hour": 10,
            "file_size": 5000,
        },
        {
            "operation_type": "DELETE",
            "timestamp": datetime(2026, 1, 1, 10, 10),
            "file_extension": ".xlsx",
            "directory": "Downloads",
            "event_hour": 10,
            "file_size": 2500,
        },
        {
            "operation_type": "MOVE",
            "timestamp": datetime(2026, 1, 1, 10, 15),
            "file_extension": ".pdf",
            "directory": "Archive",
            "event_hour": 10,
            "file_size": 8000,
        },
        {
            "operation_type": "COPY",
            "timestamp": datetime(2026, 1, 1, 10, 20),
            "file_extension": ".zip",
            "directory": "Backups",
            "event_hour": 10,
            "file_size": 15000,
        },
    ]

    for observation in observations:
        manager.updatePattern(
            "session-1",
            observation,
        )

    finalized_pattern = manager.finalizePattern(
        "session-1"
    )

    assert finalized_pattern is not None
    assert finalized_pattern.metadata.complete is True

    assert stored_records == [
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
            "event_hour": 10,
            "file_size": 5000,
        },
        {
            "event_type": "DELETED",
            "file_extension": ".xlsx",
            "directory": "Downloads",
            "event_hour": 10,
            "file_size": 2500,
        },
        {
            "event_type": "MOVED",
            "file_extension": ".pdf",
            "directory": "Archive",
            "event_hour": 10,
            "file_size": 8000,
        },
        {
            "event_type": "COPIED",
            "file_extension": ".zip",
            "directory": "Backups",
            "event_hour": 10,
            "file_size": 15000,
        },
    ]


def test_finalized_pattern_is_handed_off_only_once(
    monkeypatch,
):
    stored_records = []

    monkeypatch.setattr(
        "final_pattern_repository_adapter.store_pattern",
        lambda record: stored_records.append(record),
    )

    adapter = FinalPatternRepositoryAdapter()

    manager = CandidatePatternManager(
        final_pattern_handler=adapter.store,
    )

    manager.createPattern("session-1")

    manager.updatePattern(
        "session-1",
        {
            "operation_type": "CREATE",
            "timestamp": datetime(
                2026,
                1,
                1,
                10,
                0,
            ),
        },
    )

    first_result = manager.finalizePattern(
        "session-1"
    )

    second_result = manager.finalizePattern(
        "session-1"
    )

    assert first_result is second_result
    assert len(stored_records) == 1

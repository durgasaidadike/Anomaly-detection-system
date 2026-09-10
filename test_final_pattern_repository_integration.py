from datetime import datetime, timezone

from candidate_pattern_manager import CandidatePatternManager
from final_pattern_repository_adapter import (
    FinalPatternRepositoryAdapter,
)


def test_completed_pattern_reaches_repository_with_operations_preserved():
    adapter = FinalPatternRepositoryAdapter()

    manager = CandidatePatternManager(
        final_pattern_handler=adapter.store,
    )

    start_time = datetime(
        2026,
        1,
        1,
        10,
        0,
        tzinfo=timezone.utc,
    )

    manager.createPattern(
        "session-1",
        user_id="user-1",
        session_start_time=start_time,
    )

    observations = [
        {
            "operation_type": "CREATED",
            "timestamp": start_time,
            "file_extension": ".txt",
            "directory": "Documents",
            "event_hour": 10,
            "file_size": 1000,
        },
        {
            "operation_type": "MODIFIED",
            "timestamp": datetime(
                2026,
                1,
                1,
                10,
                5,
                tzinfo=timezone.utc,
            ),
            "file_extension": ".docx",
            "directory": "Projects",
            "event_hour": 10,
            "file_size": 5000,
        },
        {
            "operation_type": "DELETED",
            "timestamp": datetime(
                2026,
                1,
                1,
                10,
                10,
                tzinfo=timezone.utc,
            ),
            "file_extension": ".xlsx",
            "directory": "Downloads",
            "event_hour": 10,
            "file_size": 2500,
        },
        {
            "operation_type": "MOVED",
            "timestamp": datetime(
                2026,
                1,
                1,
                10,
                15,
                tzinfo=timezone.utc,
            ),
            "file_extension": ".pdf",
            "directory": "Archive",
            "event_hour": 10,
            "file_size": 8000,
        },
        {
            "operation_type": "COPIED",
            "timestamp": datetime(
                2026,
                1,
                1,
                10,
                20,
                tzinfo=timezone.utc,
            ),
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

    manager.completeSession(
        "session-1",
        session_end_time=datetime(
            2026,
            1,
            1,
            10,
            25,
            tzinfo=timezone.utc,
        ),
    )

    finalized_pattern = manager.finalizePattern(
        "session-1"
    )

    assert finalized_pattern is not None
    assert finalized_pattern.metadata.complete is True

    repository = adapter.get_repository()

    stored_patterns = repository.get_all()

    assert len(stored_patterns) == 1

    stored_pattern = stored_patterns[0]

    assert stored_pattern.session_id == "session-1"
    assert stored_pattern.user_id == "user-1"
    assert stored_pattern.observation_count == 5

    assert [
        observation["operation_type"]
        for observation in stored_pattern.observations
    ] == [
        "CREATED",
        "MODIFIED",
        "DELETED",
        "MOVED",
        "COPIED",
    ]

    assert stored_pattern.observations == observations


def test_finalized_pattern_is_handed_off_only_once():
    adapter = FinalPatternRepositoryAdapter()

    manager = CandidatePatternManager(
        final_pattern_handler=adapter.store,
    )

    start_time = datetime(
        2026,
        1,
        1,
        10,
        0,
        tzinfo=timezone.utc,
    )

    manager.createPattern(
        "session-1",
        session_start_time=start_time,
    )

    manager.updatePattern(
        "session-1",
        {
            "operation_type": "CREATED",
            "timestamp": start_time,
        },
    )

    manager.completeSession(
        "session-1",
        session_end_time=datetime(
            2026,
            1,
            1,
            10,
            1,
            tzinfo=timezone.utc,
        ),
    )

    first_result = manager.finalizePattern(
        "session-1"
    )

    second_result = manager.finalizePattern(
        "session-1"
    )

    assert first_result is second_result

    repository = adapter.get_repository()

    assert repository.count() == 1
    assert repository.knowledge_count() == 1
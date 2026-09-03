from datetime import datetime

from candidate_pattern_manager import CandidatePatternManager
from final_pattern_repository_adapter import (
    FinalPatternRepositoryAdapter,
)


def test_finalize_pattern_hands_off_to_repository_adapter(monkeypatch):
    stored_patterns = []

    adapter = FinalPatternRepositoryAdapter()

    def capture_pattern(pattern):
        stored_patterns.append(pattern)
        return True

    monkeypatch.setattr(
        adapter,
        "store",
        capture_pattern,
    )

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

    manager.updatePattern(
        "session-1",
        {
            "operation_type": "CREATE",
            "timestamp": datetime(
                2026,
                1,
                1,
                10,
                5,
            ),
            "file_extension": ".txt",
            "directory": "Documents",
            "event_hour": 10,
            "file_size": 1000,
        },
    )

    finalized_pattern = manager.finalizePattern("session-1")

    assert finalized_pattern is not None
    assert len(stored_patterns) == 1
    assert stored_patterns[0] is finalized_pattern


def test_repository_handoff_receives_completed_pattern():
    received = []

    def handler(pattern):
        received.append(pattern)
        return True

    manager = CandidatePatternManager(
        final_pattern_handler=handler,
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

    pattern = manager.finalizePattern("session-1")

    assert len(received) == 1
    assert received[0] is pattern
    assert pattern.metadata.complete is True


def test_failed_repository_handoff_does_not_create_second_handoff():
    calls = []

    def failing_handler(pattern):
        calls.append(pattern)
        return False

    manager = CandidatePatternManager(
        final_pattern_handler=failing_handler,
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

    first_result = manager.finalizePattern("session-1")
    second_result = manager.finalizePattern("session-1")

    assert first_result is second_result
    assert len(calls) == 1


def test_manager_works_without_repository_handler():
    manager = CandidatePatternManager()

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

    pattern = manager.finalizePattern("session-1")

    assert pattern is not None
    assert pattern.metadata.complete is True

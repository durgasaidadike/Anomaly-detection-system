from datetime import datetime

from candidate_pattern_manager import CandidatePatternManager
from final_pattern_repository_adapter import (
    FinalPatternRepositoryAdapter,
)


def test_completed_pattern_is_accepted(monkeypatch):
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
            "file_extension": ".txt",
            "directory": "Documents",
            "event_hour": 10,
            "file_size": 1000,
        },
    )

    pattern = manager.finalizePattern("session-1")

    stored_records = []

    monkeypatch.setattr(
        "final_pattern_repository_adapter.store_pattern",
        lambda record: stored_records.append(record),
    )

    adapter = FinalPatternRepositoryAdapter()

    assert adapter.store(pattern) is True
    assert len(stored_records) == 1


def test_incomplete_pattern_is_rejected():
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

    pattern = manager.getCurrentPattern("session-1")

    adapter = FinalPatternRepositoryAdapter()

    assert adapter.store(pattern) is False


def test_empty_pattern_is_rejected():
    manager = CandidatePatternManager()

    manager.createPattern("session-1")

    pattern = manager.getCurrentPattern("session-1")

    adapter = FinalPatternRepositoryAdapter()

    assert adapter.store(pattern) is False


def test_observation_is_translated_to_repository_record():
    adapter = FinalPatternRepositoryAdapter()

    observation = {
        "operation_type": "MODIFY",
        "timestamp": datetime(
            2026,
            1,
            1,
            12,
            0,
        ),
        "file_extension": ".docx",
        "directory": "Projects",
        "event_hour": 12,
        "file_size": 5000,
    }

    result = adapter._to_repository_record(
        observation
    )

    assert result == {
        "event_type": "MODIFIED",
        "file_extension": ".docx",
        "directory": "Projects",
        "event_hour": 12,
        "file_size": 5000,
    }


def test_invalid_observation_is_ignored():
    adapter = FinalPatternRepositoryAdapter()

    assert adapter._to_repository_record(None) is None
    assert adapter._to_repository_record("invalid") is None
    assert adapter._to_repository_record({}) is None


def test_create_operation_is_normalized():
    adapter = FinalPatternRepositoryAdapter()

    result = adapter._to_repository_record(
        {
            "operation_type": "CREATE",
            "timestamp": datetime(2026, 1, 1, 10, 0),
        }
    )

    assert result["event_type"] == "CREATED"


def test_modify_operation_is_normalized():
    adapter = FinalPatternRepositoryAdapter()

    result = adapter._to_repository_record(
        {
            "operation_type": "MODIFY",
            "timestamp": datetime(2026, 1, 1, 10, 0),
        }
    )

    assert result["event_type"] == "MODIFIED"


def test_delete_operation_is_normalized():
    adapter = FinalPatternRepositoryAdapter()

    result = adapter._to_repository_record(
        {
            "operation_type": "DELETE",
            "timestamp": datetime(2026, 1, 1, 10, 0),
        }
    )

    assert result["event_type"] == "DELETED"


def test_unknown_operation_is_rejected():
    adapter = FinalPatternRepositoryAdapter()

    result = adapter._to_repository_record(
        {
            "operation_type": "UNKNOWN_OPERATION",
            "timestamp": datetime(2026, 1, 1, 10, 0),
        }
    )

    assert result is None

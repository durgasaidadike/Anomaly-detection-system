from datetime import datetime, timedelta
import copy
import pytest

from candidate_pattern_manager import CandidatePatternManager
from candidate_pattern_models import PatternStatus


def test_create_pattern():
    manager = CandidatePatternManager()

    start_time = datetime.now()

    pattern = manager.createPattern(
        session_id="session-001",
        user_id="user-001",
        session_start_time=start_time,
    )

    assert pattern.session_id == "session-001"
    assert pattern.user_id == "user-001"
    assert pattern.session_start_time == start_time
    assert pattern.metadata.status == PatternStatus.INITIALIZING


def test_get_current_pattern():
    manager = CandidatePatternManager()

    pattern = manager.createPattern(
        session_id="session-001",
        user_id="user-001",
    )

    current = manager.getCurrentPattern("session-001")

    assert current is pattern


def test_unknown_session_returns_none():
    manager = CandidatePatternManager()

    assert manager.getCurrentPattern("unknown-session") is None


def test_multiple_sessions_are_isolated():
    manager = CandidatePatternManager()

    first = manager.createPattern(
        session_id="session-001",
        user_id="user-001",
    )

    second = manager.createPattern(
        session_id="session-002",
        user_id="user-002",
    )

    assert first is not second
    assert manager.getCurrentPattern("session-001") is first
    assert manager.getCurrentPattern("session-002") is second


def test_create_existing_session_returns_existing_pattern():
    manager = CandidatePatternManager()

    first = manager.createPattern(
        session_id="session-001",
        user_id="user-001",
    )

    second = manager.createPattern(
        session_id="session-001",
        user_id="user-001",
    )

    assert second is first


def test_update_pattern_adds_observation():
    manager = CandidatePatternManager()

    manager.createPattern(
        session_id="session-001",
        user_id="user-001",
    )

    observation = {
        "operation_type": "CREATE",
        "timestamp": datetime.now(),
    }

    pattern = manager.updatePattern(
        session_id="session-001",
        observation=observation,
    )

    assert pattern is not None
    assert pattern.observation_count() == 1
    assert pattern.timeline.observations[0] == observation
    assert pattern.metadata.status == PatternStatus.LEARNING


def test_update_pattern_accumulates_observations():
    manager = CandidatePatternManager()

    manager.createPattern(session_id="session-001")

    first = {
        "operation_type": "CREATE",
        "timestamp": datetime.now(),
    }

    second = {
        "operation_type": "MODIFY",
        "timestamp": datetime.now(),
    }

    manager.updatePattern("session-001", first)
    pattern = manager.updatePattern("session-001", second)

    assert pattern is not None
    assert pattern.observation_count() == 2
    assert pattern.timeline.observations[0] == first
    assert pattern.timeline.observations[1] == second


def test_update_pattern_updates_context():
    manager = CandidatePatternManager()

    manager.createPattern(session_id="session-001")

    observation = {
        "operation_type": "CREATE",
        "timestamp": datetime.now(),
    }

    context = {
        "working_directory": "project",
        "session_intensity": "HIGH",
    }

    pattern = manager.updatePattern(
        "session-001",
        observation,
        context,
    )

    assert pattern is not None
    assert pattern.context.values["working_directory"] == "project"
    assert pattern.context.values["session_intensity"] == "HIGH"


def test_update_pattern_updates_latest_context():
    manager = CandidatePatternManager()

    manager.createPattern(session_id="session-001")

    first = {
        "operation_type": "CREATE",
        "timestamp": datetime.now(),
    }

    second = {
        "operation_type": "MODIFY",
        "timestamp": datetime.now(),
    }

    manager.updatePattern(
        "session-001",
        first,
        {"session_intensity": "LOW"},
    )

    pattern = manager.updatePattern(
        "session-001",
        second,
        {"session_intensity": "HIGH"},
    )

    assert pattern is not None
    assert pattern.context.values["session_intensity"] == "HIGH"


def test_update_failure_rolls_back_partial_state():
    manager = CandidatePatternManager()

    pattern = manager.createPattern("session-1")

    first_observation = {
        "operation_type": "CREATE",
        "file_extension": ".txt",
        "directory": "/docs",
        "event_hour": 10,
        "file_size": 100,
        "timestamp": "2026-01-01T10:00:00",
    }

    manager.updatePattern(
        "session-1",
        first_observation,
    )

    original_count = pattern.observation_count()
    original_operations = pattern.operational_characteristics.copy()
    original_status = pattern.metadata.status

    def failing_update(*args, **kwargs):
        raise RuntimeError("simulated update failure")

    manager._update_operational_characteristics = failing_update

    second_observation = {
        "operation_type": "MODIFY",
        "file_extension": ".txt",
        "directory": "/docs",
        "event_hour": 11,
        "file_size": 200,
        "timestamp": "2026-01-01T11:00:00",
    }

    result = manager.updatePattern(
        "session-1",
        second_observation,
    )

    assert result is pattern
    assert pattern.observation_count() == original_count
    assert pattern.operational_characteristics == original_operations
    assert pattern.metadata.status == original_status


def test_update_failure_rolls_back_context_and_relationships():
    manager = CandidatePatternManager()

    pattern = manager.createPattern("session-1")

    first_observation = {
        "operation_type": "CREATE",
        "file_extension": ".txt",
        "directory": "/docs",
        "event_hour": 10,
        "file_size": 100,
        "timestamp": "2026-01-01T10:00:00",
    }

    manager.updatePattern(
        "session-1",
        first_observation,
    )

    original_count = pattern.observation_count()
    original_context = pattern.context.values.copy()
    original_relationships = (
        pattern.relationship_characteristics.copy()
    )

    def failing_relationship_update(*args, **kwargs):
        raise RuntimeError("simulated relationship failure")

    manager._update_relationship_characteristics = (
        failing_relationship_update
    )

    second_observation = {
        "operation_type": "MODIFY",
        "file_extension": ".log",
        "directory": "/logs",
        "event_hour": 11,
        "file_size": 300,
        "timestamp": "2026-01-01T11:00:00",
    }

    result = manager.updatePattern(
        "session-1",
        second_observation,
        context={
            "source": "filesystem",
            "environment": "production",
        },
        relationships=[
            {
                "type": "related_file",
                "target": "important.txt",
            }
        ],
    )

    assert result is pattern
    assert pattern.observation_count() == original_count
    assert pattern.context.values == original_context
    assert (
        pattern.relationship_characteristics
        == original_relationships
    )


def test_first_update_failure_preserves_initial_state():
    manager = CandidatePatternManager()

    pattern = manager.createPattern("session-1")

    original_status = pattern.metadata.status

    def failing_update(*args, **kwargs):
        raise RuntimeError("simulated failure")

    manager._update_operational_characteristics = failing_update

    observation = {
        "operation_type": "CREATE",
        "file_extension": ".txt",
        "directory": "/docs",
        "event_hour": 10,
        "file_size": 100,
        "timestamp": "2026-01-01T10:00:00",
    }

    result = manager.updatePattern(
        "session-1",
        observation,
    )

    assert result is pattern
    assert pattern.observation_count() == 0
    assert pattern.metadata.observation_count == 0
    assert pattern.metadata.status == original_status
    assert pattern.operational_characteristics == {}


def test_duplicate_observation_is_ignored():
    manager = CandidatePatternManager()

    manager.createPattern(session_id="session-001")

    timestamp = datetime.now()

    observation = {
        "operation_type": "CREATE",
        "timestamp": timestamp,
    }

    manager.updatePattern("session-001", observation)
    manager.updatePattern("session-001", observation)

    pattern = manager.getCurrentPattern("session-001")

    assert pattern is not None
    assert pattern.observation_count() == 1


def test_update_unknown_session_returns_none():
    manager = CandidatePatternManager()

    observation = {
        "operation_type": "CREATE",
        "timestamp": datetime.now(),
    }

    pattern = manager.updatePattern(
        "unknown-session",
        observation,
    )

    assert pattern is None


def test_empty_observation_does_not_corrupt_pattern():
    manager = CandidatePatternManager()

    manager.createPattern(session_id="session-001")

    valid_observation = {
        "operation_type": "CREATE",
        "timestamp": datetime.now(),
    }

    manager.updatePattern(
        "session-001",
        valid_observation,
    )

    pattern = manager.updatePattern(
        "session-001",
        {},
    )

    assert pattern is not None
    assert pattern.observation_count() == 1
    assert pattern.timeline.observations[0] == valid_observation


def test_sessions_remain_isolated_during_updates():
    manager = CandidatePatternManager()

    manager.createPattern(session_id="session-001")
    manager.createPattern(session_id="session-002")

    first = {
        "operation_type": "CREATE",
        "timestamp": datetime.now(),
    }

    second = {
        "operation_type": "DELETE",
        "timestamp": datetime.now(),
    }

    manager.updatePattern("session-001", first)
    manager.updatePattern("session-002", second)

    first_pattern = manager.getCurrentPattern("session-001")
    second_pattern = manager.getCurrentPattern("session-002")

    assert first_pattern is not None
    assert second_pattern is not None

    assert first_pattern.observation_count() == 1
    assert second_pattern.observation_count() == 1

    assert (
        first_pattern.timeline.observations[0]["operation_type"]
        == "CREATE"
    )

    assert (
        second_pattern.timeline.observations[0]["operation_type"]
        == "DELETE"
    )


def test_freeze_pattern_marks_pattern_interrupted():
    manager = CandidatePatternManager()

    manager.createPattern(
        session_id="session-001",
        user_id="user-001",
    )

    observation = {
        "operation_type": "CREATE",
        "timestamp": datetime.now(),
    }

    manager.updatePattern(
        "session-001",
        observation,
    )

    pattern = manager.freezePattern("session-001")

    assert pattern is not None
    assert pattern.observation_count() == 1
    assert pattern.metadata.interrupted is True
    assert pattern.metadata.complete is False


def test_freeze_empty_pattern_preserves_empty_state():
    manager = CandidatePatternManager()

    manager.createPattern(
        session_id="session-001",
    )

    pattern = manager.freezePattern("session-001")

    assert pattern is not None
    assert pattern.is_empty()
    assert pattern.metadata.interrupted is True
    assert pattern.metadata.complete is False


def test_freeze_unknown_session_returns_none():
    manager = CandidatePatternManager()

    pattern = manager.freezePattern(
        "unknown-session",
    )

    assert pattern is None


def test_freeze_preserves_latest_valid_observations():
    manager = CandidatePatternManager()

    manager.createPattern(
        session_id="session-001",
    )

    first = {
        "operation_type": "CREATE",
        "timestamp": datetime.now(),
    }

    second = {
        "operation_type": "MODIFY",
        "timestamp": datetime.now(),
    }

    manager.updatePattern("session-001", first)
    manager.updatePattern("session-001", second)

    pattern = manager.freezePattern("session-001")

    assert pattern is not None
    assert pattern.observation_count() == 2
    assert pattern.timeline.observations[0] == first
    assert pattern.timeline.observations[1] == second


def test_freeze_does_not_remove_active_pattern():
    manager = CandidatePatternManager()

    created = manager.createPattern(
        session_id="session-001",
    )

    frozen = manager.freezePattern(
        "session-001",
    )

    current = manager.getCurrentPattern(
        "session-001",
    )

    assert frozen is created
    assert current is created


def test_finalize_pattern_completes_valid_pattern():
    manager = CandidatePatternManager()

    manager.createPattern(
        session_id="session-001",
        user_id="user-001",
    )

    observation = {
        "operation_type": "CREATE",
        "timestamp": datetime.now(),
    }

    manager.updatePattern(
        "session-001",
        observation,
    )

    pattern = manager.finalizePattern("session-001")

    assert pattern is not None
    assert pattern.observation_count() == 1
    assert pattern.metadata.status == PatternStatus.COMPLETED
    assert pattern.metadata.complete is True
    assert pattern.metadata.finalized_at is not None


def test_finalize_empty_pattern_is_discarded():
    manager = CandidatePatternManager()

    manager.createPattern(
        session_id="session-001",
    )

    pattern = manager.finalizePattern("session-001")

    assert pattern is None

    current = manager.getCurrentPattern("session-001")

    assert current is not None
    assert current.is_empty()
    assert current.metadata.complete is False


def test_finalize_interrupted_pattern_is_rejected():
    manager = CandidatePatternManager()

    manager.createPattern(
        session_id="session-001",
    )

    observation = {
        "operation_type": "MODIFY",
        "timestamp": datetime.now(),
    }

    manager.updatePattern(
        "session-001",
        observation,
    )

    manager.freezePattern("session-001")

    pattern = manager.finalizePattern("session-001")

    assert pattern is None

    current = manager.getCurrentPattern("session-001")

    assert current is not None
    assert current.observation_count() == 1
    assert current.metadata.interrupted is True
    assert current.metadata.complete is False


def test_finalize_unknown_session_returns_none():
    manager = CandidatePatternManager()

    pattern = manager.finalizePattern(
        "unknown-session",
    )

    assert pattern is None


def test_finalize_preserves_latest_valid_observations():
    manager = CandidatePatternManager()

    manager.createPattern(
        session_id="session-001",
    )

    first = {
        "operation_type": "CREATE",
        "timestamp": datetime.now(),
    }

    second = {
        "operation_type": "MODIFY",
        "timestamp": datetime.now(),
    }

    manager.updatePattern(
        "session-001",
        first,
    )

    manager.updatePattern(
        "session-001",
        second,
    )

    pattern = manager.finalizePattern(
        "session-001",
    )

    assert pattern is not None
    assert pattern.observation_count() == 2
    assert pattern.timeline.observations[0] == first
    assert pattern.timeline.observations[1] == second
    assert pattern.metadata.status == PatternStatus.COMPLETED


def test_reset_pattern_removes_active_pattern():
    manager = CandidatePatternManager()

    created = manager.createPattern(
        session_id="session-001",
    )

    reset = manager.resetPattern(
        "session-001",
    )

    assert reset is created
    assert manager.getCurrentPattern("session-001") is None


def test_reset_unknown_session_returns_none():
    manager = CandidatePatternManager()

    result = manager.resetPattern(
        "unknown-session",
    )

    assert result is None


def test_reset_preserves_returned_pattern_object():
    manager = CandidatePatternManager()

    manager.createPattern(
        session_id="session-001",
    )

    observation = {
        "operation_type": "CREATE",
        "timestamp": datetime.now(),
    }

    manager.updatePattern(
        "session-001",
        observation,
    )

    finalized = manager.finalizePattern(
        "session-001",
    )

    assert finalized is not None

    reset = manager.resetPattern(
        "session-001",
    )

    assert reset is finalized
    assert reset.metadata.status == PatternStatus.COMPLETED
    assert reset.metadata.complete is True
    assert reset.observation_count() == 1

    assert manager.getCurrentPattern("session-001") is None


def test_reset_allows_new_candidate_pattern_for_same_session():
    manager = CandidatePatternManager()

    first = manager.createPattern(
        session_id="session-001",
    )

    manager.resetPattern(
        "session-001",
    )

    second = manager.createPattern(
        session_id="session-001",
    )

    assert second is not first
    assert second.session_id == "session-001"
    assert second.is_empty()


def test_reset_does_not_clear_pattern_data():
    manager = CandidatePatternManager()

    manager.createPattern(
        session_id="session-001",
    )

    observation = {
        "operation_type": "MODIFY",
        "timestamp": datetime.now(),
    }

    manager.updatePattern(
        "session-001",
        observation,
    )

    pattern = manager.resetPattern(
        "session-001",
    )

    assert pattern is not None
    assert pattern.observation_count() == 1
    assert pattern.timeline.observations[0] == observation


def test_completed_pattern_cannot_be_updated():
    manager = CandidatePatternManager()

    manager.createPattern(
        session_id="session-001",
    )

    first = {
        "operation_type": "CREATE",
        "timestamp": datetime.now(),
    }

    manager.updatePattern(
        "session-001",
        first,
    )

    finalized = manager.finalizePattern(
        "session-001",
    )

    assert finalized is not None
    assert finalized.metadata.status == PatternStatus.COMPLETED
    assert finalized.observation_count() == 1

    second = {
        "operation_type": "MODIFY",
        "timestamp": datetime.now(),
    }

    result = manager.updatePattern(
        "session-001",
        second,
    )

    assert result is finalized
    assert result.observation_count() == 1
    assert second not in result.timeline.observations


def test_interrupted_pattern_cannot_be_updated():
    manager = CandidatePatternManager()

    manager.createPattern(
        session_id="session-001",
    )

    first = {
        "operation_type": "CREATE",
        "timestamp": datetime.now(),
    }

    manager.updatePattern(
        "session-001",
        first,
    )

    frozen = manager.freezePattern(
        "session-001",
    )

    assert frozen is not None
    assert frozen.metadata.interrupted is True

    second = {
        "operation_type": "DELETE",
        "timestamp": datetime.now(),
    }

    result = manager.updatePattern(
        "session-001",
        second,
    )

    assert result is frozen
    assert result.observation_count() == 1
    assert second not in result.timeline.observations


def test_initializing_pattern_can_be_updated():
    manager = CandidatePatternManager()

    pattern = manager.createPattern(
        session_id="session-001",
    )

    assert pattern.metadata.status == PatternStatus.INITIALIZING

    observation = {
        "operation_type": "CREATE",
        "timestamp": datetime.now(),
    }

    result = manager.updatePattern(
        "session-001",
        observation,
    )

    assert result is pattern
    assert result.observation_count() == 1
    assert result.metadata.status == PatternStatus.LEARNING


def test_learning_pattern_can_continue_updates():
    manager = CandidatePatternManager()

    manager.createPattern(session_id="session-001")

    first = {
        "operation_type": "CREATE",
        "timestamp": datetime.now(),
    }

    manager.updatePattern("session-001", first)

    pattern = manager.getCurrentPattern("session-001")

    assert pattern is not None
    assert pattern.metadata.status == PatternStatus.LEARNING

    second = {
        "operation_type": "MODIFY",
        "timestamp": datetime.now(),
    }

    result = manager.updatePattern("session-001", second)

    assert result is pattern
    assert result.observation_count() == 2
    assert result.metadata.status == PatternStatus.LEARNING


def test_out_of_order_observation_is_rejected():
    manager = CandidatePatternManager()

    manager.createPattern(session_id="session-001")

    first = {
        "operation_type": "CREATE",
        "timestamp": datetime(2026, 1, 1, 10, 0, 0),
    }

    earlier = {
        "operation_type": "MODIFY",
        "timestamp": datetime(2026, 1, 1, 9, 0, 0),
    }

    manager.updatePattern(
        "session-001",
        first,
    )

    pattern = manager.updatePattern(
        "session-001",
        earlier,
    )

    assert pattern is not None
    assert pattern.observation_count() == 1
    assert pattern.timeline.observations[0] == first


def test_equal_timestamp_observation_is_allowed():
    manager = CandidatePatternManager()

    manager.createPattern(session_id="session-001")

    timestamp = datetime(2026, 1, 1, 10, 0, 0)

    first = {
        "operation_type": "CREATE",
        "timestamp": timestamp,
    }

    second = {
        "operation_type": "MODIFY",
        "timestamp": timestamp,
    }

    manager.updatePattern(
        "session-001",
        first,
    )

    pattern = manager.updatePattern(
        "session-001",
        second,
    )

    assert pattern is not None
    assert pattern.observation_count() == 2
    assert pattern.timeline.observations == [
        first,
        second,
    ]


def test_chronological_order_is_preserved():
    manager = CandidatePatternManager()

    manager.createPattern(session_id="session-001")

    observations = [
        {
            "operation_type": "CREATE",
            "timestamp": datetime(2026, 1, 1, 10, 0, 0),
        },
        {
            "operation_type": "MODIFY",
            "timestamp": datetime(2026, 1, 1, 10, 5, 0),
        },
        {
            "operation_type": "DELETE",
            "timestamp": datetime(2026, 1, 1, 10, 10, 0),
        },
    ]

    for observation in observations:
        manager.updatePattern(
            "session-001",
            observation,
        )

    pattern = manager.getCurrentPattern(
        "session-001",
    )

    assert pattern is not None

    timestamps = [
        observation["timestamp"]
        for observation in pattern.timeline.observations
    ]

    assert timestamps == sorted(timestamps)


def test_rejected_lifecycle_update_preserves_latest_valid_state():
    manager = CandidatePatternManager()

    manager.createPattern(
        session_id="session-001",
    )

    observation = {
        "operation_type": "CREATE",
        "timestamp": datetime.now(),
    }

    manager.updatePattern(
        "session-001",
        observation,
    )

    pattern = manager.finalizePattern(
        "session-001",
    )

    assert pattern is not None

    invalid_observation = {
        "operation_type": "DELETE",
        "timestamp": datetime.now(),
    }

    result = manager.updatePattern(
        "session-001",
        invalid_observation,
    )

    assert result is pattern
    assert result.metadata.status == PatternStatus.COMPLETED
    assert result.metadata.complete is True
    assert result.observation_count() == 1
    assert result.timeline.observations[0] == observation


def test_update_builds_operational_characteristics():
    manager = CandidatePatternManager()

    manager.createPattern(
        session_id="session-001",
    )

    observation = {
        "operation_type": "CREATE",
        "timestamp": datetime.now(),
    }

    pattern = manager.updatePattern(
        "session-001",
        observation,
    )

    assert pattern is not None

    assert pattern.operational_characteristics[
        "total_operations"
    ] == 1

    assert pattern.operational_characteristics[
        "operation_counts"
    ]["CREATE"] == 1

    assert pattern.operational_characteristics[
        "unique_operation_types"
    ] == 1


def test_operational_characteristics_accumulate_operation_types():
    manager = CandidatePatternManager()

    manager.createPattern(
        session_id="session-001",
    )

    observations = [
        {
            "operation_type": "CREATE",
            "timestamp": datetime.now(),
        },
        {
            "operation_type": "MODIFY",
            "timestamp": datetime.now(),
        },
        {
            "operation_type": "CREATE",
            "timestamp": datetime.now(),
        },
        {
            "operation_type": "DELETE",
            "timestamp": datetime.now(),
        },
    ]

    for observation in observations:
        manager.updatePattern(
            "session-001",
            observation,
        )

    pattern = manager.getCurrentPattern(
        "session-001",
    )

    assert pattern is not None

    characteristics = pattern.operational_characteristics

    assert characteristics["total_operations"] == 4

    assert characteristics["operation_counts"]["CREATE"] == 2
    assert characteristics["operation_counts"]["MODIFY"] == 1
    assert characteristics["operation_counts"]["DELETE"] == 1

    assert characteristics["unique_operation_types"] == 3


def test_operational_characteristics_handle_missing_operation_type():
    manager = CandidatePatternManager()

    manager.createPattern(
        session_id="session-001",
    )

    observation = {
        "timestamp": datetime.now(),
        "signal": "HIGH_ACTIVITY",
    }

    pattern = manager.updatePattern(
        "session-001",
        observation,
    )

    assert pattern is not None

    characteristics = pattern.operational_characteristics

    assert characteristics["total_operations"] == 1
    assert characteristics["operation_counts"] == {}
    assert characteristics["unique_operation_types"] == 0


def test_duplicate_observation_does_not_change_operational_characteristics():
    manager = CandidatePatternManager()

    manager.createPattern(
        session_id="session-001",
    )

    observation = {
        "operation_type": "CREATE",
        "timestamp": datetime.now(),
    }

    manager.updatePattern(
        "session-001",
        observation,
    )

    manager.updatePattern(
        "session-001",
        observation,
    )

    pattern = manager.getCurrentPattern(
        "session-001",
    )

    assert pattern is not None

    characteristics = pattern.operational_characteristics

    assert characteristics["total_operations"] == 1
    assert characteristics["operation_counts"]["CREATE"] == 1
    assert characteristics["unique_operation_types"] == 1


def test_update_builds_temporal_characteristics():
    manager = CandidatePatternManager()

    manager.createPattern(
        session_id="session-001",
    )

    timestamp = datetime(
        2026,
        9,
        1,
        10,
        0,
        0,
    )

    observation = {
        "operation_type": "CREATE",
        "timestamp": timestamp,
    }

    pattern = manager.updatePattern(
        "session-001",
        observation,
    )

    assert pattern is not None

    characteristics = pattern.temporal_characteristics

    assert characteristics["first_observation_time"] == timestamp
    assert characteristics["last_observation_time"] == timestamp
    assert characteristics["duration_seconds"] == 0.0


def test_temporal_characteristics_calculate_duration():
    manager = CandidatePatternManager()

    manager.createPattern(
        session_id="session-001",
    )

    first_timestamp = datetime(
        2026,
        9,
        1,
        10,
        0,
        0,
    )

    second_timestamp = datetime(
        2026,
        9,
        1,
        10,
        0,
        12,
    )

    manager.updatePattern(
        "session-001",
        {
            "operation_type": "CREATE",
            "timestamp": first_timestamp,
        },
    )

    pattern = manager.updatePattern(
        "session-001",
        {
            "operation_type": "MODIFY",
            "timestamp": second_timestamp,
        },
    )

    assert pattern is not None

    characteristics = pattern.temporal_characteristics

    assert characteristics["first_observation_time"] == first_timestamp
    assert characteristics["last_observation_time"] == second_timestamp
    assert characteristics["duration_seconds"] == 12.0


def test_temporal_characteristics_handle_out_of_order_timestamps():
    manager = CandidatePatternManager()

    manager.createPattern(
        session_id="session-001",
    )

    first_timestamp = datetime(
        2026,
        9,
        1,
        10,
        0,
        10,
    )

    earlier_timestamp = datetime(
        2026,
        9,
        1,
        10,
        0,
        3,
    )

    later_timestamp = datetime(
        2026,
        9,
        1,
        10,
        0,
        20,
    )

    manager.updatePattern(
        "session-001",
        {
            "operation_type": "MODIFY",
            "timestamp": first_timestamp,
        },
    )

    # Out-of-order observation is rejected
    manager.updatePattern(
        "session-001",
        {
            "operation_type": "MODIFY",
            "timestamp": earlier_timestamp,
        },
    )

    manager.updatePattern(
        "session-001",
        {
            "operation_type": "MODIFY",
            "timestamp": later_timestamp,
        },
    )

    pattern = manager.getCurrentPattern(
        "session-001",
    )

    assert pattern is not None

    characteristics = pattern.temporal_characteristics

    # Only first and later timestamps are accepted (earlier is rejected)
    assert characteristics["first_observation_time"] == first_timestamp
    assert characteristics["last_observation_time"] == later_timestamp
    assert characteristics["duration_seconds"] == 10.0


def test_temporal_characteristics_require_valid_timestamp():
    manager = CandidatePatternManager()

    manager.createPattern(
        session_id="session-001",
    )

    observation = {
        "operation_type": "CREATE",
    }

    pattern = manager.updatePattern(
        "session-001",
        observation,
    )

    assert pattern is not None
    assert pattern.observation_count() == 0
    assert pattern.temporal_characteristics == {}


def test_update_builds_sequential_characteristics():
    manager = CandidatePatternManager()

    manager.createPattern(
        session_id="session-001",
    )

    timestamp = datetime.now()

    observation = {
        "operation_type": "CREATE",
        "timestamp": timestamp,
    }

    pattern = manager.updatePattern(
        "session-001",
        observation,
    )

    assert pattern is not None

    assert pattern.sequential_characteristics == [
        {
            "operation_type": "CREATE",
            "timestamp": timestamp,
        }
    ]


def test_sequential_characteristics_preserve_operation_order():
    manager = CandidatePatternManager()

    manager.createPattern(
        session_id="session-001",
    )

    observations = [
        {
            "operation_type": "CREATE",
            "timestamp": datetime.now(),
        },
        {
            "operation_type": "MODIFY",
            "timestamp": datetime.now(),
        },
        {
            "operation_type": "DELETE",
            "timestamp": datetime.now(),
        },
    ]

    for observation in observations:
        manager.updatePattern(
            "session-001",
            observation,
        )

    pattern = manager.getCurrentPattern(
        "session-001",
    )

    assert pattern is not None

    assert [
        entry["operation_type"]
        for entry in pattern.sequential_characteristics
    ] == [
        "CREATE",
        "MODIFY",
        "DELETE",
    ]


def test_duplicate_observation_does_not_change_sequence():
    manager = CandidatePatternManager()

    manager.createPattern(
        session_id="session-001",
    )

    observation = {
        "operation_type": "CREATE",
        "timestamp": datetime.now(),
    }

    manager.updatePattern(
        "session-001",
        observation,
    )

    manager.updatePattern(
        "session-001",
        observation,
    )

    pattern = manager.getCurrentPattern(
        "session-001",
    )

    assert pattern is not None

    assert len(
        pattern.sequential_characteristics
    ) == 1


def test_sequential_characteristics_ignore_missing_operation_type():
    manager = CandidatePatternManager()

    manager.createPattern(
        session_id="session-001",
    )

    observation = {
        "timestamp": datetime.now(),
        "signal": "HIGH_ACTIVITY",
    }

    pattern = manager.updatePattern(
        "session-001",
        observation,
    )

    assert pattern is not None
    assert pattern.observation_count() == 1
    assert pattern.sequential_characteristics == []


def test_update_builds_contextual_characteristics():
    manager = CandidatePatternManager()

    manager.createPattern("session-1")

    context = {
        "user_id": "user-1",
        "directory": "/workspace",
    }

    pattern = manager.updatePattern(
        "session-1",
        {
            "operation_type": "CREATE",
            "timestamp": datetime(2026, 1, 1, 10, 0, 0),
        },
        context=context,
    )

    assert pattern.contextual_characteristics == context


def test_contextual_characteristics_evolve_incrementally():
    manager = CandidatePatternManager()

    manager.createPattern("session-1")

    manager.updatePattern(
        "session-1",
        {
            "operation_type": "CREATE",
            "timestamp": datetime(2026, 1, 1, 10, 0, 0),
        },
        context={
            "directory": "/workspace",
            "user_id": "user-1",
        },
    )

    pattern = manager.updatePattern(
        "session-1",
        {
            "operation_type": "MODIFY",
            "timestamp": datetime(2026, 1, 1, 10, 1, 0),
        },
        context={
            "directory": "/workspace/project",
        },
    )

    assert pattern.contextual_characteristics["directory"] == (
        "/workspace/project"
    )

    assert pattern.contextual_characteristics["user_id"] == "user-1"


def test_missing_context_does_not_modify_contextual_characteristics():
    manager = CandidatePatternManager()

    manager.createPattern("session-1")

    pattern = manager.updatePattern(
        "session-1",
        {
            "operation_type": "CREATE",
            "timestamp": datetime(2026, 1, 1, 10, 0, 0),
        },
    )

    assert pattern.contextual_characteristics == {}


def test_duplicate_observation_does_not_change_contextual_characteristics():
    manager = CandidatePatternManager()

    manager.createPattern("session-1")

    observation = {
        "operation_type": "CREATE",
        "timestamp": datetime(2026, 1, 1, 10, 0, 0),
    }

    context = {
        "directory": "/workspace",
    }

    manager.updatePattern(
        "session-1",
        observation,
        context=context,
    )

    manager.updatePattern(
        "session-1",
        observation,
        context={
            "directory": "/different",
        },
    )

    pattern = manager.getCurrentPattern("session-1")

    assert pattern.contextual_characteristics["directory"] == "/workspace"


def test_update_builds_relationship_characteristics():
    manager = CandidatePatternManager()

    manager.createPattern("session-1")

    relationship = {
        "source": "CREATE",
        "target": "MODIFY",
        "relationship": "follows",
    }

    pattern = manager.updatePattern(
        "session-1",
        {
            "operation_type": "MODIFY",
            "timestamp": datetime(2026, 1, 1, 10, 1, 0),
        },
        relationships=[relationship],
    )

    assert pattern.relationship_characteristics == [
        relationship
    ]


def test_multiple_relationships_are_preserved():
    manager = CandidatePatternManager()

    manager.createPattern("session-1")

    relationships = [
        {
            "source": "CREATE",
            "target": "MODIFY",
            "relationship": "follows",
        },
        {
            "source": "MODIFY",
            "target": "DELETE",
            "relationship": "precedes",
        },
    ]

    pattern = manager.updatePattern(
        "session-1",
        {
            "operation_type": "DELETE",
            "timestamp": datetime(2026, 1, 1, 10, 2, 0),
        },
        relationships=relationships,
    )

    assert pattern.relationship_characteristics == relationships


def test_duplicate_relationships_are_not_repeated():
    manager = CandidatePatternManager()

    manager.createPattern("session-1")

    relationship = {
        "source": "CREATE",
        "target": "MODIFY",
        "relationship": "follows",
    }

    observation_1 = {
        "operation_type": "CREATE",
        "timestamp": datetime(2026, 1, 1, 10, 0, 0),
    }

    observation_2 = {
        "operation_type": "MODIFY",
        "timestamp": datetime(2026, 1, 1, 10, 1, 0),
    }

    manager.updatePattern(
        "session-1",
        observation_1,
        relationships=[relationship],
    )

    pattern = manager.updatePattern(
        "session-1",
        observation_2,
        relationships=[relationship],
    )

    assert pattern.relationship_characteristics == [
        relationship
    ]


def test_invalid_relationship_entries_are_ignored():
    manager = CandidatePatternManager()

    manager.createPattern("session-1")

    pattern = manager.updatePattern(
        "session-1",
        {
            "operation_type": "CREATE",
            "timestamp": datetime(2026, 1, 1, 10, 0, 0),
        },
        relationships=[
            None,
            "invalid",
            123,
        ],
    )

    assert pattern.relationship_characteristics == []


def test_update_builds_session_characteristics():
    manager = CandidatePatternManager()

    start_time = datetime(2026, 1, 1, 10, 0, 0)

    manager.createPattern(
        "session-1",
        user_id="user-1",
        session_start_time=start_time,
    )

    pattern = manager.updatePattern(
        "session-1",
        {
            "operation_type": "CREATE",
            "timestamp": start_time,
        },
    )

    assert pattern.session_characteristics["session_id"] == (
        "session-1"
    )

    assert pattern.session_characteristics["user_id"] == (
        "user-1"
    )

    assert pattern.session_characteristics[
        "session_start_time"
    ] == start_time


def test_session_characteristics_update_observation_count():
    manager = CandidatePatternManager()

    manager.createPattern("session-1")

    first_observation = {
        "operation_type": "CREATE",
        "timestamp": datetime(2026, 1, 1, 10, 0, 0),
    }

    second_observation = {
        "operation_type": "MODIFY",
        "timestamp": datetime(2026, 1, 1, 10, 1, 0),
    }

    manager.updatePattern(
        "session-1",
        first_observation,
    )

    pattern = manager.updatePattern(
        "session-1",
        second_observation,
    )

    assert pattern.session_characteristics[
        "observation_count"
    ] == 2


def test_duplicate_observation_does_not_change_session_count():
    manager = CandidatePatternManager()

    manager.createPattern("session-1")

    observation = {
        "operation_type": "CREATE",
        "timestamp": datetime(2026, 1, 1, 10, 0, 0),
    }

    manager.updatePattern(
        "session-1",
        observation,
    )

    manager.updatePattern(
        "session-1",
        observation,
    )

    pattern = manager.getCurrentPattern("session-1")

    assert pattern.session_characteristics[
        "observation_count"
    ] == 1


def test_session_identity_remains_stable_across_updates():
    manager = CandidatePatternManager()

    manager.createPattern(
        "session-1",
        user_id="user-1",
    )

    for minute, operation in enumerate(
        ["CREATE", "MODIFY", "DELETE"]
    ):
        manager.updatePattern(
            "session-1",
            {
                "operation_type": operation,
                "timestamp": datetime(
                    2026,
                    1,
                    1,
                    10,
                    minute,
                    0,
                ),
            },
        )

    pattern = manager.getCurrentPattern("session-1")

    assert pattern.session_characteristics["session_id"] == (
        "session-1"
    )

    assert pattern.session_characteristics["user_id"] == (
        "user-1"
    )

    assert pattern.session_characteristics[
        "observation_count"
    ] == 3


def test_get_pattern_snapshot_returns_current_pattern():
    manager = CandidatePatternManager()

    manager.createPattern("session-1")

    observation = {
        "operation_type": "CREATE",
        "timestamp": datetime(2026, 1, 1, 10, 0, 0),
    }

    manager.updatePattern(
        "session-1",
        observation,
    )

    snapshot = manager.getPatternSnapshot("session-1")

    assert snapshot is not None
    assert snapshot.session_id == "session-1"
    assert snapshot.observation_count() == 1


def test_pattern_snapshot_is_independent_from_active_pattern():
    manager = CandidatePatternManager()

    manager.createPattern("session-1")

    manager.updatePattern(
        "session-1",
        {
            "operation_type": "CREATE",
            "timestamp": datetime(2026, 1, 1, 10, 0, 0),
        },
    )

    snapshot = manager.getPatternSnapshot("session-1")

    snapshot.timeline.observations.append(
        {
            "operation_type": "DELETE",
            "timestamp": datetime(2026, 1, 1, 10, 1, 0),
        }
    )

    active_pattern = manager.getCurrentPattern("session-1")

    assert active_pattern.observation_count() == 1
    assert snapshot.observation_count() == 2


def test_pattern_snapshot_nested_characteristics_are_independent():
    manager = CandidatePatternManager()

    manager.createPattern("session-1")

    manager.updatePattern(
        "session-1",
        {
            "operation_type": "CREATE",
            "timestamp": datetime(2026, 1, 1, 10, 0, 0),
        },
        context={
            "directory": "/workspace",
        },
    )

    snapshot = manager.getPatternSnapshot("session-1")

    snapshot.contextual_characteristics[
        "directory"
    ] = "/modified"

    active_pattern = manager.getCurrentPattern("session-1")

    assert active_pattern.contextual_characteristics[
        "directory"
    ] == "/workspace"


def test_get_pattern_snapshot_returns_none_for_missing_session():
    manager = CandidatePatternManager()

    snapshot = manager.getPatternSnapshot("missing-session")

    assert snapshot is None


def test_pattern_snapshot_preserves_relationships():
    manager = CandidatePatternManager()

    manager.createPattern("session-1")

    relationship = {
        "source": "CREATE",
        "target": "MODIFY",
        "relationship": "follows",
    }

    manager.updatePattern(
        "session-1",
        {
            "operation_type": "MODIFY",
            "timestamp": datetime(2026, 1, 1, 10, 1, 0),
        },
        relationships=[relationship],
    )

    snapshot = manager.getPatternSnapshot("session-1")

    assert snapshot.relationship_characteristics == [
        relationship
    ]


def test_empty_pattern_cannot_be_finalized():
    manager = CandidatePatternManager()

    manager.createPattern("session-1")

    result = manager.finalizePattern("session-1")

    assert result is None

    pattern = manager.getCurrentPattern("session-1")

    assert pattern is not None
    assert pattern.metadata.complete is False


def test_interrupted_pattern_cannot_be_finalized():
    manager = CandidatePatternManager()

    manager.createPattern("session-1")

    manager.updatePattern(
        "session-1",
        {
            "operation_type": "CREATE",
            "timestamp": datetime(2026, 1, 1, 10, 0, 0),
        },
    )

    manager.freezePattern("session-1")

    result = manager.finalizePattern("session-1")

    assert result is None

    pattern = manager.getCurrentPattern("session-1")

    assert pattern is not None
    assert pattern.metadata.interrupted is True
    assert pattern.metadata.complete is False


def test_finalization_preserves_learned_characteristics():
    manager = CandidatePatternManager()

    manager.createPattern("session-1")

    relationship = {
        "source": "CREATE",
        "target": "MODIFY",
        "relationship": "follows",
    }

    manager.updatePattern(
        "session-1",
        {
            "operation_type": "CREATE",
            "timestamp": datetime(2026, 1, 1, 10, 0, 0),
        },
        context={
            "directory": "/workspace",
        },
    )

    manager.updatePattern(
        "session-1",
        {
            "operation_type": "MODIFY",
            "timestamp": datetime(2026, 1, 1, 10, 1, 0),
        },
        relationships=[relationship],
    )

    pattern = manager.finalizePattern("session-1")

    assert pattern is not None

    assert pattern.observation_count() == 2

    assert pattern.operational_characteristics[
        "total_operations"
    ] == 2

    assert len(pattern.sequential_characteristics) == 2

    assert pattern.contextual_characteristics[
        "directory"
    ] == "/workspace"

    assert pattern.relationship_characteristics == [
        relationship
    ]


def test_completed_pattern_cannot_be_modified():
    manager = CandidatePatternManager()

    manager.createPattern("session-1")

    manager.updatePattern(
        "session-1",
        {
            "operation_type": "CREATE",
            "timestamp": datetime(2026, 1, 1, 10, 0, 0),
        },
    )

    manager.finalizePattern("session-1")

    result = manager.updatePattern(
        "session-1",
        {
            "operation_type": "DELETE",
            "timestamp": datetime(2026, 1, 1, 10, 1, 0),
        },
    )

    assert result is not None
    assert result.metadata.status == PatternStatus.COMPLETED
    assert result.observation_count() == 1


def test_repeated_finalization_returns_completed_pattern():
    manager = CandidatePatternManager()

    manager.createPattern("session-1")

    manager.updatePattern(
        "session-1",
        {
            "operation_type": "CREATE",
            "timestamp": datetime(2026, 1, 1, 10, 0, 0),
        },
    )

    first = manager.finalizePattern("session-1")

    finalized_at = first.metadata.finalized_at

    second = manager.finalizePattern("session-1")

    assert second is first
    assert second.metadata.status == PatternStatus.COMPLETED
    assert second.metadata.finalized_at == finalized_at
    assert second.observation_count() == 1


def test_finalized_pattern_is_handed_off():
    received = []

    def handler(pattern):
        received.append(pattern)

    manager = CandidatePatternManager(
        final_pattern_handler=handler,
    )

    manager.createPattern("session-1")

    manager.updatePattern(
        "session-1",
        {
            "operation_type": "CREATE",
            "timestamp": datetime(2026, 1, 1, 10, 0, 0),
        },
    )

    pattern = manager.finalizePattern("session-1")

    assert pattern is not None
    assert len(received) == 1
    assert received[0] is pattern


def test_empty_pattern_is_not_handed_off():
    received = []

    def handler(pattern):
        received.append(pattern)

    manager = CandidatePatternManager(
        final_pattern_handler=handler,
    )

    manager.createPattern("session-1")

    result = manager.finalizePattern("session-1")

    assert result is None
    assert received == []


def test_interrupted_pattern_is_not_handed_off():
    received = []

    def handler(pattern):
        received.append(pattern)

    manager = CandidatePatternManager(
        final_pattern_handler=handler,
    )

    manager.createPattern("session-1")

    manager.updatePattern(
        "session-1",
        {
            "operation_type": "CREATE",
            "timestamp": datetime(2026, 1, 1, 10, 0, 0),
        },
    )

    manager.freezePattern("session-1")

    result = manager.finalizePattern("session-1")

    assert result is None
    assert received == []


def test_missing_session_is_not_handed_off():
    received = []

    def handler(pattern):
        received.append(pattern)

    manager = CandidatePatternManager(
        final_pattern_handler=handler,
    )

    result = manager.finalizePattern("missing-session")

    assert result is None
    assert received == []


def test_failed_handoff_does_not_corrupt_completed_pattern():
    def handler(pattern):
        raise RuntimeError("repository unavailable")

    manager = CandidatePatternManager(
        final_pattern_handler=handler,
    )

    manager.createPattern("session-1")

    manager.updatePattern(
        "session-1",
        {
            "operation_type": "CREATE",
            "timestamp": datetime(2026, 1, 1, 10, 0, 0),
        },
    )

    pattern = manager.finalizePattern("session-1")

    assert pattern is not None
    assert pattern.metadata.status == PatternStatus.COMPLETED
    assert pattern.metadata.complete is True
    assert pattern.observation_count() == 1


def test_handler_returning_false_is_failed_handoff():
    received = []

    def handler(pattern):
        received.append(pattern)
        return False

    manager = CandidatePatternManager(
        final_pattern_handler=handler,
    )

    manager.createPattern("session-1")

    manager.updatePattern(
        "session-1",
        {
            "operation_type": "CREATE",
            "timestamp": datetime(2026, 1, 1, 10, 0, 0),
        },
    )

    pattern = manager.finalizePattern("session-1")

    assert pattern is not None
    assert pattern.metadata.status == PatternStatus.COMPLETED
    assert len(received) == 1


def test_finalization_without_handler_still_succeeds():
    manager = CandidatePatternManager()

    manager.createPattern("session-1")

    manager.updatePattern(
        "session-1",
        {
            "operation_type": "CREATE",
            "timestamp": datetime(2026, 1, 1, 10, 0, 0),
        },
    )

    pattern = manager.finalizePattern("session-1")

    assert pattern is not None
    assert pattern.metadata.status == PatternStatus.COMPLETED


def test_manager_can_handoff_to_final_pattern_repository_adapter():
    from final_pattern_repository import FinalPatternRepository
    from final_pattern_repository_adapter import (
        FinalPatternRepositoryAdapter,
    )

    repository = FinalPatternRepository()

    adapter = FinalPatternRepositoryAdapter(
        repository=repository,
    )

    manager = CandidatePatternManager(
        final_pattern_handler=adapter.store,
    )

    manager.createPattern(
        session_id="session-001",
        user_id="user-001",
    )

    manager.updatePattern(
        "session-001",
        {
            "operation_type": "CREATE",
            "timestamp": datetime(2026, 9, 4, 10, 0, 0),
            "file_extension": ".py",
            "directory": "/project",
        },
    )

    finalized = manager.finalizePattern(
        "session-001"
    )

    assert finalized is not None
    assert repository.count() == 1
    assert repository.knowledge_count() == 1


def test_get_behavioral_summary_returns_current_state():
    manager = CandidatePatternManager()

    manager.createPattern(
        session_id="session-001",
        user_id="user-001",
    )

    first = {
        "operation_type": "CREATE",
        "timestamp": datetime(2026, 1, 1, 10, 0, 0),
    }

    second = {
        "operation_type": "MODIFY",
        "timestamp": datetime(2026, 1, 1, 10, 5, 0),
    }

    manager.updatePattern("session-001", first)
    manager.updatePattern("session-001", second)

    summary = manager.getBehavioralSummary(
        "session-001"
    )

    assert summary is not None
    assert summary["session_id"] == "session-001"
    assert summary["user_id"] == "user-001"
    assert summary["observation_count"] == 2

    assert (
        summary["operational_characteristics"]
        ["total_operations"]
        == 2
    )

    assert summary["sequential_characteristics"] == [
        {
            "operation_type": "CREATE",
            "timestamp": datetime(2026, 1, 1, 10, 0, 0),
        },
        {
            "operation_type": "MODIFY",
            "timestamp": datetime(2026, 1, 1, 10, 5, 0),
        },
    ]


def test_get_behavioral_summary_is_detached_from_active_pattern():
    manager = CandidatePatternManager()

    manager.createPattern(
        session_id="session-001",
    )

    observation = {
        "operation_type": "CREATE",
        "timestamp": datetime(2026, 1, 1, 10, 0, 0),
    }

    manager.updatePattern(
        "session-001",
        observation,
    )

    summary = manager.getBehavioralSummary(
        "session-001"
    )

    assert summary is not None

    summary["operational_characteristics"][
        "total_operations"
    ] = 999

    summary["sequential_characteristics"].clear()

    pattern = manager.getCurrentPattern(
        "session-001"
    )

    assert pattern is not None
    assert (
        pattern.operational_characteristics[
            "total_operations"
        ]
        == 1
    )

    assert pattern.sequential_characteristics == [
        {
            "operation_type": "CREATE",
            "timestamp": datetime(2026, 1, 1, 10, 0, 0),
        }
    ]


def test_get_pattern_metadata_reflects_current_lifecycle():
    manager = CandidatePatternManager()

    manager.createPattern(
        session_id="session-001",
    )

    metadata = manager.getPatternMetadata(
        "session-001"
    )

    assert metadata is not None
    assert metadata["status"] == PatternStatus.INITIALIZING
    assert metadata["observation_count"] == 0
    assert metadata["complete"] is False
    assert metadata["interrupted"] is False
    assert metadata["finalized_at"] is None

    manager.updatePattern(
        "session-001",
        {
            "operation_type": "CREATE",
            "timestamp": datetime(2026, 1, 1, 10, 0, 0),
        },
    )

    metadata = manager.getPatternMetadata(
        "session-001"
    )

    assert metadata is not None
    assert metadata["status"] == PatternStatus.LEARNING
    assert metadata["observation_count"] == 1
    assert metadata["complete"] is False


def test_get_evaluation_snapshot_is_read_only():
    manager = CandidatePatternManager()

    manager.createPattern(
        session_id="session-001",
        user_id="user-001",
    )

    observation = {
        "operation_type": "CREATE",
        "timestamp": datetime(2026, 1, 1, 10, 0, 0),
    }

    manager.updatePattern(
        "session-001",
        observation,
    )

    evaluation = manager.getEvaluationSnapshot(
        "session-001"
    )

    assert evaluation is not None
    assert evaluation["candidate_pattern"] is not (
        manager.getCurrentPattern("session-001")
    )

    assert evaluation["behavioral_summary"][
        "observation_count"
    ] == 1

    assert evaluation["pattern_metadata"][
        "status"
    ] == PatternStatus.LEARNING

    evaluation[
        "candidate_pattern"
    ].operational_characteristics["total_operations"] = 500

    evaluation[
        "behavioral_summary"
    ]["observation_count"] = 500

    evaluation[
        "pattern_metadata"
    ]["observation_count"] = 500

    current = manager.getCurrentPattern(
        "session-001"
    )

    assert current is not None

    assert (
        current.operational_characteristics[
            "total_operations"
        ]
        == 1
    )

    assert current.observation_count() == 1
    assert current.metadata.observation_count == 1


def test_read_only_outputs_return_none_for_unknown_session():
    manager = CandidatePatternManager()

    assert manager.getBehavioralSummary(
        "unknown-session"
    ) is None

    assert manager.getPatternMetadata(
        "unknown-session"
    ) is None

    assert manager.getEvaluationSnapshot(
        "unknown-session"
    ) is None


def test_temporal_characteristics_track_operation_intervals():
    manager = CandidatePatternManager()

    manager.createPattern(
        session_id="session-001",
    )

    timestamps = [
        datetime(2026, 1, 1, 10, 0, 0),
        datetime(2026, 1, 1, 10, 0, 2),
        datetime(2026, 1, 1, 10, 0, 5),
    ]

    for index, timestamp in enumerate(timestamps):
        manager.updatePattern(
            "session-001",
            {
                "operation_type": "MODIFY",
                "timestamp": timestamp,
            },
        )

    pattern = manager.getCurrentPattern(
        "session-001",
    )

    assert pattern is not None

    temporal = pattern.temporal_characteristics

    assert temporal["time_between_operations"] == [
        2.0,
        3.0,
    ]

    assert temporal["duration_seconds"] == 5.0


def test_temporal_characteristics_track_idle_intervals():
    manager = CandidatePatternManager()

    manager.createPattern(
        session_id="session-001",
    )

    manager.updatePattern(
        "session-001",
        {
            "operation_type": "CREATE",
            "timestamp": datetime(
                2026, 1, 1, 10, 0, 0
            ),
        },
    )

    manager.updatePattern(
        "session-001",
        {
            "operation_type": "MODIFY",
            "timestamp": datetime(
                2026, 1, 1, 10, 2, 0
            ),
            "idle_threshold_seconds": 60,
        },
    )

    pattern = manager.getCurrentPattern(
        "session-001",
    )

    assert pattern is not None

    temporal = pattern.temporal_characteristics

    assert temporal["idle_intervals"] == [
        120.0
    ]

    assert temporal["idle_time_seconds"] == 120.0


def test_temporal_characteristics_track_burst_activity():
    manager = CandidatePatternManager()

    manager.createPattern(
        session_id="session-001",
    )

    manager.updatePattern(
        "session-001",
        {
            "operation_type": "CREATE",
            "timestamp": datetime(
                2026, 1, 1, 10, 0, 0
            ),
        },
    )

    manager.updatePattern(
        "session-001",
        {
            "operation_type": "MODIFY",
            "timestamp": datetime(
                2026, 1, 1, 10, 0, 2
            ),
            "burst_threshold_seconds": 5,
        },
    )

    pattern = manager.getCurrentPattern(
        "session-001",
    )

    assert pattern is not None

    temporal = pattern.temporal_characteristics

    assert temporal["burst_count"] == 1
    assert temporal["burst_activity"] is True


def test_temporal_characteristics_track_continuous_activity():
    manager = CandidatePatternManager()

    manager.createPattern(
        session_id="session-001",
    )

    timestamps = [
        datetime(2026, 1, 1, 10, 0, 0),
        datetime(2026, 1, 1, 10, 0, 2),
        datetime(2026, 1, 1, 10, 0, 4),
    ]

    for timestamp in timestamps:
        manager.updatePattern(
            "session-001",
            {
                "operation_type": "MODIFY",
                "timestamp": timestamp,
                "idle_threshold_seconds": 60,
            },
        )

    pattern = manager.getCurrentPattern(
        "session-001",
    )

    assert pattern is not None

    assert (
        pattern.temporal_characteristics[
            "continuous_activity"
        ]
        is True
    )


def test_session_characteristics_track_density_and_complexity():
    manager = CandidatePatternManager()

    manager.createPattern(
        session_id="session-001",
    )

    manager.updatePattern(
        "session-001",
        {
            "operation_type": "CREATE",
            "timestamp": datetime(
                2026, 1, 1, 10, 0, 0
            ),
        },
    )

    manager.updatePattern(
        "session-001",
        {
            "operation_type": "MODIFY",
            "timestamp": datetime(
                2026, 1, 1, 10, 0, 10
            ),
        },
    )

    pattern = manager.getCurrentPattern(
        "session-001",
    )

    assert pattern is not None

    characteristics = pattern.session_characteristics

    assert characteristics["session_length_seconds"] == 10.0
    assert characteristics["operation_diversity"] == 2
    assert characteristics["behavioral_density"] == 0.2

    assert (
        characteristics["task_complexity"]
        ["operation_diversity"]
        == 2
    )


def test_operation_frequency_tracks_accumulated_counts():
    manager = CandidatePatternManager()

    manager.createPattern(
        session_id="session-001",
    )

    timestamps = [
        datetime(2026, 1, 1, 10, 0, 0),
        datetime(2026, 1, 1, 10, 0, 1),
        datetime(2026, 1, 1, 10, 0, 2),
        datetime(2026, 1, 1, 10, 0, 3),
    ]

    operations = [
        "CREATE",
        "CREATE",
        "MODIFY",
        "DELETE",
    ]

    for operation, timestamp in zip(
        operations,
        timestamps,
    ):
        manager.updatePattern(
            "session-001",
            {
                "operation_type": operation,
                "timestamp": timestamp,
            },
        )

    pattern = manager.getCurrentPattern(
        "session-001",
    )

    assert pattern is not None

    characteristics = (
        pattern.operational_characteristics
    )

    assert characteristics["operation_frequency"] == {
        "CREATE": 2,
        "MODIFY": 1,
        "DELETE": 1,
    }


def test_operation_distribution_is_normalized():
    manager = CandidatePatternManager()

    manager.createPattern(
        session_id="session-001",
    )

    observations = [
        {
            "operation_type": "CREATE",
            "timestamp": datetime(
                2026, 1, 1, 10, 0, 0
            ),
        },
        {
            "operation_type": "CREATE",
            "timestamp": datetime(
                2026, 1, 1, 10, 0, 1
            ),
        },
        {
            "operation_type": "MODIFY",
            "timestamp": datetime(
                2026, 1, 1, 10, 0, 2
            ),
        },
        {
            "operation_type": "DELETE",
            "timestamp": datetime(
                2026, 1, 1, 10, 0, 3
            ),
        },
    ]

    for observation in observations:
        manager.updatePattern(
            "session-001",
            observation,
        )

    pattern = manager.getCurrentPattern(
        "session-001",
    )

    assert pattern is not None

    distribution = (
        pattern.operational_characteristics[
            "operation_distribution"
        ]
    )

    assert distribution["CREATE"] == 0.5
    assert distribution["MODIFY"] == 0.25
    assert distribution["DELETE"] == 0.25

    assert sum(distribution.values()) == 1.0


def test_operation_distribution_evolves_with_new_behavior():
    manager = CandidatePatternManager()

    manager.createPattern(
        session_id="session-001",
    )

    manager.updatePattern(
        "session-001",
        {
            "operation_type": "CREATE",
            "timestamp": datetime(
                2026, 1, 1, 10, 0, 0
            ),
        },
    )

    pattern = manager.getCurrentPattern(
        "session-001",
    )

    assert pattern is not None

    first_distribution = (
        pattern.operational_characteristics[
            "operation_distribution"
        ].copy()
    )

    assert first_distribution == {
        "CREATE": 1.0
    }

    manager.updatePattern(
        "session-001",
        {
            "operation_type": "MODIFY",
            "timestamp": datetime(
                2026, 1, 1, 10, 0, 1
            ),
        },
    )

    second_distribution = (
        pattern.operational_characteristics[
            "operation_distribution"
        ]
    )

    assert second_distribution == {
        "CREATE": 0.5,
        "MODIFY": 0.5,
    }

    assert "CREATE" in second_distribution
    assert "MODIFY" in second_distribution


def test_duplicate_observation_does_not_change_operation_distribution():
    manager = CandidatePatternManager()

    manager.createPattern(
        session_id="session-001",
    )

    observation = {
        "operation_type": "CREATE",
        "timestamp": datetime(
            2026, 1, 1, 10, 0, 0
        ),
    }

    manager.updatePattern(
        "session-001",
        observation,
    )

    manager.updatePattern(
        "session-001",
        observation,
    )

    pattern = manager.getCurrentPattern(
        "session-001",
    )

    assert pattern is not None

    characteristics = (
        pattern.operational_characteristics
    )

    assert characteristics["total_operations"] == 1

    assert characteristics["operation_frequency"] == {
        "CREATE": 1,
    }

    assert characteristics["operation_distribution"] == {
        "CREATE": 1.0,
    }


def test_context_refinement_preserves_previous_value():
    manager = CandidatePatternManager()

    manager.createPattern(
        session_id="session-001",
    )

    manager.updatePattern(
        "session-001",
        {
            "operation_type": "CREATE",
            "timestamp": datetime(
                2026, 1, 1, 10, 0, 0
            ),
        },
        context={
            "session_intensity": "LOW",
        },
    )

    manager.updatePattern(
        "session-001",
        {
            "operation_type": "MODIFY",
            "timestamp": datetime(
                2026, 1, 1, 10, 0, 1
            ),
        },
        context={
            "session_intensity": "HIGH",
        },
    )

    pattern = manager.getCurrentPattern(
        "session-001",
    )

    assert pattern is not None

    assert (
        pattern.context.values[
            "session_intensity"
        ]
        == "HIGH"
    )

    assert (
        pattern.context.values[
            "session_intensity__history"
        ]
        == [
            {
                "value": "LOW",
                "superseded_by": "HIGH",
            },
            {
                "value": "HIGH",
                "superseded_by": None,
            },
        ]
    )


def test_context_refinement_tracks_repeated_same_value():
    manager = CandidatePatternManager()

    manager.createPattern(
        session_id="session-001",
    )

    timestamps = [
        datetime(2026, 1, 1, 10, 0, 0),
        datetime(2026, 1, 1, 10, 0, 1),
        datetime(2026, 1, 1, 10, 0, 2),
    ]

    for timestamp in timestamps:
        manager.updatePattern(
            "session-001",
            {
                "operation_type": "MODIFY",
                "timestamp": timestamp,
            },
            context={
                "working_directory": "/project",
            },
        )

    pattern = manager.getCurrentPattern(
        "session-001",
    )

    assert pattern is not None

    assert (
        pattern.context.values[
            "working_directory"
        ]
        == "/project"
    )

    assert (
        pattern.context.values[
            "working_directory__observation_count"
        ]
        == 3
    )


def test_context_refinement_preserves_multiple_dimensions():
    manager = CandidatePatternManager()

    manager.createPattern(
        session_id="session-001",
    )

    manager.updatePattern(
        "session-001",
        {
            "operation_type": "CREATE",
            "timestamp": datetime(
                2026, 1, 1, 10, 0, 0
            ),
        },
        context={
            "working_directory": "/project",
            "active_application": "editor",
        },
    )

    manager.updatePattern(
        "session-001",
        {
            "operation_type": "MODIFY",
            "timestamp": datetime(
                2026, 1, 1, 10, 0, 1
            ),
        },
        context={
            "working_directory": "/project/src",
            "active_application": "terminal",
        },
    )

    pattern = manager.getCurrentPattern(
        "session-001",
    )

    assert pattern is not None

    characteristics = (
        pattern.contextual_characteristics
    )

    assert (
        characteristics["working_directory"]
        == "/project/src"
    )

    assert (
        characteristics["active_application"]
        == "terminal"
    )

    assert pattern.context.values[
        "working_directory__history"
    ] == [
        {
            "value": "/project",
            "superseded_by": "/project/src",
        },
        {
            "value": "/project/src",
            "superseded_by": None,
        },
    ]

    assert pattern.context.values[
        "active_application__history"
    ] == [
        {
            "value": "editor",
            "superseded_by": "terminal",
        },
        {
            "value": "terminal",
            "superseded_by": None,
        },
    ]


def test_context_refinement_rolls_back_without_losing_history():
    manager = CandidatePatternManager()

    pattern = manager.createPattern(
        session_id="session-001",
    )

    manager.updatePattern(
        "session-001",
        {
            "operation_type": "CREATE",
            "timestamp": datetime(
                2026, 1, 1, 10, 0, 0
            ),
        },
        context={
            "session_intensity": "LOW",
        },
    )

    original_context = copy.deepcopy(
        pattern.context.values
    )

    original_contextual = copy.deepcopy(
        pattern.contextual_characteristics
    )

    def failing_relationship_update(*args, **kwargs):
        raise RuntimeError(
            "simulated refinement failure"
        )

    manager._update_relationship_characteristics = (
        failing_relationship_update
    )

    manager.updatePattern(
        "session-001",
        {
            "operation_type": "MODIFY",
            "timestamp": datetime(
                2026, 1, 1, 10, 0, 1
            ),
        },
        context={
            "session_intensity": "HIGH",
        },
        relationships=[
            {
                "type": "related_file",
                "target": "important.txt",
            }
        ],
    )

    assert pattern.context.values == original_context

    assert (
        pattern.contextual_characteristics
        == original_contextual
    )


def test_complete_session_records_end_time_and_duration():
    manager = CandidatePatternManager()

    start_time = datetime(
        2026, 1, 1, 10, 0, 0
    )

    end_time = datetime(
        2026, 1, 1, 10, 5, 30
    )

    pattern = manager.createPattern(
        "session-1",
        user_id="user-1",
        session_start_time=start_time,
    )

    completed = manager.completeSession(
        "session-1",
        end_time,
    )

    assert completed is pattern

    assert (
        pattern.session_end_time
        == end_time
    )

    assert (
        pattern.session_duration_seconds
        == 330.0
    )

    assert (
        pattern.temporal_characteristics[
            "session_end_time"
        ]
        == end_time
    )

    assert (
        pattern.session_characteristics[
            "session_length_seconds"
        ]
        == 330.0
    )


def test_finalize_pattern_auto_completes_session():
    manager = CandidatePatternManager()

    start_time = datetime(
        2026, 1, 1, 10, 0, 0
    )

    manager.createPattern(
        "session-1",
        session_start_time=start_time,
    )

    manager.updatePattern(
        "session-1",
        {
            "operation_type": "CREATE",
            "timestamp": datetime(
                2026, 1, 1, 10, 0, 1
            ),
        },
    )

    finalized = manager.finalizePattern(
        "session-1"
    )

    assert finalized is not None
    assert finalized.session_end_time is not None
    assert finalized.session_duration_seconds is not None
    assert finalized.metadata.status == PatternStatus.COMPLETED


def test_complete_session_rejects_end_before_session_start():
    manager = CandidatePatternManager()

    start_time = datetime(
        2026, 1, 1, 10, 0, 0
    )

    invalid_end_time = datetime(
        2026, 1, 1, 9, 59, 59
    )

    pattern = manager.createPattern(
        "session-1",
        session_start_time=start_time,
    )

    completed = manager.completeSession(
        "session-1",
        invalid_end_time,
    )

    assert completed is pattern

    assert pattern.session_end_time is None

    assert (
        pattern.session_duration_seconds
        is None
    )


def test_finalize_after_session_completion():
    manager = CandidatePatternManager()

    start_time = datetime(
        2026, 1, 1, 10, 0, 0
    )

    end_time = datetime(
        2026, 1, 1, 10, 1, 0
    )

    manager.createPattern(
        "session-1",
        session_start_time=start_time,
    )

    manager.updatePattern(
        "session-1",
        {
            "operation_type": "CREATE",
            "timestamp": datetime(
                2026, 1, 1, 10, 0, 1
            ),
        },
    )

    manager.completeSession(
        "session-1",
        end_time,
    )

    finalized = manager.finalizePattern(
        "session-1"
    )

    assert finalized is not None

    assert finalized.session_end_time == end_time

    assert (
        finalized.session_duration_seconds
        == 60.0
    )

    assert (
        finalized.metadata.status
        == PatternStatus.COMPLETED
    )


def test_behavioral_summary_includes_session_information():
    manager = CandidatePatternManager()

    start_time = datetime(
        2026, 1, 1, 10, 0, 0
    )

    end_time = datetime(
        2026, 1, 1, 10, 2, 0
    )

    manager.createPattern(
        "session-1",
        user_id="user-1",
        session_start_time=start_time,
    )

    manager.updatePattern(
        "session-1",
        {
            "operation_type": "CREATE",
            "timestamp": datetime(
                2026, 1, 1, 10, 0, 1
            ),
        },
    )

    manager.completeSession(
        "session-1",
        end_time,
    )

    summary = manager.getBehavioralSummary(
        "session-1"
    )

    assert summary is not None

    assert (
        summary["session_start_time"]
        == start_time
    )

    assert (
        summary["session_end_time"]
        == end_time
    )

    assert (
        summary["session_duration_seconds"]
        == 120.0
    )


def test_pattern_metadata_includes_session_information():
    manager = CandidatePatternManager()

    start_time = datetime(
        2026, 1, 1, 10, 0, 0
    )

    end_time = datetime(
        2026, 1, 1, 10, 3, 0
    )

    manager.createPattern(
        "session-1",
        session_start_time=start_time,
    )

    manager.updatePattern(
        "session-1",
        {
            "operation_type": "MODIFY",
            "timestamp": datetime(
                2026, 1, 1, 10, 0, 1
            ),
        },
    )

    manager.completeSession(
        "session-1",
        end_time,
    )

    metadata = manager.getPatternMetadata(
        "session-1"
    )

    assert metadata is not None

    assert (
        metadata["session_start_time"]
        == start_time
    )

    assert (
        metadata["session_end_time"]
        == end_time
    )

    assert (
        metadata["session_duration_seconds"]
        == 180.0
    )


def test_pattern_snapshot_contains_session_completion_state():
    manager = CandidatePatternManager()

    start_time = datetime(
        2026, 1, 1, 10, 0, 0
    )

    end_time = datetime(
        2026, 1, 1, 10, 4, 0
    )

    manager.createPattern(
        "session-1",
        session_start_time=start_time,
    )

    manager.updatePattern(
        "session-1",
        {
            "operation_type": "CREATE",
            "timestamp": datetime(
                2026, 1, 1, 10, 0, 1
            ),
        },
    )

    manager.completeSession(
        "session-1",
        end_time,
    )

    snapshot = manager.getPatternSnapshot(
        "session-1"
    )

    assert snapshot is not None

    assert (
        snapshot.session_start_time
        == start_time
    )

    assert (
        snapshot.session_end_time
        == end_time
    )

    assert (
        snapshot.session_duration_seconds
        == 240.0
    )


def test_behavioral_signal_is_accepted():
    manager = CandidatePatternManager()

    manager.createPattern("session-1")

    observation = {
        "operation_type": "CREATE",
        "timestamp": datetime(
            2026, 1, 1, 10, 0, 0
        ),
    }

    pattern = manager.updatePattern(
        "session-1",
        observation,
    )

    assert pattern is not None
    assert pattern.observation_count() == 1


def test_raw_filesystem_event_is_rejected():
    manager = CandidatePatternManager()

    manager.createPattern("session-1")

    observation = {
        "event_type": "deleted",
        "path": "/workspace/secret.txt",
        "timestamp": datetime(
            2026, 1, 1, 10, 0, 0
        ),
    }

    pattern = manager.updatePattern(
        "session-1",
        observation,
    )

    assert pattern is not None
    assert pattern.observation_count() == 0


def test_signal_without_operation_type_is_accepted():
    manager = CandidatePatternManager()

    manager.createPattern("session-1")

    observation = {
        "timestamp": datetime(
            2026, 1, 1, 10, 0, 0
        ),
        "signal": "HIGH_ACTIVITY",
    }

    pattern = manager.updatePattern(
        "session-1",
        observation,
    )

    assert pattern is not None
    assert pattern.observation_count() == 1


def test_alternate_behavioral_signal_is_accepted():
    manager = CandidatePatternManager()

    manager.createPattern("session-1")

    observation = {
        "behavior_type": "rapid_modification",
        "timestamp": datetime(
            2026, 1, 1, 10, 0, 0
        ),
    }

    pattern = manager.updatePattern(
        "session-1",
        observation,
    )

    assert pattern is not None
    assert pattern.observation_count() == 1


def test_create_pattern_rejects_empty_session_id():
    manager = CandidatePatternManager()

    with pytest.raises(ValueError):
        manager.createPattern("")


def test_create_pattern_rejects_whitespace_session_id():
    manager = CandidatePatternManager()

    with pytest.raises(ValueError):
        manager.createPattern("   ")


def test_create_pattern_rejects_non_string_session_id():
    manager = CandidatePatternManager()

    with pytest.raises(ValueError):
        manager.createPattern(123)


def test_valid_session_id_creates_candidate_pattern():
    manager = CandidatePatternManager()

    pattern = manager.createPattern(
        "session-001"
    )

    assert pattern is not None
    assert pattern.session_id == "session-001"


def test_invalid_session_lookup_returns_none():
    manager = CandidatePatternManager()

    manager.createPattern(
        "session-001"
    )

    result = manager.getCurrentPattern("")

    assert result is None

    assert (
        manager.getCurrentPattern(
            "session-001"
        )
        is not None
    )


def test_begin_evaluation_changes_status():
    manager = CandidatePatternManager()

    manager.createPattern("session-1")

    manager.updatePattern(
        "session-1",
        {
            "operation_type": "CREATE",
            "timestamp": datetime(
                2026, 1, 1, 10, 0, 0
            ),
        },
    )

    pattern = manager.beginEvaluation(
        "session-1"
    )

    assert pattern is not None

    assert (
        pattern.metadata.status
        == PatternStatus.EVALUATING
    )


def test_resume_learning_restores_learning_status():
    manager = CandidatePatternManager()

    manager.createPattern("session-1")

    manager.updatePattern(
        "session-1",
        {
            "operation_type": "CREATE",
            "timestamp": datetime(
                2026, 1, 1, 10, 0, 0
            ),
        },
    )

    manager.beginEvaluation("session-1")

    pattern = manager.resumeLearning(
        "session-1"
    )

    assert pattern is not None

    assert (
        pattern.metadata.status
        == PatternStatus.LEARNING
    )


def test_new_observation_during_evaluation_returns_to_learning():
    manager = CandidatePatternManager()

    manager.createPattern("session-1")

    manager.updatePattern(
        "session-1",
        {
            "operation_type": "CREATE",
            "timestamp": datetime(
                2026, 1, 1, 10, 0, 0
            ),
        },
    )

    manager.beginEvaluation("session-1")

    pattern = manager.updatePattern(
        "session-1",
        {
            "operation_type": "MODIFY",
            "timestamp": datetime(
                2026, 1, 1, 10, 0, 1
            ),
        },
    )

    assert pattern is not None

    assert (
        pattern.metadata.status
        == PatternStatus.LEARNING
    )

    assert (
        pattern.observation_count()
        == 2
    )


def test_empty_pattern_cannot_begin_evaluation():
    manager = CandidatePatternManager()

    manager.createPattern("session-1")

    pattern = manager.beginEvaluation(
        "session-1"
    )

    assert pattern is not None

    assert (
        pattern.metadata.status
        == PatternStatus.INITIALIZING
    )


def test_completed_pattern_cannot_begin_evaluation():
    manager = CandidatePatternManager()

    manager.createPattern("session-1")

    manager.updatePattern(
        "session-1",
        {
            "operation_type": "CREATE",
            "timestamp": datetime(
                2026, 1, 1, 10, 0, 0
            ),
        },
    )

    manager.finalizePattern("session-1")

    pattern = manager.beginEvaluation(
        "session-1"
    )

    assert pattern is not None

    assert (
        pattern.metadata.status
        == PatternStatus.COMPLETED
    )


def test_candidate_patterns_are_isolated_between_sessions():
    manager = CandidatePatternManager()

    pattern_a = manager.createPattern(
        "session-a",
        user_id="user-a",
    )

    pattern_b = manager.createPattern(
        "session-b",
        user_id="user-b",
    )

    manager.updatePattern(
        "session-a",
        {
            "operation_type": "CREATE",
            "timestamp": datetime(
                2026, 1, 1, 10, 0, 0
            ),
        },
        context={
            "directory": "/project-a",
        },
    )

    manager.updatePattern(
        "session-b",
        {
            "operation_type": "DELETE",
            "timestamp": datetime(
                2026, 1, 1, 11, 0, 0
            ),
        },
        context={
            "directory": "/project-b",
        },
    )

    assert pattern_a is not pattern_b

    assert pattern_a.session_id == "session-a"
    assert pattern_b.session_id == "session-b"

    assert pattern_a.user_id == "user-a"
    assert pattern_b.user_id == "user-b"

    assert pattern_a.observation_count() == 1
    assert pattern_b.observation_count() == 1

    assert (
        pattern_a.operational_characteristics[
            "operation_counts"
        ]["CREATE"]
        == 1
    )

    assert (
        pattern_b.operational_characteristics[
            "operation_counts"
        ]["DELETE"]
        == 1
    )

    assert (
        pattern_a.contextual_characteristics[
            "directory"
        ]
        == "/project-a"
    )

    assert (
        pattern_b.contextual_characteristics[
            "directory"
        ]
        == "/project-b"
    )


def test_session_lookup_returns_only_its_own_candidate_pattern():
    manager = CandidatePatternManager()

    pattern_a = manager.createPattern(
        "session-a",
    )

    pattern_b = manager.createPattern(
        "session-b",
    )

    assert (
        manager.getCurrentPattern("session-a")
        is pattern_a
    )

    assert (
        manager.getCurrentPattern("session-b")
        is pattern_b
    )

    assert (
        manager.getCurrentPattern("session-a")
        is not pattern_b
    )

    assert (
        manager.getCurrentPattern("session-b")
        is not pattern_a
    )


def test_reset_is_isolated_to_one_session():
    manager = CandidatePatternManager()

    pattern_a = manager.createPattern(
        "session-a",
    )

    pattern_b = manager.createPattern(
        "session-b",
    )

    removed = manager.resetPattern(
        "session-a",
    )

    assert removed is pattern_a

    assert (
        manager.getCurrentPattern("session-a")
        is None
    )

    assert (
        manager.getCurrentPattern("session-b")
        is pattern_b
    )


def test_finalization_is_isolated_between_sessions():
    manager = CandidatePatternManager()

    manager.createPattern(
        "session-a",
    )

    manager.createPattern(
        "session-b",
    )

    manager.updatePattern(
        "session-a",
        {
            "operation_type": "CREATE",
            "timestamp": datetime(
                2026, 1, 1, 10, 0, 0
            ),
        },
    )

    manager.updatePattern(
        "session-b",
        {
            "operation_type": "MODIFY",
            "timestamp": datetime(
                2026, 1, 1, 11, 0, 0
            ),
        },
    )

    finalized = manager.finalizePattern(
        "session-a",
    )

    assert finalized is not None

    assert (
        finalized.metadata.status
        == PatternStatus.COMPLETED
    )

    other = manager.getCurrentPattern(
        "session-b",
    )

    assert other is not None

    assert (
        other.metadata.status
        != PatternStatus.COMPLETED
    )

    assert other.observation_count() == 1


def test_lifecycle_initializing_to_learning():
    manager = CandidatePatternManager()

    pattern = manager.createPattern(
        session_id="session-lifecycle-001",
    )

    assert pattern.metadata.status == PatternStatus.INITIALIZING

    observation = {
        "operation_type": "CREATE",
        "timestamp": datetime.now(),
    }

    updated = manager.updatePattern(
        "session-lifecycle-001",
        observation,
    )

    assert updated is pattern
    assert pattern.metadata.status == PatternStatus.LEARNING


def test_lifecycle_learning_to_evaluating():
    manager = CandidatePatternManager()

    pattern = manager.createPattern(
        session_id="session-lifecycle-002",
    )

    observation = {
        "operation_type": "CREATE",
        "timestamp": datetime.now(),
    }

    manager.updatePattern(
        "session-lifecycle-002",
        observation,
    )

    evaluated = manager.beginEvaluation(
        "session-lifecycle-002",
    )

    assert evaluated is pattern
    assert pattern.metadata.status == PatternStatus.EVALUATING


def test_lifecycle_evaluating_to_learning():
    manager = CandidatePatternManager()

    pattern = manager.createPattern(
        session_id="session-lifecycle-003",
    )

    observation = {
        "operation_type": "MODIFY",
        "timestamp": datetime.now(),
    }

    manager.updatePattern(
        "session-lifecycle-003",
        observation,
    )

    manager.beginEvaluation(
        "session-lifecycle-003",
    )

    resumed = manager.resumeLearning(
        "session-lifecycle-003",
    )

    assert resumed is pattern
    assert pattern.metadata.status == PatternStatus.LEARNING


def test_update_after_evaluation_returns_pattern_to_learning():
    manager = CandidatePatternManager()

    pattern = manager.createPattern(
        session_id="session-lifecycle-004",
    )

    first = {
        "operation_type": "CREATE",
        "timestamp": datetime.now(),
    }

    manager.updatePattern(
        "session-lifecycle-004",
        first,
    )

    manager.beginEvaluation(
        "session-lifecycle-004",
    )

    assert pattern.metadata.status == PatternStatus.EVALUATING

    second = {
        "operation_type": "MODIFY",
        "timestamp": datetime.now(),
    }

    updated = manager.updatePattern(
        "session-lifecycle-004",
        second,
    )

    assert updated is pattern
    assert pattern.observation_count() == 2
    assert pattern.metadata.status == PatternStatus.LEARNING


def test_empty_pattern_cannot_enter_evaluation():
    manager = CandidatePatternManager()

    pattern = manager.createPattern(
        session_id="session-lifecycle-005",
    )

    result = manager.beginEvaluation(
        "session-lifecycle-005",
    )

    assert result is pattern
    assert pattern.metadata.status == PatternStatus.INITIALIZING


def test_interrupted_pattern_cannot_resume_learning():
    manager = CandidatePatternManager()

    pattern = manager.createPattern(
        session_id="session-lifecycle-006",
    )

    observation = {
        "operation_type": "CREATE",
        "timestamp": datetime.now(),
    }

    manager.updatePattern(
        "session-lifecycle-006",
        observation,
    )

    manager.freezePattern(
        "session-lifecycle-006",
    )

    result = manager.resumeLearning(
        "session-lifecycle-006",
    )

    assert result is pattern
    assert pattern.metadata.interrupted is True
    assert pattern.metadata.status == PatternStatus.LEARNING


def test_interrupted_pattern_cannot_enter_evaluation():
    manager = CandidatePatternManager()

    pattern = manager.createPattern(
        session_id="session-lifecycle-007",
    )

    observation = {
        "operation_type": "MODIFY",
        "timestamp": datetime.now(),
    }

    manager.updatePattern(
        "session-lifecycle-007",
        observation,
    )

    manager.freezePattern(
        "session-lifecycle-007",
    )

    result = manager.beginEvaluation(
        "session-lifecycle-007",
    )

    assert result is pattern
    assert pattern.metadata.interrupted is True
    assert pattern.metadata.status == PatternStatus.LEARNING


def test_interrupted_pattern_cannot_complete():
    manager = CandidatePatternManager()

    start_time = datetime(2026, 1, 1, 10, 0, 0)

    pattern = manager.createPattern(
        session_id="session-lifecycle-008",
        session_start_time=start_time,
    )

    observation = {
        "operation_type": "CREATE",
        "timestamp": start_time,
    }

    manager.updatePattern(
        "session-lifecycle-008",
        observation,
    )

    manager.freezePattern(
        "session-lifecycle-008",
    )

    result = manager.completeSession(
        "session-lifecycle-008",
        datetime(2026, 1, 1, 11, 0, 0),
    )

    assert result is pattern
    assert pattern.metadata.interrupted is True
    assert pattern.metadata.complete is False
    assert pattern.session_end_time is None
    assert pattern.session_duration_seconds is None


def test_interrupted_pattern_cannot_finalize():
    manager = CandidatePatternManager()

    start_time = datetime(2026, 1, 1, 10, 0, 0)

    pattern = manager.createPattern(
        session_id="session-lifecycle-009",
        session_start_time=start_time,
    )

    observation = {
        "operation_type": "DELETE",
        "timestamp": start_time,
    }

    manager.updatePattern(
        "session-lifecycle-009",
        observation,
    )

    manager.freezePattern(
        "session-lifecycle-009",
    )

    result = manager.finalizePattern(
        "session-lifecycle-009",
    )

    assert result is None
    assert pattern.metadata.interrupted is True
    assert pattern.metadata.complete is False
    assert pattern.metadata.status != PatternStatus.COMPLETED


def test_completed_pattern_cannot_return_to_learning():
    manager = CandidatePatternManager()

    pattern = manager.createPattern(
        session_id="session-lifecycle-010",
    )

    observation = {
        "operation_type": "CREATE",
        "timestamp": datetime.now(),
    }

    manager.updatePattern(
        "session-lifecycle-010",
        observation,
    )

    manager.finalizePattern(
        "session-lifecycle-010",
    )

    assert pattern.metadata.status == PatternStatus.COMPLETED

    result = manager.resumeLearning(
        "session-lifecycle-010",
    )

    assert result is pattern
    assert pattern.metadata.status == PatternStatus.COMPLETED


def test_completed_pattern_cannot_reenter_evaluation():
    manager = CandidatePatternManager()

    pattern = manager.createPattern(
        session_id="session-lifecycle-011",
    )

    observation = {
        "operation_type": "CREATE",
        "timestamp": datetime.now(),
    }

    manager.updatePattern(
        "session-lifecycle-011",
        observation,
    )

    manager.finalizePattern(
        "session-lifecycle-011",
    )

    assert pattern.metadata.status == PatternStatus.COMPLETED

    result = manager.beginEvaluation(
        "session-lifecycle-011",
    )

    assert result is pattern
    assert pattern.metadata.status == PatternStatus.COMPLETED


def test_completed_pattern_does_not_accept_new_observations():
    manager = CandidatePatternManager()

    pattern = manager.createPattern(
        session_id="session-lifecycle-012",
    )

    first = {
        "operation_type": "CREATE",
        "timestamp": datetime.now(),
    }

    manager.updatePattern(
        "session-lifecycle-012",
        first,
    )

    manager.finalizePattern(
        "session-lifecycle-012",
    )

    second = {
        "operation_type": "MODIFY",
        "timestamp": datetime.now(),
    }

    result = manager.updatePattern(
        "session-lifecycle-012",
        second,
    )

    assert result is pattern
    assert pattern.observation_count() == 1
    assert pattern.timeline.observations == [first]


def test_freeze_preserves_latest_valid_state_after_evaluation():
    manager = CandidatePatternManager()

    pattern = manager.createPattern(
        session_id="session-lifecycle-013",
    )

    first = {
        "operation_type": "CREATE",
        "timestamp": datetime.now(),
    }

    manager.updatePattern(
        "session-lifecycle-013",
        first,
    )

    manager.beginEvaluation(
        "session-lifecycle-013",
    )

    manager.resumeLearning(
        "session-lifecycle-013",
    )

    second = {
        "operation_type": "MODIFY",
        "timestamp": datetime.now(),
    }

    manager.updatePattern(
        "session-lifecycle-013",
        second,
    )

    manager.freezePattern(
        "session-lifecycle-013",
    )

    assert pattern.observation_count() == 2
    assert pattern.timeline.observations == [
        first,
        second,
    ]
    assert pattern.metadata.interrupted is True
    assert pattern.metadata.complete is False


def test_pattern_snapshot_is_detached():
    manager = CandidatePatternManager()

    pattern = manager.createPattern(
        session_id="session-readonly-001",
        user_id="user-001",
    )

    observation = {
        "operation_type": "CREATE",
        "timestamp": datetime.now(),
    }

    manager.updatePattern(
        "session-readonly-001",
        observation,
        context={
            "working_directory": "/project",
        },
    )

    snapshot = manager.getPatternSnapshot(
        "session-readonly-001",
    )

    assert snapshot is not None
    assert snapshot is not pattern

    snapshot.timeline.observations.append(
        {
            "operation_type": "DELETE",
            "timestamp": datetime.now(),
        }
    )

    snapshot.context.values["working_directory"] = (
        "/modified"
    )

    assert pattern.observation_count() == 1
    assert (
        pattern.context.values["working_directory"]
        == "/project"
    )


def test_behavioral_summary_is_detached():
    manager = CandidatePatternManager()

    pattern = manager.createPattern(
        session_id="session-readonly-002",
    )

    observation = {
        "operation_type": "CREATE",
        "timestamp": datetime.now(),
    }

    manager.updatePattern(
        "session-readonly-002",
        observation,
        context={
            "working_directory": "/project",
        },
    )

    summary = manager.getBehavioralSummary(
        "session-readonly-002",
    )

    assert summary is not None

    summary["operational_characteristics"][
        "total_operations"
    ] = 999

    summary["contextual_characteristics"][
        "working_directory"
    ] = "/modified"

    assert (
        pattern.operational_characteristics[
            "total_operations"
        ]
        == 1
    )

    assert (
        pattern.contextual_characteristics[
            "working_directory"
        ]
        == "/project"
    )


def test_behavioral_summary_nested_data_is_detached():
    manager = CandidatePatternManager()

    pattern = manager.createPattern(
        session_id="session-readonly-003",
    )

    first = {
        "operation_type": "CREATE",
        "timestamp": datetime.now(),
    }

    second = {
        "operation_type": "MODIFY",
        "timestamp": datetime.now(),
    }

    manager.updatePattern(
        "session-readonly-003",
        first,
    )

    manager.updatePattern(
        "session-readonly-003",
        second,
    )

    summary = manager.getBehavioralSummary(
        "session-readonly-003",
    )

    assert summary is not None

    summary["sequential_characteristics"].clear()

    summary["temporal_characteristics"][
        "time_between_operations"
    ].clear()

    assert len(pattern.sequential_characteristics) == 2
    assert len(
        pattern.temporal_characteristics[
            "time_between_operations"
        ]
    ) == 1


def test_pattern_metadata_is_detached():
    manager = CandidatePatternManager()

    pattern = manager.createPattern(
        session_id="session-readonly-004",
    )

    observation = {
        "operation_type": "CREATE",
        "timestamp": datetime.now(),
    }

    manager.updatePattern(
        "session-readonly-004",
        observation,
    )

    metadata = manager.getPatternMetadata(
        "session-readonly-004",
    )

    assert metadata is not None

    metadata["observation_count"] = 999
    metadata["complete"] = True
    metadata["interrupted"] = True
    metadata["status"] = PatternStatus.COMPLETED

    assert pattern.metadata.observation_count == 1
    assert pattern.metadata.complete is False
    assert pattern.metadata.interrupted is False
    assert pattern.metadata.status == PatternStatus.LEARNING


def test_evaluation_snapshot_is_detached():
    manager = CandidatePatternManager()

    pattern = manager.createPattern(
        session_id="session-readonly-005",
        user_id="user-001",
    )

    observation = {
        "operation_type": "CREATE",
        "timestamp": datetime.now(),
    }

    manager.updatePattern(
        "session-readonly-005",
        observation,
        context={
            "working_directory": "/project",
        },
    )

    evaluation = manager.getEvaluationSnapshot(
        "session-readonly-005",
    )

    assert evaluation is not None

    candidate_snapshot = evaluation[
        "candidate_pattern"
    ]

    behavioral_summary = evaluation[
        "behavioral_summary"
    ]

    pattern_metadata = evaluation[
        "pattern_metadata"
    ]

    assert candidate_snapshot is not pattern
    assert behavioral_summary is not None
    assert pattern_metadata is not None

    candidate_snapshot.timeline.observations.clear()

    candidate_snapshot.context.values[
        "working_directory"
    ] = "/modified"

    behavioral_summary[
        "operational_characteristics"
    ]["total_operations"] = 999

    pattern_metadata["observation_count"] = 999
    pattern_metadata["complete"] = True

    assert pattern.observation_count() == 1

    assert (
        pattern.context.values[
            "working_directory"
        ]
        == "/project"
    )

    assert (
        pattern.operational_characteristics[
            "total_operations"
        ]
        == 1
    )

    assert pattern.metadata.observation_count == 1
    assert pattern.metadata.complete is False


def test_snapshot_read_does_not_change_active_pattern_status():
    manager = CandidatePatternManager()

    pattern = manager.createPattern(
        session_id="session-readonly-006",
    )

    observation = {
        "operation_type": "MODIFY",
        "timestamp": datetime.now(),
    }

    manager.updatePattern(
        "session-readonly-006",
        observation,
    )

    original_status = pattern.metadata.status

    snapshot = manager.getEvaluationSnapshot(
        "session-readonly-006",
    )

    assert snapshot is not None

    snapshot["candidate_pattern"].metadata.status = (
        PatternStatus.COMPLETED
    )

    assert pattern.metadata.status == original_status
    assert pattern.metadata.status == PatternStatus.LEARNING


def test_missing_pattern_returns_none_for_all_read_views():
    manager = CandidatePatternManager()

    session_id = "unknown-readonly-session"

    assert manager.getPatternSnapshot(session_id) is None
    assert manager.getBehavioralSummary(session_id) is None
    assert manager.getPatternMetadata(session_id) is None
    assert manager.getEvaluationSnapshot(session_id) is None


def test_duplicate_signal_does_not_change_operational_state():
    manager = CandidatePatternManager()

    pattern = manager.createPattern(
        session_id="session-integrity-001",
    )

    timestamp = datetime.now()

    observation = {
        "operation_type": "CREATE",
        "timestamp": timestamp,
    }

    manager.updatePattern(
        "session-integrity-001",
        observation,
    )

    original_operational = copy.deepcopy(
        pattern.operational_characteristics
    )
    original_temporal = copy.deepcopy(
        pattern.temporal_characteristics
    )
    original_sequential = copy.deepcopy(
        pattern.sequential_characteristics
    )
    original_session = copy.deepcopy(
        pattern.session_characteristics
    )

    manager.updatePattern(
        "session-integrity-001",
        observation,
    )

    assert pattern.observation_count() == 1
    assert (
        pattern.operational_characteristics
        == original_operational
    )
    assert (
        pattern.temporal_characteristics
        == original_temporal
    )
    assert (
        pattern.sequential_characteristics
        == original_sequential
    )
    assert (
        pattern.session_characteristics
        == original_session
    )


def test_duplicate_signal_does_not_create_duplicate_sequence_entry():
    manager = CandidatePatternManager()

    pattern = manager.createPattern(
        session_id="session-integrity-002",
    )

    timestamp = datetime.now()

    observation = {
        "operation_type": "MODIFY",
        "timestamp": timestamp,
    }

    manager.updatePattern(
        "session-integrity-002",
        observation,
    )

    manager.updatePattern(
        "session-integrity-002",
        observation,
    )

    assert len(pattern.sequential_characteristics) == 1
    assert (
        pattern.sequential_characteristics[0][
            "operation_type"
        ]
        == "MODIFY"
    )


def test_older_observation_is_rejected():
    manager = CandidatePatternManager()

    start = datetime(2026, 1, 1, 10, 0, 0)

    pattern = manager.createPattern(
        session_id="session-integrity-003",
        session_start_time=start,
    )

    first = {
        "operation_type": "CREATE",
        "timestamp": datetime(2026, 1, 1, 10, 10, 0),
    }

    older = {
        "operation_type": "MODIFY",
        "timestamp": datetime(2026, 1, 1, 10, 5, 0),
    }

    manager.updatePattern(
        "session-integrity-003",
        first,
    )

    result = manager.updatePattern(
        "session-integrity-003",
        older,
    )

    assert result is pattern
    assert pattern.observation_count() == 1
    assert pattern.timeline.observations == [first]


def test_older_observation_does_not_modify_characteristics():
    manager = CandidatePatternManager()

    start = datetime(2026, 1, 1, 10, 0, 0)

    pattern = manager.createPattern(
        session_id="session-integrity-004",
        session_start_time=start,
    )

    first = {
        "operation_type": "CREATE",
        "timestamp": datetime(2026, 1, 1, 10, 10, 0),
    }

    manager.updatePattern(
        "session-integrity-004",
        first,
    )

    original_operational = copy.deepcopy(
        pattern.operational_characteristics
    )
    original_temporal = copy.deepcopy(
        pattern.temporal_characteristics
    )
    original_sequential = copy.deepcopy(
        pattern.sequential_characteristics
    )
    original_session = copy.deepcopy(
        pattern.session_characteristics
    )

    older = {
        "operation_type": "DELETE",
        "timestamp": datetime(2026, 1, 1, 10, 5, 0),
    }

    manager.updatePattern(
        "session-integrity-004",
        older,
    )

    assert (
        pattern.operational_characteristics
        == original_operational
    )
    assert (
        pattern.temporal_characteristics
        == original_temporal
    )
    assert (
        pattern.sequential_characteristics
        == original_sequential
    )
    assert (
        pattern.session_characteristics
        == original_session
    )


def test_equal_timestamp_is_allowed_in_chronological_order():
    manager = CandidatePatternManager()

    timestamp = datetime(2026, 1, 1, 12, 0, 0)

    pattern = manager.createPattern(
        session_id="session-integrity-005",
    )

    first = {
        "operation_type": "CREATE",
        "timestamp": timestamp,
    }

    second = {
        "operation_type": "MODIFY",
        "timestamp": timestamp,
    }

    manager.updatePattern(
        "session-integrity-005",
        first,
    )

    manager.updatePattern(
        "session-integrity-005",
        second,
    )

    assert pattern.observation_count() == 2
    assert pattern.timeline.observations == [
        first,
        second,
    ]


def test_chronological_order_is_preserved_across_multiple_updates():
    manager = CandidatePatternManager()

    pattern = manager.createPattern(
        session_id="session-integrity-006",
    )

    observations = [
        {
            "operation_type": "CREATE",
            "timestamp": datetime(2026, 1, 1, 10, 0, 0),
        },
        {
            "operation_type": "MODIFY",
            "timestamp": datetime(2026, 1, 1, 10, 5, 0),
        },
        {
            "operation_type": "DELETE",
            "timestamp": datetime(2026, 1, 1, 10, 15, 0),
        },
    ]

    for observation in observations:
        manager.updatePattern(
            "session-integrity-006",
            observation,
        )

    timestamps = [
        observation["timestamp"]
        for observation in pattern.timeline.observations
    ]

    assert timestamps == sorted(timestamps)
    assert pattern.timeline.observations == observations


def test_rejected_older_observation_does_not_change_observation_count():
    manager = CandidatePatternManager()

    pattern = manager.createPattern(
        session_id="session-integrity-007",
    )

    first = {
        "operation_type": "CREATE",
        "timestamp": datetime(2026, 1, 1, 10, 0, 0),
    }

    second = {
        "operation_type": "MODIFY",
        "timestamp": datetime(2026, 1, 1, 10, 10, 0),
    }

    older = {
        "operation_type": "DELETE",
        "timestamp": datetime(2026, 1, 1, 9, 0, 0),
    }

    manager.updatePattern(
        "session-integrity-007",
        first,
    )

    manager.updatePattern(
        "session-integrity-007",
        second,
    )

    manager.updatePattern(
        "session-integrity-007",
        older,
    )

    assert pattern.observation_count() == 2
    assert pattern.metadata.observation_count == 2


def test_rejected_older_observation_does_not_change_context():
    manager = CandidatePatternManager()

    pattern = manager.createPattern(
        session_id="session-integrity-008",
    )

    first = {
        "operation_type": "CREATE",
        "timestamp": datetime(2026, 1, 1, 10, 0, 0),
    }

    manager.updatePattern(
        "session-integrity-008",
        first,
        context={
            "working_directory": "/project-a",
        },
    )

    older = {
        "operation_type": "MODIFY",
        "timestamp": datetime(2026, 1, 1, 9, 0, 0),
    }

    manager.updatePattern(
        "session-integrity-008",
        older,
        context={
            "working_directory": "/project-b",
        },
    )

    assert (
        pattern.context.values["working_directory"]
        == "/project-a"
    )

    assert (
        pattern.contextual_characteristics[
            "working_directory"
        ]
        == "/project-a"
    )


def test_duplicate_signal_after_other_observations_is_still_ignored():
    manager = CandidatePatternManager()

    pattern = manager.createPattern(
        session_id="session-integrity-009",
    )

    first = {
        "operation_type": "CREATE",
        "timestamp": datetime(2026, 1, 1, 10, 0, 0),
    }

    second = {
        "operation_type": "MODIFY",
        "timestamp": datetime(2026, 1, 1, 10, 5, 0),
    }

    manager.updatePattern(
        "session-integrity-009",
        first,
    )

    manager.updatePattern(
        "session-integrity-009",
        second,
    )

    manager.updatePattern(
        "session-integrity-009",
        first,
    )

    assert pattern.observation_count() == 2
    assert pattern.timeline.observations == [
        first,
        second,
    ]


def test_operational_characteristics_accumulate_incrementally():
    manager = CandidatePatternManager()

    pattern = manager.createPattern(
        session_id="session-growth-001",
    )

    observations = [
        {
            "operation_type": "CREATE",
            "timestamp": datetime(2026, 1, 1, 10, 0, 0),
        },
        {
            "operation_type": "MODIFY",
            "timestamp": datetime(2026, 1, 1, 10, 1, 0),
        },
        {
            "operation_type": "MODIFY",
            "timestamp": datetime(2026, 1, 1, 10, 2, 0),
        },
        {
            "operation_type": "DELETE",
            "timestamp": datetime(2026, 1, 1, 10, 3, 0),
        },
    ]

    for observation in observations:
        manager.updatePattern(
            "session-growth-001",
            observation,
        )

    operational = pattern.operational_characteristics

    assert operational["total_operations"] == 4
    assert operational["operation_counts"] == {
        "CREATE": 1,
        "MODIFY": 2,
        "DELETE": 1,
    }
    assert operational["unique_operation_types"] == 3


def test_operation_distribution_refines_with_new_observations():
    manager = CandidatePatternManager()

    pattern = manager.createPattern(
        session_id="session-growth-002",
    )

    manager.updatePattern(
        "session-growth-002",
        {
            "operation_type": "CREATE",
            "timestamp": datetime(2026, 1, 1, 10, 0, 0),
        },
    )

    distribution_after_first = copy.deepcopy(
        pattern.operational_characteristics[
            "operation_distribution"
        ]
    )

    manager.updatePattern(
        "session-growth-002",
        {
            "operation_type": "MODIFY",
            "timestamp": datetime(2026, 1, 1, 10, 1, 0),
        },
    )

    distribution_after_second = (
        pattern.operational_characteristics[
            "operation_distribution"
        ]
    )

    assert distribution_after_first == {
        "CREATE": 1.0,
    }

    assert distribution_after_second == {
        "CREATE": 0.5,
        "MODIFY": 0.5,
    }

    assert distribution_after_second != (
        distribution_after_first
    )


def test_temporal_characteristics_grow_with_observations():
    manager = CandidatePatternManager()

    pattern = manager.createPattern(
        session_id="session-growth-003",
    )

    observations = [
        {
            "operation_type": "CREATE",
            "timestamp": datetime(2026, 1, 1, 10, 0, 0),
        },
        {
            "operation_type": "MODIFY",
            "timestamp": datetime(2026, 1, 1, 10, 1, 0),
        },
        {
            "operation_type": "DELETE",
            "timestamp": datetime(2026, 1, 1, 10, 3, 0),
        },
    ]

    for observation in observations:
        manager.updatePattern(
            "session-growth-003",
            observation,
        )

    temporal = pattern.temporal_characteristics

    assert temporal["first_observation_time"] == (
        datetime(2026, 1, 1, 10, 0, 0)
    )

    assert temporal["last_observation_time"] == (
        datetime(2026, 1, 1, 10, 3, 0)
    )

    assert temporal["time_between_operations"] == [
        60.0,
        120.0,
    ]

    assert temporal["working_rhythm"][
        "observation_count"
    ] == 3


def test_sequential_characteristics_preserve_behavioral_order():
    manager = CandidatePatternManager()

    pattern = manager.createPattern(
        session_id="session-growth-004",
    )

    observations = [
        {
            "operation_type": "CREATE",
            "timestamp": datetime(2026, 1, 1, 10, 0, 0),
        },
        {
            "operation_type": "MODIFY",
            "timestamp": datetime(2026, 1, 1, 10, 1, 0),
        },
        {
            "operation_type": "MODIFY",
            "timestamp": datetime(2026, 1, 1, 10, 2, 0),
        },
        {
            "operation_type": "DELETE",
            "timestamp": datetime(2026, 1, 1, 10, 3, 0),
        },
    ]

    for observation in observations:
        manager.updatePattern(
            "session-growth-004",
            observation,
        )

    sequence = pattern.sequential_characteristics

    assert [
        item["operation_type"]
        for item in sequence
    ] == [
        "CREATE",
        "MODIFY",
        "MODIFY",
        "DELETE",
    ]

    assert [
        item["timestamp"]
        for item in sequence
    ] == [
        datetime(2026, 1, 1, 10, 0, 0),
        datetime(2026, 1, 1, 10, 1, 0),
        datetime(2026, 1, 1, 10, 2, 0),
        datetime(2026, 1, 1, 10, 3, 0),
    ]


def test_context_refinement_preserves_latest_and_history():
    manager = CandidatePatternManager()

    pattern = manager.createPattern(
        session_id="session-growth-005",
    )

    manager.updatePattern(
        "session-growth-005",
        {
            "operation_type": "CREATE",
            "timestamp": datetime(2026, 1, 1, 10, 0, 0),
        },
        context={
            "working_directory": "/project-a",
        },
    )

    manager.updatePattern(
        "session-growth-005",
        {
            "operation_type": "MODIFY",
            "timestamp": datetime(2026, 1, 1, 10, 1, 0),
        },
        context={
            "working_directory": "/project-b",
        },
    )

    manager.updatePattern(
        "session-growth-005",
        {
            "operation_type": "MODIFY",
            "timestamp": datetime(2026, 1, 1, 10, 2, 0),
        },
        context={
            "working_directory": "/project-c",
        },
    )

    values = pattern.context.values

    assert values["working_directory"] == "/project-c"
    assert values["working_directory__observation_count"] == 3

    history = values["working_directory__history"]

    assert history == [
        {
            "value": "/project-a",
            "superseded_by": "/project-b",
        },
        {
            "value": "/project-b",
            "superseded_by": "/project-c",
        },
        {
            "value": "/project-c",
            "superseded_by": None,
        },
    ]


def test_context_observation_count_refines_without_replacing_history():
    manager = CandidatePatternManager()

    pattern = manager.createPattern(
        session_id="session-growth-006",
    )

    timestamp = datetime(2026, 1, 1, 10, 0, 0)

    manager.updatePattern(
        "session-growth-006",
        {
            "operation_type": "CREATE",
            "timestamp": timestamp,
        },
        context={
            "environment": "development",
        },
    )

    manager.updatePattern(
        "session-growth-006",
        {
            "operation_type": "MODIFY",
            "timestamp": datetime(2026, 1, 1, 10, 1, 0),
        },
        context={
            "environment": "development",
        },
    )

    history = pattern.context.values[
        "environment__history"
    ]

    assert pattern.context.values[
        "environment"
    ] == "development"

    assert pattern.context.values[
        "environment__observation_count"
    ] == 2

    assert history == [
        {
            "value": "development",
            "superseded_by": None,
        }
    ]


def test_relationship_characteristics_accumulate_without_duplicate_relationships():
    manager = CandidatePatternManager()

    pattern = manager.createPattern(
        session_id="session-growth-007",
    )

    relationship = {
        "type": "related_file",
        "target": "important.txt",
    }

    manager.updatePattern(
        "session-growth-007",
        {
            "operation_type": "CREATE",
            "timestamp": datetime(2026, 1, 1, 10, 0, 0),
        },
        relationships=[relationship],
    )

    manager.updatePattern(
        "session-growth-007",
        {
            "operation_type": "MODIFY",
            "timestamp": datetime(2026, 1, 1, 10, 1, 0),
        },
        relationships=[relationship],
    )

    assert pattern.relationship_characteristics == [
        relationship,
    ]


def test_multiple_relationships_are_preserved_in_observation_order():
    manager = CandidatePatternManager()

    pattern = manager.createPattern(
        session_id="session-growth-008",
    )

    first_relationship = {
        "type": "related_file",
        "target": "first.txt",
    }

    second_relationship = {
        "type": "related_file",
        "target": "second.txt",
    }

    manager.updatePattern(
        "session-growth-008",
        {
            "operation_type": "CREATE",
            "timestamp": datetime(2026, 1, 1, 10, 0, 0),
        },
        relationships=[
            first_relationship,
            second_relationship,
        ],
    )

    assert pattern.relationship_characteristics == [
        first_relationship,
        second_relationship,
    ]


def test_session_characteristics_refine_as_pattern_grows():
    manager = CandidatePatternManager()

    pattern = manager.createPattern(
        session_id="session-growth-009",
        user_id="user-009",
    )

    manager.updatePattern(
        "session-growth-009",
        {
            "operation_type": "CREATE",
            "timestamp": datetime(2026, 1, 1, 10, 0, 0),
        },
    )

    first_session_state = copy.deepcopy(
        pattern.session_characteristics
    )

    manager.updatePattern(
        "session-growth-009",
        {
            "operation_type": "MODIFY",
            "timestamp": datetime(2026, 1, 1, 10, 1, 0),
        },
    )

    second_session_state = (
        pattern.session_characteristics
    )

    assert first_session_state[
        "observation_count"
    ] == 1

    assert second_session_state[
        "observation_count"
    ] == 2

    assert second_session_state[
        "operation_diversity"
    ] == 2

    assert second_session_state[
        "session_id"
    ] == "session-growth-009"

    assert second_session_state[
        "user_id"
    ] == "user-009"


def test_candidate_pattern_growth_preserves_previous_knowledge():
    manager = CandidatePatternManager()

    pattern = manager.createPattern(
        session_id="session-growth-010",
    )

    first = {
        "operation_type": "CREATE",
        "timestamp": datetime(2026, 1, 1, 10, 0, 0),
    }

    second = {
        "operation_type": "MODIFY",
        "timestamp": datetime(2026, 1, 1, 10, 1, 0),
    }

    manager.updatePattern(
        "session-growth-010",
        first,
        context={
            "working_directory": "/project",
        },
    )

    knowledge_after_first = {
        "observations": copy.deepcopy(
            pattern.timeline.observations
        ),
        "operational": copy.deepcopy(
            pattern.operational_characteristics
        ),
        "temporal": copy.deepcopy(
            pattern.temporal_characteristics
        ),
        "sequence": copy.deepcopy(
            pattern.sequential_characteristics
        ),
        "context": copy.deepcopy(
            pattern.context.values
        ),
        "session": copy.deepcopy(
            pattern.session_characteristics
        ),
    }

    manager.updatePattern(
        "session-growth-010",
        second,
        context={
            "working_directory": "/project",
        },
    )

    assert pattern.timeline.observations[0] == first

    assert (
        pattern.operational_characteristics[
            "operation_counts"
        ]["CREATE"]
        == 1
    )

    assert (
        pattern.temporal_characteristics[
            "first_observation_time"
        ]
        == knowledge_after_first["temporal"][
            "first_observation_time"
        ]
    )

    assert (
        pattern.context.values[
            "working_directory"
        ]
        == "/project"
    )

    assert len(
        pattern.sequential_characteristics
    ) == 2


def test_final_pattern_handler_receives_completed_candidate():
    received = []

    def handler(pattern):
        received.append(pattern)

    manager = CandidatePatternManager(
        final_pattern_handler=handler,
    )

    start_time = datetime(2026, 1, 1, 10, 0, 0)

    pattern = manager.createPattern(
        session_id="session-final-001",
        user_id="user-001",
        session_start_time=start_time,
    )

    observation = {
        "operation_type": "CREATE",
        "timestamp": start_time,
    }

    manager.updatePattern(
        "session-final-001",
        observation,
    )

    finalized = manager.finalizePattern(
        "session-final-001",
    )

    assert finalized is pattern
    assert len(received) == 1

    handed_off = received[0]

    assert handed_off is pattern
    assert handed_off.metadata.status == PatternStatus.COMPLETED
    assert handed_off.metadata.complete is True
    assert handed_off.observation_count() == 1


def test_finalization_records_session_end_before_handoff():
    received = []

    def handler(pattern):
        received.append(
            {
                "session_end_time": pattern.session_end_time,
                "duration": pattern.session_duration_seconds,
                "status": pattern.metadata.status,
            }
        )

    manager = CandidatePatternManager(
        final_pattern_handler=handler,
    )

    start_time = datetime(2026, 1, 1, 10, 0, 0)

    pattern = manager.createPattern(
        session_id="session-final-002",
        session_start_time=start_time,
    )

    manager.updatePattern(
        "session-final-002",
        {
            "operation_type": "MODIFY",
            "timestamp": start_time,
        },
    )

    explicit_end = datetime(2026, 1, 1, 10, 30, 0)

    manager.completeSession(
        "session-final-002",
        explicit_end,
    )

    manager.finalizePattern(
        "session-final-002",
    )

    assert len(received) == 1

    assert received[0]["session_end_time"] == explicit_end
    assert received[0]["duration"] == 1800.0
    assert received[0]["status"] == PatternStatus.COMPLETED

    assert pattern.session_end_time == explicit_end
    assert pattern.session_duration_seconds == 1800.0


def test_empty_candidate_pattern_never_reaches_handler():
    received = []

    def handler(pattern):
        received.append(pattern)

    manager = CandidatePatternManager(
        final_pattern_handler=handler,
    )

    manager.createPattern(
        session_id="session-final-003",
    )

    result = manager.finalizePattern(
        "session-final-003",
    )

    assert result is None
    assert received == []


def test_interrupted_candidate_pattern_never_reaches_handler():
    received = []

    def handler(pattern):
        received.append(pattern)

    manager = CandidatePatternManager(
        final_pattern_handler=handler,
    )

    manager.createPattern(
        session_id="session-final-004",
    )

    manager.updatePattern(
        "session-final-004",
        {
            "operation_type": "DELETE",
            "timestamp": datetime(2026, 1, 1, 10, 0, 0),
        },
    )

    manager.freezePattern(
        "session-final-004",
    )

    result = manager.finalizePattern(
        "session-final-004",
    )

    assert result is None
    assert received == []


def test_handler_returning_false_does_not_corrupt_completed_pattern():
    calls = []

    def handler(pattern):
        calls.append(pattern)
        return False

    manager = CandidatePatternManager(
        final_pattern_handler=handler,
    )

    pattern = manager.createPattern(
        session_id="session-final-005",
    )

    observation = {
        "operation_type": "CREATE",
        "timestamp": datetime(2026, 1, 1, 10, 0, 0),
    }

    manager.updatePattern(
        "session-final-005",
        observation,
    )

    result = manager.finalizePattern(
        "session-final-005",
    )

    assert result is pattern
    assert len(calls) == 1

    assert pattern.metadata.status == PatternStatus.COMPLETED
    assert pattern.metadata.complete is True
    assert pattern.observation_count() == 1


def test_handler_exception_does_not_corrupt_preexisting_behavior():
    def handler(pattern):
        raise RuntimeError("handoff failure")

    manager = CandidatePatternManager(
        final_pattern_handler=handler,
    )

    start_time = datetime(2026, 1, 1, 10, 0, 0)

    pattern = manager.createPattern(
        session_id="session-final-006",
        session_start_time=start_time,
    )

    observation = {
        "operation_type": "CREATE",
        "timestamp": start_time,
    }

    manager.updatePattern(
        "session-final-006",
        observation,
    )

    original_observations = copy.deepcopy(
        pattern.timeline.observations
    )
    original_operational = copy.deepcopy(
        pattern.operational_characteristics
    )

    result = manager.finalizePattern(
        "session-final-006",
    )

    assert result is pattern

    assert pattern.timeline.observations == (
        original_observations
    )

    assert (
        pattern.operational_characteristics
        == original_operational
    )

    assert pattern.observation_count() == 1


def test_handoff_failure_does_not_remove_active_pattern():
    def handler(pattern):
        return False

    manager = CandidatePatternManager(
        final_pattern_handler=handler,
    )

    pattern = manager.createPattern(
        session_id="session-final-007",
    )

    manager.updatePattern(
        "session-final-007",
        {
            "operation_type": "MODIFY",
            "timestamp": datetime(2026, 1, 1, 10, 0, 0),
        },
    )

    result = manager.finalizePattern(
        "session-final-007",
    )

    current = manager.getCurrentPattern(
        "session-final-007",
    )

    assert result is pattern
    assert current is pattern
    assert current.metadata.status == PatternStatus.COMPLETED
    assert current.observation_count() == 1


def test_explicit_session_completion_is_preserved_during_finalization():
    manager = CandidatePatternManager()

    start_time = datetime(2026, 1, 1, 8, 0, 0)
    end_time = datetime(2026, 1, 1, 9, 15, 0)

    pattern = manager.createPattern(
        session_id="session-final-008",
        session_start_time=start_time,
    )

    manager.updatePattern(
        "session-final-008",
        {
            "operation_type": "CREATE",
            "timestamp": start_time,
        },
    )

    manager.completeSession(
        "session-final-008",
        end_time,
    )

    manager.finalizePattern(
        "session-final-008",
    )

    assert pattern.session_end_time == end_time
    assert pattern.session_duration_seconds == 4500.0

    assert (
        pattern.temporal_characteristics[
            "session_end_time"
        ]
        == end_time
    )

    assert (
        pattern.session_characteristics[
            "session_length_seconds"
        ]
        == 4500.0
    )


def test_finalization_is_idempotent_after_completion():
    calls = []

    def handler(pattern):
        calls.append(pattern)

    manager = CandidatePatternManager(
        final_pattern_handler=handler,
    )

    pattern = manager.createPattern(
        session_id="session-final-009",
    )

    manager.updatePattern(
        "session-final-009",
        {
            "operation_type": "CREATE",
            "timestamp": datetime(2026, 1, 1, 10, 0, 0),
        },
    )

    first = manager.finalizePattern(
        "session-final-009",
    )

    finalized_at = pattern.metadata.finalized_at

    second = manager.finalizePattern(
        "session-final-009",
    )

    assert first is pattern
    assert second is pattern

    assert pattern.metadata.status == PatternStatus.COMPLETED
    assert pattern.metadata.finalized_at == finalized_at

    assert len(calls) == 1


def test_finalization_keeps_finalized_pattern_available_until_reset():
    manager = CandidatePatternManager()

    pattern = manager.createPattern(
        session_id="session-final-010",
    )

    manager.updatePattern(
        "session-final-010",
        {
            "operation_type": "DELETE",
            "timestamp": datetime(2026, 1, 1, 10, 0, 0),
        },
    )

    finalized = manager.finalizePattern(
        "session-final-010",
    )

    assert finalized is pattern

    current = manager.getCurrentPattern(
        "session-final-010",
    )

    assert current is pattern
    assert current.metadata.status == PatternStatus.COMPLETED

    removed = manager.resetPattern(
        "session-final-010",
    )

    assert removed is pattern
    assert manager.getCurrentPattern(
        "session-final-010"
    ) is None


def test_non_dict_observation_does_not_corrupt_pattern():
    manager = CandidatePatternManager()

    pattern = manager.createPattern(
        session_id="session-edge-001",
    )

    valid = {
        "operation_type": "CREATE",
        "timestamp": datetime(2026, 1, 1, 10, 0, 0),
    }

    manager.updatePattern(
        "session-edge-001",
        valid,
    )

    result = manager.updatePattern(
        "session-edge-001",
        "not-a-dictionary",
    )

    assert result is pattern
    assert pattern.observation_count() == 1
    assert pattern.timeline.observations == [valid]


def test_signal_without_timestamp_is_rejected_without_corruption():
    manager = CandidatePatternManager()

    pattern = manager.createPattern(
        session_id="session-edge-002",
    )

    valid = {
        "operation_type": "CREATE",
        "timestamp": datetime(2026, 1, 1, 10, 0, 0),
    }

    manager.updatePattern(
        "session-edge-002",
        valid,
    )

    invalid = {
        "operation_type": "MODIFY",
    }

    result = manager.updatePattern(
        "session-edge-002",
        invalid,
    )

    assert result is pattern
    assert pattern.observation_count() == 1
    assert pattern.timeline.observations == [valid]


def test_raw_event_markers_are_rejected():
    manager = CandidatePatternManager()

    pattern = manager.createPattern(
        session_id="session-edge-003",
    )

    valid = {
        "operation_type": "CREATE",
        "timestamp": datetime(2026, 1, 1, 10, 0, 0),
    }

    manager.updatePattern(
        "session-edge-003",
        valid,
    )

    raw_event = {
        "event_type": "created",
        "operation_type": "MODIFY",
        "timestamp": datetime(2026, 1, 1, 10, 1, 0),
    }

    result = manager.updatePattern(
        "session-edge-003",
        raw_event,
    )

    assert result is pattern
    assert pattern.observation_count() == 1
    assert pattern.timeline.observations == [valid]


@pytest.mark.parametrize(
    "raw_marker",
    [
        "event_action",
        "filesystem_event",
        "raw_event",
    ],
)
def test_all_supported_raw_event_markers_are_rejected(
    raw_marker,
):
    manager = CandidatePatternManager()

    pattern = manager.createPattern(
        session_id="session-edge-004",
    )

    valid = {
        "operation_type": "CREATE",
        "timestamp": datetime(2026, 1, 1, 10, 0, 0),
    }

    manager.updatePattern(
        "session-edge-004",
        valid,
    )

    invalid = {
        raw_marker: "raw-value",
        "operation_type": "MODIFY",
        "timestamp": datetime(2026, 1, 1, 10, 1, 0),
    }

    result = manager.updatePattern(
        "session-edge-004",
        invalid,
    )

    assert result is pattern
    assert pattern.observation_count() == 1
    assert pattern.timeline.observations == [valid]


def test_missing_session_start_time_uses_manager_timestamp():
    manager = CandidatePatternManager()

    pattern = manager.createPattern(
        session_id="session-edge-005",
        session_start_time=None,
    )

    assert pattern.session_start_time is not None

    observation = {
        "operation_type": "CREATE",
        "timestamp": pattern.session_start_time,
    }

    manager.updatePattern(
        "session-edge-005",
        observation,
    )

    session_end = (
        pattern.session_start_time
        + timedelta(minutes=5)
    )

    result = manager.completeSession(
        "session-edge-005",
        session_end,
    )

    assert result is pattern
    assert pattern.session_end_time == session_end
    assert pattern.session_duration_seconds == 300.0


def test_end_time_before_start_time_is_rejected():
    manager = CandidatePatternManager()

    start = datetime(2026, 1, 1, 10, 0, 0)

    pattern = manager.createPattern(
        session_id="session-edge-006",
        session_start_time=start,
    )

    observation = {
        "operation_type": "CREATE",
        "timestamp": start,
    }

    manager.updatePattern(
        "session-edge-006",
        observation,
    )

    result = manager.completeSession(
        "session-edge-006",
        datetime(2026, 1, 1, 9, 0, 0),
    )

    assert result is pattern
    assert pattern.session_end_time is None
    assert pattern.session_duration_seconds is None

    assert (
        "session_end_time"
        not in pattern.temporal_characteristics
    )


def test_failed_incremental_update_restores_complete_state():
    manager = CandidatePatternManager()

    pattern = manager.createPattern(
        session_id="session-edge-007",
    )

    first = {
        "operation_type": "CREATE",
        "timestamp": datetime(2026, 1, 1, 10, 0, 0),
    }

    second = {
        "operation_type": "MODIFY",
        "timestamp": datetime(2026, 1, 1, 10, 1, 0),
    }

    manager.updatePattern(
        "session-edge-007",
        first,
        context={
            "working_directory": "/project",
            "environment": "development",
        },
        relationships=[
            {
                "type": "related_file",
                "target": "main.py",
            }
        ],
    )

    original_state = copy.deepcopy(
        pattern.__dict__
    )

    def failing_session_update(*args, **kwargs):
        raise RuntimeError(
            "simulated session characteristic failure"
        )

    manager._update_session_characteristics = (
        failing_session_update
    )

    result = manager.updatePattern(
        "session-edge-007",
        second,
        context={
            "working_directory": "/changed",
            "environment": "production",
        },
        relationships=[
            {
                "type": "related_file",
                "target": "other.py",
            }
        ],
    )

    assert result is pattern
    assert pattern.__dict__ == original_state


def test_failed_first_update_leaves_no_partial_context_history():
    manager = CandidatePatternManager()

    pattern = manager.createPattern(
        session_id="session-edge-008",
    )

    def failing_contextual_update(*args, **kwargs):
        raise RuntimeError(
            "simulated contextual update failure"
        )

    manager._update_contextual_characteristics = (
        failing_contextual_update
    )

    observation = {
        "operation_type": "CREATE",
        "timestamp": datetime(2026, 1, 1, 10, 0, 0),
    }

    result = manager.updatePattern(
        "session-edge-008",
        observation,
        context={
            "working_directory": "/project",
        },
    )

    assert result is pattern
    assert pattern.observation_count() == 0
    assert pattern.context.values == {}
    assert pattern.contextual_characteristics == {}
    assert pattern.operational_characteristics == {}
    assert pattern.temporal_characteristics == {}
    assert pattern.sequential_characteristics == []
    assert pattern.relationship_characteristics == []
    assert pattern.session_characteristics == {}
    assert pattern.metadata.observation_count == 0
    assert pattern.metadata.status == PatternStatus.INITIALIZING


def test_failed_update_preserves_object_identity():
    manager = CandidatePatternManager()

    pattern = manager.createPattern(
        session_id="session-edge-009",
    )

    def failing_update(*args, **kwargs):
        raise RuntimeError(
            "simulated update failure"
        )

    manager._update_relationship_characteristics = (
        failing_update
    )

    observation = {
        "operation_type": "CREATE",
        "timestamp": datetime(2026, 1, 1, 10, 0, 0),
    }

    result = manager.updatePattern(
        "session-edge-009",
        observation,
        relationships=[
            {
                "type": "related_file",
                "target": "main.py",
            }
        ],
    )

    current = manager.getCurrentPattern(
        "session-edge-009",
    )

    assert result is pattern
    assert current is pattern


def test_pattern_can_continue_after_a_failed_update():
    manager = CandidatePatternManager()

    pattern = manager.createPattern(
        session_id="session-edge-010",
    )

    first = {
        "operation_type": "CREATE",
        "timestamp": datetime(2026, 1, 1, 10, 0, 0),
    }

    second = {
        "operation_type": "MODIFY",
        "timestamp": datetime(2026, 1, 1, 10, 1, 0),
    }

    manager.updatePattern(
        "session-edge-010",
        first,
    )

    original_method = (
        manager._update_session_characteristics
    )

    def failing_once(pattern, *args, **kwargs):
        manager._update_session_characteristics = (
            original_method
        )
        raise RuntimeError(
            "simulated one-time failure"
        )

    manager._update_session_characteristics = (
        failing_once
    )

    manager.updatePattern(
        "session-edge-010",
        second,
    )

    assert pattern.observation_count() == 1

    retry = manager.updatePattern(
        "session-edge-010",
        second,
    )

    assert retry is pattern
    assert pattern.observation_count() == 2
    assert pattern.timeline.observations == [
        first,
        second,
    ]
    assert pattern.metadata.status == PatternStatus.LEARNING


def test_freeze_preserves_state_after_failed_update():
    manager = CandidatePatternManager()

    pattern = manager.createPattern(
        session_id="session-edge-011",
    )

    first = {
        "operation_type": "CREATE",
        "timestamp": datetime(2026, 1, 1, 10, 0, 0),
    }

    manager.updatePattern(
        "session-edge-011",
        first,
        context={
            "working_directory": "/project",
        },
    )

    original_state = copy.deepcopy(
        pattern.__dict__
    )

    def failing_update(*args, **kwargs):
        raise RuntimeError("simulated failure")

    manager._update_operational_characteristics = (
        failing_update
    )

    second = {
        "operation_type": "MODIFY",
        "timestamp": datetime(2026, 1, 1, 10, 1, 0),
    }

    manager.updatePattern(
        "session-edge-011",
        second,
    )

    frozen = manager.freezePattern(
        "session-edge-011",
    )

    assert frozen is pattern
    assert pattern.metadata.interrupted is True

    current_state = copy.deepcopy(
        pattern.__dict__
    )

    assert current_state["timeline"] == (
        original_state["timeline"]
    )
    assert current_state["context"] == (
        original_state["context"]
    )
    assert current_state[
        "operational_characteristics"
    ] == original_state[
        "operational_characteristics"
    ]


def test_session_observation_count_tracks_pattern_growth():
    manager = CandidatePatternManager()

    pattern = manager.createPattern(
        session_id="session-metrics-001",
    )

    assert pattern.session_characteristics == {}

    manager.updatePattern(
        "session-metrics-001",
        {
            "operation_type": "CREATE",
            "timestamp": datetime(2026, 1, 1, 10, 0, 0),
        },
    )

    assert pattern.session_characteristics[
        "observation_count"
    ] == 1

    manager.updatePattern(
        "session-metrics-001",
        {
            "operation_type": "MODIFY",
            "timestamp": datetime(2026, 1, 1, 10, 1, 0),
        },
    )

    assert pattern.session_characteristics[
        "observation_count"
    ] == 2


def test_operation_diversity_counts_unique_operation_types():
    manager = CandidatePatternManager()

    pattern = manager.createPattern(
        session_id="session-metrics-002",
    )

    observations = [
        {
            "operation_type": "CREATE",
            "timestamp": datetime(2026, 1, 1, 10, 0, 0),
        },
        {
            "operation_type": "MODIFY",
            "timestamp": datetime(2026, 1, 1, 10, 1, 0),
        },
        {
            "operation_type": "MODIFY",
            "timestamp": datetime(2026, 1, 1, 10, 2, 0),
        },
        {
            "operation_type": "DELETE",
            "timestamp": datetime(2026, 1, 1, 10, 3, 0),
        },
    ]

    for observation in observations:
        manager.updatePattern(
            "session-metrics-002",
            observation,
        )

    assert pattern.session_characteristics[
        "operation_diversity"
    ] == 3


def test_operation_diversity_does_not_count_duplicates():
    manager = CandidatePatternManager()

    pattern = manager.createPattern(
        session_id="session-metrics-003",
    )

    for minute in range(4):
        manager.updatePattern(
            "session-metrics-003",
            {
                "operation_type": "MODIFY",
                "timestamp": datetime(
                    2026,
                    1,
                    1,
                    10,
                    minute,
                    0,
                ),
            },
        )

    assert pattern.session_characteristics[
        "operation_diversity"
    ] == 1


def test_behavioral_density_is_derived_from_activity():
    manager = CandidatePatternManager()

    pattern = manager.createPattern(
        session_id="session-metrics-004",
        session_start_time=datetime(2026, 1, 1, 10, 0, 0),
    )

    observations = [
        {
            "operation_type": "CREATE",
            "timestamp": datetime(2026, 1, 1, 10, 0, 0),
        },
        {
            "operation_type": "MODIFY",
            "timestamp": datetime(2026, 1, 1, 10, 1, 0),
        },
        {
            "operation_type": "DELETE",
            "timestamp": datetime(2026, 1, 1, 10, 2, 0),
        },
    ]

    for observation in observations:
        manager.updatePattern(
            "session-metrics-004",
            observation,
        )

    density = pattern.session_characteristics[
        "behavioral_density"
    ]

    assert density is not None
    assert density > 0


def test_behavioral_density_changes_when_session_activity_changes():
    manager = CandidatePatternManager()

    pattern = manager.createPattern(
        session_id="session-metrics-005",
        session_start_time=datetime(2026, 1, 1, 10, 0, 0),
    )

    manager.updatePattern(
        "session-metrics-005",
        {
            "operation_type": "CREATE",
            "timestamp": datetime(2026, 1, 1, 10, 0, 0),
        },
    )

    first_density = pattern.session_characteristics[
        "behavioral_density"
    ]

    manager.updatePattern(
        "session-metrics-005",
        {
            "operation_type": "MODIFY",
            "timestamp": datetime(2026, 1, 1, 10, 1, 0),
        },
    )

    second_density = pattern.session_characteristics[
        "behavioral_density"
    ]

    assert second_density != first_density


def test_behavioral_consistency_exists_for_multiple_operations():
    manager = CandidatePatternManager()

    pattern = manager.createPattern(
        session_id="session-metrics-006",
    )

    timestamps = [
        datetime(2026, 1, 1, 10, 0, 0),
        datetime(2026, 1, 1, 10, 1, 0),
        datetime(2026, 1, 1, 10, 2, 0),
        datetime(2026, 1, 1, 10, 3, 0),
    ]

    for index, timestamp in enumerate(timestamps):
        manager.updatePattern(
            "session-metrics-006",
            {
                "operation_type": "MODIFY",
                "timestamp": timestamp,
            },
        )

    consistency = pattern.session_characteristics[
        "behavioral_consistency"
    ]

    assert consistency is not None
    assert 0.0 <= consistency <= 1.0


def test_consistent_intervals_produce_high_consistency():
    manager = CandidatePatternManager()

    pattern = manager.createPattern(
        session_id="session-metrics-007",
    )

    timestamps = [
        datetime(2026, 1, 1, 10, 0, 0),
        datetime(2026, 1, 1, 10, 1, 0),
        datetime(2026, 1, 1, 10, 2, 0),
        datetime(2026, 1, 1, 10, 3, 0),
    ]

    for timestamp in timestamps:
        manager.updatePattern(
            "session-metrics-007",
            {
                "operation_type": "MODIFY",
                "timestamp": timestamp,
            },
        )

    consistency = pattern.session_characteristics[
        "behavioral_consistency"
    ]

    assert consistency == 1.0


def test_irregular_intervals_reduce_behavioral_consistency():
    manager = CandidatePatternManager()

    pattern = manager.createPattern(
        session_id="session-metrics-008",
    )

    timestamps = [
        datetime(2026, 1, 1, 10, 0, 0),
        datetime(2026, 1, 1, 10, 1, 0),
        datetime(2026, 1, 1, 10, 5, 0),
        datetime(2026, 1, 1, 10, 6, 0),
    ]

    for timestamp in timestamps:
        manager.updatePattern(
            "session-metrics-008",
            {
                "operation_type": "MODIFY",
                "timestamp": timestamp,
            },
        )

    consistency = pattern.session_characteristics[
        "behavioral_consistency"
    ]

    assert 0.0 <= consistency < 1.0


def test_task_complexity_contains_session_level_dimensions():
    manager = CandidatePatternManager()

    pattern = manager.createPattern(
        session_id="session-metrics-009",
    )

    manager.updatePattern(
        "session-metrics-009",
        {
            "operation_type": "CREATE",
            "timestamp": datetime(2026, 1, 1, 10, 0, 0),
        },
        relationships=[
            {
                "type": "related_file",
                "target": "main.py",
            }
        ],
    )

    complexity = pattern.session_characteristics[
        "task_complexity"
    ]

    assert complexity["operation_diversity"] == 1
    assert complexity["relationship_count"] == 1


def test_task_complexity_refines_as_behavior_diversifies():
    manager = CandidatePatternManager()

    pattern = manager.createPattern(
        session_id="session-metrics-010",
    )

    manager.updatePattern(
        "session-metrics-010",
        {
            "operation_type": "CREATE",
            "timestamp": datetime(2026, 1, 1, 10, 0, 0),
        },
    )

    first_complexity = copy.deepcopy(
        pattern.session_characteristics[
            "task_complexity"
        ]
    )

    manager.updatePattern(
        "session-metrics-010",
        {
            "operation_type": "MODIFY",
            "timestamp": datetime(2026, 1, 1, 10, 1, 0),
        },
        relationships=[
            {
                "type": "related_file",
                "target": "main.py",
            }
        ],
    )

    second_complexity = pattern.session_characteristics[
        "task_complexity"
    ]

    assert first_complexity[
        "operation_diversity"
    ] == 1

    assert second_complexity[
        "operation_diversity"
    ] == 2

    assert second_complexity[
        "relationship_count"
    ] == 1


def test_first_and_last_observation_times_are_tracked():
    manager = CandidatePatternManager()

    pattern = manager.createPattern(
        session_id="session-temporal-001",
    )

    first_time = datetime(2026, 1, 1, 10, 0, 0)
    last_time = datetime(2026, 1, 1, 10, 5, 0)

    manager.updatePattern(
        "session-temporal-001",
        {
            "operation_type": "CREATE",
            "timestamp": first_time,
        },
    )

    manager.updatePattern(
        "session-temporal-001",
        {
            "operation_type": "MODIFY",
            "timestamp": last_time,
        },
    )

    temporal = pattern.temporal_characteristics

    assert temporal["first_observation_time"] == first_time
    assert temporal["last_observation_time"] == last_time


def test_operation_intervals_are_incrementally_recorded():
    manager = CandidatePatternManager()

    pattern = manager.createPattern(
        session_id="session-temporal-002",
    )

    times = [
        datetime(2026, 1, 1, 10, 0, 0),
        datetime(2026, 1, 1, 10, 0, 30),
        datetime(2026, 1, 1, 10, 2, 0),
    ]

    for timestamp in times:
        manager.updatePattern(
            "session-temporal-002",
            {
                "operation_type": "MODIFY",
                "timestamp": timestamp,
            },
        )

    assert pattern.temporal_characteristics[
        "operation_intervals"
    ] == [
        30.0,
        90.0,
    ]

    assert pattern.temporal_characteristics[
        "time_between_operations"
    ] == [
        30.0,
        90.0,
    ]


def test_idle_interval_is_recorded_when_gap_exceeds_threshold():
    manager = CandidatePatternManager()

    pattern = manager.createPattern(
        session_id="session-temporal-003",
    )

    first_time = datetime(2026, 1, 1, 10, 0, 0)
    second_time = datetime(2026, 1, 1, 10, 2, 0)

    manager.updatePattern(
        "session-temporal-003",
        {
            "operation_type": "CREATE",
            "timestamp": first_time,
        },
    )

    manager.updatePattern(
        "session-temporal-003",
        {
            "operation_type": "MODIFY",
            "timestamp": second_time,
        },
    )

    temporal = pattern.temporal_characteristics

    assert temporal["idle_intervals"] == [120.0]
    assert temporal["idle_time_seconds"] == 120.0


def test_short_interval_is_not_classified_as_idle():
    manager = CandidatePatternManager()

    pattern = manager.createPattern(
        session_id="session-temporal-004",
    )

    first_time = datetime(2026, 1, 1, 10, 0, 0)
    second_time = datetime(2026, 1, 1, 10, 0, 30)

    manager.updatePattern(
        "session-temporal-004",
        {
            "operation_type": "CREATE",
            "timestamp": first_time,
        },
    )

    manager.updatePattern(
        "session-temporal-004",
        {
            "operation_type": "MODIFY",
            "timestamp": second_time,
        },
    )

    temporal = pattern.temporal_characteristics

    assert temporal["idle_intervals"] == []
    assert temporal["idle_time_seconds"] == 0.0


def test_active_time_is_based_on_non_idle_intervals():
    manager = CandidatePatternManager()

    pattern = manager.createPattern(
        session_id="session-temporal-005",
    )

    times = [
        datetime(2026, 1, 1, 10, 0, 0),
        datetime(2026, 1, 1, 10, 0, 30),
        datetime(2026, 1, 1, 10, 2, 30),
    ]

    for timestamp in times:
        manager.updatePattern(
            "session-temporal-005",
            {
                "operation_type": "MODIFY",
                "timestamp": timestamp,
            },
        )

    temporal = pattern.temporal_characteristics

    assert temporal["idle_time_seconds"] == 120.0
    assert temporal["active_time_seconds"] == 30.0


def test_working_rhythm_tracks_interval_statistics():
    manager = CandidatePatternManager()

    pattern = manager.createPattern(
        session_id="session-temporal-006",
    )

    times = [
        datetime(2026, 1, 1, 10, 0, 0),
        datetime(2026, 1, 1, 10, 1, 0),
        datetime(2026, 1, 1, 10, 3, 0),
        datetime(2026, 1, 1, 10, 6, 0),
    ]

    for timestamp in times:
        manager.updatePattern(
            "session-temporal-006",
            {
                "operation_type": "MODIFY",
                "timestamp": timestamp,
            },
        )

    rhythm = pattern.temporal_characteristics[
        "working_rhythm"
    ]

    assert rhythm["observation_count"] == 4
    assert rhythm["min_interval_seconds"] == 60.0
    assert rhythm["max_interval_seconds"] == 180.0
    assert rhythm["average_interval_seconds"] == 120.0


def test_burst_activity_is_detected_for_short_intervals():
    manager = CandidatePatternManager()

    pattern = manager.createPattern(
        session_id="session-temporal-007",
    )

    times = [
        datetime(2026, 1, 1, 10, 0, 0),
        datetime(2026, 1, 1, 10, 0, 1),
        datetime(2026, 1, 1, 10, 0, 2),
    ]

    for timestamp in times:
        manager.updatePattern(
            "session-temporal-007",
            {
                "operation_type": "MODIFY",
                "timestamp": timestamp,
            },
        )

    temporal = pattern.temporal_characteristics

    assert temporal["burst_count"] >= 1
    assert temporal["burst_activity"] is True


def test_normal_activity_does_not_create_burst():
    manager = CandidatePatternManager()

    pattern = manager.createPattern(
        session_id="session-temporal-008",
    )

    times = [
        datetime(2026, 1, 1, 10, 0, 0),
        datetime(2026, 1, 1, 10, 1, 0),
        datetime(2026, 1, 1, 10, 2, 0),
    ]

    for timestamp in times:
        manager.updatePattern(
            "session-temporal-008",
            {
                "operation_type": "MODIFY",
                "timestamp": timestamp,
            },
        )

    temporal = pattern.temporal_characteristics

    assert temporal["burst_count"] == 0
    assert temporal["burst_activity"] is False


def test_continuous_activity_is_tracked_for_close_operations():
    manager = CandidatePatternManager()

    pattern = manager.createPattern(
        session_id="session-temporal-009",
    )

    times = [
        datetime(2026, 1, 1, 10, 0, 0),
        datetime(2026, 1, 1, 10, 0, 1),
        datetime(2026, 1, 1, 10, 0, 2),
        datetime(2026, 1, 1, 10, 0, 3),
    ]

    for timestamp in times:
        manager.updatePattern(
            "session-temporal-009",
            {
                "operation_type": "MODIFY",
                "timestamp": timestamp,
            },
        )

    temporal = pattern.temporal_characteristics

    assert temporal["continuous_activity"] is True


def test_idle_period_and_burst_can_coexist():
    manager = CandidatePatternManager()

    pattern = manager.createPattern(
        session_id="session-temporal-010",
    )

    times = [
        datetime(2026, 1, 1, 10, 0, 0),
        datetime(2026, 1, 1, 10, 0, 1),
        datetime(2026, 1, 1, 10, 0, 2),
        datetime(2026, 1, 1, 10, 2, 2),
        datetime(2026, 1, 1, 10, 2, 3),
    ]

    for timestamp in times:
        manager.updatePattern(
            "session-temporal-010",
            {
                "operation_type": "MODIFY",
                "timestamp": timestamp,
            },
        )

    temporal = pattern.temporal_characteristics

    assert temporal["idle_time_seconds"] == 120.0
    assert temporal["burst_count"] >= 2
    assert temporal["burst_activity"] is True
    assert temporal["continuous_activity"] is False
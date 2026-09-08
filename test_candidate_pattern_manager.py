from datetime import datetime
import copy

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
from datetime import datetime

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

    result = manager.updatePattern(
        "session-001",
        second,
    )

    assert result is not None
    assert result.metadata.status == PatternStatus.LEARNING
    assert result.observation_count() == 2


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

    for timestamp in (
        first_timestamp,
        earlier_timestamp,
        later_timestamp,
    ):
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

    characteristics = pattern.temporal_characteristics

    assert characteristics["first_observation_time"] == earlier_timestamp
    assert characteristics["last_observation_time"] == later_timestamp
    assert characteristics["duration_seconds"] == 17.0


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
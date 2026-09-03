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
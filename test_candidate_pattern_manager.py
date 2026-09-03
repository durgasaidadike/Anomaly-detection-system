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
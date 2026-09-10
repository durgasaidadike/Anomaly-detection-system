from datetime import datetime, timezone

from candidate_pattern_manager import CandidatePatternManager
from candidate_pattern_models import PatternStatus


def _build_manager_with_signal(session_id, start_time):
    manager = CandidatePatternManager()

    manager.createPattern(
        session_id=session_id,
        user_id="user-001",
        session_start_time=start_time,
    )

    manager.updatePattern(
        session_id,
        {
            "signal_type": "EDITING_WORKFLOW",
            "operation_type": "MODIFIED",
            "timestamp": start_time,
        },
        context={
            "working_directory": "/workspace",
            "workflow_stage": "editing",
        },
        relationships=[],
    )

    return manager


def test_finalization_requires_explicit_session_completion():
    start = datetime(
        2026,
        1,
        1,
        10,
        0,
        0,
        tzinfo=timezone.utc,
    )

    session_id = "finalization-session-001"

    manager = _build_manager_with_signal(
        session_id,
        start,
    )

    result = manager.finalizePattern(session_id)

    assert result is None

    pattern = manager.getCurrentPattern(session_id)

    assert pattern is not None
    assert pattern.metadata.complete is False


def test_successful_finalization_hands_off_completed_candidate():
    start = datetime(
        2026,
        1,
        1,
        10,
        0,
        0,
        tzinfo=timezone.utc,
    )

    session_id = "finalization-session-002"

    handed_off = []

    def handler(pattern):
        handed_off.append(pattern)
        return True

    manager = CandidatePatternManager(
        final_pattern_handler=handler
    )

    pattern = manager.createPattern(
        session_id=session_id,
        user_id="user-001",
        session_start_time=start,
    )

    manager.updatePattern(
        session_id,
        {
            "signal_type": "EDITING_WORKFLOW",
            "operation_type": "MODIFIED",
            "timestamp": start,
        },
        context={
            "workflow_stage": "editing",
        },
        relationships=[],
    )

    manager.completeSession(
        session_id,
        session_end_time=start,
    )

    result = manager.finalizePattern(session_id)

    assert result is pattern
    assert result.metadata.complete is True
    assert result.metadata.status == PatternStatus.COMPLETED

    assert len(handed_off) == 1
    assert handed_off[0] is pattern


def test_failed_final_pattern_handoff_preserves_completed_candidate():
    start = datetime(
        2026,
        1,
        1,
        10,
        0,
        0,
        tzinfo=timezone.utc,
    )

    session_id = "finalization-session-003"

    def handler(pattern):
        return False

    manager = CandidatePatternManager(
        final_pattern_handler=handler
    )

    pattern = manager.createPattern(
        session_id=session_id,
        user_id="user-001",
        session_start_time=start,
    )

    manager.updatePattern(
        session_id,
        {
            "signal_type": "EDITING_WORKFLOW",
            "operation_type": "MODIFIED",
            "timestamp": start,
        },
        context={},
        relationships=[],
    )

    manager.completeSession(
        session_id,
        session_end_time=start,
    )

    result = manager.finalizePattern(session_id)

    assert result is pattern
    assert result.metadata.complete is True
    assert result.metadata.status == PatternStatus.COMPLETED

    preserved = manager.getCurrentPattern(session_id)

    assert preserved is pattern
    assert preserved.observation_count() == 1


def test_reset_releases_completed_candidate_state():
    start = datetime(
        2026,
        1,
        1,
        10,
        0,
        0,
        tzinfo=timezone.utc,
    )

    session_id = "finalization-session-004"

    manager = _build_manager_with_signal(
        session_id,
        start,
    )

    manager.completeSession(
        session_id,
        session_end_time=start,
    )

    manager.finalizePattern(session_id)

    removed = manager.resetPattern(session_id)

    assert removed is not None
    assert removed.metadata.complete is True
    assert manager.getCurrentPattern(session_id) is None
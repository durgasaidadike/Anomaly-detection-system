from datetime import datetime, timedelta, timezone

import pytest

from candidate_pattern_manager import CandidatePatternManager
from final_pattern_factory import FinalPatternFactory
from final_pattern_models import FinalPattern


def build_completed_candidate():
    start = datetime(
        2026,
        1,
        1,
        10,
        0,
        0,
        tzinfo=timezone.utc,
    )

    manager = CandidatePatternManager()

    session_id = "final-contract-001"

    manager.createPattern(
        session_id=session_id,
        user_id="user-001",
        session_start_time=start,
    )

    manager.updatePattern(
        session_id,
        {
            "signal_type": "EDITING_WORKFLOW",
            "operation_type": "CREATED",
            "timestamp": start,
        },
        context={
            "working_directory": "/workspace",
            "workflow_stage": "creation",
        },
        relationships=[],
    )

    manager.updatePattern(
        session_id,
        {
            "signal_type": "EDITING_WORKFLOW",
            "operation_type": "MODIFIED",
            "timestamp": start + timedelta(seconds=3),
        },
        context={
            "working_directory": "/workspace",
            "workflow_stage": "editing",
        },
        relationships=[
            {
                "relationship_type": "SEQUENTIAL",
                "from_operation": "CREATED",
                "to_operation": "MODIFIED",
            }
        ],
    )

    manager.completeSession(
        session_id,
        session_end_time=start + timedelta(seconds=5),
    )

    manager.finalizePattern(session_id)

    return manager.getCurrentPattern(session_id)


def test_completed_candidate_can_become_final_pattern():
    candidate = build_completed_candidate()

    assert candidate is not None
    assert candidate.metadata.complete is True

    factory = FinalPatternFactory()
    final_pattern = factory.create(candidate)

    assert final_pattern is not None
    assert isinstance(final_pattern, FinalPattern)

    assert final_pattern.session_id == candidate.session_id
    assert final_pattern.user_id == candidate.user_id

    assert final_pattern.observation_count == (
        candidate.observation_count()
    )

    assert len(final_pattern.observations) == 2

    assert final_pattern.operational_characteristics
    assert final_pattern.temporal_characteristics
    assert final_pattern.sequential_characteristics
    assert final_pattern.contextual_characteristics
    assert final_pattern.relationship_characteristics
    assert final_pattern.session_characteristics


def test_incomplete_candidate_cannot_become_final_pattern():
    start = datetime(
        2026,
        1,
        1,
        10,
        0,
        0,
        tzinfo=timezone.utc,
    )

    manager = CandidatePatternManager()

    session_id = "final-contract-002"

    manager.createPattern(
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

    candidate = manager.getCurrentPattern(session_id)

    assert candidate is not None
    assert candidate.metadata.complete is False

    factory = FinalPatternFactory()
    final_pattern = factory.create(candidate)

    assert final_pattern is None


def test_interrupted_candidate_cannot_become_final_pattern():
    start = datetime(
        2026,
        1,
        1,
        10,
        0,
        0,
        tzinfo=timezone.utc,
    )

    manager = CandidatePatternManager()

    session_id = "final-contract-003"

    manager.createPattern(
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

    manager.freezePattern(session_id)

    candidate = manager.getCurrentPattern(session_id)

    assert candidate is not None
    assert candidate.metadata.interrupted is True

    factory = FinalPatternFactory()
    final_pattern = factory.create(candidate)

    assert final_pattern is None


def test_final_pattern_snapshot_is_detached_from_candidate():
    candidate = build_completed_candidate()

    factory = FinalPatternFactory()
    final_pattern = factory.create(candidate)

    assert final_pattern is not None

    original_observation_count = len(
        final_pattern.observations
    )

    candidate.timeline.observations.clear()

    assert len(final_pattern.observations) == (
        original_observation_count
    )


def test_final_pattern_snapshot_returns_equivalent_detached_data():
    candidate = build_completed_candidate()

    factory = FinalPatternFactory()
    final_pattern = factory.create(candidate)

    assert final_pattern is not None

    snapshot = final_pattern.snapshot()

    assert snapshot == final_pattern

    assert snapshot is not final_pattern

    snapshot.observations.append(
        {
            "signal_type": "TEST_MUTATION",
            "timestamp": datetime(
                2026,
                1,
                1,
                11,
                0,
                0,
                tzinfo=timezone.utc,
            ),
        }
    )

    assert len(snapshot.observations) == (
        len(final_pattern.observations) + 1
    )

    assert len(final_pattern.observations) == 2
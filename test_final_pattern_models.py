from datetime import datetime

from candidate_pattern_models import CandidatePattern
from final_pattern_factory import FinalPatternFactory
from final_pattern_models import FinalPattern


def build_completed_pattern():
    pattern = CandidatePattern(
        session_id="session-1",
        user_id="user-1",
    )

    pattern.add_observation(
        {
            "operation_type": "CREATE",
            "timestamp": datetime.now(),
            "file_extension": ".py",
            "directory": "/project",
            "event_hour": 10,
            "file_size": 100,
        }
    )

    pattern.mark_finalized(
        datetime(2026, 9, 4, 10, 0, 0)
    )

    pattern.mark_completed()

    return pattern


def test_factory_creates_final_pattern():
    candidate = build_completed_pattern()

    final_pattern = FinalPatternFactory().create(candidate)

    assert isinstance(final_pattern, FinalPattern)
    assert final_pattern.session_id == "session-1"
    assert final_pattern.user_id == "user-1"
    assert final_pattern.observation_count == 1


def test_factory_copies_observations():
    candidate = build_completed_pattern()

    final_pattern = FinalPatternFactory().create(candidate)

    assert final_pattern is not None
    assert final_pattern.observations == candidate.timeline.observations
    assert final_pattern.observations is not candidate.timeline.observations


def test_factory_rejects_incomplete_pattern():
    candidate = CandidatePattern(session_id="session-1")

    final_pattern = FinalPatternFactory().create(candidate)

    assert final_pattern is None


def test_factory_rejects_empty_pattern():
    candidate = CandidatePattern(session_id="session-1")

    candidate.mark_finalized()

    final_pattern = FinalPatternFactory().create(candidate)

    assert final_pattern is None


def test_factory_rejects_interrupted_pattern():
    candidate = build_completed_pattern()

    candidate.metadata.interrupted = True

    final_pattern = FinalPatternFactory().create(candidate)

    assert final_pattern is None


def test_final_pattern_snapshot_is_independent():
    candidate = build_completed_pattern()

    final_pattern = FinalPatternFactory().create(candidate)

    snapshot = final_pattern.snapshot()

    assert snapshot == final_pattern
    assert snapshot is not final_pattern
    assert snapshot.observations is not final_pattern.observations

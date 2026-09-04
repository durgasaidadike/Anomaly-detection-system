from candidate_pattern_models import CandidatePattern
from final_pattern_repository import FinalPatternRepository


def build_completed_pattern(
    session_id: str = "session-1",
) -> CandidatePattern:
    pattern = CandidatePattern(session_id=session_id)
    pattern.user_id = "user-1"

    pattern.add_observation(
        {
            "operation_type": "CREATE",
            "file_extension": ".txt",
            "directory": "/docs",
            "event_hour": 10,
            "file_size": 100,
            "timestamp": "2026-01-01T10:00:00",
        }
    )

    pattern.mark_finalized()
    pattern.mark_completed()

    return pattern


def test_store_accepts_completed_final_pattern():
    repository = FinalPatternRepository()

    pattern = build_completed_pattern()

    assert repository.store(pattern) is True
    assert repository.count() == 1
    assert repository.contains("session-1") is True


def test_repository_rejects_incomplete_pattern():
    repository = FinalPatternRepository()

    pattern = CandidatePattern(session_id="session-1")

    assert repository.store(pattern) is False
    assert repository.count() == 0


def test_repository_rejects_empty_final_pattern():
    repository = FinalPatternRepository()

    pattern = CandidatePattern(session_id="session-1")
    pattern.mark_finalized()
    pattern.mark_completed()

    assert repository.store(pattern) is False
    assert repository.count() == 0


def test_repository_rejects_interrupted_pattern():
    repository = FinalPatternRepository()

    pattern = build_completed_pattern()
    pattern.metadata.interrupted = True

    assert repository.store(pattern) is False
    assert repository.count() == 0


def test_store_repeated_behavior_merges_instead_of_creating_duplicate():
    repository = FinalPatternRepository()

    first = build_completed_pattern("session-1")
    second = build_completed_pattern("session-2")

    first.metadata.observation_count = 1
    second.metadata.observation_count = 1

    assert repository.store(first)
    assert repository.store(second)

    assert repository.count() == 1

    stored = repository.get("session-1")

    assert stored is not None
    assert stored.metadata.observation_count == 2


def test_get_returns_stored_pattern():
    repository = FinalPatternRepository()

    pattern = build_completed_pattern()

    repository.store(pattern)

    result = repository.get("session-1")

    assert result is not None
    assert result.session_id == "session-1"
    assert result.observation_count() == 1


def test_get_unknown_pattern_returns_none():
    repository = FinalPatternRepository()

    assert repository.get("missing") is None


def test_get_returns_independent_copy():
    repository = FinalPatternRepository()

    pattern = build_completed_pattern()

    repository.store(pattern)

    result = repository.get("session-1")

    assert result is not None

    result.timeline.observations.clear()

    stored_again = repository.get("session-1")

    assert stored_again is not None
    assert stored_again.observation_count() == 1


def test_original_pattern_cannot_modify_repository_history():
    repository = FinalPatternRepository()

    pattern = build_completed_pattern()

    repository.store(pattern)

    pattern.timeline.observations.clear()

    stored = repository.get("session-1")

    assert stored is not None
    assert stored.observation_count() == 1


def test_get_all_returns_independent_patterns():
    repository = FinalPatternRepository()

    first = build_completed_pattern("session-1")
    second = build_completed_pattern("session-2")

    second.timeline.observations[0]["operation_type"] = "DELETE"

    repository.store(first)
    repository.store(second)

    patterns = repository.get_all()

    assert len(patterns) == 2
    assert {pattern.session_id for pattern in patterns} == {
        "session-1",
        "session-2",
    }


def test_count_starts_at_zero():
    repository = FinalPatternRepository()

    assert repository.count() == 0


def test_contains_handles_unknown_pattern():
    repository = FinalPatternRepository()

    assert repository.contains("missing") is False


def test_repeated_behavior_does_not_create_second_pattern_id():
    repository = FinalPatternRepository()

    first = build_completed_pattern("session-1")
    second = build_completed_pattern("session-2")

    assert repository.store(first)
    assert repository.store(second)

    assert repository.count() == 1
    assert repository.contains("session-1")
    assert not repository.contains("session-2")


def test_different_behavior_creates_new_pattern():
    repository = FinalPatternRepository()

    first = build_completed_pattern("session-1")
    second = build_completed_pattern("session-2")

    second.timeline.observations[0]["operation_type"] = "DELETE"

    assert repository.store(first)
    assert repository.store(second)

    assert repository.count() == 2


def test_different_user_creates_new_pattern():
    repository = FinalPatternRepository()

    first = build_completed_pattern("session-1")
    second = build_completed_pattern("session-2")

    second.user_id = "user-2"

    assert repository.store(first)
    assert repository.store(second)

    assert repository.count() == 2

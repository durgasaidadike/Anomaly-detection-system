from datetime import datetime

from final_pattern_models import FinalPattern
from final_pattern_repository import FinalPatternRepository


def build_final_pattern(
    pattern_id="pattern-1",
    session_id="session-1",
    operation_type="CREATE",
):
    return FinalPattern(
        pattern_id=pattern_id,
        session_id=session_id,
        user_id="user-1",
        created_at=datetime(2026, 9, 4, 10, 0, 0),
        observations=[
            {
                "operation_type": operation_type,
                "timestamp": datetime(
                    2026,
                    9,
                    4,
                    10,
                    0,
                    0,
                ),
                "file_extension": ".py",
                "directory": "/project",
            }
        ],
        observation_count=1,
    )


def test_store_final_pattern():
    repository = FinalPatternRepository()

    pattern = build_final_pattern()

    assert repository.store(pattern)
    assert repository.count() == 1
    assert repository.contains("pattern-1")


def test_get_returns_stored_pattern():
    repository = FinalPatternRepository()

    pattern = build_final_pattern()

    assert repository.store(pattern)

    stored = repository.get("pattern-1")

    assert stored is not None
    assert stored.pattern_id == "pattern-1"
    assert stored.session_id == "session-1"


def test_get_returns_copy():
    repository = FinalPatternRepository()

    pattern = build_final_pattern()

    assert repository.store(pattern)

    first = repository.get("pattern-1")
    second = repository.get("pattern-1")

    assert first is not None
    assert second is not None
    assert first is not second
    assert first.observations is not second.observations


def test_get_unknown_pattern_returns_none():
    repository = FinalPatternRepository()

    assert repository.get("missing") is None


def test_empty_repository_count_is_zero():
    repository = FinalPatternRepository()

    assert repository.count() == 0


def test_get_all_returns_all_patterns():
    repository = FinalPatternRepository()

    first = build_final_pattern(
        pattern_id="pattern-1",
        session_id="session-1",
    )

    second = build_final_pattern(
        pattern_id="pattern-2",
        session_id="session-2",
        operation_type="DELETE",
    )

    assert repository.store(first)
    assert repository.store(second)

    patterns = repository.get_all()

    assert len(patterns) == 2
    assert {pattern.pattern_id for pattern in patterns} == {
        "pattern-1",
        "pattern-2",
    }


def test_duplicate_pattern_id_is_rejected():
    repository = FinalPatternRepository()

    first = build_final_pattern(
        pattern_id="pattern-1",
        session_id="session-1",
    )

    second = build_final_pattern(
        pattern_id="pattern-1",
        session_id="session-2",
        operation_type="DELETE",
    )

    assert repository.store(first)
    assert not repository.store(second)
    assert repository.count() == 1


def test_repeated_behavior_is_not_stored_as_second_pattern():
    repository = FinalPatternRepository()

    first = build_final_pattern(
        pattern_id="pattern-1",
        session_id="session-1",
    )

    second = build_final_pattern(
        pattern_id="pattern-2",
        session_id="session-2",
    )

    assert repository.store(first)
    assert not repository.store(second)
    assert repository.count() == 1


def test_different_behavior_creates_new_pattern():
    repository = FinalPatternRepository()

    first = build_final_pattern(
        pattern_id="pattern-1",
        session_id="session-1",
    )

    second = build_final_pattern(
        pattern_id="pattern-2",
        session_id="session-2",
        operation_type="DELETE",
    )

    assert repository.store(first)
    assert repository.store(second)
    assert repository.count() == 2


def test_rejects_none():
    repository = FinalPatternRepository()

    assert not repository.store(None)


def test_rejects_candidate_pattern():
    from candidate_pattern_models import CandidatePattern

    repository = FinalPatternRepository()

    candidate = CandidatePattern(
        session_id="session-1",
    )

    assert not repository.store(candidate)


def test_rejects_missing_pattern_id():
    repository = FinalPatternRepository()

    pattern = build_final_pattern()
    pattern = FinalPattern(
        pattern_id="",
        session_id=pattern.session_id,
        user_id=pattern.user_id,
        created_at=pattern.created_at,
        observations=pattern.observations,
        observation_count=1,
    )

    assert not repository.store(pattern)


def test_rejects_empty_observations():
    repository = FinalPatternRepository()

    pattern = FinalPattern(
        pattern_id="pattern-1",
        session_id="session-1",
        user_id="user-1",
        created_at=datetime(2026, 9, 4, 10, 0, 0),
        observations=[],
        observation_count=0,
    )

    assert not repository.store(pattern)


def test_rejects_zero_observation_count():
    repository = FinalPatternRepository()

    pattern = build_final_pattern()

    pattern = FinalPattern(
        pattern_id=pattern.pattern_id,
        session_id=pattern.session_id,
        user_id=pattern.user_id,
        created_at=pattern.created_at,
        observations=pattern.observations,
        observation_count=0,
    )

    assert not repository.store(pattern)


def test_original_pattern_changes_do_not_affect_repository():
    repository = FinalPatternRepository()

    pattern = build_final_pattern()

    assert repository.store(pattern)

    pattern.observations[0]["directory"] = "/changed"

    stored = repository.get("pattern-1")

    assert stored is not None
    assert stored.observations[0]["directory"] == "/project"

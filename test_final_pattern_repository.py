from datetime import datetime

from final_pattern_models import FinalPattern
from final_pattern_repository import FinalPatternRepository
from repository_search_result import (
    RepositorySearchResult,
)


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


def test_repeated_behavior_strengthen_knowledge():
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
    assert repository.store(second)

    # Only one pattern stored, but knowledge strengthened
    assert repository.count() == 1
    assert repository.knowledge_count() == 1

    knowledge = repository.get_knowledge("knowledge-pattern-1")
    assert knowledge is not None
    assert knowledge.occurrence_count == 2


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


def test_repository_uses_injected_behavioral_identity():
    class StubBehavioralIdentity:
        def __init__(self):
            self.calls = 0

        def build_key(self, pattern):
            self.calls += 1
            return (
                "stub",
                pattern.pattern_id,
            )

    identity = StubBehavioralIdentity()

    repository = FinalPatternRepository(
        behavioral_identity=identity,
    )

    pattern = build_final_pattern(
        pattern_id="pattern-1",
    )

    assert repository.store(pattern)

    assert identity.calls == 1


def test_get_knowledge_returns_snapshot():
    repository = FinalPatternRepository()

    pattern = build_final_pattern()

    assert repository.store(pattern)

    knowledge = repository.get_knowledge("knowledge-pattern-1")

    assert knowledge is not None
    assert knowledge.knowledge_id == "knowledge-pattern-1"


def test_get_all_knowledge_returns_all():
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

    knowledge_list = repository.get_all_knowledge()

    assert len(knowledge_list) == 2
    assert {k.knowledge_id for k in knowledge_list} == {
        "knowledge-pattern-1",
        "knowledge-pattern-2",
    }


def test_knowledge_count_starts_at_zero():
    repository = FinalPatternRepository()

    assert repository.knowledge_count() == 0


def test_find_knowledge_returns_existing_behavior():
    repository = FinalPatternRepository()

    pattern = build_final_pattern(
        pattern_id="pattern-1",
        session_id="session-1",
    )

    assert repository.store(pattern)

    knowledge = repository.find_knowledge(
        pattern
    )

    assert knowledge is not None
    assert knowledge.knowledge_id == (
        "knowledge-pattern-1"
    )
    assert knowledge.representative_pattern_id == (
        "pattern-1"
    )


def test_find_knowledge_returns_none_for_unknown_behavior():
    repository = FinalPatternRepository()

    known = build_final_pattern(
        pattern_id="pattern-1",
        session_id="session-1",
    )

    unknown = build_final_pattern(
        pattern_id="pattern-2",
        session_id="session-2",
        operation_type="DELETE",
    )

    assert repository.store(known)

    assert repository.find_knowledge(
        unknown
    ) is None


def test_find_knowledge_returns_snapshot():
    repository = FinalPatternRepository()

    pattern = build_final_pattern()

    assert repository.store(pattern)

    first = repository.find_knowledge(
        pattern
    )

    second = repository.find_knowledge(
        pattern
    )

    assert first is not None
    assert second is not None
    assert first is not second


def test_find_representative_pattern_returns_existing_pattern():
    repository = FinalPatternRepository()

    first = build_final_pattern(
        pattern_id="pattern-1",
        session_id="session-1",
    )

    repeated = build_final_pattern(
        pattern_id="pattern-2",
        session_id="session-2",
    )

    assert repository.store(first)
    assert repository.store(repeated)

    assert repository.count() == 1
    assert repository.knowledge_count() == 1

    representative = repository.find_representative_pattern(
        repeated
    )

    assert representative is not None
    assert representative.pattern_id == (
        "pattern-1"
    )
    assert representative.session_id == (
        "session-1"
    )


def test_find_representative_pattern_returns_none_for_unknown():
    repository = FinalPatternRepository()

    pattern = build_final_pattern()

    assert repository.find_representative_pattern(
        pattern
    ) is None


def test_search_does_not_modify_knowledge():
    repository = FinalPatternRepository()

    pattern = build_final_pattern()

    assert repository.store(pattern)

    repository.find_knowledge(pattern)
    repository.find_knowledge(pattern)

    knowledge = repository.get_knowledge(
        "knowledge-pattern-1"
    )

    assert knowledge is not None
    assert knowledge.occurrence_count == 1


def test_search_does_not_modify_historical_pattern():
    repository = FinalPatternRepository()

    pattern = build_final_pattern()

    assert repository.store(pattern)

    repository.find_representative_pattern(
        pattern
    )

    stored = repository.get("pattern-1")

    assert stored is not None
    assert stored.pattern_id == "pattern-1"
    assert stored.observation_count == 1


def test_search_returns_no_match_for_unknown_behavior():
    repository = FinalPatternRepository()

    pattern = build_final_pattern()

    result = repository.search(pattern)

    assert result.matched is False
    assert result.representative_pattern is None
    assert result.behavioral_knowledge is None


def test_search_returns_match_for_known_behavior():
    repository = FinalPatternRepository()

    pattern = build_final_pattern()

    assert repository.store(pattern)

    result = repository.search(pattern)

    assert result.matched is True
    assert result.representative_pattern is not None
    assert result.representative_pattern.pattern_id == (
        "pattern-1"
    )
    assert result.behavioral_knowledge is not None
    assert result.behavioral_knowledge.knowledge_id == (
        "knowledge-pattern-1"
    )


def test_search_returns_representative_for_repeated_behavior():
    repository = FinalPatternRepository()

    first = build_final_pattern(
        pattern_id="pattern-1",
        session_id="session-1",
    )

    repeated = build_final_pattern(
        pattern_id="pattern-2",
        session_id="session-2",
    )

    assert repository.store(first)
    assert repository.store(repeated)

    result = repository.search(repeated)

    assert result.matched is True
    assert result.representative_pattern is not None
    assert result.representative_pattern.pattern_id == (
        "pattern-1"
    )
    assert result.behavioral_knowledge is not None
    assert result.behavioral_knowledge.occurrence_count == 2


def test_search_does_not_create_new_knowledge():
    repository = FinalPatternRepository()

    pattern = build_final_pattern()

    assert repository.store(pattern)

    result = repository.search(pattern)

    assert result.matched is True
    assert repository.count() == 1
    assert repository.knowledge_count() == 1


def test_search_rejects_invalid_pattern():
    repository = FinalPatternRepository()

    result = repository.search(None)

    assert result.matched is False
    assert result.representative_pattern is None
    assert result.behavioral_knowledge is None


def test_repository_search_delegates_to_search_service():
    repository = FinalPatternRepository()

    pattern = build_final_pattern()

    assert repository.store(pattern)

    class StubSearchService:
        def __init__(self):
            self.called = False

        def search(self, incoming_pattern):
            self.called = True

            assert incoming_pattern is pattern

            return RepositorySearchResult.no_match()

    stub = StubSearchService()

    repository._search_service = stub

    result = repository.search(pattern)

    assert result.matched is False
    assert stub.called is True

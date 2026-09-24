from datetime import datetime

from behavioral_identity import BehavioralIdentity
from final_pattern_models import FinalPattern
from final_pattern_repository import FinalPatternRepository
from pattern_reference import PatternReference
from repository_search_result import (
    RepositorySearchResult,
)
from repository_snapshot import RepositorySnapshot


def build_final_pattern(
    pattern_id="pattern-1",
    session_id="session-1",
    operation_type="CREATE",
    user_id="user-1",
):
    return FinalPattern(
        pattern_id=pattern_id,
        session_id=session_id,
        user_id=user_id,
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


def test_storing_same_pattern_twice_is_idempotent():
    repository = FinalPatternRepository()

    pattern = build_final_pattern(
        pattern_id="pattern-1",
        session_id="session-1",
    )

    assert repository.store(pattern)
    assert repository.store(pattern)

    assert repository.count() == 1
    assert repository.knowledge_count() == 1

    knowledge = repository.get_knowledge(
        "knowledge-pattern-1"
    )

    assert knowledge is not None
    assert knowledge.occurrence_count == 1


def test_same_pattern_id_is_not_counted_as_new_occurrence():
    repository = FinalPatternRepository()

    pattern = build_final_pattern(
        pattern_id="pattern-1",
        session_id="session-1",
    )

    assert repository.store(pattern)
    assert repository.store(pattern)

    assert repository.get_all()[0].pattern_id == (
        "pattern-1"
    )


def test_different_pattern_id_same_behavior_counts_as_occurrence():
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

    knowledge = repository.get_knowledge(
        "knowledge-pattern-1"
    )

    assert knowledge is not None
    assert knowledge.occurrence_count == 2


def test_different_pattern_id_same_behavior_is_not_stored_twice():
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

    assert repository.count() == 1
    assert repository.contains("pattern-1")
    assert not repository.contains("pattern-2")


def test_failed_repeated_recording_does_not_mark_pattern_as_recorded():
    class BrokenKnowledgeRepository(FinalPatternRepository):
        def _record_repeated_behavior(
            self,
            representative_pattern_id,
            incoming_pattern,
        ):
            return False

    repository = BrokenKnowledgeRepository()

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

    assert "pattern-2" not in (
        repository._recorded_pattern_ids
    )


def test_idempotent_store_does_not_change_search_result():
    repository = FinalPatternRepository()

    pattern = build_final_pattern(
        pattern_id="pattern-1",
        session_id="session-1",
    )

    assert repository.store(pattern)
    assert repository.store(pattern)

    result = repository.search(pattern)

    assert result.matched is True

    assert result.behavioral_knowledge is not None
    assert result.behavioral_knowledge.occurrence_count == 1


def test_find_knowledge_by_key_returns_existing_knowledge():
    repository = FinalPatternRepository()

    pattern = build_final_pattern(
        pattern_id="pattern-1",
        session_id="session-1",
    )

    assert repository.store(pattern)

    identity = BehavioralIdentity()

    key = identity.build_key(pattern)

    knowledge = repository.find_knowledge_by_key(
        key
    )

    assert knowledge is not None
    assert knowledge.knowledge_id == (
        "knowledge-pattern-1"
    )


def test_find_knowledge_by_key_returns_none_for_unknown_key():
    repository = FinalPatternRepository()

    pattern = build_final_pattern()

    identity = BehavioralIdentity()

    key = identity.build_key(pattern)

    assert repository.find_knowledge_by_key(
        key
    ) is None


def test_find_knowledge_by_key_returns_snapshot():
    repository = FinalPatternRepository()

    pattern = build_final_pattern()

    assert repository.store(pattern)

    identity = BehavioralIdentity()

    key = identity.build_key(pattern)

    first = repository.find_knowledge_by_key(
        key
    )

    second = repository.find_knowledge_by_key(
        key
    )

    assert first is not None
    assert second is not None
    assert first is not second


def test_find_knowledge_by_key_does_not_increment_occurrence():
    repository = FinalPatternRepository()

    pattern = build_final_pattern()

    assert repository.store(pattern)

    identity = BehavioralIdentity()

    key = identity.build_key(pattern)

    repository.find_knowledge_by_key(key)
    repository.find_knowledge_by_key(key)

    knowledge = repository.find_knowledge_by_key(
        key
    )

    assert knowledge is not None
    assert knowledge.occurrence_count == 1


def test_find_knowledge_by_key_returns_none_for_empty_key():
    repository = FinalPatternRepository()

    assert repository.find_knowledge_by_key(
        ()
    ) is None


def test_direct_key_lookup_matches_pattern_search():
    repository = FinalPatternRepository()

    pattern = build_final_pattern()

    assert repository.store(pattern)

    identity = BehavioralIdentity()

    key = identity.build_key(pattern)

    search_result = repository.search(
        pattern
    )

    key_result = repository.find_knowledge_by_key(
        key
    )

    assert search_result.matched is True
    assert search_result.behavioral_knowledge is not None
    assert key_result is not None

    assert key_result.knowledge_id == (
        search_result.behavioral_knowledge.knowledge_id
    )


def test_empty_repository_is_integrity_valid():
    repository = FinalPatternRepository()

    assert repository.validate_integrity() is True


def test_new_pattern_preserves_repository_integrity():
    repository = FinalPatternRepository()

    pattern = build_final_pattern()

    assert repository.store(pattern)
    assert repository.validate_integrity() is True


def test_repeated_behavior_preserves_repository_integrity():
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

    assert repository.validate_integrity() is True


def test_multiple_behaviors_preserve_repository_integrity():
    repository = FinalPatternRepository()

    first = build_final_pattern(
        pattern_id="pattern-1",
        session_id="session-1",
        operation_type="CREATE",
    )

    second = build_final_pattern(
        pattern_id="pattern-2",
        session_id="session-2",
        operation_type="DELETE",
    )

    third = build_final_pattern(
        pattern_id="pattern-3",
        session_id="session-3",
        operation_type="MODIFY",
    )

    assert repository.store(first)
    assert repository.store(second)
    assert repository.store(third)

    assert repository.count() == 3
    assert repository.knowledge_count() == 3
    assert repository.validate_integrity() is True


def test_retrieve_patterns_isolated_by_user():
    repository = FinalPatternRepository()

    user_one_pattern = FinalPattern(
        pattern_id="user1-pattern",
        session_id="user1-session",
        user_id="user-1",
        created_at=datetime(2026, 1, 1, 10, 0, 0),
        observations=[
            {
                "operation_type": "CREATE",
                "timestamp": datetime(2026, 1, 1, 10, 0, 0),
                "file_extension": ".py",
                "directory": "/user1",
            }
        ],
        observation_count=1,
    )

    user_two_pattern = FinalPattern(
        pattern_id="user2-pattern",
        session_id="user2-session",
        user_id="user-2",
        created_at=datetime(2026, 1, 2, 10, 0, 0),
        observations=[
            {
                "operation_type": "CREATE",
                "timestamp": datetime(2026, 1, 2, 10, 0, 0),
                "file_extension": ".py",
                "directory": "/user2",
            }
        ],
        observation_count=1,
    )

    assert repository.store(user_one_pattern) is True
    assert repository.store(user_two_pattern) is True

    user_one_history = repository.retrieve_patterns("user-1")
    user_two_history = repository.retrieve_patterns("user-2")

    assert [
        pattern.pattern_id
        for pattern in user_one_history
    ] == ["user1-pattern"]

    assert [
        pattern.pattern_id
        for pattern in user_two_history
    ] == ["user2-pattern"]

    assert repository.validate_integrity() is True


def test_retrieve_patterns_returns_user_history_chronologically():
    repository = FinalPatternRepository()

    patterns = [
        FinalPattern(
            pattern_id="pattern-3",
            session_id="session-3",
            user_id="user-1",
            created_at=datetime(2026, 1, 3),
            observations=[
                {"operation_type": "DELETE"}
            ],
            observation_count=1,
        ),
        FinalPattern(
            pattern_id="pattern-1",
            session_id="session-1",
            user_id="user-1",
            created_at=datetime(2026, 1, 1),
            observations=[
                {"operation_type": "CREATE"}
            ],
            observation_count=1,
        ),
        FinalPattern(
            pattern_id="pattern-2",
            session_id="session-2",
            user_id="user-1",
            created_at=datetime(2026, 1, 2),
            observations=[
                {"operation_type": "MODIFY"}
            ],
            observation_count=1,
        ),
    ]

    for pattern in patterns:
        assert repository.store(pattern) is True

    history = repository.get_behavior_history("user-1")

    assert [
        pattern.pattern_id
        for pattern in history
    ] == [
        "pattern-1",
        "pattern-2",
        "pattern-3",
    ]


def test_get_latest_pattern_returns_latest_user_pattern():
    repository = FinalPatternRepository()

    older = FinalPattern(
        pattern_id="older",
        session_id="session-older",
        user_id="user-1",
        created_at=datetime(2026, 1, 1),
        observations=[
            {"operation_type": "CREATE"}
        ],
        observation_count=1,
    )

    newer = FinalPattern(
        pattern_id="newer",
        session_id="session-newer",
        user_id="user-1",
        created_at=datetime(2026, 1, 5),
        observations=[
            {"operation_type": "DELETE"}
        ],
        observation_count=1,
    )

    assert repository.store(newer) is True
    assert repository.store(older) is True

    latest = repository.get_latest_pattern("user-1")

    assert latest is not None
    assert latest.pattern_id == "newer"


def test_duplicate_session_cannot_store_different_final_pattern():
    repository = FinalPatternRepository()

    first = FinalPattern(
        pattern_id="pattern-1",
        session_id="same-session",
        user_id="user-1",
        created_at=datetime(2026, 1, 1),
        observations=[
            {"operation_type": "CREATE"}
        ],
        observation_count=1,
    )

    duplicate_session = FinalPattern(
        pattern_id="pattern-2",
        session_id="same-session",
        user_id="user-1",
        created_at=datetime(2026, 1, 2),
        observations=[
            {"operation_type": "DELETE"}
        ],
        observation_count=1,
    )

    assert repository.store(first) is True
    assert repository.store(duplicate_session) is False

    assert repository.count() == 1
    assert repository.validate_integrity() is True


def test_retrieved_history_is_detached_from_repository():
    repository = FinalPatternRepository()

    pattern = FinalPattern(
        pattern_id="pattern-1",
        session_id="session-1",
        user_id="user-1",
        created_at=datetime(2026, 1, 1),
        observations=[
            {"operation_type": "CREATE"}
        ],
        observation_count=1,
    )

    assert repository.store(pattern) is True

    history = repository.retrieve_patterns("user-1")

    assert len(history) == 1

    history[0].observations[0]["operation_type"] = "DELETE"

    reread = repository.retrieve_patterns("user-1")

    assert (
        reread[0].observations[0]["operation_type"]
        == "CREATE"
    )

    assert repository.validate_integrity() is True


def test_integrity_detects_orphaned_pattern_index():
    repository = FinalPatternRepository()

    pattern = build_final_pattern()

    assert repository.store(pattern)

    key = next(
        iter(repository._pattern_index)
    )

    repository._pattern_index[key] = (
        "missing-pattern"
    )

    assert repository.validate_integrity() is False


def test_integrity_detects_orphaned_knowledge():
    repository = FinalPatternRepository()

    pattern = build_final_pattern()

    assert repository.store(pattern)

    repository._knowledge[
        "knowledge-orphan"
    ] = repository._knowledge[
        "knowledge-pattern-1"
    ].snapshot()

    assert repository.validate_integrity() is False


def test_integrity_detects_missing_recorded_id():
    repository = FinalPatternRepository()

    pattern = build_final_pattern()

    assert repository.store(pattern)

    repository._recorded_pattern_ids.clear()

    assert repository.validate_integrity() is False


def test_integrity_detects_user_index_mismatch():
    repository = FinalPatternRepository()

    pattern = build_final_pattern()

    assert repository.store(pattern)

    # Corrupt user index by adding a non-existent pattern
    repository._user_pattern_index["user-1"].append("non-existent")

    assert repository.validate_integrity() is False


def test_integrity_detects_session_index_mismatch():
    repository = FinalPatternRepository()

    pattern = build_final_pattern()

    assert repository.store(pattern)

    # Corrupt session index by pointing to non-existent pattern
    repository._session_pattern_index["session-1"] = "non-existent"

    assert repository.validate_integrity() is False


def test_integrity_detects_missing_user_history_reference():
    repository = FinalPatternRepository()

    pattern = build_final_pattern()

    assert repository.store(pattern)

    # Remove pattern from user index
    repository._user_pattern_index["user-1"] = []

    assert repository.validate_integrity() is False


def test_first_final_pattern_creates_user_baseline():
    repository = FinalPatternRepository()

    pattern = FinalPattern(
        pattern_id="baseline-1",
        session_id="session-1",
        user_id="user-1",
        created_at=datetime(2026, 1, 1),
        observations=[
            {"operation_type": "CREATE"}
        ],
        observation_count=1,
    )

    assert repository.store(pattern) is True

    assert repository.has_baseline("user-1") is True

    baseline = repository.get_baseline_pattern(
        "user-1"
    )

    assert baseline is not None
    assert baseline.pattern_id == "baseline-1"

    assert repository.validate_integrity() is True


def test_later_final_pattern_does_not_replace_baseline():
    repository = FinalPatternRepository()

    first = FinalPattern(
        pattern_id="pattern-1",
        session_id="session-1",
        user_id="user-1",
        created_at=datetime(2026, 1, 1),
        observations=[
            {"operation_type": "CREATE"}
        ],
        observation_count=1,
    )

    second = FinalPattern(
        pattern_id="pattern-2",
        session_id="session-2",
        user_id="user-1",
        created_at=datetime(2026, 1, 2),
        observations=[
            {"operation_type": "DELETE"}
        ],
        observation_count=1,
    )

    assert repository.store(first) is True
    assert repository.store(second) is True

    baseline = repository.get_baseline_pattern(
        "user-1"
    )

    assert baseline is not None
    assert baseline.pattern_id == "pattern-1"

    assert repository.validate_integrity() is True


def test_each_user_gets_independent_baseline():
    repository = FinalPatternRepository()

    user_one = FinalPattern(
        pattern_id="user1-pattern",
        session_id="user1-session",
        user_id="user-1",
        created_at=datetime(2026, 1, 1),
        observations=[
            {"operation_type": "CREATE"}
        ],
        observation_count=1,
    )

    user_two = FinalPattern(
        pattern_id="user2-pattern",
        session_id="user2-session",
        user_id="user-2",
        created_at=datetime(2026, 1, 1),
        observations=[
            {"operation_type": "DELETE"}
        ],
        observation_count=1,
    )

    assert repository.store(user_one) is True
    assert repository.store(user_two) is True

    assert (
        repository.get_baseline_pattern("user-1").pattern_id
        == "user1-pattern"
    )

    assert (
        repository.get_baseline_pattern("user-2").pattern_id
        == "user2-pattern"
    )

    assert repository.validate_integrity() is True


def test_repeated_behavior_does_not_create_second_baseline():
    repository = FinalPatternRepository()

    first = build_final_pattern(
        pattern_id="pattern-1",
        session_id="session-1",
    )

    # Same user, same behavioral identity, different session.
    repeated = build_final_pattern(
        pattern_id="pattern-2",
        session_id="session-2",
    )

    assert repository.store(first) is True
    assert repository.store(repeated) is True

    baseline = repository.get_baseline_pattern(
        "user-1"
    )

    assert baseline is not None
    assert baseline.pattern_id == "pattern-1"

    knowledge = repository.get_knowledge(
        "knowledge-pattern-1"
    )

    assert knowledge is not None
    assert knowledge.occurrence_count == 2

    metadata = repository.get_repository_metadata()

    assert metadata["pattern_count"] == 1
    assert metadata["knowledge_count"] == 1
    assert metadata["user_count"] == 1
    assert metadata["session_count"] == 2
    assert metadata["occurrence_count"] == 1
    assert metadata["baseline_count"] == 1

    assert repository.validate_integrity() is True


def test_repository_metadata_reflects_current_state():
    repository = FinalPatternRepository()

    pattern = FinalPattern(
        pattern_id="pattern-1",
        session_id="session-1",
        user_id="user-1",
        created_at=datetime(2026, 1, 1),
        observations=[
            {"operation_type": "CREATE"}
        ],
        observation_count=1,
    )

    assert repository.get_repository_metadata() == {
        "pattern_count": 0,
        "knowledge_count": 0,
        "user_count": 0,
        "session_count": 0,
        "occurrence_count": 0,
        "baseline_count": 0,
    }

    assert repository.store(pattern) is True

    metadata = repository.get_repository_metadata()

    assert metadata["pattern_count"] == 1
    assert metadata["knowledge_count"] == 1
    assert metadata["user_count"] == 1
    assert metadata["session_count"] == 1
    assert metadata["baseline_count"] == 1
    assert metadata["occurrence_count"] == 0

    assert repository.validate_integrity() is True


def test_failed_store_does_not_create_baseline(monkeypatch):
    repository = FinalPatternRepository()

    pattern = build_final_pattern()

    class FailingRecordedPatternIds(set):
        def add(self, pattern_id):
            raise RuntimeError(
                "forced recorded pattern registration failure"
            )

    monkeypatch.setattr(
        repository,
        "_recorded_pattern_ids",
        FailingRecordedPatternIds(),
    )

    assert repository.store(pattern) is False

    assert repository.has_baseline("user-1") is False
    assert repository.get_baseline_pattern("user-1") is None

    assert repository.count() == 0
    assert repository.knowledge_count() == 0

    metadata = repository.get_repository_metadata()

    assert metadata["user_count"] == 0
    assert metadata["baseline_count"] == 0

    assert repository.validate_integrity() is True


def test_failed_store_preserves_existing_baseline(monkeypatch):
    repository = FinalPatternRepository()

    first = build_final_pattern()

    assert repository.store(first) is True

    second = build_final_pattern(
        pattern_id="pattern-2",
        session_id="session-2",
        operation_type="DELETE",
    )

    class FailingRecordedPatternIds(set):
        def add(self, pattern_id):
            raise RuntimeError(
                "forced recorded pattern registration failure"
            )

    monkeypatch.setattr(
        repository,
        "_recorded_pattern_ids",
        FailingRecordedPatternIds(
            repository._recorded_pattern_ids
        ),
    )

    assert repository.store(second) is False

    baseline = repository.get_baseline_pattern(
        "user-1"
    )

    assert baseline is not None
    assert baseline.pattern_id == "pattern-1"

    assert repository.has_baseline("user-1") is True

    metadata = repository.get_repository_metadata()

    assert metadata["pattern_count"] == 1
    assert metadata["user_count"] == 1
    assert metadata["baseline_count"] == 1

    assert repository.validate_integrity() is True


def test_integrity_detects_missing_knowledge():
    repository = FinalPatternRepository()

    pattern = build_final_pattern()

    assert repository.store(pattern)

    repository._knowledge.clear()

    assert repository.validate_integrity() is False


def test_repository_rejects_inconsistent_observation_count():
    repository = FinalPatternRepository()
    pattern = FinalPattern(
        pattern_id="pattern-1",
        session_id="session-1",
        user_id="user-1",
        created_at=datetime(2026, 9, 4, 10, 0, 0),
        observations=[
            {"operation_type": "CREATE", "timestamp": datetime(2026, 9, 4, 10, 0, 0), "file_extension": ".py", "directory": "/project"},
            {"operation_type": "DELETE", "timestamp": datetime(2026, 9, 4, 10, 0, 0), "file_extension": ".py", "directory": "/project"},
        ],
        observation_count=1,
    )
    assert repository.store(pattern) is False
    assert repository.count() == 0
    assert repository.validate_integrity() is True


def test_repository_rejects_non_dict_observation():
    repository = FinalPatternRepository()
    pattern = FinalPattern(
        pattern_id="pattern-1",
        session_id="session-1",
        user_id="user-1",
        created_at=datetime(2026, 9, 4, 10, 0, 0),
        observations=["invalid"],
        observation_count=1,
    )
    assert repository.store(pattern) is False
    assert repository.count() == 0


def test_get_all_returns_patterns_in_chronological_order():
    repository = FinalPatternRepository()
    newest = FinalPattern(
        pattern_id="pattern-new",
        session_id="session-new",
        user_id="user-1",
        created_at=datetime(2026, 1, 3),
        observations=[
            {
                "operation_type": "DELETE",
                "timestamp": datetime(2026, 1, 3),
                "file_extension": ".py",
                "directory": "/project",
            }
        ],
        observation_count=1,
    )
    oldest = FinalPattern(
        pattern_id="pattern-old",
        session_id="session-old",
        user_id="user-1",
        created_at=datetime(2026, 1, 1),
        observations=[
            {
                "operation_type": "CREATE",
                "timestamp": datetime(2026, 1, 1),
                "file_extension": ".py",
                "directory": "/project",
            }
        ],
        observation_count=1,
    )
    middle = FinalPattern(
        pattern_id="pattern-middle",
        session_id="session-middle",
        user_id="user-1",
        created_at=datetime(2026, 1, 2),
        observations=[
            {
                "operation_type": "MODIFY",
                "timestamp": datetime(2026, 1, 2),
                "file_extension": ".py",
                "directory": "/project",
            }
        ],
        observation_count=1,
    )
    assert repository.store(newest) is True
    assert repository.store(oldest) is True
    assert repository.store(middle) is True

    patterns = repository.get_all()
    assert len(patterns) == 3
    assert patterns[0].pattern_id == "pattern-old"
    assert patterns[1].pattern_id == "pattern-middle"
    assert patterns[2].pattern_id == "pattern-new"


def test_occurrence_id_reuse_for_different_behavior_is_rejected():
    repository = FinalPatternRepository()
    first = build_final_pattern(
        pattern_id="pattern-1",
        session_id="session-1",
        operation_type="CREATE",
    )
    repeated = build_final_pattern(
        pattern_id="pattern-2",
        session_id="session-2",
        operation_type="CREATE",
    )
    conflicting = build_final_pattern(
        pattern_id="pattern-2",
        session_id="session-3",
        operation_type="DELETE",
    )
    assert repository.store(first) is True
    assert repository.store(repeated) is True
    assert repository.store(conflicting) is False
    assert repository.count() == 1
    assert repository.validate_integrity() is True


def test_get_pattern_references_returns_historical_references():
    repository = FinalPatternRepository()

    pattern = FinalPattern(
        pattern_id="pattern-1",
        session_id="session-1",
        user_id="user-1",
        created_at=datetime(2026, 1, 1),
        observations=[
            {"operation_type": "CREATE"}
        ],
        observation_count=1,
    )

    assert repository.store(pattern) is True

    references = repository.get_pattern_references(
        "user-1"
    )

    assert len(references) == 1

    reference = references[0]

    assert reference.pattern_id == "pattern-1"
    assert reference.session_id == "session-1"
    assert reference.user_id == "user-1"
    assert reference.created_at == pattern.created_at


def test_pattern_reference_resolves_to_detached_pattern():
    repository = FinalPatternRepository()

    pattern = FinalPattern(
        pattern_id="pattern-1",
        session_id="session-1",
        user_id="user-1",
        created_at=datetime(2026, 1, 1),
        observations=[
            {"operation_type": "CREATE"}
        ],
        observation_count=1,
    )

    assert repository.store(pattern) is True

    reference = repository.get_pattern_references(
        "user-1"
    )[0]

    resolved = repository.resolve_pattern_reference(
        reference
    )

    assert resolved is not None
    assert resolved.pattern_id == "pattern-1"
    assert resolved is not pattern


def test_invalid_pattern_reference_returns_none():
    repository = FinalPatternRepository()

    invalid_reference = PatternReference(
        pattern_id="missing",
        session_id="session-1",
        user_id="user-1",
        created_at=datetime(2026, 1, 1),
    )

    assert (
        repository.resolve_pattern_reference(
            invalid_reference
        )
        is None
    )


def test_tampered_pattern_reference_is_rejected():
    repository = FinalPatternRepository()

    pattern = FinalPattern(
        pattern_id="pattern-1",
        session_id="session-1",
        user_id="user-1",
        created_at=datetime(2026, 1, 1),
        observations=[
            {"operation_type": "CREATE"}
        ],
        observation_count=1,
    )

    assert repository.store(pattern) is True

    tampered = PatternReference(
        pattern_id="pattern-1",
        session_id="wrong-session",
        user_id="user-1",
        created_at=pattern.created_at,
    )

    assert (
        repository.resolve_pattern_reference(
            tampered
        )
        is None
    )


def test_retrieve_recent_patterns_respects_limit():
    repository = FinalPatternRepository()

    for index, operation in enumerate(
        ["CREATE", "MODIFY", "DELETE", "MOVE"],
        start=1,
    ):
        pattern = FinalPattern(
            pattern_id=f"pattern-{index}",
            session_id=f"session-{index}",
            user_id="user-1",
            created_at=datetime(
                2026,
                1,
                index,
            ),
            observations=[
                {
                    "operation_type": operation,
                }
            ],
            observation_count=1,
        )

        assert repository.store(pattern) is True

    recent = repository.retrieve_recent_patterns(
        "user-1",
        2,
    )

    assert [
        pattern.pattern_id
        for pattern in recent
    ] == [
        "pattern-3",
        "pattern-4",
    ]


def test_recent_pattern_retrieval_rejects_non_positive_limit():
    repository = FinalPatternRepository()

    assert (
        repository.retrieve_recent_patterns(
            "user-1",
            0,
        )
        == []
    )

    assert (
        repository.retrieve_recent_patterns(
            "user-1",
            -1,
        )
        == []
    )


def test_snapshot_round_trip_restores_history():
    source = FinalPatternRepository()

    first = build_final_pattern(
        pattern_id="pattern-1",
        session_id="session-1",
    )

    second = build_final_pattern(
        pattern_id="pattern-2",
        session_id="session-2",
        operation_type="DELETE",
    )

    assert source.store(first) is True
    assert source.store(second) is True

    snapshot = source.create_snapshot()

    recovered = FinalPatternRepository()

    assert recovered.restore_snapshot(snapshot) is True

    assert recovered.count() == source.count()

    assert [
        pattern.pattern_id
        for pattern in recovered.retrieve_patterns(
            "user-1"
        )
    ] == [
        pattern.pattern_id
        for pattern in source.retrieve_patterns(
            "user-1"
        )
    ]


def test_created_snapshot_is_detached_from_repository():
    repository = FinalPatternRepository()

    pattern = build_final_pattern()

    assert repository.store(pattern) is True

    snapshot = repository.create_snapshot()

    # A snapshot is a detached logical container. Mutating it must never
    # modify the live repository.
    snapshot.patterns[0] = build_final_pattern(
        pattern_id="pattern-tampered",
        session_id="session-tampered",
    )

    snapshot.knowledge[0].occurrence_count = 99

    snapshot.pattern_index.clear()
    snapshot.session_pattern_index.clear()

    snapshot.user_pattern_index["user-1"].append(
        "pattern-tampered"
    )

    snapshot.recorded_pattern_ids.append(
        "pattern-tampered"
    )

    snapshot.recorded_occurrence_ids.append(
        "pattern-tampered"
    )

    snapshot.occurrence_behavior_keys[
        "pattern-tampered"
    ] = (
        "user-1",
        ("CREATE",),
        (".py",),
        ("/project",),
    )

    snapshot.baseline_pattern_ids["user-1"] = (
        "pattern-tampered"
    )

    assert repository.count() == 1
    assert repository.knowledge_count() == 1
    assert repository.contains("pattern-tampered") is False

    assert [
        pattern.pattern_id
        for pattern in repository.retrieve_patterns(
            "user-1"
        )
    ] == ["pattern-1"]

    baseline = repository.get_baseline_pattern("user-1")

    assert baseline is not None
    assert baseline.pattern_id == "pattern-1"

    knowledge = repository.get_knowledge(
        "knowledge-pattern-1"
    )

    assert knowledge is not None
    assert knowledge.occurrence_count == 1

    assert repository.search(pattern).matched is True

    assert repository.validate_integrity() is True


def test_restore_snapshot_after_shutdown_preserves_state():
    repository = FinalPatternRepository()

    for index, operation in enumerate(
        ["CREATE", "MODIFY", "DELETE"],
        start=1,
    ):
        pattern = FinalPattern(
            pattern_id=f"pattern-{index}",
            session_id=f"session-{index}",
            user_id="user-1",
            created_at=datetime(
                2026,
                1,
                index,
            ),
            observations=[
                {
                    "operation_type": operation,
                }
            ],
            observation_count=1,
        )

        assert repository.store(pattern) is True

    snapshot = repository.create_snapshot()

    references = repository.get_pattern_references(
        "user-1"
    )

    baseline = repository.get_baseline_pattern("user-1")
    latest = repository.get_latest_pattern("user-1")

    assert baseline is not None
    assert latest is not None

    # Simulated shutdown: a fresh repository instance recovers its
    # logical state from the snapshot alone.
    recovered = FinalPatternRepository()

    assert recovered.restore_snapshot(snapshot) is True

    assert recovered.count() == 3
    assert recovered.knowledge_count() == 3

    assert [
        pattern.pattern_id
        for pattern in recovered.retrieve_patterns(
            "user-1"
        )
    ] == [
        "pattern-1",
        "pattern-2",
        "pattern-3",
    ]

    restored_baseline = recovered.get_baseline_pattern(
        "user-1"
    )

    assert restored_baseline is not None
    assert restored_baseline.pattern_id == (
        baseline.pattern_id
    )

    restored_latest = recovered.get_latest_pattern(
        "user-1"
    )

    assert restored_latest is not None
    assert restored_latest.pattern_id == latest.pattern_id

    restored_references = (
        recovered.get_pattern_references("user-1")
    )

    assert [
        (
            reference.pattern_id,
            reference.session_id,
            reference.user_id,
            reference.created_at,
        )
        for reference in restored_references
    ] == [
        (
            reference.pattern_id,
            reference.session_id,
            reference.user_id,
            reference.created_at,
        )
        for reference in references
    ]

    resolved = recovered.resolve_pattern_reference(
        restored_references[0]
    )

    assert resolved is not None
    assert resolved.pattern_id == "pattern-1"

    assert recovered.validate_integrity() is True


def test_restored_repository_resumes_normal_search():
    repository = FinalPatternRepository()

    pattern = build_final_pattern()

    assert repository.store(pattern) is True

    snapshot = repository.create_snapshot()

    recovered = FinalPatternRepository()

    assert recovered.restore_snapshot(snapshot) is True

    result = recovered.search(pattern)

    assert result.matched is True
    assert result.representative_pattern is not None
    assert result.representative_pattern.pattern_id == (
        "pattern-1"
    )
    assert result.behavioral_knowledge is not None


def test_corrupted_snapshot_is_rejected_without_changes():
    repository = FinalPatternRepository()

    pattern = build_final_pattern()

    assert repository.store(pattern) is True

    corrupted = RepositorySnapshot(
        patterns="not-a-list",
        knowledge=None,
        pattern_index="not-a-dict",
        user_pattern_index=[],
        session_pattern_index=None,
        recorded_pattern_ids=[],
        recorded_occurrence_ids=[],
        occurrence_behavior_keys={},
        baseline_pattern_ids={},
    )

    assert repository.validate_snapshot(corrupted) is False
    assert repository.validate_snapshot(None) is False
    assert repository.validate_snapshot("not-a-snapshot") is (
        False
    )

    assert repository.restore_snapshot(corrupted) is False
    assert repository.restore_snapshot(None) is False

    assert repository.count() == 1
    assert repository.contains("pattern-1") is True

    baseline = repository.get_baseline_pattern("user-1")

    assert baseline is not None
    assert baseline.pattern_id == "pattern-1"

    assert repository.validate_integrity() is True


def test_failed_restore_preserves_original_state(monkeypatch):
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

    assert repository.store(first) is True
    assert repository.store(second) is True

    incoming = FinalPatternRepository()

    replacement = FinalPattern(
        pattern_id="pattern-recovered",
        session_id="session-recovered",
        user_id="user-1",
        created_at=datetime(2026, 5, 1),
        observations=[
            {
                "operation_type": "MOVE",
            }
        ],
        observation_count=1,
    )

    assert incoming.store(replacement) is True

    snapshot = incoming.create_snapshot()

    # Force integrity validation to reject the restored state.
    monkeypatch.setattr(
        repository,
        "validate_integrity",
        lambda: False,
    )

    assert repository.restore_snapshot(snapshot) is False

    monkeypatch.undo()

    assert repository.count() == 2
    assert repository.contains("pattern-recovered") is False

    assert [
        pattern.pattern_id
        for pattern in repository.retrieve_patterns(
            "user-1"
        )
    ] == ["pattern-1", "pattern-2"]

    baseline = repository.get_baseline_pattern("user-1")
    latest = repository.get_latest_pattern("user-1")

    assert baseline is not None
    assert baseline.pattern_id == "pattern-1"

    assert latest is not None
    assert latest.pattern_id == "pattern-2"

    # The rollback must restore the behavioral search boundary too.
    assert repository.search(first).matched is True

    assert repository.validate_integrity() is True


def test_pattern_version_and_learning_metadata_are_preserved():
    repository = FinalPatternRepository()

    pattern = FinalPattern(
        pattern_id="pattern-1",
        session_id="session-1",
        user_id="user-1",
        created_at=datetime(2026, 1, 1),
        pattern_version=2,
        learning_metadata={
            "origin": "candidate_pattern_manager",
            "reason": "behavioral_evolution",
        },
        observations=[
            {"operation_type": "CREATE"}
        ],
        observation_count=1,
    )

    assert repository.store(pattern) is True

    stored = repository.get("pattern-1")

    assert stored is not None
    assert stored.pattern_version == 2
    assert stored.learning_metadata == {
        "origin": "candidate_pattern_manager",
        "reason": "behavioral_evolution",
    }


def test_repository_rejects_invalid_pattern_version():
    repository = FinalPatternRepository()

    pattern = FinalPattern(
        pattern_id="pattern-1",
        session_id="session-1",
        user_id="user-1",
        created_at=datetime(2026, 1, 1),
        pattern_version=0,
        observations=[
            {"operation_type": "CREATE"}
        ],
        observation_count=1,
    )

    assert repository.store(pattern) is False
    assert repository.count() == 0


def test_repository_rejects_invalid_learning_metadata():
    repository = FinalPatternRepository()

    pattern = FinalPattern(
        pattern_id="pattern-1",
        session_id="session-1",
        user_id="user-1",
        created_at=datetime(2026, 1, 1),
        learning_metadata="invalid",
        observations=[
            {"operation_type": "CREATE"}
        ],
        observation_count=1,
    )

    assert repository.store(pattern) is False
    assert repository.count() == 0


def test_repository_rejects_final_pattern_without_user_id():
    repository = FinalPatternRepository()

    pattern = build_final_pattern(
        user_id=None,
    )

    assert repository.store(
        pattern
    ) is False

    assert repository.count() == 0


def test_repository_rejects_blank_user_id():
    repository = FinalPatternRepository()

    pattern = build_final_pattern(
        user_id="   ",
    )

    assert repository.store(
        pattern
    ) is False

    assert repository.count() == 0


def test_repository_rejects_non_identity_user_values():
    repository = FinalPatternRepository()

    for invalid_user_id in ("", 123, []):
        pattern = build_final_pattern(
            user_id=invalid_user_id,
        )

        assert repository.store(pattern) is False
        assert repository.count() == 0


def test_same_behavior_is_not_consolidated_across_users():
    repository = FinalPatternRepository()

    user_a = build_final_pattern(
        pattern_id="pattern-a",
        session_id="session-a",
        user_id="user-a",
    )

    user_b = build_final_pattern(
        pattern_id="pattern-b",
        session_id="session-b",
        user_id="user-b",
    )

    assert repository.store(user_a) is True
    assert repository.store(user_b) is True

    assert repository.count() == 2
    assert repository.knowledge_count() == 2

    assert len(
        repository.retrieve_patterns("user-a")
    ) == 1

    assert len(
        repository.retrieve_patterns("user-b")
    ) == 1

    knowledge_a = repository.get_knowledge(
        "knowledge-pattern-a"
    )

    knowledge_b = repository.get_knowledge(
        "knowledge-pattern-b"
    )

    assert knowledge_a is not None
    assert knowledge_b is not None
    assert knowledge_a.occurrence_count == 1
    assert knowledge_b.occurrence_count == 1

    assert repository.validate_integrity() is True


def test_userless_history_retrieval_fails_closed():
    repository = FinalPatternRepository()

    pattern = build_final_pattern(
        user_id="user-a",
    )

    assert repository.store(
        pattern
    ) is True

    assert repository.retrieve_patterns(
        None
    ) == []

    assert repository.get_behavior_history(
        None
    ) == []

    assert repository.get_latest_pattern(
        None
    ) is None

    assert repository.get_baseline_pattern(
        None
    ) is None

    assert repository.has_baseline(
        None
    ) is False


def test_userless_reference_retrieval_fails_closed():
    repository = FinalPatternRepository()

    pattern = build_final_pattern(
        user_id="user-a",
    )

    repository.store(pattern)

    assert repository.retrieve_recent_patterns(
        None,
        limit=10,
    ) == []

    assert repository.get_pattern_references(
        None
    ) == []

    assert repository.get_recent_pattern_references(
        None,
        limit=10,
    ) == []

    assert repository.retrieve_recent_patterns(
        "   ",
        limit=10,
    ) == []

    assert repository.get_pattern_references(
        "   "
    ) == []

    assert repository.get_recent_pattern_references(
        "   ",
        limit=10,
    ) == []


def test_pattern_reference_cannot_cross_user_boundary():
    repository = FinalPatternRepository()

    pattern = build_final_pattern(
        user_id="user-a",
    )

    repository.store(pattern)

    stored = repository.get_all()[0]

    reference = PatternReference(
        pattern_id=stored.pattern_id,
        session_id=stored.session_id,
        user_id="user-b",
        created_at=stored.created_at,
    )

    assert repository.resolve_pattern_reference(
        reference
    ) is None


def test_repository_integrity_rejects_userless_state():
    repository = FinalPatternRepository()

    invalid_pattern = build_final_pattern(
        user_id=None,
    )

    repository._patterns[
        invalid_pattern.pattern_id
    ] = invalid_pattern

    assert repository.validate_integrity() is False

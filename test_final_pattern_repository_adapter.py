from datetime import datetime

from candidate_pattern_models import CandidatePattern
from final_pattern_repository import FinalPatternRepository
from final_pattern_repository_adapter import (
    FinalPatternRepositoryAdapter,
)


def build_completed_candidate(
    session_id="session-1",
):
    pattern = CandidatePattern(
        session_id=session_id,
        user_id="user-1",
    )

    pattern.add_observation(
        {
            "operation_type": "CREATE",
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
    )

    pattern.mark_finalized(
        datetime(
            2026,
            9,
            4,
            10,
            0,
            0,
        )
    )

    pattern.mark_completed()

    return pattern


def test_adapter_stores_completed_candidate():
    repository = FinalPatternRepository()

    adapter = FinalPatternRepositoryAdapter(
        repository=repository,
    )

    candidate = build_completed_candidate()

    assert adapter.store(candidate) is True
    assert repository.count() == 1
    assert repository.knowledge_count() == 1


def test_adapter_rejects_incomplete_candidate():
    repository = FinalPatternRepository()

    adapter = FinalPatternRepositoryAdapter(
        repository=repository,
    )

    candidate = CandidatePattern(
        session_id="session-1",
        user_id="user-1",
    )

    assert adapter.store(candidate) is False
    assert repository.count() == 0


def test_adapter_rejects_empty_candidate():
    repository = FinalPatternRepository()

    adapter = FinalPatternRepositoryAdapter(
        repository=repository,
    )

    candidate = CandidatePattern(
        session_id="session-1",
        user_id="user-1",
    )

    candidate.mark_finalized()

    assert adapter.store(candidate) is False
    assert repository.count() == 0


def test_adapter_uses_supplied_repository():
    repository = FinalPatternRepository()

    adapter = FinalPatternRepositoryAdapter(
        repository=repository,
    )

    assert adapter.get_repository() is repository


def test_adapter_creates_final_pattern_with_factory():
    repository = FinalPatternRepository()

    adapter = FinalPatternRepositoryAdapter(
        repository=repository,
    )

    candidate = build_completed_candidate()

    assert adapter.store(candidate)

    stored_patterns = repository.get_all()

    assert len(stored_patterns) == 1
    assert stored_patterns[0].session_id == (
        "session-1"
    )
    assert stored_patterns[0].user_id == (
        "user-1"
    )


def test_repeated_behavior_updates_knowledge():
    repository = FinalPatternRepository()

    adapter = FinalPatternRepositoryAdapter(
        repository=repository,
    )

    first = build_completed_candidate(
        session_id="session-1",
    )

    second = build_completed_candidate(
        session_id="session-2",
    )

    assert adapter.store(first)
    assert adapter.store(second)

    assert repository.count() == 1
    assert repository.knowledge_count() == 1

    knowledge = repository.get_knowledge(
        "knowledge-" + repository.get_all()[0].pattern_id
    )

    assert knowledge is not None
    assert knowledge.occurrence_count == 2


def test_failed_repository_store_is_returned():
    class FailingRepository:
        def store(self, pattern):
            return False

    adapter = FinalPatternRepositoryAdapter(
        repository=FailingRepository(),
    )

    candidate = build_completed_candidate()

    assert adapter.store(candidate) is False

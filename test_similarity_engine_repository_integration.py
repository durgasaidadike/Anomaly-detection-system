from datetime import datetime

from final_pattern_models import FinalPattern
from final_pattern_repository import FinalPatternRepository
from similarity_engine import SimilarityEngine
from similarity_result import SimilarityStatus


def build_final_pattern(
    pattern_id,
    session_id,
    user_id,
    *,
    operational,
    temporal=None,
    sequential=None,
    contextual=None,
    relationship=None,
    session=None,
):
    return FinalPattern(
        pattern_id=pattern_id,
        session_id=session_id,
        user_id=user_id,
        created_at=datetime(2026, 9, 1, 10, 0, 0),
        observations=[
            {
                "operation_type": "CREATE",
                "timestamp": datetime(2026, 9, 1, 10, 0, 0),
            }
        ],
        operational_characteristics=operational,
        temporal_characteristics=(
            temporal if temporal is not None else {}
        ),
        sequential_characteristics=(
            sequential if sequential is not None else []
        ),
        contextual_characteristics=(
            contextual if contextual is not None else {}
        ),
        relationship_characteristics=(
            relationship if relationship is not None else []
        ),
        session_characteristics=(
            session if session is not None else {}
        ),
        observation_count=1,
    )


def build_candidate(
    *,
    session_id,
    user_id,
    operational,
    temporal=None,
    sequential=None,
    contextual=None,
    relationship=None,
    session=None,
):
    """
    Lightweight Candidate Pattern representation for the integration
    boundary. The repository underneath is the real implementation.
    """

    class Candidate:
        pass

    candidate = Candidate()

    candidate.session_id = session_id
    candidate.user_id = user_id

    candidate.operational_characteristics = operational
    candidate.temporal_characteristics = (
        temporal if temporal is not None else {}
    )
    candidate.sequential_characteristics = (
        sequential if sequential is not None else []
    )
    candidate.contextual_characteristics = (
        contextual if contextual is not None else {}
    )
    candidate.relationship_characteristics = (
        relationship if relationship is not None else []
    )
    candidate.session_characteristics = (
        session if session is not None else {}
    )

    return candidate


def test_similarity_engine_uses_real_final_pattern_repository():
    repository = FinalPatternRepository()

    historical = build_final_pattern(
        pattern_id="final-001",
        session_id="historical-session-001",
        user_id="user-001",
        operational={
            "create": 5,
            "modify": 2,
        },
    )

    assert repository.store(historical) is True

    candidate = build_candidate(
        session_id="candidate-session-001",
        user_id="user-001",
        operational={
            "create": 5,
            "modify": 2,
        },
    )

    engine = SimilarityEngine(repository)

    result = engine.evaluate(candidate)

    assert result.status == SimilarityStatus.SUCCESS
    assert result.score == 1.0
    assert result.best_match_pattern_id == "final-001"
    assert result.compared_pattern_count == 1


def test_similarity_engine_respects_user_isolation_with_real_repository():
    repository = FinalPatternRepository()

    user_a_pattern = build_final_pattern(
        pattern_id="final-user-a",
        session_id="historical-a",
        user_id="user-a",
        operational={
            "create": 5,
        },
    )

    user_b_pattern = build_final_pattern(
        pattern_id="final-user-b",
        session_id="historical-b",
        user_id="user-b",
        operational={
            "create": 5,
        },
    )

    assert repository.store(user_a_pattern) is True
    assert repository.store(user_b_pattern) is True

    candidate = build_candidate(
        session_id="candidate-a",
        user_id="user-a",
        operational={
            "create": 5,
        },
    )

    engine = SimilarityEngine(repository)

    result = engine.evaluate(candidate)

    assert result.status == SimilarityStatus.SUCCESS
    assert result.score == 1.0
    assert result.best_match_pattern_id == "final-user-a"
    assert result.compared_pattern_count == 1


def test_empty_real_repository_produces_cold_start():
    repository = FinalPatternRepository()

    candidate = build_candidate(
        session_id="candidate-cold-start",
        user_id="user-001",
        operational={
            "create": 1,
        },
    )

    engine = SimilarityEngine(repository)

    result = engine.evaluate(candidate)

    assert result.status == SimilarityStatus.COLD_START
    assert result.score is None
    assert result.compared_pattern_count == 0


def test_repository_history_remains_unchanged_after_similarity_evaluation():
    repository = FinalPatternRepository()

    historical = build_final_pattern(
        pattern_id="final-readonly",
        session_id="historical-readonly",
        user_id="user-001",
        operational={
            "create": 7,
            "modify": 3,
        },
    )

    assert repository.store(historical) is True

    before = repository.get("final-readonly")

    candidate = build_candidate(
        session_id="candidate-readonly",
        user_id="user-001",
        operational={
            "create": 7,
            "modify": 3,
        },
    )

    engine = SimilarityEngine(repository)

    result = engine.evaluate(candidate)

    after = repository.get("final-readonly")

    assert result.status == SimilarityStatus.SUCCESS
    assert before == after


def test_repository_returns_independent_history_used_by_similarity_engine():
    repository = FinalPatternRepository()

    historical = build_final_pattern(
        pattern_id="final-copy",
        session_id="historical-copy",
        user_id="user-001",
        operational={
            "create": 4,
        },
    )

    assert repository.store(historical) is True

    first_snapshot = repository.get_all()
    second_snapshot = repository.get_all()

    assert first_snapshot is not second_snapshot
    assert first_snapshot[0] is not second_snapshot[0]
    assert first_snapshot[0] == second_snapshot[0]

    candidate = build_candidate(
        session_id="candidate-copy",
        user_id="user-001",
        operational={
            "create": 4,
        },
    )

    result = SimilarityEngine(repository).evaluate(
        candidate
    )

    assert result.status == SimilarityStatus.SUCCESS
    assert result.score == 1.0


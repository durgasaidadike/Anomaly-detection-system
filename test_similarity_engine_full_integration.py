"""
Full Candidate -> Final Pattern -> Repository -> Similarity integration.

Real frozen pipeline under test:

    CandidatePattern
            |
            v
    FinalPatternFactory
            |
            v
    FinalPattern
            |
            v
    FinalPatternRepository
            |
            v
    SimilarityEngine
            |
            v
    SimilarityResult

Architectural guarantees locked down by this layer:

    1. The Candidate Pattern is never modified by similarity evaluation.
    2. The historical Final Pattern is never modified.
    3. Other users' history is never compared.

Note on candidate construction:

    CandidatePattern.add_observation() records the raw timeline only.
    The operational, temporal, sequential, contextual, relationship and
    session characteristics are derived by the Candidate Pattern Manager
    (Module 05) while interpreted observations are applied. A candidate
    built through add_observation() alone carries no comparable
    behavioral dimension, so Module 07 correctly reports
    INSUFFICIENT_DATA.

    build_completed_candidate() therefore drives the real Module 05
    lifecycle, which performs the equivalent of mark_finalized() +
    mark_completed() while deriving the behavioral characteristics that
    Module 06 copies into the Final Pattern.
"""

from datetime import datetime

from candidate_pattern_manager import CandidatePatternManager
from candidate_pattern_models import CandidatePattern
from final_pattern_factory import FinalPatternFactory
from final_pattern_repository import FinalPatternRepository
from similarity_engine import SimilarityEngine
from similarity_result import SimilarityStatus


def build_completed_candidate(
    session_id,
    user_id,
    observations,
):
    """
    Build a completed Candidate Pattern through the real Module 05 flow.

    The manager lifecycle below is the real equivalent of constructing
    a CandidatePattern directly, adding every observation, and marking
    it finalized and completed:

        createPattern(...)   -> CandidatePattern(session_id, user_id)
        updatePattern(...)   -> add_observation(...) plus behavioral
                                characteristic derivation
        completeSession(...) -> session end time and duration
        finalizePattern(...) -> mark_finalized() + mark_completed()
    """

    manager = CandidatePatternManager()

    manager.createPattern(
        session_id=session_id,
        user_id=user_id,
        session_start_time=observations[0]["timestamp"],
    )

    for index, observation in enumerate(observations):
        context = {
            key: value
            for key, value in observation.items()
            if key
            not in (
                "timestamp",
                "operation_type",
            )
        }

        relationships = []

        if index > 0:
            relationships.append(
                {
                    "relationship_type": "SEQUENTIAL",
                    "from_operation": observations[
                        index - 1
                    ]["operation_type"],
                    "to_operation": observation[
                        "operation_type"
                    ],
                }
            )

        manager.updatePattern(
            session_id,
            observation,
            context=context,
            relationships=relationships,
        )

    manager.completeSession(
        session_id,
        session_end_time=observations[-1]["timestamp"],
    )

    pattern = manager.finalizePattern(session_id)

    assert isinstance(pattern, CandidatePattern)
    assert pattern.metadata.complete is True

    return pattern


def test_candidate_to_similarity_full_flow():
    historical_candidate = build_completed_candidate(
        session_id="historical-session-001",
        user_id="user-001",
        observations=[
            {
                "operation_type": "CREATE",
                "timestamp": datetime(
                    2026, 9, 1, 10, 0
                ),
                "file_extension": ".py",
                "directory": "/project",
            },
            {
                "operation_type": "MODIFY",
                "timestamp": datetime(
                    2026, 9, 1, 10, 5
                ),
                "file_extension": ".py",
                "directory": "/project",
            },
        ],
    )

    final_pattern = FinalPatternFactory().create(
        historical_candidate
    )

    assert final_pattern is not None

    repository = FinalPatternRepository()

    assert repository.store(final_pattern) is True

    current_candidate = build_completed_candidate(
        session_id="current-session-001",
        user_id="user-001",
        observations=[
            {
                "operation_type": "CREATE",
                "timestamp": datetime(
                    2026, 9, 2, 10, 0
                ),
                "file_extension": ".py",
                "directory": "/project",
            },
            {
                "operation_type": "MODIFY",
                "timestamp": datetime(
                    2026, 9, 2, 10, 5
                ),
                "file_extension": ".py",
                "directory": "/project",
            },
        ],
    )

    result = SimilarityEngine(
        repository
    ).evaluate(current_candidate)

    assert result.status == SimilarityStatus.SUCCESS
    assert result.score is not None
    assert 0.0 <= result.score <= 1.0

    assert result.best_match_pattern_id == (
        final_pattern.pattern_id
    )

    assert result.compared_pattern_count == 1


def test_full_flow_preserves_candidate_pattern():
    historical_candidate = build_completed_candidate(
        session_id="historical-session-002",
        user_id="user-001",
        observations=[
            {
                "operation_type": "CREATE",
                "timestamp": datetime(
                    2026, 9, 3, 12, 0
                ),
                "file_extension": ".txt",
                "directory": "/documents",
            }
        ],
    )

    final_pattern = FinalPatternFactory().create(
        historical_candidate
    )

    assert final_pattern is not None

    repository = FinalPatternRepository()

    assert repository.store(final_pattern) is True

    current_candidate = build_completed_candidate(
        session_id="current-session-002",
        user_id="user-001",
        observations=[
            {
                "operation_type": "CREATE",
                "timestamp": datetime(
                    2026, 9, 4, 12, 0
                ),
                "file_extension": ".txt",
                "directory": "/documents",
            }
        ],
    )

    original_observations = [
        dict(item)
        for item in current_candidate.timeline.observations
    ]

    original_operational = dict(
        current_candidate.operational_characteristics
    )

    result = SimilarityEngine(
        repository
    ).evaluate(current_candidate)

    assert result.status == SimilarityStatus.SUCCESS

    assert current_candidate.timeline.observations == (
        original_observations
    )

    assert (
        current_candidate.operational_characteristics
        == original_operational
    )


def test_full_flow_preserves_historical_pattern():
    historical_candidate = build_completed_candidate(
        session_id="historical-session-003",
        user_id="user-001",
        observations=[
            {
                "operation_type": "CREATE",
                "timestamp": datetime(
                    2026, 9, 5, 10, 0
                ),
                "file_extension": ".py",
                "directory": "/project",
            }
        ],
    )

    final_pattern = FinalPatternFactory().create(
        historical_candidate
    )

    assert final_pattern is not None

    repository = FinalPatternRepository()

    assert repository.store(final_pattern) is True

    before = repository.get(
        final_pattern.pattern_id
    )

    current_candidate = build_completed_candidate(
        session_id="current-session-003",
        user_id="user-001",
        observations=[
            {
                "operation_type": "CREATE",
                "timestamp": datetime(
                    2026, 9, 6, 10, 0
                ),
                "file_extension": ".py",
                "directory": "/project",
            }
        ],
    )

    result = SimilarityEngine(
        repository
    ).evaluate(current_candidate)

    after = repository.get(
        final_pattern.pattern_id
    )

    assert result.status == SimilarityStatus.SUCCESS
    assert before == after


def test_full_flow_keeps_users_isolated():
    repository = FinalPatternRepository()

    user_a_candidate = build_completed_candidate(
        session_id="historical-user-a",
        user_id="user-a",
        observations=[
            {
                "operation_type": "CREATE",
                "timestamp": datetime(
                    2026, 9, 7, 10, 0
                ),
                "file_extension": ".py",
                "directory": "/a",
            }
        ],
    )

    user_b_candidate = build_completed_candidate(
        session_id="historical-user-b",
        user_id="user-b",
        observations=[
            {
                "operation_type": "CREATE",
                "timestamp": datetime(
                    2026, 9, 7, 11, 0
                ),
                "file_extension": ".py",
                "directory": "/b",
            }
        ],
    )

    factory = FinalPatternFactory()

    user_a_final = factory.create(
        user_a_candidate
    )

    user_b_final = factory.create(
        user_b_candidate
    )

    assert user_a_final is not None
    assert user_b_final is not None

    assert repository.store(
        user_a_final
    ) is True

    assert repository.store(
        user_b_final
    ) is True

    current_user_a = build_completed_candidate(
        session_id="current-user-a",
        user_id="user-a",
        observations=[
            {
                "operation_type": "CREATE",
                "timestamp": datetime(
                    2026, 9, 8, 10, 0
                ),
                "file_extension": ".py",
                "directory": "/a",
            }
        ],
    )

    result = SimilarityEngine(
        repository
    ).evaluate(current_user_a)

    assert result.status == SimilarityStatus.SUCCESS
    assert result.best_match_pattern_id == (
        user_a_final.pattern_id
    )
    assert result.compared_pattern_count == 1



def test_full_integration_does_not_penalize_session_identity_or_absolute_time():
    historical_candidate = build_completed_candidate(
        session_id="historical-semantic",
        user_id="user-001",
        observations=[
            {
                "operation_type": "CREATE",
                "timestamp": datetime(
                    2026,
                    9,
                    10,
                    10,
                    0,
                ),
                "file_extension": ".py",
                "directory": "/project",
            },
            {
                "operation_type": "MODIFY",
                "timestamp": datetime(
                    2026,
                    9,
                    10,
                    10,
                    5,
                ),
                "file_extension": ".py",
                "directory": "/project",
            },
        ],
    )

    historical_final = FinalPatternFactory().create(
        historical_candidate
    )

    assert historical_final is not None

    repository = FinalPatternRepository()

    assert repository.store(
        historical_final
    ) is True

    current_candidate = build_completed_candidate(
        session_id="current-semantic",
        user_id="user-001",
        observations=[
            {
                "operation_type": "CREATE",
                "timestamp": datetime(
                    2026,
                    9,
                    25,
                    18,
                    0,
                ),
                "file_extension": ".py",
                "directory": "/project",
            },
            {
                "operation_type": "MODIFY",
                "timestamp": datetime(
                    2026,
                    9,
                    25,
                    18,
                    5,
                ),
                "file_extension": ".py",
                "directory": "/project",
            },
        ],
    )

    result = SimilarityEngine(
        repository
    ).evaluate(current_candidate)

    assert result.status == SimilarityStatus.SUCCESS
    assert result.score is not None

    assert result.best_match_pattern_id == (
        historical_final.pattern_id
    )

    assert (
        result.dimension_scores["sequential"]
        == 1.0
    )

    assert (
        result.dimension_scores["session"]
        == 1.0
    )


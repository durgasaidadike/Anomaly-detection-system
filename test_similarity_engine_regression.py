from datetime import datetime

from candidate_pattern_manager import CandidatePatternManager
from final_pattern_repository import FinalPatternRepository
from final_pattern_repository_adapter import (
    FinalPatternRepositoryAdapter,
)
from similarity_engine import SimilarityEngine
from similarity_result import SimilarityStatus


def test_candidate_manager_to_repository_to_similarity_regression():
    repository = FinalPatternRepository()

    # The Candidate Pattern Manager hands off the completed
    # CandidatePattern, while FinalPatternRepository.store() accepts
    # only FinalPattern instances. The Module 06 adapter owns that
    # conversion at the boundary.
    adapter = FinalPatternRepositoryAdapter(
        repository=repository,
    )

    manager = CandidatePatternManager(
        final_pattern_handler=adapter.store,
    )

    manager.createPattern(
        "historical-regression",
        user_id="user-001",
        session_start_time=datetime(
            2026,
            9,
            20,
            10,
            0,
        ),
    )

    manager.updatePattern(
        "historical-regression",
        {
            "operation_type": "CREATE",
            "timestamp": datetime(
                2026,
                9,
                20,
                10,
                0,
            ),
            "file_extension": ".py",
            "directory": "/project",
        },
    )

    manager.updatePattern(
        "historical-regression",
        {
            "operation_type": "MODIFY",
            "timestamp": datetime(
                2026,
                9,
                20,
                10,
                5,
            ),
            "file_extension": ".py",
            "directory": "/project",
        },
    )

    manager.completeSession(
        "historical-regression",
        datetime(
            2026,
            9,
            20,
            10,
            10,
        ),
    )

    finalized_candidate = manager.finalizePattern(
        "historical-regression"
    )

    assert finalized_candidate is not None
    assert repository.count() == 1

    # finalizePattern() returns the completed CandidatePattern, so the
    # historical FinalPattern is read back from the repository that
    # received it.
    historical = repository.get_all()[0]

    current_manager = CandidatePatternManager()

    current = current_manager.createPattern(
        "current-regression",
        user_id="user-001",
        session_start_time=datetime(
            2026,
            9,
            21,
            10,
            0,
        ),
    )

    current_manager.updatePattern(
        "current-regression",
        {
            "operation_type": "CREATE",
            "timestamp": datetime(
                2026,
                9,
                21,
                10,
                0,
            ),
            "file_extension": ".py",
            "directory": "/project",
        },
    )

    current_manager.updatePattern(
        "current-regression",
        {
            "operation_type": "MODIFY",
            "timestamp": datetime(
                2026,
                9,
                21,
                10,
                5,
            ),
            "file_extension": ".py",
            "directory": "/project",
        },
    )

    current_manager.completeSession(
        "current-regression",
        datetime(
            2026,
            9,
            21,
            10,
            10,
        ),
    )

    result = SimilarityEngine(
        repository
    ).evaluate(current)

    assert result.status == SimilarityStatus.SUCCESS
    assert result.score is not None
    assert 0.0 <= result.score <= 1.0

    assert result.best_match_pattern_id == (
        historical.pattern_id
    )

    assert result.compared_pattern_count == 1

import pytest

from confidence_result import (
    CONFIDENCE_DIMENSIONS,
    ConfidenceResult,
    ConfidenceStatus,
)


def test_success_result_accepts_valid_score() -> None:
    result = ConfidenceResult(
        status=ConfidenceStatus.SUCCESS,
        score=0.82,
        candidate_pattern_id="candidate-1",
        historical_pattern_count=5,
        dimension_scores={
            "history_availability": 0.8,
            "candidate_completeness": 0.9,
        },
    )

    assert result.score == 0.82
    assert result.is_available()
    assert not result.is_failed()


def test_cold_start_can_return_reduced_confidence() -> None:
    result = ConfidenceResult(
        status=ConfidenceStatus.COLD_START,
        score=0.15,
        candidate_pattern_id="candidate-1",
        historical_pattern_count=0,
        dimension_scores={
            "history_availability": 0.0,
            "candidate_completeness": 0.5,
        },
    )

    assert result.score == 0.15
    assert result.is_available()


def test_failed_result_must_not_have_score() -> None:
    result = ConfidenceResult(
        status=ConfidenceStatus.FAILED,
        score=None,
        candidate_pattern_id="candidate-1",
        historical_pattern_count=0,
        dimension_scores={},
    )

    assert result.is_failed()
    assert not result.is_available()


def test_failed_result_with_score_is_rejected() -> None:
    with pytest.raises(ValueError):
        ConfidenceResult(
            status=ConfidenceStatus.FAILED,
            score=0.5,
            candidate_pattern_id="candidate-1",
            historical_pattern_count=0,
            dimension_scores={},
        )


def test_score_must_be_between_zero_and_one() -> None:
    with pytest.raises(ValueError):
        ConfidenceResult(
            status=ConfidenceStatus.SUCCESS,
            score=1.1,
            candidate_pattern_id="candidate-1",
            historical_pattern_count=1,
            dimension_scores={},
        )


def test_historical_count_cannot_be_negative() -> None:
    with pytest.raises(ValueError):
        ConfidenceResult(
            status=ConfidenceStatus.SUCCESS,
            score=0.5,
            candidate_pattern_id="candidate-1",
            historical_pattern_count=-1,
            dimension_scores={},
        )


def test_unknown_dimension_is_rejected() -> None:
    with pytest.raises(ValueError):
        ConfidenceResult(
            status=ConfidenceStatus.SUCCESS,
            score=0.5,
            candidate_pattern_id="candidate-1",
            historical_pattern_count=1,
            dimension_scores={
                "unknown_dimension": 0.5,
            },
        )


def test_all_documented_dimensions_are_known() -> None:
    assert set(CONFIDENCE_DIMENSIONS) == {
        "history_availability",
        "candidate_completeness",
        "behavioral_consistency",
        "session_maturity",
        "behavioral_stability",
    }

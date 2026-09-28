import pytest

from drift_result import DriftResult, DriftStatus


def test_successful_result():
    result = DriftResult(
        status=DriftStatus.SUCCESS,
        score=0.42,
        candidate_pattern_id="candidate-1",
        historical_pattern_count=3,
        dimension_scores={
            "behavioral_workflow": 0.40,
            "operation_frequency": 0.50,
        },
        comparison_summary={
            "trend": "gradual_change",
        },
        metadata={
            "source": "historical_patterns",
        },
    )

    assert result.status == DriftStatus.SUCCESS
    assert result.score == 0.42
    assert result.candidate_pattern_id == "candidate-1"
    assert result.historical_pattern_count == 3
    assert result.is_successful()


def test_cold_start_result_has_no_score():
    result = DriftResult(
        status=DriftStatus.COLD_START,
        score=None,
        candidate_pattern_id="candidate-1",
        historical_pattern_count=0,
    )

    assert result.status == DriftStatus.COLD_START
    assert result.score is None
    assert not result.is_successful()


def test_insufficient_data_result_has_no_score():
    result = DriftResult(
        status=DriftStatus.INSUFFICIENT_DATA,
        score=None,
        candidate_pattern_id="candidate-1",
        historical_pattern_count=1,
    )

    assert result.status == DriftStatus.INSUFFICIENT_DATA
    assert result.score is None
    assert not result.is_successful()


def test_failed_result_has_no_score():
    result = DriftResult(
        status=DriftStatus.FAILED,
        score=None,
        candidate_pattern_id="candidate-1",
        historical_pattern_count=2,
    )

    assert result.status == DriftStatus.FAILED
    assert result.score is None
    assert not result.is_successful()


def test_negative_historical_pattern_count_rejected():
    with pytest.raises(ValueError):
        DriftResult(
            status=DriftStatus.SUCCESS,
            score=0.5,
            candidate_pattern_id="candidate-1",
            historical_pattern_count=-1,
        )


def test_invalid_drift_score_rejected():
    with pytest.raises(ValueError):
        DriftResult(
            status=DriftStatus.SUCCESS,
            score=1.5,
            candidate_pattern_id="candidate-1",
            historical_pattern_count=2,
        )


def test_invalid_dimension_score_rejected():
    with pytest.raises(ValueError):
        DriftResult(
            status=DriftStatus.SUCCESS,
            score=0.5,
            candidate_pattern_id="candidate-1",
            historical_pattern_count=2,
            dimension_scores={
                "operation_frequency": -0.1,
            },
        )


def test_non_success_result_cannot_have_score():
    with pytest.raises(ValueError):
        DriftResult(
            status=DriftStatus.COLD_START,
            score=0.2,
            candidate_pattern_id="candidate-1",
            historical_pattern_count=0,
        )


def test_none_dimension_values_are_allowed():
    result = DriftResult(
        status=DriftStatus.SUCCESS,
        score=0.5,
        candidate_pattern_id="candidate-1",
        historical_pattern_count=3,
        dimension_scores={
            "behavioral_workflow": 0.6,
            "operation_frequency": None,
        },
    )

    assert result.dimension_scores["operation_frequency"] is None

import pytest

from confidence_calculator import (
    ConfidenceCalculator,
    ConfidenceWeights,
)


def test_equal_weight_average() -> None:
    calculator = ConfidenceCalculator()

    score = calculator.calculate(
        {
            "history_availability": 0.8,
            "candidate_completeness": 0.6,
            "behavioral_consistency": 1.0,
            "session_maturity": 0.4,
            "behavioral_stability": 0.2,
        }
    )

    assert score == pytest.approx(0.6)


def test_missing_dimensions_are_ignored() -> None:
    calculator = ConfidenceCalculator()

    score = calculator.calculate(
        {
            "history_availability": 0.8,
            "candidate_completeness": None,
            "behavioral_consistency": 0.6,
        }
    )

    assert score == pytest.approx(0.7)


def test_zero_weight_dimension_is_ignored() -> None:
    calculator = ConfidenceCalculator(
        ConfidenceWeights(
            history_availability=1.0,
            candidate_completeness=0.0,
            behavioral_consistency=1.0,
            session_maturity=1.0,
            behavioral_stability=1.0,
        )
    )

    score = calculator.calculate(
        {
            "history_availability": 1.0,
            "candidate_completeness": 0.0,
            "behavioral_consistency": 1.0,
            "session_maturity": 1.0,
            "behavioral_stability": 1.0,
        }
    )

    assert score == pytest.approx(1.0)


def test_negative_weight_is_rejected() -> None:
    with pytest.raises(ValueError):
        ConfidenceWeights(
            history_availability=-1.0,
        )


def test_all_zero_weights_are_rejected() -> None:
    with pytest.raises(ValueError):
        ConfidenceWeights(
            history_availability=0.0,
            candidate_completeness=0.0,
            behavioral_consistency=0.0,
            session_maturity=0.0,
            behavioral_stability=0.0,
        )


def test_invalid_dimension_score_is_rejected() -> None:
    calculator = ConfidenceCalculator()

    with pytest.raises(ValueError):
        calculator.calculate(
            {
                "history_availability": 1.5,
            }
        )


def test_no_available_dimensions_returns_zero() -> None:
    calculator = ConfidenceCalculator()

    score, details = calculator.calculate_with_details(
        {
            "history_availability": None,
            "candidate_completeness": None,
            "behavioral_consistency": None,
            "session_maturity": None,
            "behavioral_stability": None,
        }
    )

    assert score == 0.0
    assert details["available_dimensions"] == []

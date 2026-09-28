import pytest

from drift_calculator import (
    DRIFT_DIMENSIONS,
    DriftCalculator,
    DriftWeights,
)


def test_default_weights_are_equal():
    weights = DriftWeights()

    assert all(
        getattr(weights, dimension) == 1.0
        for dimension in DRIFT_DIMENSIONS
    )


def test_equal_weighted_calculation():
    calculator = DriftCalculator()

    scores = {
        "behavioral_workflow": 0.2,
        "operation_frequency": 0.4,
        "temporal_characteristics": 0.6,
    }

    result = calculator.calculate(scores)

    assert result == pytest.approx(0.4)


def test_partial_dimensions_are_supported():
    calculator = DriftCalculator()

    scores = {
        "behavioral_workflow": 0.2,
        "operation_frequency": None,
        "temporal_characteristics": 0.6,
    }

    result = calculator.calculate(scores)

    assert result == pytest.approx(0.4)


def test_all_dimensions_unavailable_returns_none():
    calculator = DriftCalculator()

    scores = {
        dimension: None
        for dimension in DRIFT_DIMENSIONS
    }

    result = calculator.calculate(scores)

    assert result is None


def test_custom_weights_are_applied():
    weights = DriftWeights(
        behavioral_workflow=2.0,
        operation_frequency=1.0,
    )

    calculator = DriftCalculator(weights)

    scores = {
        "behavioral_workflow": 1.0,
        "operation_frequency": 0.0,
    }

    result = calculator.calculate(scores)

    assert result == pytest.approx(
        2.0 / 3.0
    )


def test_zero_weight_dimension_is_ignored():
    weights = DriftWeights(
        behavioral_workflow=0.0,
        operation_frequency=1.0,
    )

    calculator = DriftCalculator(weights)

    scores = {
        "behavioral_workflow": 1.0,
        "operation_frequency": 0.4,
    }

    result = calculator.calculate(scores)

    assert result == pytest.approx(0.4)


def test_negative_weight_is_rejected():
    with pytest.raises(ValueError):
        DriftWeights(
            behavioral_workflow=-1.0
        )


def test_invalid_dimension_score_is_rejected():
    calculator = DriftCalculator()

    with pytest.raises(ValueError):
        calculator.calculate(
            {
                "behavioral_workflow": 1.2,
            }
        )


def test_negative_dimension_score_is_rejected():
    calculator = DriftCalculator()

    with pytest.raises(ValueError):
        calculator.calculate(
            {
                "behavioral_workflow": -0.1,
            }
        )


def test_calculation_details_report_available_dimensions():
    calculator = DriftCalculator()

    scores = {
        "behavioral_workflow": 0.5,
        "operation_frequency": None,
        "temporal_characteristics": 0.7,
    }

    score, details = calculator.calculate_with_details(
        scores
    )

    assert score == pytest.approx(0.6)

    assert details["available_dimensions"] == [
        "behavioral_workflow",
        "temporal_characteristics",
    ]

    assert "operation_frequency" in (
        details["unavailable_dimensions"]
    )


def test_calculation_details_include_weights():
    weights = DriftWeights(
        behavioral_workflow=2.0,
        operation_frequency=3.0,
    )

    calculator = DriftCalculator(weights)

    score, details = calculator.calculate_with_details(
        {
            "behavioral_workflow": 0.5,
            "operation_frequency": 0.5,
        }
    )

    assert score == pytest.approx(0.5)

    assert details["weights_used"] == {
        "behavioral_workflow": 2.0,
        "operation_frequency": 3.0,
    }

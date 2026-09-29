import pytest

from ml_result_models import ModelScore
from score_calibration import (
    ScoreCalibrationEngine,
)
from score_semantics import (
    ScoreDirection,
)


def test_calibration_preserves_raw_score():
    engine = ScoreCalibrationEngine(
        {
            "IsolationForest": (
                lambda value: value / 2
            ),
        }
    )

    result = engine.calibrate(
        model_score=ModelScore(
            model_name="IsolationForest",
            score=-0.6,
        ),
        direction=(
            ScoreDirection.LOWER_IS_MORE_ANOMALOUS
        ),
    )

    assert result.raw_score == -0.6
    assert result.canonical_score == 0.6
    assert result.calibrated_score == 0.3


def test_calibration_receives_canonical_score():
    received = []

    def calibration_function(value):
        received.append(value)
        return value

    engine = ScoreCalibrationEngine(
        {
            "IsolationForest": calibration_function,
        }
    )

    result = engine.calibrate(
        model_score=ModelScore(
            model_name="IsolationForest",
            score=-0.75,
        ),
        direction=(
            ScoreDirection.LOWER_IS_MORE_ANOMALOUS
        ),
    )

    assert received == [0.75]
    assert result.canonical_score == 0.75
    assert result.calibrated_score == 0.75


def test_higher_is_more_anomalous_preserves_direction():
    engine = ScoreCalibrationEngine(
        {
            "TestModel": (
                lambda value: value
            ),
        }
    )

    result = engine.calibrate(
        model_score=ModelScore(
            model_name="TestModel",
            score=0.8,
        ),
        direction=(
            ScoreDirection.HIGHER_IS_MORE_ANOMALOUS
        ),
    )

    assert result.raw_score == 0.8
    assert result.canonical_score == 0.8
    assert result.calibrated_score == 0.8


def test_missing_calibration_policy_is_rejected():
    engine = ScoreCalibrationEngine({})

    with pytest.raises(ValueError):
        engine.calibrate(
            model_score=ModelScore(
                model_name="IsolationForest",
                score=-0.2,
            ),
            direction=(
                ScoreDirection.LOWER_IS_MORE_ANOMALOUS
            ),
        )


def test_non_numeric_calibration_output_is_rejected():
    engine = ScoreCalibrationEngine(
        {
            "IsolationForest": (
                lambda value: "invalid"
            ),
        }
    )

    with pytest.raises(ValueError):
        engine.calibrate(
            model_score=ModelScore(
                model_name="IsolationForest",
                score=-0.2,
            ),
            direction=(
                ScoreDirection.LOWER_IS_MORE_ANOMALOUS
            ),
        )


@pytest.mark.parametrize(
    "bad_output",
    [
        float("nan"),
        float("inf"),
        float("-inf"),
    ],
)
def test_non_finite_calibration_output_is_rejected(
    bad_output,
):
    engine = ScoreCalibrationEngine(
        {
            "IsolationForest": (
                lambda value: bad_output
            ),
        }
    )

    with pytest.raises(ValueError):
        engine.calibrate(
            model_score=ModelScore(
                model_name="IsolationForest",
                score=-0.2,
            ),
            direction=(
                ScoreDirection.LOWER_IS_MORE_ANOMALOUS
            ),
        )


def test_invalid_model_score_type_is_rejected():
    engine = ScoreCalibrationEngine(
        {
            "IsolationForest": (
                lambda value: value
            ),
        }
    )

    with pytest.raises(TypeError):
        engine.calibrate(
            model_score="invalid",
            direction=(
                ScoreDirection.LOWER_IS_MORE_ANOMALOUS
            ),
        )


def test_calibration_engine_does_not_force_zero_to_one_range():
    engine = ScoreCalibrationEngine(
        {
            "IsolationForest": (
                lambda value: value * 10
            ),
        }
    )

    result = engine.calibrate(
        model_score=ModelScore(
            model_name="IsolationForest",
            score=-0.5,
        ),
        direction=(
            ScoreDirection.LOWER_IS_MORE_ANOMALOUS
        ),
    )

    assert result.calibrated_score == 5.0

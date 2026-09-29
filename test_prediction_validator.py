import pytest

from prediction_validator import PredictionValidator


def test_valid_prediction_is_accepted():
    result = PredictionValidator.validate(
        model_name="IsolationForest",
        prediction=0.73,
    )

    assert result == 0.73


def test_integer_prediction_is_converted_to_float():
    result = PredictionValidator.validate(
        model_name="IsolationForest",
        prediction=1,
    )

    assert result == 1.0
    assert isinstance(result, float)


@pytest.mark.parametrize(
    "prediction",
    [
        "0.73",
        None,
        [],
        {},
    ],
)
def test_non_numeric_prediction_is_rejected(prediction):
    with pytest.raises(ValueError):
        PredictionValidator.validate(
            model_name="IsolationForest",
            prediction=prediction,
        )


@pytest.mark.parametrize(
    "prediction",
    [
        float("nan"),
        float("inf"),
        float("-inf"),
    ],
)
def test_non_finite_prediction_is_rejected(prediction):
    with pytest.raises(ValueError):
        PredictionValidator.validate(
            model_name="IsolationForest",
            prediction=prediction,
        )


def test_empty_model_name_is_rejected():
    with pytest.raises(ValueError):
        PredictionValidator.validate(
            model_name="",
            prediction=0.5,
        )


def test_whitespace_model_name_is_rejected():
    with pytest.raises(ValueError):
        PredictionValidator.validate(
            model_name="   ",
            prediction=0.5,
        )


def test_prediction_validator_is_stateless():
    assert PredictionValidator.__dict__.get(
        "__init__"
    ) is None

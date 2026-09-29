import pytest

from score_semantics import (
    ScoreDirection,
    to_anomaly_direction,
)


def test_lower_is_more_anomalous_is_inverted():
    result = to_anomaly_direction(
        raw_score=-0.55,
        direction=(
            ScoreDirection.LOWER_IS_MORE_ANOMALOUS
        ),
    )

    assert result == 0.55


def test_higher_is_more_anomalous_is_preserved():
    result = to_anomaly_direction(
        raw_score=0.55,
        direction=(
            ScoreDirection.HIGHER_IS_MORE_ANOMALOUS
        ),
    )

    assert result == 0.55


def test_zero_remains_zero():
    assert (
        to_anomaly_direction(
            0.0,
            ScoreDirection.LOWER_IS_MORE_ANOMALOUS,
        )
        == 0.0
    )


def test_negative_value_is_not_abs():
    result = to_anomaly_direction(
        raw_score=-2.5,
        direction=(
            ScoreDirection.LOWER_IS_MORE_ANOMALOUS
        ),
    )

    assert result == 2.5


def test_invalid_direction_is_rejected():
    with pytest.raises(TypeError):
        to_anomaly_direction(
            0.5,
            "invalid",
        )

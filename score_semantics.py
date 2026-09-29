from __future__ import annotations

from enum import Enum


class ScoreDirection(str, Enum):
    """
    Defines how a model's raw score relates to anomaly severity.
    """

    HIGHER_IS_MORE_ANOMALOUS = (
        "higher_is_more_anomalous"
    )

    LOWER_IS_MORE_ANOMALOUS = (
        "lower_is_more_anomalous"
    )


def to_anomaly_direction(
    raw_score: float,
    direction: ScoreDirection,
) -> float:
    """
    Convert a model's raw score into a canonical anomaly direction.

    Canonical rule:
        higher value = more anomalous

    This function does not normalize the magnitude into [0, 1].
    It only resolves score orientation.
    """

    if not isinstance(direction, ScoreDirection):
        raise TypeError(
            "direction must be a ScoreDirection."
        )

    if direction == ScoreDirection.HIGHER_IS_MORE_ANOMALOUS:
        return float(raw_score)

    return -float(raw_score)

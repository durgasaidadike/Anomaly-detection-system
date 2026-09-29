from __future__ import annotations

import math
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from ml_result_models import ModelScore
from score_semantics import (
    ScoreDirection,
)


CalibrationFunction = Callable[[float], float]


@dataclass(frozen=True)
class CalibratedModelScore:
    """
    Represents one model score after calibration.

    raw_score:
        Original estimator output.

    canonical_score:
        Score converted into PRISM's canonical anomaly direction.

    calibrated_score:
        Score produced by the configured calibration policy.

    The calibration policy itself is deliberately injected rather
    than hard-coded here.
    """

    model_name: str
    raw_score: float
    canonical_score: float
    calibrated_score: float


class ScoreCalibrationEngine:
    """
    Applies explicitly supplied per-model score calibration policies.

    This component does not decide which mathematical calibration
    strategy PRISM should use. That policy is provided through the
    calibration-function mapping.

    Responsibilities:
    - convert raw scores into canonical anomaly direction
    - apply the configured calibration function
    - validate calibration output
    - preserve raw score traceability

    Does not:
    - assign risk
    - fuse model scores
    - choose decision thresholds
    - modify behavioral knowledge
    """

    def __init__(
        self,
        calibration_functions: Mapping[
            str,
            CalibrationFunction,
        ],
    ) -> None:
        self._calibration_functions = dict(
            calibration_functions
        )

    def calibrate(
        self,
        *,
        model_score: ModelScore,
        direction: ScoreDirection,
    ) -> CalibratedModelScore:
        if not isinstance(
            model_score,
            ModelScore,
        ):
            raise TypeError(
                "model_score must be a ModelScore."
            )

        if not isinstance(
            direction,
            ScoreDirection,
        ):
            raise TypeError(
                "direction must be a ScoreDirection."
            )

        calibration_function = (
            self._calibration_functions.get(
                model_score.model_name
            )
        )

        if calibration_function is None:
            raise ValueError(
                f"No calibration policy supplied for "
                f"model '{model_score.model_name}'."
            )

        canonical_score = model_score.as_anomaly_score(
            direction
        )

        calibrated_score = calibration_function(
            canonical_score
        )

        if not isinstance(
            calibrated_score,
            (int, float),
        ):
            raise ValueError(
                f"Calibration policy for model "
                f"'{model_score.model_name}' must return "
                "a numerical value."
            )

        calibrated_score = float(
            calibrated_score
        )

        if not math.isfinite(
            calibrated_score
        ):
            raise ValueError(
                f"Calibration policy for model "
                f"'{model_score.model_name}' returned "
                "a non-finite value."
            )

        return CalibratedModelScore(
            model_name=model_score.model_name,
            raw_score=model_score.score,
            canonical_score=canonical_score,
            calibrated_score=calibrated_score,
        )

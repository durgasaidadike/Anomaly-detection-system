from math import isfinite

from decision_models import (
    DecisionConfiguration,
    RiskLevel,
)


class DecisionThresholdEvaluator:
    """
    Deterministically maps an anomaly score to a configured risk level.

    Thresholds represent the minimum score required to enter each
    risk level.
    """

    _RISK_ORDER = (
        RiskLevel.NORMAL,
        RiskLevel.SUSPICIOUS,
        RiskLevel.HIGH_RISK,
        RiskLevel.CRITICAL,
    )

    def __init__(
        self,
        configuration: DecisionConfiguration,
    ) -> None:
        if not isinstance(
            configuration,
            DecisionConfiguration,
        ):
            raise TypeError(
                "configuration must be DecisionConfiguration"
            )

        self._configuration = configuration

    def evaluate(
        self,
        anomaly_score: float,
    ) -> RiskLevel:
        if not isinstance(
            anomaly_score,
            (int, float),
        ):
            raise ValueError(
                "anomaly_score must be numeric"
            )

        score = float(anomaly_score)

        if not isfinite(score):
            raise ValueError(
                "anomaly_score must be finite"
            )

        selected_level = RiskLevel.NORMAL

        for risk_level in self._RISK_ORDER:
            threshold = float(
                self._configuration.thresholds[risk_level]
            )

            if score >= threshold:
                selected_level = risk_level

        return selected_level

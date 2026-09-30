import logging

from math import isfinite

from decision_models import (
    DecisionConfiguration,
    DecisionMetadata,
    DecisionResult,
    DecisionStatus,
    RiskLevel,
)
from decision_threshold_evaluator import (
    DecisionThresholdEvaluator,
)
from ensemble_result_models import MLMetadata, EnsembleResult


logger = logging.getLogger(__name__)


class DecisionEngine:
    """
    Converts ML anomaly output into a deterministic
    operational decision using configured policies.

    The engine does not perform ML, recovery, persistence,
    or behavioral-state modification.
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
        self._threshold_evaluator = (
            DecisionThresholdEvaluator(
                configuration
            )
        )

    def classify_risk(
        self,
        anomaly_score: float,
    ) -> RiskLevel:
        return self._threshold_evaluator.evaluate(
            anomaly_score
        )

    def determine_action(
        self,
        risk_level: RiskLevel,
    ) -> str:
        if not isinstance(
            risk_level,
            RiskLevel,
        ):
            raise TypeError(
                "risk_level must be RiskLevel"
            )

        return self._configuration.actions[
            risk_level
        ]

    def make_decision(
        self,
        anomaly_score: float | None,
        model_metadata: MLMetadata,
    ) -> DecisionResult:
        if not isinstance(
            model_metadata,
            MLMetadata,
        ):
            raise TypeError(
                "model_metadata must be MLMetadata"
            )

        if anomaly_score is None:
            return self._make_safe_default(
                model_metadata,
                "missing anomaly score",
            )

        if (
            isinstance(anomaly_score, bool)
            or not isinstance(
                anomaly_score,
                (int, float),
            )
        ):
            return self._make_safe_default(
                model_metadata,
                "invalid anomaly score",
            )

        score = float(anomaly_score)

        if not isfinite(score):
            return self._make_safe_default(
                model_metadata,
                "non-finite anomaly score",
            )

        try:
            risk_level = self.classify_risk(score)

        except ValueError as exc:
            logger.exception(
                "Decision threshold evaluation failed"
            )

            return self._make_safe_default(
                model_metadata,
                f"threshold evaluation failed: {exc}",
            )

        decision = self._configuration.decisions[
            risk_level
        ]

        recommended_action = self.determine_action(
            risk_level
        )

        metadata = DecisionMetadata(
            configured_risk_levels=tuple(
                level.value
                for level in self._RISK_ORDER
            ),
            evaluated_from_score=score,
            model_metadata=model_metadata,
            status=DecisionStatus.SUCCESS,
            failure_reason=None,
        )

        return DecisionResult(
            decision=decision,
            risk_level=risk_level,
            recommended_action=recommended_action,
            metadata=metadata,
        )

    def make_decision_from_ensemble(
        self,
        ensemble_result: EnsembleResult,
    ) -> DecisionResult:
        if not isinstance(
            ensemble_result,
            EnsembleResult,
        ):
            raise TypeError(
                "ensemble_result must be EnsembleResult"
            )

        return self.make_decision(
            anomaly_score=ensemble_result.anomaly_score,
            model_metadata=ensemble_result.metadata,
        )

    def _make_safe_default(
        self,
        model_metadata: MLMetadata,
        reason: str,
    ) -> DecisionResult:
        risk_level = (
            self._configuration.safe_default_risk_level
        )

        decision = self._configuration.decisions[
            risk_level
        ]

        recommended_action = self.determine_action(
            risk_level
        )

        logger.warning(
            "Decision Engine using safe default: %s",
            reason,
        )

        metadata = DecisionMetadata(
            configured_risk_levels=tuple(
                level.value
                for level in self._RISK_ORDER
            ),
            evaluated_from_score=None,
            model_metadata=model_metadata,
            status=DecisionStatus.SAFE_DEFAULT,
            failure_reason=reason,
        )

        return DecisionResult(
            decision=decision,
            risk_level=risk_level,
            recommended_action=recommended_action,
            metadata=metadata,
        )

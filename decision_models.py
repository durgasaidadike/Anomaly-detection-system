from dataclasses import dataclass
from enum import Enum
from math import isfinite
from types import MappingProxyType
from typing import Mapping

from ensemble_result_models import MLMetadata


class RiskLevel(str, Enum):
    NORMAL = "NORMAL"
    SUSPICIOUS = "SUSPICIOUS"
    HIGH_RISK = "HIGH_RISK"
    CRITICAL = "CRITICAL"


class DecisionStatus(str, Enum):
    SUCCESS = "SUCCESS"
    SAFE_DEFAULT = "SAFE_DEFAULT"


@dataclass(frozen=True)
class DecisionConfiguration:
    thresholds: Mapping[RiskLevel, float]
    decisions: Mapping[RiskLevel, str]
    actions: Mapping[RiskLevel, str]
    safe_default_risk_level: RiskLevel

    def __post_init__(self) -> None:
        if not isinstance(
            self.safe_default_risk_level,
            RiskLevel,
        ):
            raise ValueError(
                "safe_default_risk_level must be RiskLevel"
            )

        thresholds = dict(self.thresholds)
        decisions = dict(self.decisions)
        actions = dict(self.actions)

        expected_levels = set(RiskLevel)

        if set(thresholds) != expected_levels:
            raise ValueError(
                "thresholds must define exactly one threshold "
                "for every risk level"
            )

        if set(decisions) != expected_levels:
            raise ValueError(
                "decisions must define exactly one decision "
                "for every risk level"
            )

        if set(actions) != expected_levels:
            raise ValueError(
                "actions must define exactly one action "
                "for every risk level"
            )

        for risk_level, threshold in thresholds.items():
            if not isinstance(threshold, (int, float)):
                raise ValueError(
                    f"threshold for {risk_level.value} must be numeric"
                )

            if not isfinite(float(threshold)):
                raise ValueError(
                    f"threshold for {risk_level.value} must be finite"
                )

        for risk_level, decision in decisions.items():
            if not isinstance(decision, str) or not decision.strip():
                raise ValueError(
                    f"decision for {risk_level.value} "
                    "must be a non-empty string"
                )

        for risk_level, action in actions.items():
            if not isinstance(action, str) or not action.strip():
                raise ValueError(
                    f"action for {risk_level.value} "
                    "must be a non-empty string"
                )

        ordered_levels = (
            RiskLevel.NORMAL,
            RiskLevel.SUSPICIOUS,
            RiskLevel.HIGH_RISK,
            RiskLevel.CRITICAL,
        )

        ordered_thresholds = tuple(
            float(thresholds[level])
            for level in ordered_levels
        )

        if any(
            current >= following
            for current, following in zip(
                ordered_thresholds,
                ordered_thresholds[1:],
            )
        ):
            raise ValueError(
                "thresholds must strictly increase in risk-level order"
            )

        object.__setattr__(
            self,
            "thresholds",
            MappingProxyType(thresholds),
        )
        object.__setattr__(
            self,
            "decisions",
            MappingProxyType(decisions),
        )
        object.__setattr__(
            self,
            "actions",
            MappingProxyType(actions),
        )
@dataclass(frozen=True)
class DecisionMetadata:
    configured_risk_levels: tuple[str, ...]
    evaluated_from_score: float | None
    model_metadata: MLMetadata
    status: DecisionStatus
    failure_reason: str | None

    def __post_init__(self) -> None:
        if not self.configured_risk_levels:
            raise ValueError(
                "configured_risk_levels must not be empty"
            )

        for level in self.configured_risk_levels:
            if not isinstance(level, str) or not level.strip():
                raise ValueError(
                    "configured_risk_levels must contain "
                    "non-empty strings"
                )

        if self.evaluated_from_score is not None:
            if (
                isinstance(
                    self.evaluated_from_score,
                    bool,
                )
                or not isinstance(
                    self.evaluated_from_score,
                    (int, float),
                )
            ):
                raise ValueError(
                    "evaluated_from_score must be numeric"
                )

            if not isfinite(
                float(self.evaluated_from_score)
            ):
                raise ValueError(
                    "evaluated_from_score must be finite"
                )

        if not isinstance(
            self.model_metadata,
            MLMetadata,
        ):
            raise ValueError(
                "model_metadata must be MLMetadata"
            )

        if not isinstance(
            self.status,
            DecisionStatus,
        ):
            raise ValueError(
                "status must be DecisionStatus"
            )

        if self.status == DecisionStatus.SUCCESS:
            if self.evaluated_from_score is None:
                raise ValueError(
                    "successful decision requires "
                    "evaluated_from_score"
                )

            if self.failure_reason is not None:
                raise ValueError(
                    "successful decision must not contain "
                    "failure_reason"
                )

        if self.status == DecisionStatus.SAFE_DEFAULT:
            if (
                not isinstance(
                    self.failure_reason,
                    str,
                )
                or not self.failure_reason.strip()
            ):
                raise ValueError(
                    "safe-default decision requires "
                    "failure_reason"
                )


@dataclass(frozen=True)
class DecisionResult:
    decision: str
    risk_level: RiskLevel
    recommended_action: str
    metadata: DecisionMetadata

    def __post_init__(self) -> None:
        if not isinstance(self.decision, str) or not self.decision.strip():
            raise ValueError(
                "decision must be a non-empty string"
            )

        if not isinstance(self.risk_level, RiskLevel):
            raise ValueError(
                "risk_level must be a RiskLevel"
            )

        if (
            not isinstance(self.recommended_action, str)
            or not self.recommended_action.strip()
        ):
            raise ValueError(
                "recommended_action must be a non-empty string"
            )

        if not isinstance(self.metadata, DecisionMetadata):
            raise ValueError(
                "metadata must be DecisionMetadata"
            )


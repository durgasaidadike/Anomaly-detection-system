from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from confidence_evaluator import (
    ConfidenceEvaluationConfig,
    ConfidenceEvaluator,
)


class FakeCandidate:
    def __init__(
        self,
        observation_count=0,
        behavioral_consistency=None,
        duration_seconds=0.0,
        contextual_history=None,
    ):
        self.pattern_id = "candidate-1"
        self.session_id = "session-1"

        self.metadata = SimpleNamespace(
            observation_count=observation_count,
            complete=False,
            interrupted=False,
            status="evaluating",
        )

        self.operational_characteristics = (
            {"operation_counts": {"MODIFIED": 3}}
            if observation_count
            else {}
        )

        self.temporal_characteristics = (
            {
                "duration_seconds": duration_seconds,
                "time_between_operations": [
                    1.0,
                    1.0,
                    1.0,
                ],
            }
            if observation_count
            else {}
        )

        self.sequential_characteristics = (
            [
                {
                    "operation_type": "MODIFIED",
                    "timestamp": datetime.now(timezone.utc),
                }
            ]
            if observation_count
            else []
        )

        self.contextual_characteristics = (
            {"directory": "project"}
            if observation_count
            else {}
        )

        self.relationship_characteristics = (
            [{"from": "OPEN", "to": "MODIFIED"}]
            if observation_count
            else []
        )

        self.session_characteristics = (
            {
                "observation_count": observation_count,
                "behavioral_consistency": (
                    behavioral_consistency
                    if behavioral_consistency is not None
                    else 1.0
                ),
                "session_length_seconds": duration_seconds,
                "operation_diversity": 1,
            }
            if observation_count
            else {}
        )

        context_values = {}

        if contextual_history:
            context_values["directory__history"] = (
                contextual_history
            )

        self.context = SimpleNamespace(
            values=context_values
        )

    def observation_count(self):
        return self.metadata.observation_count


def test_zero_history_produces_zero_history_availability():
    evaluator = ConfidenceEvaluator()

    result = evaluator.evaluate(
        FakeCandidate(observation_count=5),
        [],
    )

    assert result["dimension_scores"][
        "history_availability"
    ] == 0.0


def test_history_availability_grows_with_history():
    evaluator = ConfidenceEvaluator(
        ConfidenceEvaluationConfig(
            history_target=4,
        )
    )

    result = evaluator.evaluate(
        FakeCandidate(observation_count=5),
        [object(), object()],
    )

    assert result["dimension_scores"][
        "history_availability"
    ] == pytest.approx(0.5)


def test_candidate_completeness_is_zero_for_empty_candidate():
    evaluator = ConfidenceEvaluator()

    result = evaluator.evaluate(
        FakeCandidate(observation_count=0),
        [],
        behavioral_metadata={},
        session_metadata={},
    )

    assert result["dimension_scores"][
        "candidate_completeness"
    ] == 0.0


def test_behavioral_consistency_uses_candidate_value():
    evaluator = ConfidenceEvaluator()

    candidate = FakeCandidate(
        observation_count=5,
        behavioral_consistency=0.72,
    )

    result = evaluator.evaluate(
        candidate,
        [object()],
    )

    assert result["dimension_scores"][
        "behavioral_consistency"
    ] == pytest.approx(0.72)


def test_session_maturity_grows_with_observations_and_duration():
    evaluator = ConfidenceEvaluator(
        ConfidenceEvaluationConfig(
            observation_target=10,
            session_duration_target_seconds=100.0,
        )
    )

    candidate = FakeCandidate(
        observation_count=5,
        duration_seconds=50.0,
    )

    result = evaluator.evaluate(
        candidate,
        [object()],
    )

    assert result["dimension_scores"][
        "session_maturity"
    ] == pytest.approx(0.5)


def test_stable_context_produces_higher_stability():
    evaluator = ConfidenceEvaluator()

    stable = FakeCandidate(
        observation_count=10,
        behavioral_consistency=1.0,
        duration_seconds=100.0,
        contextual_history=[
            {"value": "project", "superseded_by": None},
        ],
    )

    changing = FakeCandidate(
        observation_count=10,
        behavioral_consistency=1.0,
        duration_seconds=100.0,
        contextual_history=[
            {"value": "project-a", "superseded_by": "project-b"},
            {"value": "project-b", "superseded_by": None},
            {"value": "project-c", "superseded_by": None},
        ],
    )

    stable_result = evaluator.evaluate(
        stable,
        [object(), object(), object()],
    )

    changing_result = evaluator.evaluate(
        changing,
        [object(), object(), object()],
    )

    assert (
        stable_result["dimension_scores"][
            "behavioral_stability"
        ]
        >
        changing_result["dimension_scores"][
            "behavioral_stability"
        ]
    )


def test_similarity_and_drift_values_are_not_used():
    evaluator = ConfidenceEvaluator()

    candidate = FakeCandidate(
        observation_count=8,
        behavioral_consistency=0.8,
        duration_seconds=80.0,
    )

    first = evaluator.evaluate(
        candidate,
        [object(), object()],
        similarity_metadata={"score": 0.0},
        drift_metadata={"score": 1.0},
    )

    second = evaluator.evaluate(
        candidate,
        [object(), object()],
        similarity_metadata={"score": 1.0},
        drift_metadata={"score": 0.0},
    )

    assert (
        first["dimension_scores"]
        == second["dimension_scores"]
    )


def test_candidate_is_not_mutated():
    evaluator = ConfidenceEvaluator()

    candidate = FakeCandidate(
        observation_count=5,
        behavioral_consistency=0.8,
        duration_seconds=50.0,
    )

    before = candidate.session_characteristics.copy()

    evaluator.evaluate(
        candidate,
        [object()],
    )

    assert candidate.session_characteristics == before

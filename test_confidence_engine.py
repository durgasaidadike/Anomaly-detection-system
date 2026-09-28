from datetime import datetime, timezone
from types import SimpleNamespace
from copy import deepcopy

import pytest

from confidence_engine import ConfidenceEngine
from confidence_result import ConfidenceStatus


class FakeCandidate:
    def __init__(
        self,
        user_id="user-1",
        session_id="current-session",
        observation_count=5,
    ):
        self.pattern_id = "candidate-1"
        self.user_id = user_id
        self.session_id = session_id

        self.metadata = SimpleNamespace(
            observation_count=observation_count,
            complete=False,
            interrupted=False,
            status="evaluating",
        )

        self.operational_characteristics = (
            {"operation_counts": {"MODIFY": observation_count}}
            if observation_count
            else {}
        )

        self.temporal_characteristics = (
            {
                "duration_seconds": 100.0,
                "time_between_operations": [
                    10.0,
                    10.0,
                ],
            }
            if observation_count
            else {}
        )

        self.sequential_characteristics = (
            [{"operation_type": "MODIFY"}]
            if observation_count
            else []
        )

        self.contextual_characteristics = (
            {"directory": "Projects"}
            if observation_count
            else {}
        )

        self.relationship_characteristics = (
            [{"from": "OPEN", "to": "MODIFY"}]
            if observation_count
            else []
        )

        self.session_characteristics = (
            {
                "observation_count": observation_count,
                "behavioral_consistency": 1.0,
                "session_length_seconds": 100.0,
                "operation_diversity": 1,
            }
            if observation_count
            else {}
        )

        self.context = SimpleNamespace(
            values={}
        )

    def observation_count(self):
        return self.metadata.observation_count


class FakeFinalPattern:
    def __init__(
        self,
        user_id,
        session_id,
    ):
        self.user_id = user_id
        self.session_id = session_id


class FakeRepository:
    def __init__(self, patterns):
        self.patterns = patterns

    def get_all(self):
        return list(self.patterns)


def test_repository_required():
    with pytest.raises(ValueError):
        ConfidenceEngine(repository=None)


def test_cold_start_returns_reduced_confidence():
    candidate = FakeCandidate(
        user_id="user-1"
    )

    repository = FakeRepository([])

    engine = ConfidenceEngine(repository)

    result = engine.calculateConfidence(
        candidate
    )

    assert result.status == ConfidenceStatus.COLD_START
    assert result.score is not None
    assert result.score < 1.0
    assert result.historical_pattern_count == 0


def test_normal_historical_evaluation():
    candidate = FakeCandidate(
        user_id="user-1",
        session_id="current-session",
    )

    repository = FakeRepository(
        [
            FakeFinalPattern(
                "user-1",
                "old-session-1",
            ),
            FakeFinalPattern(
                "user-1",
                "old-session-2",
            ),
        ]
    )

    engine = ConfidenceEngine(repository)

    result = engine.calculateConfidence(
        candidate
    )

    assert result.status == ConfidenceStatus.SUCCESS
    assert result.score is not None
    assert 0.0 <= result.score <= 1.0
    assert result.historical_pattern_count == 2


def test_user_isolation_preserved():
    candidate = FakeCandidate(
        user_id="user-1",
        session_id="current-session",
    )

    repository = FakeRepository(
        [
            FakeFinalPattern(
                "user-1",
                "old-session-1",
            ),
            FakeFinalPattern(
                "user-2",
                "other-user-session",
            ),
        ]
    )

    engine = ConfidenceEngine(repository)

    result = engine.calculateConfidence(
        candidate
    )

    assert result.status == ConfidenceStatus.SUCCESS
    assert result.historical_pattern_count == 1


def test_current_session_is_excluded():
    candidate = FakeCandidate(
        user_id="user-1",
        session_id="session-1",
    )

    repository = FakeRepository(
        [
            FakeFinalPattern(
                "user-1",
                "session-1",
            ),
            FakeFinalPattern(
                "user-1",
                "session-2",
            ),
        ]
    )

    engine = ConfidenceEngine(repository)

    history = engine.retrieveBehaviorHistory(
        candidate
    )

    assert len(history) == 1
    assert history[0].session_id == "session-2"


def test_none_user_id_does_not_share_history():
    candidate = FakeCandidate(
        user_id=None,
    )

    repository = FakeRepository(
        [
            FakeFinalPattern(
                None,
                "old-session",
            )
        ]
    )

    engine = ConfidenceEngine(repository)

    history = engine.retrieveBehaviorHistory(
        candidate
    )

    assert history == []


def test_missing_candidate_returns_failed_result():
    repository = FakeRepository([])

    engine = ConfidenceEngine(repository)

    result = engine.calculateConfidence(
        None
    )

    assert result.status == ConfidenceStatus.FAILED
    assert result.score is None


def test_insufficient_behavioral_data():
    candidate = FakeCandidate(
        user_id="user-1",
        observation_count=0,
    )

    repository = FakeRepository([])

    engine = ConfidenceEngine(repository)

    result = engine.calculateConfidence(
        candidate
    )

    assert result.status == ConfidenceStatus.COLD_START
    assert result.score is not None
    assert result.score < 1.0


def test_evaluator_failure_returns_failed_result():
    class FailingEvaluator:
        def evaluate(self, *args, **kwargs):
            raise RuntimeError("evaluator failed")

    candidate = FakeCandidate(
        user_id="user-1"
    )

    repository = FakeRepository([])

    engine = ConfidenceEngine(
        repository,
        evaluator=FailingEvaluator()
    )

    result = engine.calculateConfidence(
        candidate
    )

    assert result.status == ConfidenceStatus.FAILED
    assert result.score is None


def test_calculator_failure_returns_failed_result():
    class FailingCalculator:
        def calculate(self, dimension_scores):
            raise RuntimeError("calculator failed")

    candidate = FakeCandidate(
        user_id="user-1"
    )

    repository = FakeRepository([])

    engine = ConfidenceEngine(
        repository,
        calculator=FailingCalculator()
    )

    result = engine.calculateConfidence(
        candidate
    )

    assert result.status == ConfidenceStatus.FAILED
    assert result.score is None


def test_candidate_immutability():
    candidate = FakeCandidate(
        user_id="user-1"
    )

    original_session = dict(
        candidate.session_characteristics
    )

    repository = FakeRepository([])

    engine = ConfidenceEngine(repository)

    engine.calculateConfidence(candidate)

    assert (
        candidate.session_characteristics
        == original_session
    )


def test_stateless_repeated_evaluation():
    candidate = FakeCandidate(
        user_id="user-1"
    )

    repository = FakeRepository([])

    engine = ConfidenceEngine(repository)

    first = engine.calculateConfidence(candidate)
    second = engine.calculateConfidence(candidate)

    assert first.score == pytest.approx(second.score)
    assert first.status == second.status


def test_historical_patterns_remain_untouched():
    historical = [
        FakeFinalPattern(
            "user-1",
            "session-1",
        ),
        FakeFinalPattern(
            "user-1",
            "session-2",
        ),
    ]

    snapshot = deepcopy(historical)

    candidate = FakeCandidate(
        user_id="user-1"
    )

    repository = FakeRepository(historical)

    engine = ConfidenceEngine(repository)

    engine.calculateConfidence(candidate)

    for original, current in zip(
        snapshot,
        historical,
    ):
        assert (
            original.__dict__
            == current.__dict__
        )


def test_similarity_metadata_does_not_control_confidence():
    candidate = FakeCandidate(
        user_id="user-1"
    )

    repository = FakeRepository([])

    engine = ConfidenceEngine(repository)

    first = engine.calculateConfidence(
        candidate,
        similarity_metadata={"score": 0.0},
    )

    second = engine.calculateConfidence(
        candidate,
        similarity_metadata={"score": 1.0},
    )

    assert first.score == pytest.approx(second.score)


def test_drift_metadata_does_not_control_confidence():
    candidate = FakeCandidate(
        user_id="user-1"
    )

    repository = FakeRepository([])

    engine = ConfidenceEngine(repository)

    first = engine.calculateConfidence(
        candidate,
        drift_metadata={"score": 0.0},
    )

    second = engine.calculateConfidence(
        candidate,
        drift_metadata={"score": 1.0},
    )

    assert first.score == pytest.approx(second.score)


def test_score_remains_in_valid_range():
    candidate = FakeCandidate(
        user_id="user-1"
    )

    repository = FakeRepository([])

    engine = ConfidenceEngine(repository)

    result = engine.calculateConfidence(candidate)

    assert 0.0 <= result.score <= 1.0


def test_adapter_repository_is_supported():
    repository = FakeRepository(
        [
            FakeFinalPattern(
                "user-1",
                "session-1",
            )
        ]
    )

    adapter = SimpleNamespace(
        get_repository=lambda: repository
    )

    candidate = FakeCandidate(
        user_id="user-1"
    )

    engine = ConfidenceEngine(adapter)

    result = engine.calculateConfidence(
        candidate
    )

    assert result.historical_pattern_count == 1


def test_repository_failure_returns_failed_result():
    class FailingRepository:
        def get_all(self):
            raise RuntimeError(
                "repository unavailable"
            )

    candidate = FakeCandidate()

    engine = ConfidenceEngine(
        FailingRepository()
    )

    result = engine.calculateConfidence(
        candidate
    )

    assert result.status == ConfidenceStatus.FAILED
    assert result.score is None

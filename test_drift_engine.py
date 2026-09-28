from behavioral_trend_analyzer import (
    BehavioralTrendAnalyzer,
)
from drift_calculator import DriftCalculator
from drift_engine import DriftEngine
from drift_result import DriftStatus


class FakePattern:
    def __init__(
        self,
        *,
        session_id,
        user_id,
        operational=None,
        temporal=None,
        sequential=None,
        contextual=None,
        relationships=None,
        session=None,
    ):
        self.session_id = session_id
        self.user_id = user_id

        self.operational_characteristics = (
            operational or {}
        )

        self.temporal_characteristics = (
            temporal or {}
        )

        self.sequential_characteristics = (
            sequential or []
        )

        self.contextual_characteristics = (
            contextual or {}
        )

        self.relationship_characteristics = (
            relationships or []
        )

        self.session_characteristics = (
            session or {}
        )


class FakeRepository:
    def __init__(self, patterns=None):
        self.patterns = list(
            patterns or []
        )
        self.read_count = 0

    def get_all(self):
        self.read_count += 1
        return [
            pattern
            for pattern in self.patterns
        ]


def make_pattern(
    session_id,
    user_id,
    operations,
):
    sequence = [
        {
            "operation_type": operation,
            "timestamp": (
                f"2026-01-01T10:0{index}:00"
            ),
        }
        for index, operation in enumerate(
            operations
        )
    ]

    counts = {}

    for operation in operations:
        counts[operation] = (
            counts.get(operation, 0) + 1
        )

    return FakePattern(
        session_id=session_id,
        user_id=user_id,
        operational={
            "operation_counts": counts,
        },
        temporal={
            "duration_seconds": 60.0,
            "time_between_operations": [60.0],
            "working_rhythm": 1.0,
        },
        sequential=sequence,
        contextual={
            "directory": "Documents",
        },
        session={
            "session_id": session_id,
            "user_id": user_id,
            "session_start_time": (
                "2026-01-01T10:00:00"
            ),
            "observation_count": len(
                operations
            ),
            "operation_diversity": len(
                set(operations)
            ),
            "behavioral_density": 1.0,
            "behavioral_consistency": 1.0,
        },
    )


def build_engine(repository):
    return DriftEngine(
        repository=repository,
        analyzer=BehavioralTrendAnalyzer(
            minimum_history=2
        ),
        calculator=DriftCalculator(),
        minimum_history=2,
    )


def test_cold_start_when_no_history_exists():
    candidate = make_pattern(
        "active-1",
        "user-1",
        ["CREATE"],
    )

    repository = FakeRepository()

    engine = build_engine(repository)

    result = engine.calculateDrift(
        candidate
    )

    assert result.status == DriftStatus.COLD_START
    assert result.score is None
    assert result.historical_pattern_count == 0


def test_one_historical_pattern_is_insufficient():
    candidate = make_pattern(
        "active-1",
        "user-1",
        ["CREATE"],
    )

    historical = [
        make_pattern(
            "old-1",
            "user-1",
            ["CREATE"],
        )
    ]

    engine = build_engine(
        FakeRepository(historical)
    )

    result = engine.calculateDrift(
        candidate
    )

    assert (
        result.status
        == DriftStatus.INSUFFICIENT_DATA
    )
    assert result.score is None
    assert result.historical_pattern_count == 1


def test_successful_drift_evaluation():
    candidate = make_pattern(
        "active-1",
        "user-1",
        ["DELETE", "MOVE"],
    )

    historical = [
        make_pattern(
            "old-1",
            "user-1",
            ["CREATE", "MODIFY"],
        ),
        make_pattern(
            "old-2",
            "user-1",
            ["CREATE", "MODIFY"],
        ),
    ]

    engine = build_engine(
        FakeRepository(historical)
    )

    result = engine.calculateDrift(
        candidate
    )

    assert result.status == DriftStatus.SUCCESS
    assert result.score is not None
    assert 0.0 <= result.score <= 1.0
    assert result.historical_pattern_count == 2


def test_stable_behavior_produces_zero_or_near_zero_drift():
    candidate = make_pattern(
        "active-1",
        "user-1",
        ["CREATE", "MODIFY"],
    )

    historical = [
        make_pattern(
            "old-1",
            "user-1",
            ["CREATE", "MODIFY"],
        ),
        make_pattern(
            "old-2",
            "user-1",
            ["CREATE", "MODIFY"],
        ),
    ]

    engine = build_engine(
        FakeRepository(historical)
    )

    result = engine.calculateDrift(
        candidate
    )

    assert result.status == DriftStatus.SUCCESS
    assert result.score == 0.0


def test_user_isolation_is_preserved():
    candidate = make_pattern(
        "active-1",
        "user-1",
        ["CREATE", "MODIFY"],
    )

    historical = [
        make_pattern(
            "user1-old-1",
            "user-1",
            ["CREATE", "MODIFY"],
        ),
        make_pattern(
            "user1-old-2",
            "user-1",
            ["CREATE", "MODIFY"],
        ),
        make_pattern(
            "user2-old-1",
            "user-2",
            ["DELETE", "MOVE"],
        ),
        make_pattern(
            "user2-old-2",
            "user-2",
            ["DELETE", "MOVE"],
        ),
    ]

    repository = FakeRepository(historical)

    engine = build_engine(repository)

    eligible = engine.retrieveBehaviorHistory(
        candidate
    )

    assert len(eligible) == 2
    assert all(
        pattern.user_id == "user-1"
        for pattern in eligible
    )


def test_unscoped_candidate_does_not_share_history_bucket():
    candidate = make_pattern(
        "active-1",
        None,
        ["CREATE"],
    )

    historical = [
        make_pattern(
            "old-1",
            None,
            ["CREATE"],
        ),
        make_pattern(
            "old-2",
            None,
            ["CREATE"],
        ),
    ]

    repository = FakeRepository(historical)

    engine = build_engine(repository)

    eligible = engine.retrieveBehaviorHistory(
        candidate
    )

    assert eligible == []


def test_current_session_is_not_used_as_history():
    candidate = make_pattern(
        "session-1",
        "user-1",
        ["CREATE"],
    )

    historical = [
        make_pattern(
            "session-1",
            "user-1",
            ["CREATE"],
        ),
        make_pattern(
            "old-1",
            "user-1",
            ["CREATE"],
        ),
        make_pattern(
            "old-2",
            "user-1",
            ["CREATE"],
        ),
    ]

    engine = build_engine(
        FakeRepository(historical)
    )

    eligible = engine.retrieveBehaviorHistory(
        candidate
    )

    assert len(eligible) == 2
    assert all(
        pattern.session_id != "session-1"
        for pattern in eligible
    )


def test_repository_history_is_read_only():
    historical = [
        make_pattern(
            "old-1",
            "user-1",
            ["CREATE"],
        ),
        make_pattern(
            "old-2",
            "user-1",
            ["CREATE"],
        ),
    ]

    repository = FakeRepository(
        historical
    )

    candidate = make_pattern(
        "active-1",
        "user-1",
        ["DELETE"],
    )

    engine = build_engine(repository)

    before = [
        list(
            pattern.sequential_characteristics
        )
        for pattern in repository.patterns
    ]

    result = engine.calculateDrift(
        candidate
    )

    after = [
        list(
            pattern.sequential_characteristics
        )
        for pattern in repository.patterns
    ]

    assert result.status == DriftStatus.SUCCESS
    assert before == after


def test_repository_failure_returns_failed_result():
    class FailingRepository:
        def get_all(self):
            raise RuntimeError(
                "repository unavailable"
            )

    candidate = make_pattern(
        "active-1",
        "user-1",
        ["CREATE"],
    )

    engine = build_engine(
        FailingRepository()
    )

    result = engine.calculateDrift(
        candidate
    )

    assert result.status == DriftStatus.FAILED
    assert result.score is None

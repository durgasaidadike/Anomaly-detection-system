from copy import deepcopy
from datetime import datetime

import pytest

from behavioral_trend_analyzer import (
    BehavioralTrendAnalyzer,
)
from drift_engine import DriftEngine
from drift_result import DriftStatus


class Pattern:
    def __init__(
        self,
        *,
        session_id,
        user_id,
        operations,
        duration_seconds=60.0,
        working_rhythm=1.0,
        context=None,
        relationships=None,
    ):
        self.session_id = session_id
        self.user_id = user_id

        counts = {}

        for operation in operations:
            counts[operation] = (
                counts.get(operation, 0) + 1
            )

        self.operational_characteristics = {
            "operation_counts": counts,
        }

        self.temporal_characteristics = {
            "duration_seconds": duration_seconds,
            "time_between_operations": [60.0],
            "working_rhythm": working_rhythm,
        }

        self.sequential_characteristics = [
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

        self.contextual_characteristics = (
            context or {}
        )

        self.relationship_characteristics = (
            relationships or []
        )

        self.session_characteristics = {
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
        }


class Repository:
    def __init__(self, patterns):
        self.patterns = list(patterns)

    def get_all(self):
        return [
            deepcopy(pattern)
            for pattern in self.patterns
        ]


def engine(repository):
    return DriftEngine(
        repository=repository,
        analyzer=BehavioralTrendAnalyzer(
            minimum_history=2
        ),
        minimum_history=2,
    )


def test_extremely_stable_behavior_has_no_drift():
    historical = [
        Pattern(
            session_id="old-1",
            user_id="user-1",
            operations=["CREATE", "MODIFY"],
        ),
        Pattern(
            session_id="old-2",
            user_id="user-1",
            operations=["CREATE", "MODIFY"],
        ),
    ]

    candidate = Pattern(
        session_id="active",
        user_id="user-1",
        operations=["CREATE", "MODIFY"],
    )

    result = engine(
        Repository(historical)
    ).calculateDrift(candidate)

    assert result.status == DriftStatus.SUCCESS
    assert result.score == 0.0


def test_rapid_behavioral_evolution_is_detected():
    historical = [
        Pattern(
            session_id="old-1",
            user_id="user-1",
            operations=["CREATE", "MODIFY"],
        ),
        Pattern(
            session_id="old-2",
            user_id="user-1",
            operations=["CREATE", "MODIFY"],
        ),
    ]

    candidate = Pattern(
        session_id="active",
        user_id="user-1",
        operations=[
            "DELETE",
            "MOVE",
            "COPY",
            "RENAME",
        ],
    )

    result = engine(
        Repository(historical)
    ).calculateDrift(candidate)

    assert result.status == DriftStatus.SUCCESS
    assert result.score is not None
    assert result.score > 0.0


def test_long_inactivity_is_reflected_in_temporal_drift():
    historical = [
        Pattern(
            session_id="old-1",
            user_id="user-1",
            operations=["CREATE"],
            duration_seconds=60.0,
        ),
        Pattern(
            session_id="old-2",
            user_id="user-1",
            operations=["CREATE"],
            duration_seconds=60.0,
        ),
    ]

    candidate = Pattern(
        session_id="active",
        user_id="user-1",
        operations=["CREATE"],
        duration_seconds=3600.0,
    )

    result = engine(
        Repository(historical)
    ).calculateDrift(candidate)

    assert result.status == DriftStatus.SUCCESS
    assert (
        result.dimension_scores[
            "temporal_characteristics"
        ]
        > 0.0
    )


def test_duplicate_historical_sessions_are_handled():
    historical = [
        Pattern(
            session_id="old-1",
            user_id="user-1",
            operations=["CREATE", "MODIFY"],
        ),
        Pattern(
            session_id="old-2",
            user_id="user-1",
            operations=["CREATE", "MODIFY"],
        ),
        Pattern(
            session_id="old-3",
            user_id="user-1",
            operations=["CREATE", "MODIFY"],
        ),
    ]

    candidate = Pattern(
        session_id="active",
        user_id="user-1",
        operations=["CREATE", "MODIFY"],
    )

    result = engine(
        Repository(historical)
    ).calculateDrift(candidate)

    assert result.status == DriftStatus.SUCCESS
    assert result.score == 0.0


def test_missing_dimensions_do_not_crash_engine():
    class PartialPattern:
        def __init__(
            self,
            session_id,
            user_id,
        ):
            self.session_id = session_id
            self.user_id = user_id
            self.operational_characteristics = {
                "operation_counts": {
                    "CREATE": 1,
                }
            }
            self.temporal_characteristics = {}
            self.sequential_characteristics = []
            self.contextual_characteristics = {}
            self.relationship_characteristics = []
            self.session_characteristics = {}

    historical = [
        PartialPattern(
            "old-1",
            "user-1",
        ),
        PartialPattern(
            "old-2",
            "user-1",
        ),
    ]

    candidate = PartialPattern(
        "active",
        "user-1",
    )

    result = engine(
        Repository(historical)
    ).calculateDrift(candidate)

    assert result.status in (
        DriftStatus.SUCCESS,
        DriftStatus.INSUFFICIENT_DATA,
    )


def test_candidate_pattern_is_not_modified():
    historical = [
        Pattern(
            session_id="old-1",
            user_id="user-1",
            operations=["CREATE"],
        ),
        Pattern(
            session_id="old-2",
            user_id="user-1",
            operations=["CREATE"],
        ),
    ]

    candidate = Pattern(
        session_id="active",
        user_id="user-1",
        operations=["DELETE"],
    )

    before = deepcopy(candidate)

    engine(
        Repository(historical)
    ).calculateDrift(candidate)

    assert (
        candidate.__dict__
        == before.__dict__
    )


def test_historical_patterns_are_not_modified():
    historical = [
        Pattern(
            session_id="old-1",
            user_id="user-1",
            operations=["CREATE"],
        ),
        Pattern(
            session_id="old-2",
            user_id="user-1",
            operations=["CREATE"],
        ),
    ]

    snapshot = deepcopy(historical)

    candidate = Pattern(
        session_id="active",
        user_id="user-1",
        operations=["DELETE"],
    )

    engine(
        Repository(historical)
    ).calculateDrift(candidate)

    for original, current in zip(
        snapshot,
        historical,
    ):
        assert (
            original.__dict__
            == current.__dict__
        )


def test_interrupted_analysis_returns_failed_result():
    class FailingAnalyzer:
        def analyze(
            self,
            candidate_pattern,
            historical_patterns,
        ):
            raise RuntimeError(
                "comparison interrupted"
            )

    historical = [
        Pattern(
            session_id="old-1",
            user_id="user-1",
            operations=["CREATE"],
        ),
        Pattern(
            session_id="old-2",
            user_id="user-1",
            operations=["CREATE"],
        ),
    ]

    candidate = Pattern(
        session_id="active",
        user_id="user-1",
        operations=["DELETE"],
    )

    drift_engine = DriftEngine(
        repository=Repository(historical),
        analyzer=FailingAnalyzer(),
        minimum_history=2,
    )

    result = drift_engine.calculateDrift(
        candidate
    )

    assert result.status == DriftStatus.FAILED
    assert result.score is None


def test_result_contains_all_documented_dimensions():
    historical = [
        Pattern(
            session_id="old-1",
            user_id="user-1",
            operations=["CREATE"],
        ),
        Pattern(
            session_id="old-2",
            user_id="user-1",
            operations=["CREATE"],
        ),
    ]

    candidate = Pattern(
        session_id="active",
        user_id="user-1",
        operations=["CREATE"],
    )

    result = engine(
        Repository(historical)
    ).calculateDrift(candidate)

    expected = {
        "behavioral_workflow",
        "operation_frequency",
        "temporal_characteristics",
        "working_rhythm",
        "behavioral_relationships",
        "session_characteristics",
        "contextual_behavior",
    }

    assert set(
        result.dimension_scores.keys()
    ) == expected

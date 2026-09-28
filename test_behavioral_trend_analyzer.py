from behavioral_trend_analyzer import (
    BehavioralTrendAnalyzer,
)


class FakePattern:
    def __init__(
        self,
        *,
        operational=None,
        temporal=None,
        sequential=None,
        contextual=None,
        relationships=None,
        session=None,
    ):
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


def make_pattern(
    operations,
    timestamps=None,
    *,
    working_rhythm=None,
    context=None,
    relationships=None,
    session=None,
):
    timestamps = timestamps or [
        "2026-01-01T10:00:00",
        "2026-01-01T10:01:00",
    ]

    sequential = [
        {
            "operation_type": operation,
            "timestamp": timestamp,
        }
        for operation, timestamp in zip(
            operations,
            timestamps,
        )
    ]

    counts = {}

    for operation in operations:
        counts[operation] = (
            counts.get(operation, 0) + 1
        )

    return FakePattern(
        operational={
            "operation_counts": counts,
        },
        temporal={
            "duration_seconds": 60.0,
            "time_between_operations": [60.0],
            "working_rhythm": working_rhythm,
        },
        sequential=sequential,
        contextual=context or {},
        relationships=relationships or [],
        session=session or {
            "observation_count": len(
                operations
            ),
            "operation_diversity": len(
                set(operations)
            ),
            "behavioral_density": 1.0,
            "behavioral_consistency": 1.0,
            "task_complexity": {
                "operation_diversity": len(
                    set(operations)
                )
            },
            "session_id": "session",
            "user_id": "user",
            "session_start_time": (
                "2026-01-01T10:00:00"
            ),
        },
    )


def test_insufficient_history_returns_none_dimensions():
    analyzer = BehavioralTrendAnalyzer(
        minimum_history=2
    )

    candidate = make_pattern(["CREATE"])

    result = analyzer.analyze(
        candidate,
        [make_pattern(["CREATE"])],
    )

    assert all(
        value is None
        for value in result.values()
    )


def test_identical_behavior_has_zero_drift():
    analyzer = BehavioralTrendAnalyzer()

    historical = [
        make_pattern(["CREATE", "MODIFY"]),
        make_pattern(["CREATE", "MODIFY"]),
    ]

    candidate = make_pattern(
        ["CREATE", "MODIFY"],
        timestamps=[
            "2026-09-01T12:00:00",
            "2026-09-01T12:20:00",
        ],
    )

    result = analyzer.analyze(
        candidate,
        historical,
    )

    assert result[
        "behavioral_workflow"
    ] == 0.0

    assert result[
        "operation_frequency"
    ] == 0.0


def test_different_workflow_produces_drift():
    analyzer = BehavioralTrendAnalyzer()

    historical = [
        make_pattern(["CREATE", "MODIFY"]),
        make_pattern(["CREATE", "MODIFY"]),
    ]

    candidate = make_pattern(
        ["DELETE", "MOVE"]
    )

    result = analyzer.analyze(
        candidate,
        historical,
    )

    assert result[
        "behavioral_workflow"
    ] > 0.0

    assert result[
        "operation_frequency"
    ] > 0.0


def test_absolute_timestamps_do_not_create_workflow_drift():
    analyzer = BehavioralTrendAnalyzer()

    historical = [
        make_pattern(
            ["CREATE", "MODIFY"],
            timestamps=[
                "2026-01-01T09:00:00",
                "2026-01-01T09:01:00",
            ],
        ),
        make_pattern(
            ["CREATE", "MODIFY"],
            timestamps=[
                "2026-02-01T14:00:00",
                "2026-02-01T14:01:00",
            ],
        ),
    ]

    candidate = make_pattern(
        ["CREATE", "MODIFY"],
        timestamps=[
            "2026-09-28T23:30:00",
            "2026-09-28T23:31:00",
        ],
    )

    result = analyzer.analyze(
        candidate,
        historical,
    )

    assert result[
        "behavioral_workflow"
    ] == 0.0


def test_context_change_is_detected():
    analyzer = BehavioralTrendAnalyzer()

    historical = [
        make_pattern(
            ["CREATE"],
            context={
                "directory": "Downloads",
            },
        ),
        make_pattern(
            ["CREATE"],
            context={
                "directory": "Downloads",
            },
        ),
    ]

    candidate = make_pattern(
        ["CREATE"],
        context={
            "directory": "Projects",
        },
    )

    result = analyzer.analyze(
        candidate,
        historical,
    )

    assert result[
        "contextual_behavior"
    ] > 0.0


def test_relationship_change_is_detected():
    analyzer = BehavioralTrendAnalyzer()

    historical = [
        make_pattern(
            ["CREATE"],
            relationships=[
                {
                    "source": "CREATE",
                    "target": "MODIFY",
                    "relationship": "FOLLOWS",
                }
            ],
        ),
        make_pattern(
            ["CREATE"],
            relationships=[
                {
                    "source": "CREATE",
                    "target": "MODIFY",
                    "relationship": "FOLLOWS",
                }
            ],
        ),
    ]

    candidate = make_pattern(
        ["CREATE"],
        relationships=[
            {
                "source": "DELETE",
                "target": "MOVE",
                "relationship": "FOLLOWS",
            }
        ],
    )

    result = analyzer.analyze(
        candidate,
        historical,
    )

    assert result[
        "behavioral_relationships"
    ] > 0.0


def test_session_identity_does_not_create_drift():
    analyzer = BehavioralTrendAnalyzer()

    historical = [
        make_pattern(
            ["CREATE", "MODIFY"],
            session={
                "session_id": "old-1",
                "user_id": "user",
                "session_start_time": (
                    "2026-01-01T09:00:00"
                ),
                "observation_count": 2,
                "operation_diversity": 2,
                "behavioral_density": 1.0,
                "behavioral_consistency": 1.0,
            },
        ),
        make_pattern(
            ["CREATE", "MODIFY"],
            session={
                "session_id": "old-2",
                "user_id": "user",
                "session_start_time": (
                    "2026-02-01T14:00:00"
                ),
                "observation_count": 2,
                "operation_diversity": 2,
                "behavioral_density": 1.0,
                "behavioral_consistency": 1.0,
            },
        ),
    ]

    candidate = make_pattern(
        ["CREATE", "MODIFY"],
        session={
            "session_id": "new-session",
            "user_id": "user",
            "session_start_time": (
                "2026-09-28T23:00:00"
            ),
            "observation_count": 2,
            "operation_diversity": 2,
            "behavioral_density": 1.0,
            "behavioral_consistency": 1.0,
        },
    )

    result = analyzer.analyze(
        candidate,
        historical,
    )

    assert result[
        "session_characteristics"
    ] == 0.0

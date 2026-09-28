from datetime import datetime, timedelta

from candidate_pattern_manager import CandidatePatternManager
from drift_engine import DriftEngine
from drift_result import DriftStatus
from final_pattern_repository import FinalPatternRepository
from final_pattern_repository_adapter import (
    FinalPatternRepositoryAdapter,
)


def build_completed_pattern(
    session_id,
    user_id,
    operations,
    start_time,
):
    repository = FinalPatternRepository()

    adapter = FinalPatternRepositoryAdapter(
        repository=repository
    )

    manager = CandidatePatternManager(
        final_pattern_handler=adapter.store
    )

    manager.createPattern(
        session_id=session_id,
        user_id=user_id,
        session_start_time=start_time,
    )

    for index, operation in enumerate(operations):
        manager.updatePattern(
            session_id,
            {
                "operation_type": operation,
                "timestamp": (
                    start_time
                    + timedelta(minutes=index)
                ),
                "file_extension": ".txt",
                "directory": "Documents",
                "event_hour": 10,
                "file_size": 1000 + index,
            },
        )

    manager.completeSession(
        session_id,
        start_time + timedelta(hours=1)
    )

    finalized = manager.finalizePattern(
        session_id
    )

    assert finalized is not None
    assert finalized.metadata.complete is True

    stored = repository.get_all()

    assert len(stored) == 1

    return stored[0]


def test_drift_engine_reads_real_repository():
    repository = FinalPatternRepository()

    adapter = FinalPatternRepositoryAdapter(
        repository=repository
    )

    historical_candidates = [
        (
            "session-old-1",
            [
                "CREATE",
                "MODIFY",
            ],
            datetime(2026, 1, 1, 10, 0),
        ),
        (
            "session-old-2",
            [
                "CREATE",
                "DELETE",
            ],
            datetime(2026, 2, 1, 10, 0),
        ),
        (
            "session-old-3",
            [
                "MODIFY",
                "MOVE",
            ],
            datetime(2026, 3, 1, 10, 0),
        ),
    ]

    for session_id, operations, start_time in (
        historical_candidates
    ):
        manager = CandidatePatternManager(
            final_pattern_handler=adapter.store
        )

        manager.createPattern(
            session_id=session_id,
            user_id="user-1",
            session_start_time=start_time,
        )

        for index, operation in enumerate(
            operations
        ):
            manager.updatePattern(
                session_id,
                {
                    "operation_type": operation,
                    "timestamp": (
                        start_time
                        + timedelta(minutes=index)
                    ),
                    "file_extension": ".txt",
                    "directory": "Documents",
                    "event_hour": 10,
                    "file_size": 1000 + index,
                },
            )

        manager.completeSession(
            session_id,
            start_time + timedelta(hours=1)
        )

        finalized = manager.finalizePattern(
            session_id
        )

        assert finalized is not None
        assert finalized.metadata.complete is True

    assert repository.count() == 3

    candidate_manager = CandidatePatternManager()

    candidate_manager.createPattern(
        "session-active",
        user_id="user-1",
        session_start_time=datetime(
            2026,
            9,
            28,
            10,
            0,
        ),
    )

    candidate_manager.updatePattern(
        "session-active",
        {
            "operation_type": "CREATE",
            "timestamp": datetime(
                2026,
                9,
                28,
                10,
                0,
            ),
            "file_extension": ".txt",
            "directory": "Documents",
            "event_hour": 10,
            "file_size": 1000,
        },
    )

    candidate_manager.updatePattern(
        "session-active",
        {
            "operation_type": "MODIFY",
            "timestamp": datetime(
                2026,
                9,
                28,
                10,
                1,
            ),
            "file_extension": ".txt",
            "directory": "Documents",
            "event_hour": 10,
            "file_size": 1001,
        },
    )

    candidate_manager.completeSession(
        "session-active",
        datetime(2026, 9, 28, 11, 0)
    )

    candidate = candidate_manager.getPatternSnapshot(
        "session-active"
    )

    assert candidate is not None

    engine = DriftEngine(
        repository=repository
    )

    result = engine.calculateDrift(
        candidate
    )

    assert result.status == DriftStatus.SUCCESS
    assert result.score is not None
    assert 0.0 <= result.score <= 1.0
    assert result.historical_pattern_count == 3


def test_real_repository_preserves_user_isolation():
    repository = FinalPatternRepository()

    adapter = FinalPatternRepositoryAdapter(
        repository=repository
    )

    patterns = [
        (
            "u1-session-1",
            "user-1",
            ["CREATE", "MODIFY"],
            datetime(2026, 1, 1, 10, 0),
        ),
        (
            "u1-session-2",
            "user-1",
            ["CREATE", "DELETE"],
            datetime(2026, 2, 1, 10, 0),
        ),
        (
            "u1-session-3",
            "user-1",
            ["MODIFY", "MOVE"],
            datetime(2026, 3, 1, 10, 0),
        ),
        (
            "u2-session-1",
            "user-2",
            ["DELETE", "MOVE"],
            datetime(2026, 4, 1, 10, 0),
        ),
        (
            "u2-session-2",
            "user-2",
            ["COPY", "CREATE"],
            datetime(2026, 5, 1, 10, 0),
        ),
    ]

    for (
        session_id,
        user_id,
        operations,
        start_time,
    ) in patterns:
        manager = CandidatePatternManager(
            final_pattern_handler=adapter.store
        )

        manager.createPattern(
            session_id=session_id,
            user_id=user_id,
            session_start_time=start_time,
        )

        for index, operation in enumerate(
            operations
        ):
            manager.updatePattern(
                session_id,
                {
                    "operation_type": operation,
                    "timestamp": (
                        start_time
                        + timedelta(minutes=index)
                    ),
                    "file_extension": ".txt",
                    "directory": "Documents",
                    "event_hour": 10,
                    "file_size": 2000 + index,
                },
            )

        manager.completeSession(
            session_id,
            start_time + timedelta(hours=1)
        )

        finalized = manager.finalizePattern(
            session_id
        )

        assert finalized is not None

    assert repository.count() == 5

    active_manager = CandidatePatternManager()

    active_manager.createPattern(
        "active-user-1",
        user_id="user-1",
        session_start_time=datetime(
            2026,
            9,
            28,
            12,
            0,
        ),
    )

    active_manager.updatePattern(
        "active-user-1",
        {
            "operation_type": "CREATE",
            "timestamp": datetime(
                2026,
                9,
                28,
                12,
                0,
            ),
        },
    )

    candidate = active_manager.getPatternSnapshot(
        "active-user-1"
    )

    engine = DriftEngine(
        repository=repository
    )

    eligible = engine.retrieveBehaviorHistory(
        candidate
    )

    assert len(eligible) == 3
    assert all(
        pattern.user_id == "user-1"
        for pattern in eligible
    )


def test_real_repository_history_remains_unchanged():
    repository = FinalPatternRepository()

    adapter = FinalPatternRepositoryAdapter(
        repository=repository
    )

    manager = CandidatePatternManager(
        final_pattern_handler=adapter.store
    )

    manager.createPattern(
        "historical-session",
        user_id="user-1",
        session_start_time=datetime(
            2026,
            1,
            1,
            10,
            0,
        ),
    )

    manager.updatePattern(
        "historical-session",
        {
            "operation_type": "CREATE",
            "timestamp": datetime(
                2026,
                1,
                1,
                10,
                0,
            ),
        },
    )

    manager.updatePattern(
        "historical-session",
        {
            "operation_type": "MODIFY",
            "timestamp": datetime(
                2026,
                1,
                1,
                10,
                1,
            ),
        },
    )

    manager.completeSession(
        "historical-session",
        datetime(2026, 1, 1, 11, 0)
    )

    finalized = manager.finalizePattern(
        "historical-session"
    )

    assert finalized is not None

    before = repository.get_all()

    active_manager = CandidatePatternManager()

    active_manager.createPattern(
        "active-session",
        user_id="user-1",
        session_start_time=datetime(
            2026,
            9,
            28,
            12,
            0,
        ),
    )

    active_manager.updatePattern(
        "active-session",
        {
            "operation_type": "DELETE",
            "timestamp": datetime(
                2026,
                9,
                28,
                12,
                0,
            ),
        },
    )

    active_manager.completeSession(
        "active-session",
        datetime(2026, 9, 28, 13, 0)
    )

    candidate = active_manager.getPatternSnapshot(
        "active-session"
    )

    engine = DriftEngine(
        repository=repository
    )

    engine.calculateDrift(candidate)

    after = repository.get_all()

    assert len(before) == len(after)

    for before_pattern, after_pattern in zip(
        before,
        after,
    ):
        assert (
            before_pattern.pattern_id
            == after_pattern.pattern_id
        )

        assert (
            before_pattern.observations
            == after_pattern.observations
        )

        assert (
            before_pattern.operational_characteristics
            == after_pattern.operational_characteristics
        )

        assert (
            before_pattern.sequential_characteristics
            == after_pattern.sequential_characteristics
        )

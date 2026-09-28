from datetime import datetime, timezone

from candidate_pattern_manager import CandidatePatternManager
from confidence_engine import ConfidenceEngine
from confidence_result import ConfidenceStatus
from final_pattern_repository import FinalPatternRepository
from final_pattern_repository_adapter import (
    FinalPatternRepositoryAdapter,
)


def build_completed_historical_pattern(
    adapter,
    session_id,
    user_id,
    start_time,
):
    manager = CandidatePatternManager(
        final_pattern_handler=adapter.store,
    )

    manager.createPattern(
        session_id=session_id,
        user_id=user_id,
        session_start_time=start_time,
    )

    observations = [
        {
            "operation_type": "CREATED",
            "timestamp": start_time,
            "file_extension": ".txt",
            "directory": "Documents",
            "event_hour": 10,
            "file_size": 1000,
        },
        {
            "operation_type": "MODIFIED",
            "timestamp": (
                start_time.replace(minute=5)
            ),
            "file_extension": ".docx",
            "directory": "Projects",
            "event_hour": 10,
            "file_size": 5000,
        },
        {
            "operation_type": "MODIFIED",
            "timestamp": (
                start_time.replace(minute=10)
            ),
            "file_extension": ".docx",
            "directory": "Projects",
            "event_hour": 10,
            "file_size": 4500,
        },
    ]

    for observation in observations:
        manager.updatePattern(
            session_id,
            observation,
        )

    manager.completeSession(
        session_id,
        start_time.replace(hour=11)
    )

    finalized = manager.finalizePattern(
        session_id
    )

    assert finalized is not None
    assert finalized.metadata.complete is True

    return finalized


def build_current_candidate(
    session_id,
    user_id,
    start_time,
):
    manager = CandidatePatternManager()

    manager.createPattern(
        session_id=session_id,
        user_id=user_id,
        session_start_time=start_time,
    )

    observations = [
        {
            "operation_type": "CREATED",
            "timestamp": start_time,
            "file_extension": ".txt",
            "directory": "Documents",
            "event_hour": 10,
            "file_size": 1000,
        },
        {
            "operation_type": "MODIFIED",
            "timestamp": (
                start_time.replace(minute=5)
            ),
            "file_extension": ".docx",
            "directory": "Projects",
            "event_hour": 10,
            "file_size": 5000,
        },
        {
            "operation_type": "MODIFIED",
            "timestamp": (
                start_time.replace(minute=10)
            ),
            "file_extension": ".docx",
            "directory": "Projects",
            "event_hour": 10,
            "file_size": 4500,
        },
    ]

    for observation in observations:
        manager.updatePattern(
            session_id,
            observation,
        )

    candidate = manager.getCurrentPattern(
        session_id
    )

    assert candidate is not None

    return candidate


def test_confidence_engine_reads_real_repository_history():
    repository = FinalPatternRepository()

    adapter = FinalPatternRepositoryAdapter(
        repository=repository,
    )

    historical = build_completed_historical_pattern(
        adapter=adapter,
        session_id="historical-session-1",
        user_id="user-001",
        start_time=datetime(
            2026,
            1,
            1,
            10,
            0,
            tzinfo=timezone.utc,
        ),
    )

    assert historical.user_id == "user-001"

    candidate = build_current_candidate(
        session_id="current-session-1",
        user_id="user-001",
        start_time=datetime(
            2026,
            2,
            1,
            10,
            0,
            tzinfo=timezone.utc,
        ),
    )

    engine = ConfidenceEngine(
        repository=repository,
    )

    result = engine.calculateConfidence(
        candidate,
    )

    assert result.status == ConfidenceStatus.SUCCESS
    assert result.score is not None
    assert 0.0 <= result.score <= 1.0
    assert result.historical_pattern_count == 1

    assert result.get_dimension_score(
        "history_availability"
    ) > 0.0


def test_confidence_engine_excludes_current_session_from_real_repository():
    repository = FinalPatternRepository()

    adapter = FinalPatternRepositoryAdapter(
        repository=repository,
    )

    session_id = "shared-session"

    build_completed_historical_pattern(
        adapter=adapter,
        session_id=session_id,
        user_id="user-001",
        start_time=datetime(
            2026,
            1,
            1,
            10,
            0,
            tzinfo=timezone.utc,
        ),
    )

    candidate = build_current_candidate(
        session_id=session_id,
        user_id="user-001",
        start_time=datetime(
            2026,
            2,
            1,
            10,
            0,
            tzinfo=timezone.utc,
        ),
    )

    engine = ConfidenceEngine(
        repository=repository,
    )

    history = engine.retrieveBehaviorHistory(
        candidate,
    )

    assert history == []


def test_confidence_engine_preserves_user_isolation_with_real_repository():
    repository = FinalPatternRepository()

    adapter = FinalPatternRepositoryAdapter(
        repository=repository,
    )

    build_completed_historical_pattern(
        adapter=adapter,
        session_id="user-a-session",
        user_id="user-a",
        start_time=datetime(
            2026,
            1,
            1,
            10,
            0,
            tzinfo=timezone.utc,
        ),
    )

    build_completed_historical_pattern(
        adapter=adapter,
        session_id="user-b-session",
        user_id="user-b",
        start_time=datetime(
            2026,
            1,
            2,
            10,
            0,
            tzinfo=timezone.utc,
        ),
    )

    candidate = build_current_candidate(
        session_id="user-a-current",
        user_id="user-a",
        start_time=datetime(
            2026,
            2,
            1,
            10,
            0,
            tzinfo=timezone.utc,
        ),
    )

    engine = ConfidenceEngine(
        repository=repository,
    )

    history = engine.retrieveBehaviorHistory(
        candidate,
    )

    assert len(history) == 1
    assert history[0].user_id == "user-a"
    assert history[0].session_id == "user-a-session"


def test_confidence_engine_cold_start_with_real_repository():
    repository = FinalPatternRepository()

    candidate = build_current_candidate(
        session_id="cold-start-session",
        user_id="new-user",
        start_time=datetime(
            2026,
            2,
            1,
            10,
            0,
            tzinfo=timezone.utc,
        ),
    )

    engine = ConfidenceEngine(
        repository=repository,
    )

    result = engine.calculateConfidence(
        candidate,
    )

    assert result.status == ConfidenceStatus.COLD_START
    assert result.score is not None
    assert 0.0 <= result.score <= 1.0
    assert result.historical_pattern_count == 0

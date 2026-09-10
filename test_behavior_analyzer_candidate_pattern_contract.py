from datetime import datetime, timezone

from behavior_analyzer import BehaviorAnalyzer
from candidate_pattern_manager import CandidatePatternManager
from session_models import Session, SessionMetadata


def create_session():
    start = datetime(
        2026,
        1,
        1,
        10,
        0,
        0,
        tzinfo=timezone.utc,
    )

    metadata = SessionMetadata(
        session_id="contract-session-001",
        start_time=start,
        last_activity=start,
        event_count=0,
        status="ACTIVE",
    )

    session = Session(
        metadata=metadata,
        events=[],
    )

    return session


def test_behavior_analyzer_output_is_acceptable_to_candidate_pattern_boundary():
    session = create_session()

    analyzer = BehaviorAnalyzer()

    result = analyzer.analyzeSession(session)

    assert "behavioral_signals" in result
    assert "behavioral_context" in result
    assert "session_behavior_summary" in result

    manager = CandidatePatternManager()

    manager.createPattern(
        session_id="contract-session-001",
        session_start_time=session.metadata.start_time,
    )

    signals = result["behavioral_signals"]

    assert isinstance(signals, list)

    for signal in signals:
        assert isinstance(signal, dict)


def test_empty_session_generates_no_behavioral_signals():
    session = create_session()

    analyzer = BehaviorAnalyzer()

    result = analyzer.analyzeSession(session)

    assert result["behavioral_signals"] == []


def test_non_empty_behavioral_signal_contains_behavioral_information():
    from datetime import datetime, timezone

    timestamp = datetime(
        2026,
        1,
        1,
        10,
        0,
        0,
        tzinfo=timezone.utc,
    )

    metadata = SessionMetadata(
        session_id="contract-session-002",
        start_time=timestamp,
        last_activity=timestamp,
        event_count=1,
        status="ACTIVE",
    )

    session = Session(
        metadata=metadata,
        events=[
            {
                "event_type": "CREATED",
                "file_path": "/workspace/a.txt",
                "extension": ".txt",
                "directory": "/workspace",
            }
        ],
    )

    analyzer = BehaviorAnalyzer()

    result = analyzer.analyzeSession(session)

    assert len(result["behavioral_signals"]) > 0

    for signal in result["behavioral_signals"]:
        assert isinstance(signal, dict)
        assert "signal_type" in signal
from datetime import datetime, timezone

from behavior_analyzer import BehaviorAnalyzer
from candidate_pattern_manager import CandidatePatternManager
from session_models import Session, SessionMetadata


def create_behavioral_session():
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
        session_id="integration-session-001",
        start_time=timestamp,
        last_activity=timestamp,
        event_count=3,
        status="ACTIVE",
    )

    session = Session(
        metadata=metadata,
        events=[
            {
                "event_type": "CREATED",
                "file_path": "/workspace/report.txt",
                "extension": ".txt",
                "directory": "/workspace",
            },
            {
                "event_type": "MODIFIED",
                "file_path": "/workspace/report.txt",
                "extension": ".txt",
                "directory": "/workspace",
            },
            {
                "event_type": "RENAMED",
                "file_path": "/workspace/report.txt",
                "extension": ".txt",
                "directory": "/workspace",
            },
        ],
    )

    return session


def test_behavior_analyzer_output_can_build_candidate_pattern():
    session = create_behavioral_session()

    manager = CandidatePatternManager()

    manager.createPattern(
        session_id=session.metadata.session_id,
        user_id="user-001",
        session_start_time=session.metadata.start_time,
    )

    analyzer = BehaviorAnalyzer()

    result = analyzer.analyzeSession(session)

    assert result["behavioral_signals"]

    for signal in result["behavioral_signals"]:
        accepted = manager.updatePattern(
            session.metadata.session_id,
            signal,
            context=result["behavioral_context"],
            relationships=result["behavioral_relationships"],
        )

        assert accepted is not None

    pattern = manager.getCurrentPattern(
        session.metadata.session_id
    )

    assert pattern is not None
    assert pattern.observation_count() == len(
        result["behavioral_signals"]
    )


def test_behavior_analyzer_never_sends_raw_filesystem_event_to_cpm():
    session = create_behavioral_session()

    manager = CandidatePatternManager()

    manager.createPattern(
        session_id=session.metadata.session_id,
        user_id="user-001",
        session_start_time=session.metadata.start_time,
    )

    analyzer = BehaviorAnalyzer()

    result = analyzer.analyzeSession(session)

    for signal in result["behavioral_signals"]:
        assert "event_type" not in signal
        assert "event_action" not in signal
        assert "filesystem_event" not in signal
        assert "raw_event" not in signal

        manager.updatePattern(
            session.metadata.session_id,
            signal,
            context=result["behavioral_context"],
            relationships=result["behavioral_relationships"],
        )

    pattern = manager.getCurrentPattern(
        session.metadata.session_id
    )

    assert pattern is not None

    for observation in pattern.timeline.observations:
        assert "event_type" not in observation
        assert "event_action" not in observation
        assert "filesystem_event" not in observation
        assert "raw_event" not in observation
from datetime import datetime, timezone

from behavior_analyzer import BehaviorAnalyzer
from session_models import Session, SessionMetadata


def create_session(events=None, status="ACTIVE"):
    """
    Create a valid Session using the Module 03 Session model.
    """
    timestamp = datetime.now(timezone.utc)

    metadata = SessionMetadata(
        session_id="test-session-001",
        start_time=timestamp,
        last_activity=timestamp,
        event_count=0,
        status=status,
    )

    session = Session(
        metadata=metadata,
        events=events or [],
    )

    return session


def print_result(title, result):
    print(f"\n========== {title} ==========")
    print(f"Session ID: {result['session_id']}")
    print(f"Signals: {len(result['behavioral_signals'])}")
    print(f"Context: {result['behavioral_context']}")
    print(f"Summary: {result['session_behavior_summary']}")
    print("================================")


def test_basic_session():
    analyzer = BehaviorAnalyzer()

    events = [
        {
            "event_type": "CREATED",
            "file_path": r"C:\projects\watched-folder\a.txt",
            "extension": ".txt",
            "directory": r"C:\projects\watched-folder",
        },
        {
            "event_type": "MODIFIED",
            "file_path": r"C:\projects\watched-folder\a.txt",
            "extension": ".txt",
            "directory": r"C:\projects\watched-folder",
        },
    ]

    session = create_session(events)

    result = analyzer.analyzeSession(session)

    assert result["session_id"] == "test-session-001"
    assert result["behavioral_context"]["event_count"] == 2
    assert result["session_behavior_summary"]["event_count"] == 2

    print_result("BASIC SESSION TEST", result)


def test_empty_session():
    analyzer = BehaviorAnalyzer()

    session = create_session()

    result = analyzer.analyzeSession(session)

    assert result["session_id"] == "test-session-001"
    assert result["behavioral_context"]["event_count"] == 0
    assert result["behavioral_context"]["session_state"] == "EMPTY"
    assert result["behavioral_signals"][0]["signal_type"] == "EMPTY_SESSION"
    assert result["session_behavior_summary"]["event_count"] == 0

    print("\n========== EMPTY SESSION TEST ==========")
    print("Empty session handled: True")
    print("No phantom behavior: True")
    print("========================================")


def test_interrupted_session():
    analyzer = BehaviorAnalyzer()

    events = [
        {
            "event_type": "CREATED",
            "file_path": r"C:\projects\watched-folder\a.txt",
            "extension": ".txt",
            "directory": r"C:\projects\watched-folder",
        }
    ]

    session = create_session(
        events=events,
        status="INTERRUPTED",
    )

    result = analyzer.analyzeSession(session)

    assert result["session_id"] == "test-session-001"
    assert result["behavioral_context"]["session_state"] == "INTERRUPTED"
    assert result["session_behavior_summary"]["session_state"] == "INTERRUPTED"
    assert result["behavioral_context"]["event_count"] == 1

    print("\n========== INTERRUPTED SESSION TEST ==========")
    print("Interrupted session handled: True")
    print("Partial behavioral information preserved: True")
    print("==============================================")


def test_high_frequency_session():
    analyzer = BehaviorAnalyzer()

    events = []

    for index in range(20):
        events.append(
            {
                "event_type": "MODIFIED",
                "file_path": (
                    rf"C:\projects\watched-folder\file_{index}.txt"
                ),
                "extension": ".txt",
                "directory": r"C:\projects\watched-folder",
            }
        )

    session = create_session(events)

    result = analyzer.analyzeSession(session)

    assert result["session_id"] == "test-session-001"
    assert result["behavioral_context"]["event_count"] == 20
    assert (
        result["behavioral_context"]["operation_types"]["MODIFIED"]
        == 20
    )
    assert result["behavioral_context"]["unique_paths"] == 20

    print("\n========== HIGH-FREQUENCY SESSION TEST ==========")
    print("Event Count: 20")
    print("MODIFIED Operations: 20")
    print("High-frequency session handled: True")
    print("===============================================")


def test_partial_failure_handling():
    analyzer = BehaviorAnalyzer()

    events = [
        {
            "event_type": "CREATED",
            "file_path": r"C:\projects\watched-folder\a.txt",
            "extension": ".txt",
            "directory": r"C:\projects\watched-folder",
        }
    ]

    session = create_session(events)

    original_summary = analyzer.summarizeBehavior

    def failing_summary(*args, **kwargs):
        raise RuntimeError("Simulated summary failure")

    analyzer.summarizeBehavior = failing_summary

    result = analyzer.analyzeSession(session)

    analyzer.summarizeBehavior = original_summary

    assert result["session_id"] == "test-session-001"
    assert result["behavioral_context"]["event_count"] == 1
    assert len(result["behavioral_signals"]) > 0
    assert result["session_behavior_summary"] == {}

    print("\n========== PARTIAL FAILURE TEST ==========")
    print("Context preserved: True")
    print("Signals preserved: True")
    print("Failed summary isolated: True")
    print("Partial behavioral information preserved: True")
    print("==========================================")


def test_successful_observation_handoff():
    forwarded = []

    def observation_sink(observation):
        forwarded.append(observation)

    analyzer = BehaviorAnalyzer(
        observation_sink=observation_sink
    )

    events = [
        {
            "event_type": "CREATED",
            "file_path": r"C:\projects\watched-folder\a.txt",
            "extension": ".txt",
            "directory": r"C:\projects\watched-folder",
        }
    ]

    session = create_session(events)

    result = analyzer.analyzeSession(session)

    assert len(forwarded) == 1
    assert forwarded[0] is result
    assert forwarded[0]["session_id"] == "test-session-001"

    print("\n========== HANDOFF TEST ==========")
    print("Observation forwarded: True")
    print("Correct session forwarded: True")
    print("==================================")


def test_failed_observation_handoff():
    def failing_sink(observation):
        raise RuntimeError("Simulated downstream failure")

    analyzer = BehaviorAnalyzer(
        observation_sink=failing_sink
    )

    events = [
        {
            "event_type": "MODIFIED",
            "file_path": r"C:\projects\watched-folder\a.txt",
            "extension": ".txt",
            "directory": r"C:\projects\watched-folder",
        }
    ]

    session = create_session(events)

    result = analyzer.analyzeSession(session)

    assert result["session_id"] == "test-session-001"
    assert result["behavioral_context"]["event_count"] == 1
    assert len(result["behavioral_signals"]) > 0

    print("\n========== HANDOFF FAILURE TEST ==========")
    print("Downstream failure isolated: True")
    print("Behavioral result preserved: True")
    print("==========================================")


if __name__ == "__main__":
    test_basic_session()
    test_empty_session()
    test_interrupted_session()
    test_high_frequency_session()
    test_partial_failure_handling()
    test_successful_observation_handoff()
    test_failed_observation_handoff()

    print("\nAll initial Behavior Analyzer tests passed.")
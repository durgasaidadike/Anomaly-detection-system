from datetime import datetime

from candidate_pattern_models import (
    BehavioralContext,
    BehavioralTimeline,
    CandidatePattern,
    PatternMetadata,
    PatternStatus,
)


def test_pattern_statuses():
    assert PatternStatus.INITIALIZING == "Initializing"
    assert PatternStatus.LEARNING == "Learning"
    assert PatternStatus.EVALUATING == "Evaluating"
    assert PatternStatus.FINALIZING == "Finalizing"
    assert PatternStatus.COMPLETED == "Completed"


def test_empty_candidate_pattern():
    start_time = datetime.now()

    pattern = CandidatePattern(
        session_id="session-001",
        user_id="user-001",
        session_start_time=start_time,
    )

    assert pattern.session_id == "session-001"
    assert pattern.user_id == "user-001"
    assert pattern.session_start_time == start_time

    assert pattern.is_empty()
    assert pattern.observation_count() == 0

    assert pattern.metadata.status == PatternStatus.INITIALIZING
    assert pattern.metadata.observation_count == 0
    assert pattern.metadata.complete is False


def test_behavioral_timeline_stores_observations():
    timeline = BehavioralTimeline()

    observation = {
        "operation_type": "CREATE",
        "timestamp": datetime.now(),
    }

    timeline.add_observation(observation)

    assert len(timeline) == 1
    assert timeline.observations[0]["operation_type"] == "CREATE"


def test_behavioral_context_accumulates_values():
    context = BehavioralContext()

    context.update({
        "working_directory": "project",
        "session_intensity": "HIGH",
    })

    assert context.values["working_directory"] == "project"
    assert context.values["session_intensity"] == "HIGH"


def test_behavioral_context_updates_latest_understanding():
    context = BehavioralContext()

    context.update({
        "session_intensity": "LOW",
    })

    context.update({
        "session_intensity": "HIGH",
    })

    assert context.values["session_intensity"] == "HIGH"


def test_pattern_metadata_initial_state():
    metadata = PatternMetadata()

    assert metadata.status == PatternStatus.INITIALIZING
    assert metadata.observation_count == 0
    assert metadata.complete is False
    assert metadata.interrupted is False
    assert metadata.finalized_at is None
from datetime import datetime, timedelta, timezone

from candidate_pattern_manager import CandidatePatternManager


def test_candidate_pattern_grows_incrementally_from_behavioral_signals():
    manager = CandidatePatternManager()

    start = datetime(
        2026,
        1,
        1,
        10,
        0,
        0,
        tzinfo=timezone.utc,
    )

    session_id = "growth-session-001"

    pattern = manager.createPattern(
        session_id=session_id,
        user_id="user-001",
        session_start_time=start,
    )

    first_signal = {
        "signal_type": "OPERATION_ACTIVITY",
        "operation_type": "CREATED",
        "count": 1,
        "timestamp": start,
    }

    second_signal = {
        "signal_type": "OPERATION_ACTIVITY",
        "operation_type": "MODIFIED",
        "count": 1,
        "timestamp": start + timedelta(seconds=2),
    }

    third_signal = {
        "signal_type": "OPERATION_ACTIVITY",
        "operation_type": "RENAMED",
        "count": 1,
        "timestamp": start + timedelta(seconds=5),
    }

    manager.updatePattern(
        session_id,
        first_signal,
        context={
            "working_directory": "/workspace",
            "workflow_stage": "creation",
        },
        relationships=[],
    )

    assert pattern.observation_count() == 1
    assert pattern.operational_characteristics["total_operations"] == 1

    manager.updatePattern(
        session_id,
        second_signal,
        context={
            "working_directory": "/workspace",
            "workflow_stage": "editing",
        },
        relationships=[
            {
                "relationship_type": "SEQUENTIAL",
                "from_operation": "CREATED",
                "to_operation": "MODIFIED",
            }
        ],
    )

    assert pattern.observation_count() == 2
    assert pattern.operational_characteristics["total_operations"] == 2
    assert (
        pattern.operational_characteristics["operation_counts"]["CREATED"]
        == 1
    )
    assert (
        pattern.operational_characteristics["operation_counts"]["MODIFIED"]
        == 1
    )

    manager.updatePattern(
        session_id,
        third_signal,
        context={
            "working_directory": "/workspace",
            "workflow_stage": "rename",
        },
        relationships=[
            {
                "relationship_type": "SEQUENTIAL",
                "from_operation": "MODIFIED",
                "to_operation": "RENAMED",
            }
        ],
    )

    assert pattern.observation_count() == 3
    assert pattern.operational_characteristics["total_operations"] == 3

    assert (
        pattern.operational_characteristics["operation_counts"]["RENAMED"]
        == 1
    )

    assert len(pattern.sequential_characteristics) == 3
    assert len(pattern.relationship_characteristics) == 2

    assert (
        pattern.contextual_characteristics["workflow_stage"]
        == "rename"
    )

    assert (
        pattern.temporal_characteristics["last_observation_time"]
        == start + timedelta(seconds=5)
    )


def test_previous_behavioral_knowledge_is_not_discarded():
    manager = CandidatePatternManager()

    start = datetime(
        2026,
        1,
        1,
        10,
        0,
        0,
        tzinfo=timezone.utc,
    )

    session_id = "growth-session-002"

    manager.createPattern(
        session_id=session_id,
        user_id="user-001",
        session_start_time=start,
    )

    first_signal = {
        "signal_type": "EDITING_WORKFLOW",
        "operation_type": "MODIFIED",
        "timestamp": start,
    }

    second_signal = {
        "signal_type": "RENAME_ACTIVITY",
        "operation_type": "RENAMED",
        "timestamp": start + timedelta(seconds=3),
    }

    manager.updatePattern(
        session_id,
        first_signal,
        context={"workflow_stage": "editing"},
        relationships=[],
    )

    manager.updatePattern(
        session_id,
        second_signal,
        context={"workflow_stage": "renaming"},
        relationships=[
            {
                "relationship_type": "SEQUENTIAL",
                "from_operation": "MODIFIED",
                "to_operation": "RENAMED",
            }
        ],
    )

    pattern = manager.getCurrentPattern(session_id)

    assert pattern is not None

    assert pattern.observation_count() == 2

    assert (
        pattern.operational_characteristics["operation_counts"]["MODIFIED"]
        == 1
    )

    assert (
        pattern.operational_characteristics["operation_counts"]["RENAMED"]
        == 1
    )

    assert (
        pattern.contextual_characteristics["workflow_stage"]
        == "renaming"
    )

    assert len(pattern.relationship_characteristics) == 1
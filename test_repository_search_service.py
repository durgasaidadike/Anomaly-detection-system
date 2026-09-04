from datetime import datetime

from behavioral_identity import BehavioralIdentity
from behavioral_knowledge import BehavioralKnowledge
from final_pattern_models import FinalPattern
from repository_search_result import (
    SearchOutcome,
)
from repository_search_service import (
    RepositorySearchService,
)


def build_pattern(
    pattern_id="pattern-1",
    session_id="session-1",
    operation_type="CREATE",
):
    timestamp = datetime(
        2026,
        9,
        4,
        10,
        0,
        0,
    )

    return FinalPattern(
        pattern_id=pattern_id,
        session_id=session_id,
        user_id="user-1",
        created_at=timestamp,
        observations=[
            {
                "operation_type": operation_type,
                "timestamp": timestamp,
                "file_extension": ".py",
                "directory": "/project",
            }
        ],
        observation_count=1,
    )


def build_knowledge():
    return BehavioralKnowledge(
        knowledge_id="knowledge-pattern-1",
        user_id="user-1",
        behavior_key=(
            "user-1",
            ("CREATE",),
            (".py",),
            ("/project",),
        ),
        representative_pattern_id="pattern-1",
        occurrence_count=1,
    )


def build_service():
    pattern = build_pattern()
    knowledge = build_knowledge()

    identity = BehavioralIdentity()

    key = identity.build_key(pattern)

    return RepositorySearchService(
        patterns={
            "pattern-1": pattern,
        },
        pattern_index={
            key: "pattern-1",
        },
        knowledge={
            "knowledge-pattern-1": knowledge,
        },
        behavioral_identity=identity,
    )


def test_search_finds_exact_match():
    service = build_service()

    pattern = build_pattern(
        pattern_id="incoming",
        session_id="incoming-session",
    )

    result = service.search(pattern)

    assert result.matched is True
    assert result.outcome == (
        SearchOutcome.EXACT_MATCH
    )


def test_search_returns_representative_pattern():
    service = build_service()

    pattern = build_pattern(
        pattern_id="incoming",
        session_id="incoming-session",
    )

    result = service.search(pattern)

    assert result.representative_pattern is not None
    assert result.representative_pattern.pattern_id == (
        "pattern-1"
    )


def test_search_returns_behavioral_knowledge():
    service = build_service()

    pattern = build_pattern(
        pattern_id="incoming",
        session_id="incoming-session",
    )

    result = service.search(pattern)

    assert result.behavioral_knowledge is not None
    assert result.behavioral_knowledge.knowledge_id == (
        "knowledge-pattern-1"
    )


def test_search_returns_no_match_for_unknown_behavior():
    service = build_service()

    pattern = build_pattern(
        operation_type="DELETE",
    )

    result = service.search(pattern)

    assert result.matched is False
    assert result.outcome == (
        SearchOutcome.NO_MATCH
    )


def test_search_returns_no_match_for_invalid_pattern():
    service = build_service()

    result = service.search(None)

    assert result.matched is False
    assert result.outcome == (
        SearchOutcome.NO_MATCH
    )


def test_search_returns_independent_snapshots():
    service = build_service()

    pattern = build_pattern(
        pattern_id="incoming",
        session_id="incoming-session",
    )

    result = service.search(pattern)

    assert result.representative_pattern is not None
    assert result.behavioral_knowledge is not None

    assert result.representative_pattern is not (
        service._patterns["pattern-1"]
    )

    assert result.behavioral_knowledge is not (
        service._knowledge[
            "knowledge-pattern-1"
        ]
    )

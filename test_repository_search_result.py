from datetime import datetime

from behavioral_knowledge import BehavioralKnowledge
from final_pattern_models import FinalPattern
from repository_search_result import RepositorySearchResult


def build_pattern():
    timestamp = datetime(
        2026,
        9,
        4,
        10,
        0,
        0,
    )

    return FinalPattern(
        pattern_id="pattern-1",
        session_id="session-1",
        user_id="user-1",
        created_at=timestamp,
        observations=[
            {
                "operation_type": "CREATE",
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


def test_no_match_factory_creates_unmatched_result():
    result = RepositorySearchResult.no_match()

    assert result.matched is False
    assert result.representative_pattern is None
    assert result.behavioral_knowledge is None


def test_match_factory_creates_matched_result():
    pattern = build_pattern()
    knowledge = build_knowledge()

    result = RepositorySearchResult.match(
        representative_pattern=pattern,
        behavioral_knowledge=knowledge,
    )

    assert result.matched is True
    assert result.representative_pattern is pattern
    assert result.behavioral_knowledge is knowledge


def test_result_is_immutable():
    result = RepositorySearchResult.no_match()

    try:
        result.matched = True
    except AttributeError:
        pass
    else:
        raise AssertionError(
            "RepositorySearchResult should be immutable"
        )

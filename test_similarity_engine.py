from types import SimpleNamespace

import pytest

from pattern_comparator import PatternComparator
from similarity_calculator import (
    SimilarityCalculator,
    SimilarityWeights,
)
from similarity_engine import SimilarityEngine
from similarity_result import (
    SimilarityResult,
    SimilarityStatus,
)


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------

def make_pattern(
    session_id="session-001",
    user_id="user-001",
    *,
    operational=None,
    temporal=None,
    sequential=None,
    contextual=None,
    relationship=None,
    session=None,
    pattern_id=None,
):
    """
    Lightweight behavioral pattern used for unit tests.

    SimpleNamespace keeps these tests focused on Module 07 behavior
    rather than CandidatePattern/FinalPattern construction details.
    """

    pattern = SimpleNamespace(
        session_id=session_id,
        user_id=user_id,
        operational_characteristics=(
            operational if operational is not None else {}
        ),
        temporal_characteristics=(
            temporal if temporal is not None else {}
        ),
        sequential_characteristics=(
            sequential if sequential is not None else []
        ),
        contextual_characteristics=(
            contextual if contextual is not None else {}
        ),
        relationship_characteristics=(
            relationship if relationship is not None else []
        ),
        session_characteristics=(
            session if session is not None else {}
        ),
    )

    if pattern_id is not None:
        pattern.pattern_id = pattern_id

    return pattern


class FakeRepository:
    """
    Minimal repository boundary for SimilarityEngine unit tests.
    """

    def __init__(self, patterns=None):
        self._patterns = list(patterns or [])

    def get_all(self):
        return list(self._patterns)


# ----------------------------------------------------------------------
# SimilarityResult
# ----------------------------------------------------------------------

def test_similarity_result_accepts_valid_success_result():
    result = SimilarityResult(
        status=SimilarityStatus.SUCCESS,
        score=0.85,
        candidate_pattern_id="session-001",
        best_match_pattern_id="pattern-001",
        compared_pattern_count=2,
        dimension_scores={
            "operational": 1.0,
            "temporal": 0.8,
        },
    )

    assert result.status == SimilarityStatus.SUCCESS
    assert result.score == 0.85
    assert result.is_successful() is True


def test_similarity_result_rejects_score_outside_valid_range():
    with pytest.raises(ValueError):
        SimilarityResult(
            status=SimilarityStatus.SUCCESS,
            score=1.5,
            candidate_pattern_id="session-001",
            best_match_pattern_id="pattern-001",
            compared_pattern_count=1,
        )


def test_non_success_result_cannot_contain_score():
    with pytest.raises(ValueError):
        SimilarityResult(
            status=SimilarityStatus.COLD_START,
            score=0.0,
            candidate_pattern_id="session-001",
            best_match_pattern_id=None,
            compared_pattern_count=0,
        )



# ----------------------------------------------------------------------
# PatternComparator
# ----------------------------------------------------------------------

def test_identical_behavior_gets_full_dimension_similarity():
    candidate = make_pattern(
        operational={
            "create": 3,
            "modify": 2,
        },
        temporal={
            "hour": 10,
        },
        sequential=[
            {"operation": "create"},
            {"operation": "modify"},
        ],
    )

    historical = make_pattern(
        pattern_id="pattern-001",
        operational={
            "create": 3,
            "modify": 2,
        },
        temporal={
            "hour": 10,
        },
        sequential=[
            {"operation": "create"},
            {"operation": "modify"},
        ],
    )

    comparator = PatternComparator()

    scores = comparator.compare(
        candidate,
        historical,
    )

    assert scores["operational"] == 1.0
    assert scores["temporal"] == 1.0
    assert scores["sequential"] == 1.0


def test_missing_behavioral_information_is_not_treated_as_zero():
    candidate = make_pattern()

    historical = make_pattern(
        pattern_id="pattern-001",
        operational={
            "create": 5,
        },
    )

    comparator = PatternComparator()

    scores = comparator.compare(
        candidate,
        historical,
    )

    assert scores["operational"] is None
    assert scores["temporal"] is None
    assert scores["sequential"] is None


def test_different_string_values_produce_partial_or_zero_similarity():
    comparator = PatternComparator()

    score = comparator.compare_dimension(
        "create file",
        "create document",
    )

    assert 0.0 <= score <= 1.0
    assert score < 1.0


# ----------------------------------------------------------------------
# SimilarityCalculator
# ----------------------------------------------------------------------

def test_calculator_returns_weighted_average_of_available_dimensions():
    calculator = SimilarityCalculator()

    score = calculator.calculate(
        {
            "operational": 1.0,
            "temporal": 0.5,
            "sequential": None,
            "contextual": 0.5,
            "relationship": None,
            "session": 1.0,
        }
    )

    expected = (
        1.0 + 0.5 + 0.5 + 1.0
    ) / 4.0

    assert score == pytest.approx(expected)


def test_calculator_returns_none_when_no_dimension_is_available():
    calculator = SimilarityCalculator()

    score = calculator.calculate(
        {
            "operational": None,
            "temporal": None,
            "sequential": None,
            "contextual": None,
            "relationship": None,
            "session": None,
        }
    )

    assert score is None


def test_custom_weights_are_applied():
    calculator = SimilarityCalculator(
        SimilarityWeights(
            operational=2.0,
            temporal=1.0,
            sequential=0.0,
            contextual=0.0,
            relationship=0.0,
            session=0.0,
        )
    )

    score = calculator.calculate(
        {
            "operational": 1.0,
            "temporal": 0.0,
        }
    )

    assert score == pytest.approx(
        2.0 / 3.0
    )




# ----------------------------------------------------------------------
# SimilarityEngine
# ----------------------------------------------------------------------

def test_engine_returns_cold_start_when_repository_has_no_history():
    candidate = make_pattern(
        session_id="session-001",
        user_id="user-001",
        operational={
            "create": 1,
        },
    )

    repository = FakeRepository()

    engine = SimilarityEngine(repository)

    result = engine.evaluate(candidate)

    assert result.status == SimilarityStatus.COLD_START
    assert result.score is None
    assert result.compared_pattern_count == 0


def test_engine_compares_only_same_user_patterns():
    candidate = make_pattern(
        session_id="session-current",
        user_id="user-001",
        operational={
            "create": 2,
        },
    )

    matching_user = make_pattern(
        session_id="old-session-a",
        user_id="user-001",
        pattern_id="pattern-a",
        operational={
            "create": 2,
        },
    )

    different_user = make_pattern(
        session_id="old-session-b",
        user_id="user-002",
        pattern_id="pattern-b",
        operational={
            "create": 2,
        },
    )

    repository = FakeRepository(
        [
            matching_user,
            different_user,
        ]
    )

    engine = SimilarityEngine(repository)

    result = engine.evaluate(candidate)

    assert result.status == SimilarityStatus.SUCCESS
    assert result.best_match_pattern_id == "pattern-a"
    assert result.compared_pattern_count == 1


def test_engine_selects_highest_similarity_match():
    candidate = make_pattern(
        session_id="session-current",
        user_id="user-001",
        operational={
            "create": 5,
            "modify": 2,
        },
    )

    weaker_match = make_pattern(
        session_id="old-session-a",
        user_id="user-001",
        pattern_id="pattern-a",
        operational={
            "create": 1,
        },
    )

    stronger_match = make_pattern(
        session_id="old-session-b",
        user_id="user-001",
        pattern_id="pattern-b",
        operational={
            "create": 5,
            "modify": 2,
        },
    )

    repository = FakeRepository(
        [
            weaker_match,
            stronger_match,
        ]
    )

    engine = SimilarityEngine(repository)

    result = engine.evaluate(candidate)

    assert result.status == SimilarityStatus.SUCCESS
    assert result.best_match_pattern_id == "pattern-b"
    assert result.score == 1.0


def test_engine_returns_insufficient_data_when_history_exists_but_behavior_is_unavailable():
    candidate = make_pattern(
        session_id="session-current",
        user_id="user-001",
    )

    historical = make_pattern(
        session_id="old-session",
        user_id="user-001",
        pattern_id="pattern-a",
    )

    repository = FakeRepository(
        [historical]
    )

    engine = SimilarityEngine(repository)

    result = engine.evaluate(candidate)

    assert result.status == SimilarityStatus.INSUFFICIENT_DATA
    assert result.score is None
    assert result.compared_pattern_count == 1



# ----------------------------------------------------------------------
# Edge Cases
# ----------------------------------------------------------------------

def test_empty_candidate_is_handled_without_comparison():
    repository = FakeRepository(
        [
            make_pattern(
                user_id="user-001",
                pattern_id="pattern-001",
                operational={"create": 1},
            )
        ]
    )

    engine = SimilarityEngine(repository)

    result = engine.evaluate(None)

    assert result.status == SimilarityStatus.INSUFFICIENT_DATA
    assert result.score is None
    assert result.candidate_pattern_id is None
    assert result.compared_pattern_count == 0


def test_minimal_candidate_uses_only_available_dimensions():
    candidate = make_pattern(
        session_id="session-minimal",
        user_id="user-001",
        operational={
            "create": 2,
        },
    )

    historical = make_pattern(
        session_id="old-session",
        user_id="user-001",
        pattern_id="pattern-001",
        operational={
            "create": 2,
        },
        temporal={
            "hour": 10,
        },
    )

    engine = SimilarityEngine(
        FakeRepository([historical])
    )

    result = engine.evaluate(candidate)

    assert result.status == SimilarityStatus.SUCCESS
    assert result.score == 1.0

    assert "operational" in (
        result.comparison_summary["dimensions_used"]
    )

    assert "temporal" in (
        result.comparison_summary["dimensions_unavailable"]
    )


def test_duplicate_historical_patterns_do_not_break_evaluation():
    candidate = make_pattern(
        session_id="session-current",
        user_id="user-001",
        operational={
            "create": 3,
        },
    )

    historical_a = make_pattern(
        session_id="old-session-a",
        user_id="user-001",
        pattern_id="pattern-a",
        operational={
            "create": 3,
        },
    )

    historical_b = make_pattern(
        session_id="old-session-b",
        user_id="user-001",
        pattern_id="pattern-b",
        operational={
            "create": 3,
        },
    )

    engine = SimilarityEngine(
        FakeRepository(
            [
                historical_a,
                historical_b,
            ]
        )
    )

    result = engine.evaluate(candidate)

    assert result.status == SimilarityStatus.SUCCESS
    assert result.score == 1.0
    assert result.compared_pattern_count == 2

    assert result.best_match_pattern_id in {
        "pattern-a",
        "pattern-b",
    }



# ----------------------------------------------------------------------
# Failure Handling
# ----------------------------------------------------------------------

class FailingRepository:
    def get_all(self):
        raise RuntimeError(
            "repository retrieval failed"
        )


def test_repository_failure_returns_failed_status():
    candidate = make_pattern(
        session_id="session-failure",
        user_id="user-001",
        operational={
            "create": 1,
        },
    )

    engine = SimilarityEngine(
        FailingRepository()
    )

    result = engine.evaluate(candidate)

    assert result.status == SimilarityStatus.FAILED
    assert result.score is None
    assert result.best_match_pattern_id is None
    assert result.comparison_summary["reason"] == (
        "comparison_failure"
    )


class FailingComparator:
    def compare(
        self,
        candidate_pattern,
        historical_pattern,
    ):
        raise RuntimeError(
            "comparison failed"
        )


def test_comparator_failure_returns_failed_status():
    candidate = make_pattern(
        session_id="session-comparator-failure",
        user_id="user-001",
        operational={
            "create": 1,
        },
    )

    historical = make_pattern(
        session_id="old-session",
        user_id="user-001",
        pattern_id="pattern-001",
        operational={
            "create": 1,
        },
    )

    engine = SimilarityEngine(
        FakeRepository([historical]),
        comparator=FailingComparator(),
    )

    result = engine.evaluate(candidate)

    assert result.status == SimilarityStatus.FAILED
    assert result.score is None
    assert result.comparison_summary["reason"] == (
        "comparison_failure"
    )



# ----------------------------------------------------------------------
# Read-only / Preservation Contract
# ----------------------------------------------------------------------

def test_candidate_pattern_is_not_modified():
    candidate = make_pattern(
        session_id="session-immutability",
        user_id="user-001",
        operational={
            "create": 3,
        },
    )

    original_operational = dict(
        candidate.operational_characteristics
    )

    historical = make_pattern(
        session_id="old-session",
        user_id="user-001",
        pattern_id="pattern-001",
        operational={
            "create": 3,
        },
    )

    engine = SimilarityEngine(
        FakeRepository([historical])
    )

    result = engine.evaluate(candidate)

    assert result.status == SimilarityStatus.SUCCESS
    assert (
        candidate.operational_characteristics
        == original_operational
    )


def test_historical_pattern_is_not_modified():
    candidate = make_pattern(
        session_id="session-history-readonly",
        user_id="user-001",
        operational={
            "create": 3,
        },
    )

    historical = make_pattern(
        session_id="old-session",
        user_id="user-001",
        pattern_id="pattern-001",
        operational={
            "create": 3,
        },
    )

    original_operational = dict(
        historical.operational_characteristics
    )

    engine = SimilarityEngine(
        FakeRepository([historical])
    )

    result = engine.evaluate(candidate)

    assert result.status == SimilarityStatus.SUCCESS
    assert (
        historical.operational_characteristics
        == original_operational
    )


def test_engine_does_not_store_historical_state_between_evaluations():
    first_candidate = make_pattern(
        session_id="session-one",
        user_id="user-001",
        operational={
            "create": 5,
        },
    )

    second_candidate = make_pattern(
        session_id="session-two",
        user_id="user-001",
        operational={
            "modify": 5,
        },
    )

    historical = make_pattern(
        session_id="old-session",
        user_id="user-001",
        pattern_id="pattern-001",
        operational={
            "create": 5,
        },
    )

    repository = FakeRepository(
        [historical]
    )

    engine = SimilarityEngine(repository)

    first_result = engine.evaluate(
        first_candidate
    )

    second_result = engine.evaluate(
        second_candidate
    )

    assert first_result.score == 1.0
    assert second_result.score is not None

    assert first_result.candidate_pattern_id == (
        "session-one"
    )

    assert second_result.candidate_pattern_id == (
        "session-two"
    )


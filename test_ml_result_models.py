import pytest

from ml_result_models import ModelEvaluation, ModelScore


def test_model_score_stores_model_name_and_score():
    result = ModelScore(
        model_name="IsolationForest",
        score=0.73,
    )

    assert result.model_name == "IsolationForest"
    assert result.score == 0.73


def test_model_evaluation_stores_identity():
    evaluation = ModelEvaluation(
        pattern_id="pattern-1",
        knowledge_id="knowledge-pattern-1",
        model_scores=(
            ModelScore(
                model_name="IsolationForest",
                score=0.73,
            ),
        ),
    )

    assert evaluation.pattern_id == "pattern-1"
    assert evaluation.knowledge_id == "knowledge-pattern-1"


def test_model_evaluation_counts_models():
    evaluation = ModelEvaluation(
        pattern_id="pattern-1",
        knowledge_id="knowledge-pattern-1",
        model_scores=(
            ModelScore(
                model_name="IsolationForest",
                score=0.73,
            ),
            ModelScore(
                model_name="LocalOutlierFactor",
                score=0.61,
            ),
        ),
    )

    assert evaluation.model_count() == 2


def test_model_score_is_immutable():
    result = ModelScore(
        model_name="IsolationForest",
        score=0.73,
    )

    with pytest.raises(AttributeError):
        result.score = 0.9


def test_model_evaluation_is_immutable():
    evaluation = ModelEvaluation(
        pattern_id="pattern-1",
        knowledge_id="knowledge-pattern-1",
        model_scores=(),
    )

    with pytest.raises(AttributeError):
        evaluation.pattern_id = "changed"

from ml_inference_results import (
    InferenceResult,
    ModelFailure,
)
from ml_result_models import (
    ModelEvaluation,
    ModelScore,
)


def test_model_failure_stores_failure_metadata():
    failure = ModelFailure(
        model_name="OneClassSVM",
        error_type="ValueError",
        error_message="Invalid prediction",
    )

    assert failure.model_name == "OneClassSVM"
    assert failure.error_type == "ValueError"
    assert failure.error_message == "Invalid prediction"


def test_inference_result_separates_success_and_failure():
    evaluation = ModelEvaluation(
        pattern_id="pattern-1",
        knowledge_id="knowledge-pattern-1",
        model_scores=(
            ModelScore(
                model_name="IsolationForest",
                score=-0.2,
            ),
            ModelScore(
                model_name="LocalOutlierFactor",
                score=-1.3,
            ),
        ),
    )

    result = InferenceResult(
        evaluation=evaluation,
        failures=(
            ModelFailure(
                model_name="OneClassSVM",
                error_type="RuntimeError",
                error_message="model unavailable",
            ),
        ),
    )

    assert result.successful_model_count() == 2
    assert result.failed_model_count() == 1

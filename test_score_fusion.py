import pytest

from score_fusion import WeightedScoreFusion
from score_calibration import CalibratedModelScore


def calibrated(
    model_name: str,
    score: float,
) -> CalibratedModelScore:
    return CalibratedModelScore(
        model_name=model_name,
        raw_score=score,
        canonical_score=score,
        calibrated_score=score,
    )


def test_weighted_fusion_combines_scores():
    fusion = WeightedScoreFusion(
        {
            "IsolationForest": 0.5,
            "LocalOutlierFactor": 0.5,
        }
    )

    result = fusion.combine(
        (
            calibrated(
                "IsolationForest",
                0.8,
            ),
            calibrated(
                "LocalOutlierFactor",
                0.4,
            ),
        )
    )

    assert result == pytest.approx(0.6)


def test_weighted_fusion_uses_relative_weights():
    fusion = WeightedScoreFusion(
        {
            "IsolationForest": 3.0,
            "LocalOutlierFactor": 1.0,
        }
    )

    result = fusion.combine(
        (
            calibrated(
                "IsolationForest",
                1.0,
            ),
            calibrated(
                "LocalOutlierFactor",
                0.0,
            ),
        )
    )

    assert result == 0.75


def test_weights_do_not_need_to_sum_to_one():
    fusion = WeightedScoreFusion(
        {
            "IsolationForest": 35.0,
            "LocalOutlierFactor": 25.0,
        }
    )

    result = fusion.combine(
        (
            calibrated(
                "IsolationForest",
                1.0,
            ),
            calibrated(
                "LocalOutlierFactor",
                0.0,
            ),
        )
    )

    assert result == 35.0 / 60.0


def test_partial_model_set_can_be_fused():
    fusion = WeightedScoreFusion(
        {
            "IsolationForest": 0.5,
            "LocalOutlierFactor": 0.25,
            "OneClassSVM": 0.25,
        }
    )

    result = fusion.combine(
        (
            calibrated(
                "IsolationForest",
                0.8,
            ),
            calibrated(
                "LocalOutlierFactor",
                0.4,
            ),
        )
    )

    expected = (
        (0.8 * 0.5) +
        (0.4 * 0.25)
    ) / (
        0.5 + 0.25
    )

    assert result == expected


def test_unconfigured_model_is_rejected():
    fusion = WeightedScoreFusion(
        {
            "IsolationForest": 1.0,
        }
    )

    with pytest.raises(ValueError):
        fusion.combine(
            (
                calibrated(
                    "LocalOutlierFactor",
                    0.5,
                ),
            )
        )


def test_duplicate_model_score_is_rejected():
    fusion = WeightedScoreFusion(
        {
            "IsolationForest": 1.0,
        }
    )

    score = calibrated(
        "IsolationForest",
        0.5,
    )

    with pytest.raises(ValueError):
        fusion.combine(
            (
                score,
                score,
            )
        )


def test_empty_score_collection_is_rejected():
    fusion = WeightedScoreFusion(
        {
            "IsolationForest": 1.0,
        }
    )

    with pytest.raises(ValueError):
        fusion.combine(())


def test_invalid_score_type_is_rejected():
    fusion = WeightedScoreFusion(
        {
            "IsolationForest": 1.0,
        }
    )

    with pytest.raises(TypeError):
        fusion.combine(
            (
                "invalid",
            )
        )


@pytest.mark.parametrize(
    "weights",
    [
        {},
        {"IsolationForest": 0},
        {"IsolationForest": -1},
        {"IsolationForest": float("nan")},
        {"IsolationForest": float("inf")},
        {"IsolationForest": "invalid"},
        {"": 1.0},
    ],
)
def test_invalid_weights_are_rejected(weights):
    with pytest.raises((TypeError, ValueError)):
        WeightedScoreFusion(weights)


def test_configured_models_are_reported_in_order():
    fusion = WeightedScoreFusion(
        {
            "IsolationForest": 0.5,
            "LocalOutlierFactor": 0.3,
            "OneClassSVM": 0.2,
        }
    )

    assert fusion.configured_models() == (
        "IsolationForest",
        "LocalOutlierFactor",
        "OneClassSVM",
    )


def test_fusion_does_not_invent_weights():
    fusion = WeightedScoreFusion(
        {
            "IsolationForest": 1.0,
            "LocalOutlierFactor": 1.0,
        }
    )

    result = fusion.combine(
        (
            calibrated(
                "IsolationForest",
                0.8,
            ),
            calibrated(
                "LocalOutlierFactor",
                0.2,
            ),
        )
    )

    assert result == 0.5

import pytest

from feature_validator import FeatureValidator


def test_valid_feature_representation_is_accepted():
    FeatureValidator.validate(
        pattern_id="pattern-1",
        knowledge_id="knowledge-1",
        features={
            "operation.modify_ratio": 0.8,
            "intelligence.confidence": 0.9,
        },
        feature_names=(
            "operation.modify_ratio",
            "intelligence.confidence",
        ),
    )


def test_missing_feature_is_rejected():
    with pytest.raises(
        ValueError,
        match="Feature representation is incomplete",
    ):
        FeatureValidator.validate(
            pattern_id="pattern-1",
            knowledge_id="knowledge-1",
            features={
                "operation.modify_ratio": 0.8,
            },
            feature_names=(
                "operation.modify_ratio",
                "intelligence.confidence",
            ),
        )


def test_undeclared_feature_is_rejected():
    with pytest.raises(
        ValueError,
        match="undeclared features",
    ):
        FeatureValidator.validate(
            pattern_id="pattern-1",
            knowledge_id="knowledge-1",
            features={
                "operation.modify_ratio": 0.8,
                "extra.feature": 0.5,
            },
            feature_names=(
                "operation.modify_ratio",
            ),
        )


def test_duplicate_feature_names_are_rejected():
    with pytest.raises(
        ValueError,
        match="Feature names must be unique",
    ):
        FeatureValidator.validate(
            pattern_id="pattern-1",
            knowledge_id="knowledge-1",
            features={
                "operation.modify_ratio": 0.8,
            },
            feature_names=(
                "operation.modify_ratio",
                "operation.modify_ratio",
            ),
        )


def test_non_numeric_feature_is_rejected():
    with pytest.raises(
        ValueError,
        match="must be numerical",
    ):
        FeatureValidator.validate(
            pattern_id="pattern-1",
            knowledge_id="knowledge-1",
            features={
                "operation.modify_ratio": "invalid",
            },
            feature_names=(
                "operation.modify_ratio",
            ),
        )


def test_nan_feature_is_rejected():
    with pytest.raises(
        ValueError,
        match="finite value",
    ):
        FeatureValidator.validate(
            pattern_id="pattern-1",
            knowledge_id="knowledge-1",
            features={
                "operation.modify_ratio": float("nan"),
            },
            feature_names=(
                "operation.modify_ratio",
            ),
        )


def test_infinite_feature_is_rejected():
    with pytest.raises(
        ValueError,
        match="finite value",
    ):
        FeatureValidator.validate(
            pattern_id="pattern-1",
            knowledge_id="knowledge-1",
            features={
                "operation.modify_ratio": float("inf"),
            },
            feature_names=(
                "operation.modify_ratio",
            ),
        )


def test_empty_pattern_id_is_rejected():
    with pytest.raises(
        ValueError,
        match="pattern_id must be a non-empty string",
    ):
        FeatureValidator.validate(
            pattern_id="",
            knowledge_id="knowledge-1",
            features={
                "feature_a": 0.5,
            },
            feature_names=(
                "feature_a",
            ),
        )


def test_empty_knowledge_id_is_rejected():
    with pytest.raises(
        ValueError,
        match="knowledge_id must be a non-empty string",
    ):
        FeatureValidator.validate(
            pattern_id="pattern-1",
            knowledge_id="",
            features={
                "feature_a": 0.5,
            },
            feature_names=(
                "feature_a",
            ),
        )

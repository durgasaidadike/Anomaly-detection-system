import pytest

from normalization_engine import NormalizationEngine


def test_normalization_engine_applies_supplied_rules():
    engine = NormalizationEngine()

    features = {
        "feature_a": 10.0,
        "feature_b": 20.0,
    }

    normalizers = {
        "feature_a": lambda value: value / 10.0,
        "feature_b": lambda value: value / 20.0,
    }

    normalized = engine.normalize_features(
        features,
        normalizers,
    )

    assert normalized == {
        "feature_a": 1.0,
        "feature_b": 1.0,
    }


def test_normalization_engine_preserves_feature_names():
    engine = NormalizationEngine()

    features = {
        "operation.modify_ratio": 0.8,
        "intelligence.confidence": 0.9,
    }

    normalizers = {
        "operation.modify_ratio": lambda value: value,
        "intelligence.confidence": lambda value: value,
    }

    normalized = engine.normalize_features(
        features,
        normalizers,
    )

    assert tuple(normalized.keys()) == (
        "operation.modify_ratio",
        "intelligence.confidence",
    )


def test_normalization_engine_does_not_modify_source_mapping():
    engine = NormalizationEngine()

    features = {
        "feature_a": 10.0,
        "feature_b": 20.0,
    }

    original = dict(features)

    normalizers = {
        "feature_a": lambda value: value / 10.0,
        "feature_b": lambda value: value / 20.0,
    }

    engine.normalize_features(
        features,
        normalizers,
    )

    assert features == original


def test_missing_normalization_rule_is_rejected():
    engine = NormalizationEngine()

    with pytest.raises(
        ValueError,
        match="No normalization rule supplied",
    ):
        engine.normalize_features(
            {
                "feature_a": 10.0,
            },
            {},
        )


def test_non_numeric_feature_is_rejected():
    engine = NormalizationEngine()

    with pytest.raises(
        ValueError,
        match="must have a numerical value",
    ):
        engine.normalize_features(
            {
                "feature_a": "invalid",
            },
            {
                "feature_a": lambda value: value,
            },
        )


def test_non_finite_input_is_rejected():
    engine = NormalizationEngine()

    with pytest.raises(
        ValueError,
        match="non-finite value",
    ):
        engine.normalize_features(
            {
                "feature_a": float("nan"),
            },
            {
                "feature_a": lambda value: value,
            },
        )


def test_non_finite_normalized_output_is_rejected():
    engine = NormalizationEngine()

    with pytest.raises(
        ValueError,
        match="returned a non-finite value",
    ):
        engine.normalize_features(
            {
                "feature_a": 10.0,
            },
            {
                "feature_a": lambda value: float("inf"),
            },
        )


def test_normalization_engine_is_deterministic():
    engine = NormalizationEngine()

    features = {
        "feature_a": 10.0,
        "feature_b": 20.0,
    }

    normalizers = {
        "feature_a": lambda value: value / 10.0,
        "feature_b": lambda value: value / 20.0,
    }

    first = engine.normalize_features(
        features,
        normalizers,
    )

    second = engine.normalize_features(
        features,
        normalizers,
    )

    assert first == second

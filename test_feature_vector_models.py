from feature_vector_models import FeatureVector


def test_feature_vector_preserves_feature_order():
    vector = FeatureVector(
        pattern_id="pattern-1",
        knowledge_id="knowledge-pattern-1",
        features={
            "delete_ratio": 0.2,
            "modify_ratio": 0.8,
            "rename_ratio": 0.1,
        },
        feature_names=(
            "modify_ratio",
            "rename_ratio",
            "delete_ratio",
        ),
    )

    assert vector.as_vector() == (
        0.8,
        0.1,
        0.2,
    )


def test_feature_vector_dimension():
    vector = FeatureVector(
        pattern_id="pattern-1",
        knowledge_id="knowledge-pattern-1",
        features={
            "modify_ratio": 0.8,
            "delete_ratio": 0.2,
        },
        feature_names=(
            "modify_ratio",
            "delete_ratio",
        ),
    )

    assert vector.dimension() == 2


def test_feature_vector_reports_complete_vector():
    vector = FeatureVector(
        pattern_id="pattern-1",
        knowledge_id="knowledge-pattern-1",
        features={
            "modify_ratio": 0.8,
            "delete_ratio": 0.2,
        },
        feature_names=(
            "modify_ratio",
            "delete_ratio",
        ),
    )

    assert vector.is_complete() is True


def test_feature_vector_reports_incomplete_vector():
    vector = FeatureVector(
        pattern_id="pattern-1",
        knowledge_id="knowledge-pattern-1",
        features={
            "modify_ratio": 0.8,
        },
        feature_names=(
            "modify_ratio",
            "delete_ratio",
        ),
    )

    assert vector.is_complete() is False


def test_feature_vector_is_immutable():
    vector = FeatureVector(
        pattern_id="pattern-1",
        knowledge_id="knowledge-pattern-1",
        features={
            "modify_ratio": 0.8,
        },
        feature_names=(
            "modify_ratio",
        ),
    )

    try:
        vector.pattern_id = "changed"
    except AttributeError:
        pass
    else:
        raise AssertionError(
            "FeatureVector should be immutable"
        )


def test_feature_vector_handles_zero_dimension():
    vector = FeatureVector(
        pattern_id="pattern-1",
        knowledge_id="knowledge-pattern-1",
        features={},
        feature_names=(),
    )

    assert vector.dimension() == 0
    assert vector.as_vector() == ()

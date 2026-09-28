import pytest

from feature_extractor import FeatureExtractor
from feature_vector_models import FeatureVector


def test_build_feature_vector_creates_one_vector_for_one_pattern():
    extractor = FeatureExtractor()

    vector = extractor.build_feature_vector(
        pattern_id="pattern-1",
        knowledge_id="knowledge-pattern-1",
        features={
            "feature_a": 0.8,
            "feature_b": 0.2,
        },
        feature_names=(
            "feature_a",
            "feature_b",
        ),
    )

    assert isinstance(vector, FeatureVector)
    assert vector.pattern_id == "pattern-1"
    assert vector.knowledge_id == "knowledge-pattern-1"


def test_build_feature_vector_preserves_feature_order():
    extractor = FeatureExtractor()

    vector = extractor.build_feature_vector(
        pattern_id="pattern-1",
        knowledge_id="knowledge-pattern-1",
        features={
            "feature_b": 0.2,
            "feature_a": 0.8,
        },
        feature_names=(
            "feature_a",
            "feature_b",
        ),
    )

    assert vector.as_vector() == (
        0.8,
        0.2,
    )


def test_build_feature_vector_accepts_mapping_input():
    extractor = FeatureExtractor()

    source_features = {
        "feature_a": 0.75,
        "feature_b": 0.25,
    }

    vector = extractor.build_feature_vector(
        pattern_id="pattern-1",
        knowledge_id="knowledge-pattern-1",
        features=source_features,
        feature_names=(
            "feature_a",
            "feature_b",
        ),
    )

    assert vector.features == source_features


def test_incomplete_feature_vector_is_rejected():
    extractor = FeatureExtractor()

    with pytest.raises(
        ValueError,
        match="Feature representation is incomplete",
    ):
        extractor.build_feature_vector(
            pattern_id="pattern-1",
            knowledge_id="knowledge-pattern-1",
            features={
                "feature_a": 0.8,
            },
            feature_names=(
                "feature_a",
                "feature_b",
            ),
        )


def test_feature_extractor_does_not_modify_source_mapping():
    extractor = FeatureExtractor()

    source_features = {
        "feature_a": 0.8,
        "feature_b": 0.2,
    }

    original = dict(source_features)

    extractor.build_feature_vector(
        pattern_id="pattern-1",
        knowledge_id="knowledge-pattern-1",
        features=source_features,
        feature_names=(
            "feature_a",
            "feature_b",
        ),
    )

    assert source_features == original


def test_feature_extractor_is_stateless():
    extractor = FeatureExtractor()

    first = extractor.build_feature_vector(
        pattern_id="pattern-1",
        knowledge_id="knowledge-pattern-1",
        features={
            "feature_a": 0.8,
        },
        feature_names=(
            "feature_a",
        ),
    )

    second = extractor.build_feature_vector(
        pattern_id="pattern-2",
        knowledge_id="knowledge-pattern-2",
        features={
            "feature_a": 0.3,
        },
        feature_names=(
            "feature_a",
        ),
    )

    assert first.pattern_id == "pattern-1"
    assert second.pattern_id == "pattern-2"
    assert first.as_vector() == (0.8,)
    assert second.as_vector() == (0.3,)


def test_feature_extractor_separates_feature_categories():
    extractor = FeatureExtractor()

    groups = extractor.separate_features(
        operation={"modify_ratio": 0.8},
        temporal={"session_duration": 120.0},
        sequence={"sequence_score": 0.7},
        contextual={"directory_transition": 0.3},
        session={"session_intensity": 0.6},
        intelligence={"confidence": 0.9},
        recurrence={"recurrence": 500.0},
        drift={"drift": 0.2},
    )

    assert groups.operation == {
        "modify_ratio": 0.8
    }

    assert groups.temporal == {
        "session_duration": 120.0
    }

    assert groups.sequence == {
        "sequence_score": 0.7
    }

    assert groups.contextual == {
        "directory_transition": 0.3
    }

    assert groups.session == {
        "session_intensity": 0.6
    }

    assert groups.intelligence == {
        "confidence": 0.9
    }

    assert groups.recurrence == {
        "recurrence": 500.0
    }

    assert groups.drift == {
        "drift": 0.2
    }


def test_feature_extractor_does_not_modify_feature_group_inputs():
    extractor = FeatureExtractor()

    operation = {"modify_ratio": 0.8}
    temporal = {"session_duration": 120.0}

    groups = extractor.separate_features(
        operation=operation,
        temporal=temporal,
        sequence={},
        contextual={},
        session={},
        intelligence={},
        recurrence={},
        drift={},
    )

    assert groups.operation is not operation
    assert groups.temporal is not temporal


def test_feature_extractor_constructs_qualified_feature_names():
    extractor = FeatureExtractor()

    groups = extractor.separate_features(
        operation={
            "modify_ratio": 0.8,
        },
        temporal={
            "session_duration": 120.0,
        },
        sequence={
            "sequence_score": 0.7,
        },
        contextual={
            "directory_transition": 0.3,
        },
        session={
            "session_intensity": 0.6,
        },
        intelligence={
            "confidence": 0.9,
        },
        recurrence={
            "recurrence": 500.0,
        },
        drift={
            "drift": 0.2,
        },
    )

    features, feature_names = extractor.construct_features(groups)

    assert feature_names == (
        "operation.modify_ratio",
        "temporal.session_duration",
        "sequence.sequence_score",
        "contextual.directory_transition",
        "session.session_intensity",
        "intelligence.confidence",
        "recurrence.recurrence",
        "drift.drift",
    )

    assert features == {
        "operation.modify_ratio": 0.8,
        "temporal.session_duration": 120.0,
        "sequence.sequence_score": 0.7,
        "contextual.directory_transition": 0.3,
        "session.session_intensity": 0.6,
        "intelligence.confidence": 0.9,
        "recurrence.recurrence": 500.0,
        "drift.drift": 0.2,
    }


def test_feature_extractor_preserves_group_order():
    extractor = FeatureExtractor()

    groups = extractor.separate_features(
        operation={
            "operation_a": 1.0,
            "operation_b": 2.0,
        },
        temporal={
            "temporal_a": 3.0,
        },
        sequence={
            "sequence_a": 4.0,
        },
        contextual={},
        session={},
        intelligence={},
        recurrence={},
        drift={},
    )

    features, feature_names = extractor.construct_features(groups)

    assert feature_names == (
        "operation.operation_a",
        "operation.operation_b",
        "temporal.temporal_a",
        "sequence.sequence_a",
    )

    assert tuple(features.values()) == (
        1.0,
        2.0,
        3.0,
        4.0,
    )


def test_feature_extractor_constructs_empty_feature_set():
    extractor = FeatureExtractor()

    groups = extractor.separate_features(
        operation={},
        temporal={},
        sequence={},
        contextual={},
        session={},
        intelligence={},
        recurrence={},
        drift={},
    )

    features, feature_names = extractor.construct_features(groups)

    assert features == {}
    assert feature_names == ()


def test_feature_extractor_does_not_modify_feature_groups():
    extractor = FeatureExtractor()

    groups = extractor.separate_features(
        operation={
            "modify_ratio": 0.8,
        },
        temporal={
            "session_duration": 120.0,
        },
        sequence={},
        contextual={},
        session={},
        intelligence={},
        recurrence={},
        drift={},
    )

    original_groups = groups.as_groups()

    extractor.construct_features(groups)

    assert groups.as_groups() == original_groups


def test_feature_extractor_constructs_deterministic_feature_representation():
    extractor = FeatureExtractor()

    groups = extractor.separate_features(
        operation={
            "modify_ratio": 0.8,
            "delete_ratio": 0.2,
        },
        temporal={
            "session_duration": 120.0,
        },
        sequence={
            "sequence_score": 0.7,
        },
        contextual={
            "directory_transition": 0.3,
        },
        session={
            "session_intensity": 0.6,
        },
        intelligence={
            "confidence": 0.9,
        },
        recurrence={
            "recurrence": 500.0,
        },
        drift={
            "drift": 0.2,
        },
    )

    features, feature_names = extractor.construct_features(groups)

    assert feature_names == (
        "operation.modify_ratio",
        "operation.delete_ratio",
        "temporal.session_duration",
        "sequence.sequence_score",
        "contextual.directory_transition",
        "session.session_intensity",
        "intelligence.confidence",
        "recurrence.recurrence",
        "drift.drift",
    )

    assert features == {
        "operation.modify_ratio": 0.8,
        "operation.delete_ratio": 0.2,
        "temporal.session_duration": 120.0,
        "sequence.sequence_score": 0.7,
        "contextual.directory_transition": 0.3,
        "session.session_intensity": 0.6,
        "intelligence.confidence": 0.9,
        "recurrence.recurrence": 500.0,
        "drift.drift": 0.2,
    }


def test_feature_extractor_preserves_feature_group_identity():
    extractor = FeatureExtractor()

    groups = extractor.separate_features(
        operation={
            "score": 0.8,
        },
        temporal={
            "score": 0.4,
        },
        sequence={},
        contextual={},
        session={},
        intelligence={},
        recurrence={},
        drift={},
    )

    features, feature_names = extractor.construct_features(groups)

    assert feature_names == (
        "operation.score",
        "temporal.score",
    )

    assert features == {
        "operation.score": 0.8,
        "temporal.score": 0.4,
    }


def test_feature_extractor_construct_features_is_deterministic():
    extractor = FeatureExtractor()

    groups = extractor.separate_features(
        operation={
            "feature_a": 0.8,
            "feature_b": 0.2,
        },
        temporal={
            "feature_c": 10.0,
        },
        sequence={},
        contextual={},
        session={},
        intelligence={},
        recurrence={},
        drift={},
    )

    first_features, first_names = extractor.construct_features(groups)
    second_features, second_names = extractor.construct_features(groups)

    assert first_features == second_features
    assert first_names == second_names


def test_feature_extractor_construct_features_does_not_modify_groups():
    extractor = FeatureExtractor()

    groups = extractor.separate_features(
        operation={
            "modify_ratio": 0.8,
        },
        temporal={
            "session_duration": 120.0,
        },
        sequence={},
        contextual={},
        session={},
        intelligence={},
        recurrence={},
        drift={},
    )

    before = groups.as_groups()

    extractor.construct_features(groups)

    after = groups.as_groups()

    assert after == before


def test_feature_extractor_constructs_empty_representation():
    extractor = FeatureExtractor()

    groups = extractor.separate_features(
        operation={},
        temporal={},
        sequence={},
        contextual={},
        session={},
        intelligence={},
        recurrence={},
        drift={},
    )

    features, feature_names = extractor.construct_features(groups)

    assert features == {}
    assert feature_names == ()


def test_feature_extractor_delegates_normalization():
    extractor = FeatureExtractor()

    features = {
        "operation.modify_ratio": 80.0,
        "intelligence.confidence": 90.0,
    }

    normalizers = {
        "operation.modify_ratio": lambda value: value / 100.0,
        "intelligence.confidence": lambda value: value / 100.0,
    }

    normalized = extractor.normalize_features(
        features,
        normalizers,
    )

    assert normalized == {
        "operation.modify_ratio": 0.8,
        "intelligence.confidence": 0.9,
    }


def test_feature_extractor_rejects_invalid_numeric_feature():
    extractor = FeatureExtractor()

    with pytest.raises(
        ValueError,
        match="must be numerical",
    ):
        extractor.build_feature_vector(
            pattern_id="pattern-1",
            knowledge_id="knowledge-1",
            features={
                "feature_a": "invalid",
            },
            feature_names=(
                "feature_a",
            ),
        )


def test_feature_extractor_rejects_non_finite_feature():
    extractor = FeatureExtractor()

    with pytest.raises(
        ValueError,
        match="finite value",
    ):
        extractor.build_feature_vector(
            pattern_id="pattern-1",
            knowledge_id="knowledge-1",
            features={
                "feature_a": float("nan"),
            },
            feature_names=(
                "feature_a",
            ),
        )


def test_feature_extractor_rejects_undeclared_feature():
    extractor = FeatureExtractor()

    with pytest.raises(
        ValueError,
        match="undeclared features",
    ):
        extractor.build_feature_vector(
            pattern_id="pattern-1",
            knowledge_id="knowledge-1",
            features={
                "feature_a": 0.8,
                "feature_b": 0.2,
            },
            feature_names=(
                "feature_a",
            ),
        )


def test_build_normalized_feature_vector_integrates_normalization_and_validation():
    extractor = FeatureExtractor()

    vector = extractor.build_normalized_feature_vector(
        pattern_id="pattern-1",
        knowledge_id="knowledge-1",
        features={
            "operation.modify_ratio": 80.0,
            "intelligence.confidence": 90.0,
        },
        feature_names=(
            "operation.modify_ratio",
            "intelligence.confidence",
        ),
        normalizers={
            "operation.modify_ratio": lambda value: value / 100.0,
            "intelligence.confidence": lambda value: value / 100.0,
        },
    )

    assert isinstance(vector, FeatureVector)

    assert vector.pattern_id == "pattern-1"
    assert vector.knowledge_id == "knowledge-1"

    assert vector.feature_names == (
        "operation.modify_ratio",
        "intelligence.confidence",
    )

    assert vector.as_vector() == (
        0.8,
        0.9,
    )


def test_build_normalized_feature_vector_preserves_feature_order():
    extractor = FeatureExtractor()

    vector = extractor.build_normalized_feature_vector(
        pattern_id="pattern-1",
        knowledge_id="knowledge-1",
        features={
            "feature_b": 20.0,
            "feature_a": 10.0,
        },
        feature_names=(
            "feature_a",
            "feature_b",
        ),
        normalizers={
            "feature_a": lambda value: value / 10.0,
            "feature_b": lambda value: value / 20.0,
        },
    )

    assert vector.as_vector() == (
        1.0,
        1.0,
    )


def test_build_normalized_feature_vector_rejects_missing_normalizer():
    extractor = FeatureExtractor()

    with pytest.raises(
        ValueError,
        match="No normalization rule supplied",
    ):
        extractor.build_normalized_feature_vector(
            pattern_id="pattern-1",
            knowledge_id="knowledge-1",
            features={
                "feature_a": 10.0,
                "feature_b": 20.0,
            },
            feature_names=(
                "feature_a",
                "feature_b",
            ),
            normalizers={
                "feature_a": lambda value: value / 10.0,
            },
        )


def test_build_normalized_feature_vector_rejects_invalid_normalized_value():
    extractor = FeatureExtractor()

    with pytest.raises(
        ValueError,
        match="non-finite value",
    ):
        extractor.build_normalized_feature_vector(
            pattern_id="pattern-1",
            knowledge_id="knowledge-1",
            features={
                "feature_a": 10.0,
            },
            feature_names=(
                "feature_a",
            ),
            normalizers={
                "feature_a": lambda value: float("nan"),
            },
        )


def test_build_normalized_feature_vector_does_not_modify_source_features():
    extractor = FeatureExtractor()

    features = {
        "feature_a": 10.0,
        "feature_b": 20.0,
    }

    original = dict(features)

    extractor.build_normalized_feature_vector(
        pattern_id="pattern-1",
        knowledge_id="knowledge-1",
        features=features,
        feature_names=(
            "feature_a",
            "feature_b",
        ),
        normalizers={
            "feature_a": lambda value: value / 10.0,
            "feature_b": lambda value: value / 20.0,
        },
    )

    assert features == original


def test_build_normalized_feature_vector_is_stateless():
    extractor = FeatureExtractor()

    first = extractor.build_normalized_feature_vector(
        pattern_id="pattern-1",
        knowledge_id="knowledge-1",
        features={
            "feature_a": 10.0,
        },
        feature_names=(
            "feature_a",
        ),
        normalizers={
            "feature_a": lambda value: value / 10.0,
        },
    )

    second = extractor.build_normalized_feature_vector(
        pattern_id="pattern-2",
        knowledge_id="knowledge-2",
        features={
            "feature_a": 30.0,
        },
        feature_names=(
            "feature_a",
        ),
        normalizers={
            "feature_a": lambda value: value / 10.0,
        },
    )

    assert first.pattern_id == "pattern-1"
    assert second.pattern_id == "pattern-2"

    assert first.as_vector() == (1.0,)
    assert second.as_vector() == (3.0,)


def test_feature_extractor_builds_one_matrix_row_per_vector():
    extractor = FeatureExtractor()

    vector_one = FeatureVector(
        pattern_id="pattern-1",
        knowledge_id="knowledge-1",
        features={
            "feature_a": 0.8,
            "feature_b": 0.2,
        },
        feature_names=(
            "feature_a",
            "feature_b",
        ),
    )

    vector_two = FeatureVector(
        pattern_id="pattern-2",
        knowledge_id="knowledge-2",
        features={
            "feature_a": 0.4,
            "feature_b": 0.6,
        },
        feature_names=(
            "feature_a",
            "feature_b",
        ),
    )

    matrix = extractor.build_feature_matrix(
        (
            vector_one,
            vector_two,
        )
    )

    assert matrix.feature_names == (
        "feature_a",
        "feature_b",
    )

    assert matrix.rows == (
        (0.8, 0.2),
        (0.4, 0.6),
    )

    assert matrix.pattern_ids == (
        "pattern-1",
        "pattern-2",
    )

    assert matrix.knowledge_ids == (
        "knowledge-1",
        "knowledge-2",
    )


def test_feature_extractor_rejects_inconsistent_feature_columns():
    extractor = FeatureExtractor()

    vector_one = FeatureVector(
        pattern_id="pattern-1",
        knowledge_id="knowledge-1",
        features={
            "feature_a": 0.8,
            "feature_b": 0.2,
        },
        feature_names=(
            "feature_a",
            "feature_b",
        ),
    )

    vector_two = FeatureVector(
        pattern_id="pattern-2",
        knowledge_id="knowledge-2",
        features={
            "feature_a": 0.4,
            "feature_c": 0.6,
        },
        feature_names=(
            "feature_a",
            "feature_c",
        ),
    )

    with pytest.raises(
        ValueError,
        match="same feature-name ordering",
    ):
        extractor.build_feature_matrix(
            (
                vector_one,
                vector_two,
            )
        )


def test_feature_extractor_builds_empty_feature_matrix():
    extractor = FeatureExtractor()

    matrix = extractor.build_feature_matrix(())

    assert matrix.feature_names == ()
    assert matrix.rows == ()
    assert matrix.pattern_ids == ()
    assert matrix.knowledge_ids == ()


def test_feature_extractor_preserves_vector_order_in_matrix():
    extractor = FeatureExtractor()

    vector_one = FeatureVector(
        pattern_id="pattern-1",
        knowledge_id="knowledge-1",
        features={
            "feature_a": 0.1,
        },
        feature_names=("feature_a",),
    )

    vector_two = FeatureVector(
        pattern_id="pattern-2",
        knowledge_id="knowledge-2",
        features={
            "feature_a": 0.9,
        },
        feature_names=("feature_a",),
    )

    matrix = extractor.build_feature_matrix(
        (
            vector_two,
            vector_one,
        )
    )

    assert matrix.rows == (
        (0.9,),
        (0.1,),
    )

    assert matrix.pattern_ids == (
        "pattern-2",
        "pattern-1",
    )

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

    with pytest.raises(ValueError, match="Incomplete feature vector"):
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

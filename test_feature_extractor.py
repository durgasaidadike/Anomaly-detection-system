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

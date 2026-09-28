from __future__ import annotations

import pytest

from feature_extractor import FeatureExtractor
from feature_vector_models import FeatureVector


class RecordingFeatureSink:
    """
    Test double representing the downstream ML boundary.
    """

    def __init__(self) -> None:
        self.received: list[FeatureVector] = []

    def accept_feature_vector(
        self,
        vector: FeatureVector,
    ) -> None:
        self.received.append(vector)


def test_full_feature_extractor_pipeline():
    extractor = FeatureExtractor()

    # ---------------------------------------------------------
    # 1. Feature separation
    # ---------------------------------------------------------

    groups = extractor.separate_features(
        operation={
            "modify_ratio": 80.0,
            "delete_ratio": 20.0,
        },
        temporal={
            "session_duration": 120.0,
        },
        sequence={
            "sequence_score": 70.0,
        },
        contextual={
            "directory_transition": 30.0,
        },
        session={
            "session_intensity": 60.0,
        },
        intelligence={
            "confidence": 90.0,
        },
        recurrence={
            "recurrence": 500.0,
        },
        drift={
            "drift": 20.0,
        },
    )

    # ---------------------------------------------------------
    # 2. Feature construction
    # ---------------------------------------------------------

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

    # ---------------------------------------------------------
    # 3. Normalization
    # ---------------------------------------------------------

    normalizers = {
        "operation.modify_ratio": lambda value: value / 100.0,
        "operation.delete_ratio": lambda value: value / 100.0,
        "temporal.session_duration": lambda value: value / 120.0,
        "sequence.sequence_score": lambda value: value / 100.0,
        "contextual.directory_transition": lambda value: value / 100.0,
        "session.session_intensity": lambda value: value / 100.0,
        "intelligence.confidence": lambda value: value / 100.0,
        "recurrence.recurrence": lambda value: value / 500.0,
        "drift.drift": lambda value: value / 100.0,
    }

    normalized = extractor.normalize_features(
        features,
        normalizers,
    )

    assert normalized == {
        "operation.modify_ratio": 0.8,
        "operation.delete_ratio": 0.2,
        "temporal.session_duration": 1.0,
        "sequence.sequence_score": 0.7,
        "contextual.directory_transition": 0.3,
        "session.session_intensity": 0.6,
        "intelligence.confidence": 0.9,
        "recurrence.recurrence": 1.0,
        "drift.drift": 0.2,
    }

    # ---------------------------------------------------------
    # 4. Feature vector formation + validation
    # ---------------------------------------------------------

    vector = extractor.build_feature_vector(
        pattern_id="pattern-1",
        knowledge_id="knowledge-1",
        features=normalized,
        feature_names=feature_names,
    )

    assert vector.pattern_id == "pattern-1"
    assert vector.knowledge_id == "knowledge-1"
    assert vector.is_complete() is True

    assert vector.as_vector() == (
        0.8,
        0.2,
        1.0,
        0.7,
        0.3,
        0.6,
        0.9,
        1.0,
        0.2,
    )

    # ---------------------------------------------------------
    # 5. Matrix formation
    # ---------------------------------------------------------

    matrix = extractor.build_feature_matrix(
        (vector,)
    )

    assert matrix.row_count() == 1
    assert matrix.column_count() == 9

    assert matrix.rows == (
        vector.as_vector(),
    )

    assert matrix.pattern_ids == (
        "pattern-1",
    )

    assert matrix.knowledge_ids == (
        "knowledge-1",
    )

    # ---------------------------------------------------------
    # 6. ML delivery boundary
    # ---------------------------------------------------------

    sink = RecordingFeatureSink()

    extractor.deliver_feature_vector(
        vector,
        sink,
    )

    assert sink.received == [vector]
    assert sink.received[0] is vector


def test_multiple_patterns_produce_consistent_matrix():
    extractor = FeatureExtractor()

    feature_names = (
        "operation.modify_ratio",
        "intelligence.confidence",
    )

    vector_one = FeatureVector(
        pattern_id="pattern-1",
        knowledge_id="knowledge-1",
        features={
            "operation.modify_ratio": 0.8,
            "intelligence.confidence": 0.9,
        },
        feature_names=feature_names,
    )

    vector_two = FeatureVector(
        pattern_id="pattern-2",
        knowledge_id="knowledge-2",
        features={
            "operation.modify_ratio": 0.4,
            "intelligence.confidence": 0.6,
        },
        feature_names=feature_names,
    )

    matrix = extractor.build_feature_matrix(
        (
            vector_one,
            vector_two,
        )
    )

    assert matrix.feature_names == feature_names

    assert matrix.rows == (
        (0.8, 0.9),
        (0.4, 0.6),
    )

    assert matrix.pattern_ids == (
        "pattern-1",
        "pattern-2",
    )


def test_pipeline_preserves_one_pattern_one_vector():
    extractor = FeatureExtractor()

    vector_one = FeatureVector(
        pattern_id="pattern-1",
        knowledge_id="knowledge-1",
        features={"feature_a": 0.8},
        feature_names=("feature_a",),
    )

    vector_two = FeatureVector(
        pattern_id="pattern-2",
        knowledge_id="knowledge-2",
        features={"feature_a": 0.2},
        feature_names=("feature_a",),
    )

    matrix = extractor.build_feature_matrix(
        (vector_one, vector_two)
    )

    assert len(matrix.rows) == 2
    assert len(matrix.pattern_ids) == 2

    assert matrix.rows[0] == vector_one.as_vector()
    assert matrix.rows[1] == vector_two.as_vector()


def test_pipeline_rejects_inconsistent_vector_schema():
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
            (vector_one, vector_two)
        )


def test_pipeline_rejects_incomplete_vector_before_delivery():
    extractor = FeatureExtractor()

    vector = FeatureVector(
        pattern_id="pattern-1",
        knowledge_id="knowledge-1",
        features={
            "feature_a": 0.8,
        },
        feature_names=(
            "feature_a",
            "feature_b",
        ),
    )

    sink = RecordingFeatureSink()

    with pytest.raises(ValueError):
        extractor.deliver_feature_vector(
            vector,
            sink,
        )

    assert sink.received == []


def test_pipeline_propagates_downstream_failure():
    extractor = FeatureExtractor()

    class FailingSink:
        def accept_feature_vector(
            self,
            vector: FeatureVector,
        ) -> None:
            raise RuntimeError(
                "Downstream ML boundary failed."
            )

    vector = FeatureVector(
        pattern_id="pattern-1",
        knowledge_id="knowledge-1",
        features={
            "feature_a": 0.8,
        },
        feature_names=(
            "feature_a",
        ),
    )

    with pytest.raises(
        RuntimeError,
        match="Downstream ML boundary failed",
    ):
        extractor.deliver_feature_vector(
            vector,
            FailingSink(),
        )


def test_feature_extractor_pipeline_is_stateless():
    extractor = FeatureExtractor()

    first = FeatureVector(
        pattern_id="pattern-1",
        knowledge_id="knowledge-1",
        features={
            "feature_a": 0.8,
        },
        feature_names=(
            "feature_a",
        ),
    )

    second = FeatureVector(
        pattern_id="pattern-2",
        knowledge_id="knowledge-2",
        features={
            "feature_a": 0.3,
        },
        feature_names=(
            "feature_a",
        ),
    )

    first_matrix = extractor.build_feature_matrix(
        (first,)
    )

    second_matrix = extractor.build_feature_matrix(
        (second,)
    )

    assert first_matrix.rows == ((0.8,),)
    assert second_matrix.rows == ((0.3,),)

    assert first_matrix.pattern_ids == ("pattern-1",)
    assert second_matrix.pattern_ids == ("pattern-2",)

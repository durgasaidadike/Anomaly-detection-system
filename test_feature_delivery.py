from __future__ import annotations

from feature_delivery import FeatureVectorSink
from feature_vector_models import FeatureVector


class RecordingFeatureSink:
    def __init__(self) -> None:
        self.received: list[FeatureVector] = []

    def accept_feature_vector(
        self,
        vector: FeatureVector,
    ) -> None:
        self.received.append(vector)


def test_feature_vector_sink_contract_can_receive_vector():
    vector = FeatureVector(
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

    sink = RecordingFeatureSink()

    sink.accept_feature_vector(vector)

    assert sink.received == [vector]


def test_feature_extractor_delivers_complete_vector():
    from feature_extractor import FeatureExtractor

    extractor = FeatureExtractor()

    vector = FeatureVector(
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

    sink = RecordingFeatureSink()

    extractor.deliver_feature_vector(
        vector,
        sink,
    )

    assert sink.received == [vector]


def test_feature_extractor_does_not_modify_delivered_vector():
    from feature_extractor import FeatureExtractor

    extractor = FeatureExtractor()

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

    sink = RecordingFeatureSink()

    extractor.deliver_feature_vector(
        vector,
        sink,
    )

    delivered = sink.received[0]

    assert delivered is vector
    assert delivered.as_vector() == (0.8,)


def test_incomplete_vector_is_not_delivered():
    from feature_extractor import FeatureExtractor

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

    try:
        extractor.deliver_feature_vector(
            vector,
            sink,
        )
    except ValueError:
        pass
    else:
        raise AssertionError(
            "Incomplete vectors must not be delivered."
        )

    assert sink.received == []


def test_invalid_delivery_object_is_rejected():
    from feature_extractor import FeatureExtractor

    extractor = FeatureExtractor()

    sink = RecordingFeatureSink()

    try:
        extractor.deliver_feature_vector(
            object(),  # type: ignore[arg-type]
            sink,
        )
    except TypeError:
        pass
    else:
        raise AssertionError(
            "Non-FeatureVector objects must be rejected."
        )

    assert sink.received == []


def test_downstream_delivery_failure_is_propagated():
    from feature_extractor import FeatureExtractor

    class FailingSink:
        def accept_feature_vector(
            self,
            vector: FeatureVector,
        ) -> None:
            raise RuntimeError("ML delivery failed.")

    extractor = FeatureExtractor()

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

    sink = FailingSink()

    try:
        extractor.deliver_feature_vector(
            vector,
            sink,
        )
    except RuntimeError as exc:
        assert str(exc) == "ML delivery failed."
    else:
        raise AssertionError(
            "Downstream delivery failures must propagate."
        )

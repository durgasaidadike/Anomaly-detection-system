from __future__ import annotations

import ast
from pathlib import Path

from feature_extractor import FeatureExtractor
from feature_matrix_models import FeatureMatrix
from feature_vector_models import FeatureVector


FEATURE_EXTRACTOR_PATH = Path(__file__).with_name(
    "feature_extractor.py"
)


def test_feature_extractor_is_stateless():
    extractor = FeatureExtractor()

    assert extractor.__dict__ == {}


def test_feature_extractor_does_not_retain_feature_vectors():
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

    class Sink:
        def __init__(self) -> None:
            self.received = []

        def accept_feature_vector(self, value):
            self.received.append(value)

    sink = Sink()

    extractor.deliver_feature_vector(
        vector,
        sink,
    )

    assert extractor.__dict__ == {}
    assert sink.received == [vector]


def test_feature_extractor_produces_only_feature_vectors_and_matrices():
    extractor = FeatureExtractor()

    vector = extractor.build_feature_vector(
        pattern_id="pattern-1",
        knowledge_id="knowledge-1",
        features={
            "feature_a": 0.8,
        },
        feature_names=(
            "feature_a",
        ),
    )

    matrix = extractor.build_feature_matrix(
        (vector,)
    )

    assert isinstance(vector, FeatureVector)
    assert isinstance(matrix, FeatureMatrix)


def test_feature_extractor_has_no_forbidden_ml_or_persistence_imports():
    source = FEATURE_EXTRACTOR_PATH.read_text(
        encoding="utf-8"
    )

    tree = ast.parse(source)

    forbidden_roots = {
        "sklearn",
        "torch",
        "tensorflow",
        "pymongo",
        "motor",
        "sqlalchemy",
        "flask",
    }

    imported_roots: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_roots.add(
                    alias.name.split(".", maxsplit=1)[0]
                )

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported_roots.add(
                    node.module.split(".", maxsplit=1)[0]
                )

    forbidden_imports = (
        imported_roots & forbidden_roots
    )

    assert forbidden_imports == set()


def test_feature_extractor_does_not_accept_raw_event_values():
    extractor = FeatureExtractor()

    try:
        extractor.build_feature_vector(
            pattern_id="pattern-1",
            knowledge_id="knowledge-1",
            features={
                "path": "C:/documents/file.txt",
                "operation": "delete",
            },
            feature_names=(
                "path",
                "operation",
            ),
        )
    except ValueError:
        pass
    else:
        raise AssertionError(
            "Raw/non-numerical event information must not "
            "enter the FeatureVector."
        )


def test_feature_extractor_does_not_collapse_multiple_patterns_into_one_vector():
    extractor = FeatureExtractor()

    vector_one = FeatureVector(
        pattern_id="pattern-1",
        knowledge_id="knowledge-1",
        features={
            "feature_a": 0.8,
        },
        feature_names=("feature_a",),
    )

    vector_two = FeatureVector(
        pattern_id="pattern-2",
        knowledge_id="knowledge-2",
        features={
            "feature_a": 0.3,
        },
        feature_names=("feature_a",),
    )

    matrix = extractor.build_feature_matrix(
        (
            vector_one,
            vector_two,
        )
    )

    assert matrix.row_count() == 2
    assert matrix.pattern_ids == (
        "pattern-1",
        "pattern-2",
    )

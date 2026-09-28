from feature_matrix_models import FeatureMatrix


def test_feature_matrix_reports_dimensions():
    matrix = FeatureMatrix(
        feature_names=(
            "feature_a",
            "feature_b",
        ),
        rows=(
            (0.8, 0.2),
            (0.4, 0.6),
        ),
        pattern_ids=(
            "pattern-1",
            "pattern-2",
        ),
        knowledge_ids=(
            "knowledge-1",
            "knowledge-2",
        ),
    )

    assert matrix.row_count() == 2
    assert matrix.column_count() == 2


def test_feature_matrix_returns_rows():
    matrix = FeatureMatrix(
        feature_names=(
            "feature_a",
            "feature_b",
        ),
        rows=(
            (0.8, 0.2),
            (0.4, 0.6),
        ),
        pattern_ids=(
            "pattern-1",
            "pattern-2",
        ),
        knowledge_ids=(
            "knowledge-1",
            "knowledge-2",
        ),
    )

    assert matrix.as_matrix() == (
        (0.8, 0.2),
        (0.4, 0.6),
    )


def test_feature_matrix_is_immutable():
    matrix = FeatureMatrix(
        feature_names=("feature_a",),
        rows=((0.8,),),
        pattern_ids=("pattern-1",),
        knowledge_ids=("knowledge-1",),
    )

    try:
        matrix.feature_names = ("changed",)
    except AttributeError:
        pass
    else:
        raise AssertionError(
            "FeatureMatrix should be immutable"
        )

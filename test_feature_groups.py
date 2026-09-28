from feature_groups import FeatureGroups


def test_feature_groups_preserve_behavioral_categories():
    groups = FeatureGroups(
        operation={"modify_ratio": 0.8},
        temporal={"session_duration": 120.0},
        sequence={"sequence_score": 0.7},
        contextual={"directory_transition": 0.3},
        session={"session_intensity": 0.6},
        intelligence={"confidence": 0.9},
        recurrence={"recurrence": 500.0},
        drift={"drift": 0.2},
    )

    separated = groups.as_groups()

    assert separated["operation"] == {
        "modify_ratio": 0.8
    }

    assert separated["temporal"] == {
        "session_duration": 120.0
    }

    assert separated["sequence"] == {
        "sequence_score": 0.7
    }

    assert separated["contextual"] == {
        "directory_transition": 0.3
    }

    assert separated["session"] == {
        "session_intensity": 0.6
    }

    assert separated["intelligence"] == {
        "confidence": 0.9
    }

    assert separated["recurrence"] == {
        "recurrence": 500.0
    }

    assert separated["drift"] == {
        "drift": 0.2
    }


def test_feature_groups_are_immutable():
    groups = FeatureGroups(
        operation={},
        temporal={},
        sequence={},
        contextual={},
        session={},
        intelligence={},
        recurrence={},
        drift={},
    )

    try:
        groups.operation = {"changed": 1.0}
    except AttributeError:
        pass
    else:
        raise AssertionError(
            "FeatureGroups should be immutable"
        )

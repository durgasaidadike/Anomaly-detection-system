from datetime import datetime

import pytest

from behavioral_identity import BehavioralIdentity
from final_pattern_models import FinalPattern


def build_pattern(
    pattern_id="pattern-1",
    session_id="session-1",
    user_id="user-1",
    operation_type="CREATE",
):
    timestamp = datetime(
        2026,
        9,
        4,
        10,
        0,
        0,
    )

    return FinalPattern(
        pattern_id=pattern_id,
        session_id=session_id,
        user_id=user_id,
        created_at=timestamp,
        observations=[
            {
                "operation_type": operation_type,
                "timestamp": timestamp,
                "file_extension": ".py",
                "directory": "/project",
            }
        ],
        observation_count=1,
    )


def test_build_key_is_deterministic():
    identity = BehavioralIdentity()

    pattern = build_pattern()

    first_key = identity.build_key(pattern)
    second_key = identity.build_key(pattern)

    assert first_key == second_key


def test_same_behavior_has_same_key():
    identity = BehavioralIdentity()

    first = build_pattern(
        pattern_id="pattern-1",
        session_id="session-1",
    )

    second = build_pattern(
        pattern_id="pattern-2",
        session_id="session-2",
    )

    assert identity.build_key(first) == (
        identity.build_key(second)
    )


def test_different_operation_has_different_key():
    identity = BehavioralIdentity()

    first = build_pattern(
        operation_type="CREATE",
    )

    second = build_pattern(
        operation_type="DELETE",
    )

    assert identity.build_key(first) != (
        identity.build_key(second)
    )


def test_different_user_has_different_key():
    identity = BehavioralIdentity()

    first = build_pattern(
        user_id="user-1",
    )

    second = build_pattern(
        user_id="user-2",
    )

    assert identity.build_key(first) != (
        identity.build_key(second)
    )


def test_file_extension_is_normalized():
    identity = BehavioralIdentity()

    first = build_pattern()
    first.observations[0][
        "file_extension"
    ] = ".PY"

    second = build_pattern()
    second.observations[0][
        "file_extension"
    ] = ".py"

    assert identity.build_key(first) == (
        identity.build_key(second)
    )


def test_operation_type_is_normalized():
    identity = BehavioralIdentity()

    first = build_pattern(
        operation_type="create",
    )

    second = build_pattern(
        operation_type="CREATE",
    )

    assert identity.build_key(first) == (
        identity.build_key(second)
    )


def test_directory_is_part_of_identity():
    identity = BehavioralIdentity()

    first = build_pattern()

    second = build_pattern()

    second.observations[0][
        "directory"
    ] = "/different"

    assert identity.build_key(first) != (
        identity.build_key(second)
    )


def test_invalid_pattern_raises_value_error():
    identity = BehavioralIdentity()

    with pytest.raises(ValueError):
        identity.build_key(None)

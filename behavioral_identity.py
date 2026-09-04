from __future__ import annotations

from typing import Tuple

from final_pattern_models import FinalPattern


BehavioralKey = Tuple[
    object,
    Tuple[str, ...],
    Tuple[str, ...],
    Tuple[str, ...],
]


class BehavioralIdentity:
    """
    Builds the deterministic behavioral identity used by the
    Final Pattern Repository.

    This component currently performs exact behavioral identity
    construction. Similarity, relationship, context, and drift
    analysis are intentionally outside this component.
    """

    def build_key(
        self,
        pattern: FinalPattern,
    ) -> BehavioralKey:
        """
        Build a deterministic key representing the behavior
        contained in a FinalPattern.
        """

        if not self._validate(pattern):
            raise ValueError(
                "Invalid FinalPattern"
            )

        observations = pattern.observations

        operation_sequence = tuple(
            str(
                observation.get(
                    "operation_type",
                    "",
                )
            ).upper()
            for observation in observations
        )

        extensions = tuple(
            str(
                observation.get(
                    "file_extension",
                    "",
                )
            ).lower()
            for observation in observations
        )

        directories = tuple(
            str(
                observation.get(
                    "directory",
                    "",
                )
            )
            for observation in observations
        )

        return (
            pattern.user_id,
            operation_sequence,
            extensions,
            directories,
        )

    def _validate(
        self,
        pattern: FinalPattern,
    ) -> bool:
        if pattern is None:
            return False

        if not isinstance(
            pattern,
            FinalPattern,
        ):
            return False

        if not pattern.pattern_id:
            return False

        if not pattern.session_id:
            return False

        if not pattern.observations:
            return False

        if pattern.observation_count <= 0:
            return False

        return True

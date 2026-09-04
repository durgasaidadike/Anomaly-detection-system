from __future__ import annotations

import copy
from typing import Dict, List, Optional, Tuple

from final_pattern_models import FinalPattern


class FinalPatternRepository:
    """
    In-memory repository for immutable historical Final Patterns.

    The repository stores FinalPattern instances and keeps a separate
    behavioral index for identifying repeated behavior.
    """

    def __init__(self) -> None:
        self._patterns: Dict[str, FinalPattern] = {}
        self._pattern_index: Dict[Tuple, str] = {}

    def store(self, pattern: FinalPattern) -> bool:
        if not self._validate_final_pattern(pattern):
            return False

        try:
            pattern_key = self._behavioral_key(pattern)

            if pattern_key in self._pattern_index:
                return False

            pattern_id = pattern.pattern_id

            if not pattern_id:
                return False

            if pattern_id in self._patterns:
                return False

            self._patterns[pattern_id] = copy.deepcopy(pattern)
            self._pattern_index[pattern_key] = pattern_id

            return True

        except Exception:
            return False

    def get(self, pattern_id: str) -> Optional[FinalPattern]:
        if not pattern_id:
            return None

        pattern = self._patterns.get(pattern_id)

        if pattern is None:
            return None

        return copy.deepcopy(pattern)

    def get_all(self) -> List[FinalPattern]:
        return [
            copy.deepcopy(pattern)
            for pattern in self._patterns.values()
        ]

    def count(self) -> int:
        return len(self._patterns)

    def contains(self, pattern_id: str) -> bool:
        if not pattern_id:
            return False

        return pattern_id in self._patterns

    def _behavioral_key(
        self,
        pattern: FinalPattern,
    ) -> Tuple:
        observations = pattern.observations

        operation_sequence = tuple(
            str(
                observation.get("operation_type", "")
            ).upper()
            for observation in observations
        )

        extensions = tuple(
            str(
                observation.get("file_extension", "")
            ).lower()
            for observation in observations
        )

        directories = tuple(
            str(
                observation.get("directory", "")
            )
            for observation in observations
        )

        return (
            pattern.user_id,
            operation_sequence,
            extensions,
            directories,
        )

    def _validate_final_pattern(
        self,
        pattern: FinalPattern,
    ) -> bool:
        if pattern is None:
            return False

        if not isinstance(pattern, FinalPattern):
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

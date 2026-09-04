from __future__ import annotations

import copy
from typing import Dict, List, Optional, Tuple

from candidate_pattern_models import CandidatePattern


class FinalPatternRepository:
    """
    In-memory repository for immutable Final Patterns.

    The repository consolidates repeated behavioral patterns instead
    of storing duplicate behavioral knowledge.
    """

    def __init__(self) -> None:
        self._patterns: Dict[str, CandidatePattern] = {}
        self._pattern_index: Dict[Tuple, str] = {}

    def store(self, pattern: CandidatePattern) -> bool:
        if not self._validate_final_pattern(pattern):
            return False

        try:
            pattern_key = self._behavioral_key(pattern)

            existing_pattern_id = self._pattern_index.get(pattern_key)

            if existing_pattern_id is not None:
                return self._merge_repeated_pattern(
                    existing_pattern_id,
                    pattern,
                )

            pattern_id = self._pattern_id(pattern)

            if pattern_id in self._patterns:
                return False

            self._patterns[pattern_id] = copy.deepcopy(pattern)
            self._pattern_index[pattern_key] = pattern_id

            return True

        except Exception:
            return False

    def get(self, pattern_id: str) -> Optional[CandidatePattern]:
        if not pattern_id:
            return None

        pattern = self._patterns.get(pattern_id)

        if pattern is None:
            return None

        return copy.deepcopy(pattern)

    def get_all(self) -> List[CandidatePattern]:
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

    def _pattern_id(self, pattern: CandidatePattern) -> str:
        return pattern.session_id

    def _behavioral_key(
        self,
        pattern: CandidatePattern,
    ) -> Tuple:
        observations = pattern.timeline.observations

        operation_sequence = tuple(
            str(observation.get("operation_type", "")).upper()
            for observation in observations
        )

        extensions = tuple(
            str(observation.get("file_extension", "")).lower()
            for observation in observations
        )

        directories = tuple(
            str(observation.get("directory", ""))
            for observation in observations
        )

        return (
            pattern.user_id,
            operation_sequence,
            extensions,
            directories,
        )

    def _merge_repeated_pattern(
        self,
        existing_pattern_id: str,
        incoming_pattern: CandidatePattern,
    ) -> bool:
        existing_pattern = self._patterns.get(existing_pattern_id)

        if existing_pattern is None:
            return False

        existing_pattern.metadata.observation_count += (
            incoming_pattern.metadata.observation_count
        )

        return True

    def _validate_final_pattern(
        self,
        pattern: CandidatePattern,
    ) -> bool:
        if pattern is None:
            return False

        if not isinstance(pattern, CandidatePattern):
            return False

        if not pattern.session_id:
            return False

        if not pattern.metadata.complete:
            return False

        if pattern.is_empty():
            return False

        if pattern.metadata.interrupted:
            return False

        return True

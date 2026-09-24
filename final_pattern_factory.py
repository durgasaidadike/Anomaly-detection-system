from __future__ import annotations

import copy
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import uuid4

from candidate_pattern_models import CandidatePattern
from final_pattern_models import FinalPattern


class FinalPatternFactory:
    """
    Converts a completed CandidatePattern into an immutable FinalPattern.
    """

    def create(
        self,
        pattern: CandidatePattern,
        *,
        pattern_version: int = 1,
        learning_metadata: Optional[
            Dict[str, Any]
        ] = None,
    ) -> FinalPattern | None:
        if not self._validate(pattern):
            return None

        if not isinstance(pattern_version, int):
            return None

        if pattern_version <= 0:
            return None

        if learning_metadata is not None and not isinstance(
            learning_metadata,
            dict,
        ):
            return None

        return FinalPattern(
            pattern_id=str(uuid4()),
            session_id=pattern.session_id,
            user_id=pattern.user_id,
            created_at=(
                pattern.metadata.finalized_at
                or datetime.now(timezone.utc)
            ),
            observations=[
                dict(observation)
                for observation in pattern.timeline.observations
            ],
            operational_characteristics=dict(
                pattern.operational_characteristics
            ),
            temporal_characteristics=dict(
                pattern.temporal_characteristics
            ),
            sequential_characteristics=[
                dict(item)
                for item in pattern.sequential_characteristics
            ],
            contextual_characteristics=dict(
                pattern.contextual_characteristics
            ),
            relationship_characteristics=[
                dict(item)
                for item in pattern.relationship_characteristics
            ],
            session_characteristics=dict(
                pattern.session_characteristics
            ),
            pattern_version=pattern_version,
            learning_metadata=(
                copy.deepcopy(learning_metadata)
                if learning_metadata is not None
                else {
                    "origin": "candidate_pattern_manager",
                    "finalized_at": (
                        pattern.metadata.finalized_at
                    ),
                    "initial_observation_count": (
                        pattern.observation_count()
                    ),
                }
            ),
            observation_count=pattern.observation_count(),
        )

    def _validate(self, pattern: CandidatePattern) -> bool:
        if pattern is None:
            return False

        if not isinstance(pattern, CandidatePattern):
            return False

        if not pattern.session_id:
            return False

        if not pattern.metadata.complete:
            return False

        if pattern.metadata.interrupted:
            return False

        if pattern.is_empty():
            return False

        return True

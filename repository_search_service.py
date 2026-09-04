from __future__ import annotations

import copy
from typing import Dict, Optional

from behavioral_identity import (
    BehavioralIdentity,
    BehavioralKey,
)
from behavioral_knowledge import BehavioralKnowledge
from final_pattern_models import FinalPattern
from repository_search_result import (
    RepositorySearchResult,
)


class RepositorySearchService:
    """
    Performs repository searches using behavioral identity.

    The service is responsible for locating an existing behavioral
    blueprint. Persistence remains the responsibility of the
    FinalPatternRepository.
    """

    def __init__(
        self,
        patterns: Dict[str, FinalPattern],
        pattern_index: Dict[BehavioralKey, str],
        knowledge: Dict[str, BehavioralKnowledge],
        behavioral_identity: Optional[
            BehavioralIdentity
        ] = None,
    ) -> None:
        self._patterns = patterns
        self._pattern_index = pattern_index
        self._knowledge = knowledge

        self._behavioral_identity = (
            behavioral_identity
            or BehavioralIdentity()
        )

    def search(
        self,
        pattern: FinalPattern,
    ) -> RepositorySearchResult:
        """
        Search for an exact behavioral match.
        """

        if not self._validate(pattern):
            return RepositorySearchResult.no_match()

        try:
            pattern_key = (
                self._behavioral_identity.build_key(
                    pattern
                )
            )

            pattern_id = self._pattern_index.get(
                pattern_key
            )

            if pattern_id is None:
                return RepositorySearchResult.no_match()

            representative = self._patterns.get(
                pattern_id
            )

            knowledge = self._knowledge.get(
                f"knowledge-{pattern_id}"
            )

            if representative is None:
                return RepositorySearchResult.no_match()

            if knowledge is None:
                return RepositorySearchResult.no_match()

            return RepositorySearchResult.match(
                representative_pattern=copy.deepcopy(
                    representative
                ),
                behavioral_knowledge=knowledge.snapshot(),
            )

        except Exception:
            return RepositorySearchResult.no_match()

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

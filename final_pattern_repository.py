from __future__ import annotations

import copy
from typing import Dict, List, Optional

from behavioral_identity import (
    BehavioralIdentity,
    BehavioralKey,
)
from behavioral_knowledge import BehavioralKnowledge
from final_pattern_models import FinalPattern
from repository_search_result import RepositorySearchResult
from repository_search_service import (
    RepositorySearchService,
)


class FinalPatternRepository:
    """
    In-memory repository for immutable historical Final Patterns and
    consolidated behavioral knowledge.
    """

    def __init__(
        self,
        behavioral_identity: Optional[
            BehavioralIdentity
        ] = None,
    ) -> None:
        self._patterns: Dict[str, FinalPattern] = {}

        self._pattern_index: Dict[
            BehavioralKey,
            str,
        ] = {}

        self._knowledge: Dict[
            str,
            BehavioralKnowledge,
        ] = {}

        self._recorded_pattern_ids = set()

        self._behavioral_identity = (
            behavioral_identity
            or BehavioralIdentity()
        )

        self._search_service = (
            RepositorySearchService(
                patterns=self._patterns,
                pattern_index=self._pattern_index,
                knowledge=self._knowledge,
                behavioral_identity=self._behavioral_identity,
            )
        )

    def store(
        self,
        pattern: FinalPattern,
    ) -> bool:
        """
        Store a new historical FinalPattern or record another
        occurrence of an already-known behavioral blueprint.

        Re-submitting the same historical FinalPattern is idempotent.
        Reusing an existing pattern ID for different behavior is rejected.
        """

        if not self._validate_final_pattern(pattern):
            return False

        try:
            pattern_id = pattern.pattern_id

            pattern_key = (
                self._behavioral_identity.build_key(
                    pattern
                )
            )

            existing_pattern = self._patterns.get(
                pattern_id
            )

            if existing_pattern is not None:
                existing_pattern_key = (
                    self._behavioral_identity.build_key(
                        existing_pattern
                    )
                )

                if existing_pattern_key != pattern_key:
                    return False

                return True

            if pattern_id in self._recorded_pattern_ids:
                return True

            existing_pattern_id = (
                self._pattern_index.get(
                    pattern_key
                )
            )

            if existing_pattern_id is not None:
                result = self._record_repeated_behavior(
                    existing_pattern_id,
                    pattern,
                )

                if result:
                    self._recorded_pattern_ids.add(
                        pattern_id
                    )

                return result

            self._patterns[
                pattern_id
            ] = copy.deepcopy(pattern)

            self._pattern_index[
                pattern_key
            ] = pattern_id

            self._create_behavioral_knowledge(
                pattern_id,
                pattern,
                pattern_key,
            )

            self._recorded_pattern_ids.add(
                pattern_id
            )

            return True

        except Exception:
            return False

    def get(
        self,
        pattern_id: str,
    ) -> Optional[FinalPattern]:
        """
        Return an independent copy of a historical FinalPattern.
        """

        if not pattern_id:
            return None

        pattern = self._patterns.get(
            pattern_id
        )

        if pattern is None:
            return None

        return copy.deepcopy(pattern)

    def get_all(
        self,
    ) -> List[FinalPattern]:
        """
        Return independent copies of all historical FinalPatterns.
        """

        return [
            copy.deepcopy(pattern)
            for pattern in self._patterns.values()
        ]

    def find_knowledge_by_key(
        self,
        behavior_key: BehavioralKey,
    ) -> Optional[BehavioralKnowledge]:
        """
        Find consolidated behavioral knowledge directly from a
        deterministic behavioral identity key.

        Returns an independent snapshot when the behavioral identity
        is already known.
        """

        if not behavior_key:
            return None

        try:
            pattern_id = self._pattern_index.get(
                behavior_key
            )

            if pattern_id is None:
                return None

            knowledge_id = (
                f"knowledge-{pattern_id}"
            )

            return self.get_knowledge(
                knowledge_id
            )

        except Exception:
            return None

    def get_knowledge(
        self,
        knowledge_id: str,
    ) -> Optional[BehavioralKnowledge]:
        """
        Return an independent snapshot of learned behavioral knowledge.
        """

        if not knowledge_id:
            return None

        knowledge = self._knowledge.get(
            knowledge_id
        )

        if knowledge is None:
            return None

        return knowledge.snapshot()

    def get_all_knowledge(
        self,
    ) -> List[BehavioralKnowledge]:
        """
        Return independent snapshots of all behavioral knowledge.
        """

        return [
            knowledge.snapshot()
            for knowledge in self._knowledge.values()
        ]

    def count(self) -> int:
        return len(self._patterns)

    def knowledge_count(self) -> int:
        return len(self._knowledge)

    def contains(
        self,
        pattern_id: str,
    ) -> bool:
        if not pattern_id:
            return False

        return pattern_id in self._patterns

    def validate_integrity(self) -> bool:
        """
        Validate internal consistency between historical patterns,
        behavioral indexes, behavioral knowledge, and recorded IDs.

        This method is read-only and does not repair or mutate state.
        """

        try:
            pattern_ids = set(
                self._patterns.keys()
            )

            recorded_ids = set(
                self._recorded_pattern_ids
            )

            # Every stored pattern must be marked as recorded.
            if not pattern_ids.issubset(
                recorded_ids
            ):
                return False

            # Every recorded ID must correspond to a stored pattern.
            if not recorded_ids.issubset(
                pattern_ids
            ):
                return False

            # Every behavioral index entry must point to an existing
            # historical pattern.
            for (
                behavior_key,
                pattern_id,
            ) in self._pattern_index.items():
                if pattern_id not in self._patterns:
                    return False

                pattern = self._patterns[
                    pattern_id
                ]

                expected_key = (
                    self._behavioral_identity.build_key(
                        pattern
                    )
                )

                if expected_key != behavior_key:
                    return False

            # Every stored pattern must have exactly one behavioral
            # index entry pointing to it.
            indexed_pattern_ids = set(
                self._pattern_index.values()
            )

            if indexed_pattern_ids != pattern_ids:
                return False

            # Each historical representative pattern must have
            # corresponding behavioral knowledge.
            expected_knowledge_ids = {
                f"knowledge-{pattern_id}"
                for pattern_id in pattern_ids
            }

            if set(self._knowledge.keys()) != (
                expected_knowledge_ids
            ):
                return False

            # Every knowledge record must point to an existing
            # representative historical pattern.
            for knowledge_id, knowledge in (
                self._knowledge.items()
            ):
                if knowledge.representative_pattern_id not in (
                    pattern_ids
                ):
                    return False

                expected_knowledge_id = (
                    "knowledge-"
                    + knowledge.representative_pattern_id
                )

                if knowledge_id != (
                    expected_knowledge_id
                ):
                    return False

            return True

        except Exception:
            return False

    def search(
        self,
        pattern: FinalPattern,
    ) -> RepositorySearchResult:
        """
        Search the repository for an exact behavioral match.
        """

        return self._search_service.search(
            pattern
        )

    def find_knowledge(
        self,
        pattern: FinalPattern,
    ) -> Optional[BehavioralKnowledge]:
        """
        Find learned behavioral knowledge matching the supplied
        FinalPattern using the repository's exact behavioral identity.

        Returns an independent snapshot of the knowledge when a
        matching behavioral blueprint exists.
        """

        if not self._validate_final_pattern(pattern):
            return None

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
                return None

            knowledge_id = (
                f"knowledge-{pattern_id}"
            )

            return self.get_knowledge(
                knowledge_id
            )

        except Exception:
            return None

    def find_representative_pattern(
        self,
        pattern: FinalPattern,
    ) -> Optional[FinalPattern]:
        """
        Find the historical FinalPattern representing the supplied
        behavioral identity.

        Returns an independent copy when the behavior is already known.
        """

        if not self._validate_final_pattern(pattern):
            return None

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
                return None

            return self.get(pattern_id)

        except Exception:
            return None

    def _create_behavioral_knowledge(
        self,
        pattern_id: str,
        pattern: FinalPattern,
        pattern_key: BehavioralKey,
    ) -> BehavioralKnowledge:
        """
        Create the initial knowledge aggregate for a new behavior.
        """

        knowledge_id = (
            f"knowledge-{pattern_id}"
        )

        knowledge = BehavioralKnowledge(
            knowledge_id=knowledge_id,
            user_id=pattern.user_id,
            behavior_key=pattern_key,
            representative_pattern_id=pattern_id,
            occurrence_count=1,
            first_seen=pattern.created_at,
            last_seen=pattern.created_at,
        )

        self._knowledge[
            knowledge_id
        ] = knowledge

        return knowledge

    def _record_repeated_behavior(
        self,
        representative_pattern_id: str,
        incoming_pattern: FinalPattern,
    ) -> bool:
        """
        Strengthen the existing behavioral knowledge without mutating
        the historical FinalPattern.
        """

        knowledge_id = (
            f"knowledge-{representative_pattern_id}"
        )

        knowledge = self._knowledge.get(
            knowledge_id
        )

        if knowledge is None:
            return False

        knowledge.record_occurrence(
            incoming_pattern.created_at
        )

        return True

    def _validate_final_pattern(
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

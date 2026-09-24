from __future__ import annotations

import copy
import logging
from datetime import datetime
from typing import Dict, List, Optional

from behavioral_identity import (
    BehavioralIdentity,
    BehavioralKey,
)
from behavioral_knowledge import BehavioralKnowledge
from final_pattern_models import FinalPattern
from pattern_reference import PatternReference
from repository_search_result import RepositorySearchResult
from repository_search_service import (
    RepositorySearchService,
)
from repository_snapshot import RepositorySnapshot

logger = logging.getLogger(__name__)


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
        self._recorded_occurrence_ids = set()
        self._occurrence_behavior_keys: Dict[str, BehavioralKey] = {}
        self._user_pattern_index: Dict[str, List[str]] = {}
        self._session_pattern_index: Dict[str, str] = {}
        self._baseline_pattern_ids: Dict[str, str] = {}

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
        Store a FinalPattern atomically.

        A failed store operation must not leave partial state behind.
        Historical FinalPatterns remain immutable once stored.
        """

        try:
            if not self._validate_final_pattern(pattern):
                logger.warning("Rejected invalid FinalPattern: %r", pattern)
                return False

            pattern_id = pattern.pattern_id

            pattern_key = (
                self._behavioral_identity.build_key(
                    pattern
                )
            )

            # ------------------------------------------------------------------
            # Existing pattern-id handling
            # ------------------------------------------------------------------
            # A previously stored representative pattern.
            if pattern_id in self._patterns:
                existing_pattern = self._patterns[pattern_id]

                # Exact retry of the same immutable object is idempotent.
                if existing_pattern == pattern:
                    return True

                # Same ID with changed content violates immutability/traceability.
                logger.warning(
                    "Rejected FinalPattern %s: pattern ID already exists "
                    "with different content",
                    pattern_id,
                )
                return False

            # A repeated occurrence that was already recorded.
            if pattern_id in self._recorded_occurrence_ids:
                recorded_key = self._occurrence_behavior_keys.get(pattern_id)
                if recorded_key == pattern_key:
                    return True

                logger.warning(
                    "Rejected FinalPattern %s: occurrence ID reused "
                    "for different behavioral identity",
                    pattern_id,
                )
                return False

            # A repository bookkeeping contradiction must never create
            # partial or corrupted state.
            if pattern_id in self._recorded_pattern_ids:
                logger.error(
                    "Repository integrity violation: pattern ID %s is "
                    "recorded but not present in stored patterns",
                    pattern_id,
                )
                return False

            # ------------------------------------------------------------------
            # Repeated behavioral identity
            # ------------------------------------------------------------------
            if pattern_key in self._pattern_index:
                existing_pattern_id = self._pattern_index[
                    pattern_key
                ]

                if pattern_id in self._recorded_occurrence_ids:
                    return True

                return self._record_repeated_behavior(
                    existing_pattern_id,
                    pattern,
                    pattern_key,
                )

            # ------------------------------------------------------------------
            # New behavioral identity
            # ------------------------------------------------------------------
            # Check session-ID uniqueness for genuinely new representative
            existing_session_pattern_id = (
                self._session_pattern_index.get(
                    pattern.session_id
                )
            )

            if existing_session_pattern_id is not None:
                logger.warning(
                    "Rejected FinalPattern %s: session %s is already "
                    "associated with pattern %s",
                    pattern_id,
                    pattern.session_id,
                    existing_session_pattern_id,
                )
                return False

            stored_pattern = copy.deepcopy(pattern)

            # Create knowledge before publishing the new repository state.
            #
            # If this fails, no repository structures have been modified yet.
            knowledge = self._create_behavioral_knowledge(
                pattern_id,
                stored_pattern,
                pattern_key,
            )

            if knowledge is None:
                return False

            # Determine if this is the user's first stored pattern
            is_first_user_pattern = (
                pattern.user_id
                not in self._user_pattern_index
            )

            # Take snapshots of index state before modification for rollback.
            user_pattern_ids_snapshot = list(
                self._user_pattern_index.get(
                    pattern.user_id,
                    [],
                )
            )

            session_pattern_id_snapshot = (
                self._session_pattern_index.get(
                    pattern.session_id
                )
            )

            baseline_pattern_id_snapshot = (
                self._baseline_pattern_ids.get(
                    pattern.user_id
                )
            )

            # Publish the new state only after every required operation above
            # has succeeded.
            user_pattern_ids = list(
                self._user_pattern_index.get(
                    pattern.user_id,
                    [],
                )
            )
            user_pattern_ids.append(pattern_id)

            self._patterns[pattern_id] = stored_pattern
            self._pattern_index[pattern_key] = pattern_id
            self._knowledge[knowledge.knowledge_id] = knowledge
            self._recorded_pattern_ids.add(pattern_id)

            self._user_pattern_index[
                pattern.user_id
            ] = user_pattern_ids

            self._session_pattern_index[
                pattern.session_id
            ] = pattern_id

            if is_first_user_pattern:
                self._baseline_pattern_ids[
                    pattern.user_id
                ] = pattern_id

            return True

        except Exception:
            # Rollback all repository state modifications if they were made
            self._patterns.pop(pattern_id, None)
            self._pattern_index.pop(pattern_key, None)
            self._knowledge.pop(f"knowledge-{pattern_id}", None)
            self._recorded_pattern_ids.discard(pattern_id)

            # Rollback index state if snapshots were taken
            try:
                # Restore user history exactly. A user that had no
                # history before this failed operation must not be left
                # behind as a phantom user with an empty history.
                if user_pattern_ids_snapshot:
                    self._user_pattern_index[
                        pattern.user_id
                    ] = user_pattern_ids_snapshot
                else:
                    self._user_pattern_index.pop(
                        pattern.user_id,
                        None,
                    )

                if session_pattern_id_snapshot is not None:
                    self._session_pattern_index[
                        pattern.session_id
                    ] = session_pattern_id_snapshot
                else:
                    try:
                        del self._session_pattern_index[
                            pattern.session_id
                        ]
                    except KeyError:
                        pass

                # Restore the baseline to its pre-store state. A failed
                # store must never leave a partially created baseline
                # behind, and must never discard a pre-existing one.
                if baseline_pattern_id_snapshot is None:
                    self._baseline_pattern_ids.pop(
                        pattern.user_id,
                        None,
                    )
                else:
                    self._baseline_pattern_ids[
                        pattern.user_id
                    ] = baseline_pattern_id_snapshot
            except NameError:
                # Snapshots weren't taken yet, nothing to rollback
                pass

            logger.exception(
                "Unexpected repository failure while storing FinalPattern"
            )

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

        patterns = sorted(
            self._patterns.values(),
            key=lambda pattern: (pattern.created_at, pattern.pattern_id),
        )
        return [copy.deepcopy(pattern) for pattern in patterns]

    def retrieve_patterns(
        self,
        user_id: Optional[str],
    ) -> List[FinalPattern]:
        """
        Return chronological historical FinalPatterns for one user.

        Only stored representative FinalPatterns are returned.
        Returned objects are independent copies and cannot mutate
        repository state.

        Userless requests fail closed and return no history.
        """

        if not self._is_valid_user_id(user_id):
            return []

        try:
            pattern_ids = self._user_pattern_index.get(
                user_id,
                [],
            )

            patterns = []

            for pid in pattern_ids:
                pattern = self._patterns.get(
                    pid
                )

                if pattern is not None:
                    patterns.append(pattern)

            patterns.sort(
                key=lambda pattern: (
                    pattern.created_at,
                    pattern.pattern_id,
                )
            )

            return [
                copy.deepcopy(pattern)
                for pattern in patterns
            ]

        except Exception:
            logger.exception(
                "Failed to retrieve historical patterns for user %r",
                user_id,
            )
            return []

    def get_behavior_history(
        self,
        user_id: Optional[str],
    ) -> List[FinalPattern]:
        """
        Return the historical behavioral FinalPattern collection
        associated with one user.
        """

        return self.retrieve_patterns(user_id)

    def retrieve_recent_patterns(
        self,
        user_id: Optional[str],
        limit: int,
    ) -> List[FinalPattern]:
        """
        Return the most recent historical FinalPatterns for a user.

        Results remain chronological from oldest to newest within
        the selected window.
        """

        if limit <= 0:
            return []

        if not self._is_valid_user_id(user_id):
            return []

        patterns = self.retrieve_patterns(user_id)

        return patterns[-limit:]

    def get_pattern_references(
        self,
        user_id: Optional[str],
    ) -> List[PatternReference]:
        """
        Return immutable logical references to a user's
        historical FinalPatterns.
        """

        if not self._is_valid_user_id(user_id):
            return []

        patterns = self.retrieve_patterns(user_id)

        return [
            PatternReference(
                pattern_id=pattern.pattern_id,
                session_id=pattern.session_id,
                user_id=pattern.user_id,
                created_at=pattern.created_at,
            )
            for pattern in patterns
        ]

    def get_recent_pattern_references(
        self,
        user_id: Optional[str],
        limit: int,
    ) -> List[PatternReference]:
        """
        Return references for the most recent historical patterns.
        """

        if not self._is_valid_user_id(user_id):
            return []

        patterns = self.retrieve_recent_patterns(
            user_id,
            limit,
        )

        return [
            PatternReference(
                pattern_id=pattern.pattern_id,
                session_id=pattern.session_id,
                user_id=pattern.user_id,
                created_at=pattern.created_at,
            )
            for pattern in patterns
        ]

    def resolve_pattern_reference(
        self,
        reference: PatternReference,
    ) -> Optional[FinalPattern]:
        """
        Resolve a historical reference into a detached
        FinalPattern snapshot.

        A reference is only resolvable when it is structurally valid,
        its owner identity is real, and it matches the stored pattern's
        user, session, and creation timestamp.
        """

        if not self._validate_pattern_reference(reference):
            return None

        if not self._is_valid_user_id(
            reference.user_id
        ):
            return None

        pattern = self._patterns.get(
            reference.pattern_id
        )

        if pattern is None:
            return None

        if pattern.user_id != reference.user_id:
            return None

        if pattern.session_id != reference.session_id:
            return None

        if pattern.created_at != reference.created_at:
            return None

        return copy.deepcopy(pattern)

    def get_latest_pattern(
        self,
        user_id: Optional[str],
    ) -> Optional[FinalPattern]:
        """
        Return the most recent historical FinalPattern for a user.
        """

        if not self._is_valid_user_id(user_id):
            return None

        patterns = self.retrieve_patterns(user_id)

        if not patterns:
            return None

        return patterns[-1]

    def get_baseline_pattern(
        self,
        user_id: Optional[str],
    ) -> Optional[FinalPattern]:
        """
        Return the user's initial behavioral baseline.

        The returned FinalPattern is detached from repository state.
        """

        if not self._is_valid_user_id(user_id):
            return None

        pattern_id = self._baseline_pattern_ids.get(
            user_id
        )

        if pattern_id is None:
            return None

        return self.get(pattern_id)

    def has_baseline(
        self,
        user_id: Optional[str],
    ) -> bool:
        if not self._is_valid_user_id(user_id):
            return False

        return user_id in self._baseline_pattern_ids

    def get_repository_metadata(self) -> Dict[str, int]:
        """
        Return read-only repository statistics derived from current state.
        """

        return {
            "pattern_count": len(self._patterns),
            "knowledge_count": len(self._knowledge),
            "user_count": len(self._user_pattern_index),
            "session_count": len(self._session_pattern_index),
            "occurrence_count": len(
                self._recorded_occurrence_ids
            ),
            "baseline_count": len(
                self._baseline_pattern_ids
            ),
        }

    # ------------------------------------------------------------------
    # Recovery boundary
    # ------------------------------------------------------------------
    def create_snapshot(self) -> RepositorySnapshot:
        """
        Create a detached snapshot of repository state for recovery.
        """

        return RepositorySnapshot(
            patterns=copy.deepcopy(
                list(self._patterns.values())
            ),
            knowledge=copy.deepcopy(
                list(self._knowledge.values())
            ),
            pattern_index=copy.deepcopy(
                self._pattern_index
            ),
            user_pattern_index=copy.deepcopy(
                self._user_pattern_index
            ),
            session_pattern_index=copy.deepcopy(
                self._session_pattern_index
            ),
            recorded_pattern_ids=list(
                self._recorded_pattern_ids
            ),
            recorded_occurrence_ids=list(
                self._recorded_occurrence_ids
            ),
            occurrence_behavior_keys=copy.deepcopy(
                self._occurrence_behavior_keys
            ),
            baseline_pattern_ids=copy.deepcopy(
                self._baseline_pattern_ids
            ),
        )

    def validate_snapshot(
        self,
        snapshot: RepositorySnapshot,
    ) -> bool:
        """
        Structurally validate a recovery snapshot.

        This is structural validation only. It must not perform
        behavioral interpretation of the snapshot contents.
        """

        if snapshot is None:
            return False

        if not isinstance(
            snapshot,
            RepositorySnapshot,
        ):
            return False

        if not isinstance(snapshot.patterns, list):
            return False

        if not isinstance(snapshot.knowledge, list):
            return False

        if not isinstance(
            snapshot.pattern_index,
            dict,
        ):
            return False

        if not isinstance(
            snapshot.user_pattern_index,
            dict,
        ):
            return False

        if not isinstance(
            snapshot.session_pattern_index,
            dict,
        ):
            return False

        return True

    def restore_snapshot(
        self,
        snapshot: RepositorySnapshot,
    ) -> bool:
        """
        Restore repository logical state atomically.

        A failed restore operation must never leave the repository
        partially restored. The previous logical state is captured
        before publication and re-applied if recovery fails.
        """

        if not self.validate_snapshot(snapshot):
            return False

        try:
            previous_snapshot = self.create_snapshot()
        except Exception:
            logger.exception(
                "Failed to capture pre-restore repository state"
            )
            return False

        try:
            self._apply_snapshot_state(snapshot)

            if not self.validate_integrity():
                raise ValueError(
                    "Restored repository state failed integrity "
                    "validation"
                )

            return True

        except Exception:
            logger.exception(
                "Failed to restore repository snapshot"
            )

            # Roll back through the same internal state loader used by
            # forward recovery. The public recovery API must never
            # re-enter itself.
            try:
                self._apply_snapshot_state(previous_snapshot)
            except Exception:
                logger.exception(
                    "Failed to roll back repository state"
                )

            return False

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

        if not self._is_valid_user_id(
            behavior_key[0]
        ):
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

            # Every physically stored representative pattern must have been recorded.
            if not pattern_ids.issubset(
                recorded_ids
            ):
                return False

            # A recorded pattern ID is allowed to exist without a corresponding
            # entry in _patterns when it represents a repeated behavioral occurrence.
            #
            # Repeated behavioral occurrences intentionally update the existing
            # behavioral knowledge record instead of creating another historical
            # representative pattern.

            # Representative and occurrence tracking must never overlap.
            if recorded_ids.intersection(
                self._recorded_occurrence_ids
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

            # Every stored FinalPattern must belong to a real user.
            for pattern in self._patterns.values():
                if not self._is_valid_user_id(
                    pattern.user_id
                ):
                    return False

            # Every user-indexed pattern must exist.
            for user_id, indexed_ids in (
                self._user_pattern_index.items()
            ):
                if not self._is_valid_user_id(
                    user_id
                ):
                    return False

                for pattern_id in indexed_ids:
                    if pattern_id not in self._patterns:
                        return False

                    pattern = self._patterns[
                        pattern_id
                    ]

                    if pattern.user_id != user_id:
                        return False

            # Every session reference must point to an accepted pattern
            # or recorded occurrence.
            for session_id, pattern_id in (
                self._session_pattern_index.items()
            ):
                if (
                    pattern_id not in self._patterns
                    and pattern_id not in self._recorded_occurrence_ids
                ):
                    return False

            # Every stored representative has a user-history reference.
            for pattern_id, pattern in (
                self._patterns.items()
            ):
                user_pattern_ids = self._user_pattern_index.get(
                    pattern.user_id,
                    [],
                )

                if pattern_id not in user_pattern_ids:
                    return False

            # Every baseline must point to an existing
            # representative FinalPattern.
            for user_id, baseline_pattern_id in (
                self._baseline_pattern_ids.items()
            ):
                if not self._is_valid_user_id(
                    user_id
                ):
                    return False

                if baseline_pattern_id not in self._patterns:
                    return False

                baseline_pattern = self._patterns[
                    baseline_pattern_id
                ]

                if baseline_pattern.user_id != user_id:
                    return False

                user_history = self._user_pattern_index.get(
                    user_id,
                    [],
                )

                if baseline_pattern_id not in user_history:
                    return False

            # Every user with historical patterns has a baseline.
            # A user entry without stored patterns is not a user with
            # historical patterns and is therefore not required to have
            # a baseline.
            for user_id, indexed_ids in (
                self._user_pattern_index.items()
            ):
                if not indexed_ids:
                    continue

                if user_id not in self._baseline_pattern_ids:
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

        This method creates the knowledge object but does not insert it
        into the repository's knowledge store. The caller is responsible
        for insertion to ensure atomic state publication.
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

        return knowledge

    def _record_repeated_behavior(
        self,
        representative_pattern_id: str,
        incoming_pattern: FinalPattern,
        incoming_key: BehavioralKey,
    ) -> bool:
        """
        Strengthen existing behavioral knowledge atomically.

        The historical FinalPattern is never mutated. If any part of
        repeated-occurrence recording fails, the existing knowledge state
        is restored and the operation reports failure.
        """

        representative_pattern = self._patterns.get(
            representative_pattern_id
        )

        if representative_pattern is None:
            return False

        if not self._is_valid_user_id(
            incoming_pattern.user_id
        ):
            return False

        if (
            representative_pattern.user_id
            != incoming_pattern.user_id
        ):
            return False

        knowledge_id = (
            f"knowledge-{representative_pattern_id}"
        )

        knowledge = self._knowledge.get(
            knowledge_id
        )

        if knowledge is None:
            logger.error(
                "Missing behavioral knowledge for representative %s",
                representative_pattern_id,
            )
            return False

        knowledge_snapshot = knowledge.snapshot()

        user_pattern_ids_snapshot = list(
            self._user_pattern_index.get(
                incoming_pattern.user_id,
                [],
            )
        )

        try:
            knowledge.record_occurrence(
                incoming_pattern.created_at
            )

            self._recorded_occurrence_ids.add(
                incoming_pattern.pattern_id
            )

            self._occurrence_behavior_keys[
                incoming_pattern.pattern_id
            ] = incoming_key

            user_pattern_ids = list(
                self._user_pattern_index.get(
                    incoming_pattern.user_id,
                    [],
                )
            )

            if representative_pattern_id not in user_pattern_ids:
                user_pattern_ids.append(
                    representative_pattern_id
                )

            self._user_pattern_index[
                incoming_pattern.user_id
            ] = user_pattern_ids

            self._session_pattern_index[
                incoming_pattern.session_id
            ] = incoming_pattern.pattern_id

            return True

        except Exception:
            self._knowledge[knowledge_id] = (
                knowledge_snapshot
            )

            self._recorded_occurrence_ids.discard(
                incoming_pattern.pattern_id
            )

            self._occurrence_behavior_keys.pop(
                incoming_pattern.pattern_id,
                None,
            )

            self._user_pattern_index[
                incoming_pattern.user_id
            ] = user_pattern_ids_snapshot

            # Only remove the session mapping if this operation
            # created it.
            if (
                self._session_pattern_index.get(
                    incoming_pattern.session_id
                )
                == incoming_pattern.pattern_id
            ):
                try:
                    del self._session_pattern_index[
                        incoming_pattern.session_id
                    ]
                except KeyError:
                    pass

            logger.exception(
                "Failed to record repeated behavior for "
                "representative %s",
                representative_pattern_id,
            )

            return False

    def _apply_snapshot_state(
        self,
        snapshot: RepositorySnapshot,
    ) -> None:
        """
        Publish repository logical state derived from a snapshot.

        This is the single internal state loader used by both forward
        recovery and deterministic rollback. Structural and integrity
        validation remain the responsibility of the public API, and this
        helper never re-enters the public recovery path.

        Every state container is fully materialized before any repository
        state is reassigned, so a failure while building state cannot
        leave the repository partially restored.
        """

        candidate_patterns = {
            pattern.pattern_id: copy.deepcopy(pattern)
            for pattern in snapshot.patterns
        }

        candidate_knowledge = {
            knowledge.knowledge_id: copy.deepcopy(knowledge)
            for knowledge in snapshot.knowledge
        }

        candidate_pattern_index = copy.deepcopy(
            snapshot.pattern_index
        )

        candidate_user_pattern_index = copy.deepcopy(
            snapshot.user_pattern_index
        )

        candidate_session_pattern_index = copy.deepcopy(
            snapshot.session_pattern_index
        )

        candidate_recorded_pattern_ids = set(
            snapshot.recorded_pattern_ids
        )

        candidate_recorded_occurrence_ids = set(
            snapshot.recorded_occurrence_ids
        )

        candidate_occurrence_behavior_keys = copy.deepcopy(
            snapshot.occurrence_behavior_keys
        )

        candidate_baseline_pattern_ids = copy.deepcopy(
            snapshot.baseline_pattern_ids
        )

        self._patterns = candidate_patterns
        self._pattern_index = candidate_pattern_index
        self._knowledge = candidate_knowledge
        self._user_pattern_index = candidate_user_pattern_index
        self._session_pattern_index = candidate_session_pattern_index
        self._recorded_pattern_ids = (
            candidate_recorded_pattern_ids
        )
        self._recorded_occurrence_ids = (
            candidate_recorded_occurrence_ids
        )
        self._occurrence_behavior_keys = (
            candidate_occurrence_behavior_keys
        )
        self._baseline_pattern_ids = (
            candidate_baseline_pattern_ids
        )

        # The search service holds live references to the published state
        # containers, so it must be rebuilt against the restored state in
        # order to resume normal operation after recovery.
        self._search_service = RepositorySearchService(
            patterns=self._patterns,
            pattern_index=self._pattern_index,
            knowledge=self._knowledge,
            behavioral_identity=self._behavioral_identity,
        )

    @staticmethod
    def _is_valid_user_id(
        user_id: Optional[str],
    ) -> bool:
        """
        Return True only for a real, non-blank user identity.

        The repository validates identity existence, not identity
        format.
        """

        return (
            isinstance(user_id, str)
            and bool(user_id.strip())
        )

    def _validate_pattern_reference(
        self,
        reference: PatternReference,
    ) -> bool:
        if reference is None:
            return False

        if not isinstance(
            reference,
            PatternReference,
        ):
            return False

        if not reference.pattern_id:
            return False

        if not reference.session_id:
            return False

        if not isinstance(
            reference.created_at,
            datetime,
        ):
            return False

        return True

    def _validate_final_pattern(
        self,
        pattern: FinalPattern,
    ) -> bool:
        if pattern is None:
            return False

        if not isinstance(pattern, FinalPattern):
            return False

        if not isinstance(pattern.pattern_id, str) or not pattern.pattern_id.strip():
            return False

        if not isinstance(pattern.session_id, str) or not pattern.session_id.strip():
            return False

        if not self._is_valid_user_id(
            pattern.user_id
        ):
            return False

        if not isinstance(pattern.created_at, datetime):
            return False

        if not isinstance(
            pattern.pattern_version,
            int,
        ):
            return False

        if pattern.pattern_version <= 0:
            return False

        if not isinstance(
            pattern.learning_metadata,
            dict,
        ):
            return False

        if not isinstance(pattern.observation_count, int):
            return False

        if pattern.observation_count <= 0:
            return False

        if pattern.observation_count != len(pattern.observations):
            return False

        if not isinstance(pattern.observations, list):
            return False

        if not pattern.observations:
            return False

        if any(not isinstance(observation, dict) for observation in pattern.observations):
            return False

        return True

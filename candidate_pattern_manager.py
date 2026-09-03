from __future__ import annotations

import copy

from datetime import datetime
from typing import Any, Dict, List, Optional

from candidate_pattern_models import (
    CandidatePattern,
    PatternStatus,
)


class CandidatePatternManager:
    """
    Manages active Candidate Patterns for running sessions.

    The manager owns creation, incremental evolution, and access
    to temporary active-session Candidate Pattern state.
    """

    def __init__(
        self,
        final_pattern_handler: Optional[Any] = None,
    ) -> None:
        """
        Initialize the Candidate Pattern Manager.
        """

        self._active_patterns: Dict[str, CandidatePattern] = {}
        self._final_pattern_handler = final_pattern_handler

    def createPattern(
        self,
        session_id: str,
        user_id: Optional[str] = None,
        session_start_time: Optional[datetime] = None,
    ) -> CandidatePattern:
        """
        Create and register a Candidate Pattern for a session.
        """

        if session_id in self._active_patterns:
            return self._active_patterns[session_id]

        if session_start_time is None:
            session_start_time = datetime.now()

        pattern = CandidatePattern(
            session_id=session_id,
            user_id=user_id,
            session_start_time=session_start_time,
        )

        self._active_patterns[session_id] = pattern

        return pattern

    def getCurrentPattern(
        self,
        session_id: str,
    ) -> Optional[CandidatePattern]:
        """
        Return the active Candidate Pattern for a session.

        Returns None when no active Candidate Pattern exists.
        """

        return self._active_patterns.get(session_id)

    def getPatternSnapshot(
        self,
        session_id: str,
    ) -> Optional[CandidatePattern]:
        """
        Return a detached snapshot of the current Candidate Pattern.

        The snapshot allows downstream consumers to inspect the
        current behavioral state without modifying the active pattern.
        """

        pattern = self.getCurrentPattern(session_id)

        if pattern is None:
            return None

        return copy.deepcopy(pattern)

    def updatePattern(
        self,
        session_id: str,
        observation: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        relationships: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[CandidatePattern]:
        pattern = self.getCurrentPattern(session_id)

        if pattern is None:
            return None

        if pattern.metadata.interrupted:
            return pattern

        if pattern.metadata.status == PatternStatus.COMPLETED:
            return pattern

        if not isinstance(observation, dict):
            return pattern

        previous_state = None

        try:
            if self._is_duplicate_observation(pattern, observation):
                return pattern

            self._validate_observation(observation)

            # Capture the complete state before any mutation occurs.
            previous_state = copy.deepcopy(pattern)

            pattern.add_observation(observation)

            self._update_operational_characteristics(
                pattern,
                observation,
            )

            self._update_temporal_characteristics(
                pattern,
                observation,
            )

            self._update_sequential_characteristics(
                pattern,
                observation,
            )

            if context:
                pattern.context.update(context)

                self._update_contextual_characteristics(
                    pattern,
                    context,
                )

            self._update_relationship_characteristics(
                pattern,
                relationships,
            )

            self._update_session_characteristics(pattern)

            if previous_state.metadata.status == PatternStatus.INITIALIZING:
                pattern.metadata.status = PatternStatus.LEARNING

            return pattern

        except Exception:
            if previous_state is not None:
                self._restore_pattern_state(
                    pattern,
                    previous_state,
                )

            return pattern

    def freezePattern(
        self,
        session_id: str,
    ) -> Optional[CandidatePattern]:
        """
        Freeze the latest valid Candidate Pattern for a session.

        Freezing preserves the current behavioral state without
        finalizing or persisting the pattern.
        """

        pattern = self.getCurrentPattern(session_id)

        if pattern is None:
            return None

        try:
            pattern.mark_interrupted()

            return pattern

        except Exception:
            return pattern

    def finalizePattern(
        self,
        session_id: str,
    ) -> Optional[CandidatePattern]:
        """
        Finalize the active Candidate Pattern.

        Finalization converts the evolving Candidate Pattern into a
        completed immutable state. Persistence and repository handoff
        are intentionally outside this operation.
        """

        pattern = self.getCurrentPattern(session_id)

        if pattern is None:
            return None

        if pattern.is_empty():
            return None

        if pattern.metadata.interrupted:
            return None

        if pattern.metadata.status == PatternStatus.COMPLETED:
            return pattern

        previous_status = pattern.metadata.status
        previous_complete = pattern.metadata.complete
        previous_finalized_at = pattern.metadata.finalized_at

        try:
            pattern.metadata.status = PatternStatus.FINALIZING

            pattern.mark_finalized()

            pattern.mark_completed()

            if not self._handoff_final_pattern(pattern):
                return pattern

            return pattern

        except Exception:
            pattern.metadata.status = previous_status
            pattern.metadata.complete = previous_complete
            pattern.metadata.finalized_at = previous_finalized_at

            return pattern

    def resetPattern(
        self,
        session_id: str,
    ) -> Optional[CandidatePattern]:
        """
        Remove and return the active Candidate Pattern for a session.

        Reset releases temporary active-session state. It does not
        modify historical patterns or perform persistence.
        """

        return self._active_patterns.pop(session_id, None)

    def _handoff_final_pattern(
        self,
        pattern: CandidatePattern,
    ) -> bool:
        """
        Hand off a successfully finalized Candidate Pattern to the
        downstream final-pattern consumer.

        Persistence remains outside the Candidate Pattern Manager.
        """

        if self._final_pattern_handler is None:
            return True

        try:
            result = self._final_pattern_handler(pattern)

            if result is False:
                return False

            return True

        except Exception:
            return False

    def _is_duplicate_observation(
        self,
        pattern: CandidatePattern,
        observation: Dict[str, Any],
    ) -> bool:
        """
        Determine whether an observation already exists.

        Duplicate detection is intentionally limited to exact
        observation equality.
        """

        return observation in pattern.timeline.observations

    def _validate_observation(
        self,
        observation: Dict[str, Any],
    ) -> None:
        """
        Validate the minimum structure required for an observation.
        """

        if not observation:
            raise ValueError("Observation cannot be empty")

        if "timestamp" not in observation:
            raise ValueError("Observation must contain a timestamp")

    def _restore_pattern_state(
        self,
        pattern: CandidatePattern,
        snapshot: CandidatePattern,
    ) -> None:
        """
        Restore a Candidate Pattern to its exact state before
        a failed update.

        The original pattern object is preserved so callers holding
        a reference to it continue to receive the same object.
        """
        pattern.__dict__.clear()
        pattern.__dict__.update(
            copy.deepcopy(snapshot.__dict__)
        )

    def _update_operational_characteristics(
        self,
        pattern: CandidatePattern,
        observation: Dict[str, Any],
    ) -> None:
        """
        Incrementally update operational characteristics from an
        interpreted behavioral observation.
        """

        operation_type = observation.get("operation_type")

        characteristics = pattern.operational_characteristics

        total_operations = characteristics.get(
            "total_operations",
            0,
        )

        characteristics["total_operations"] = total_operations + 1

        operation_counts = characteristics.setdefault(
            "operation_counts",
            {},
        )

        if operation_type is not None:
            operation_counts[operation_type] = (
                operation_counts.get(operation_type, 0) + 1
            )

        characteristics["unique_operation_types"] = len(
            operation_counts
        )

    def _update_temporal_characteristics(
        self,
        pattern: CandidatePattern,
        observation: Dict[str, Any],
    ) -> None:
        """
        Incrementally update temporal characteristics from an
        interpreted behavioral observation.
        """

        timestamp = observation.get("timestamp")

        if timestamp is None:
            return

        characteristics = pattern.temporal_characteristics

        first_timestamp = characteristics.get(
            "first_observation_time"
        )

        last_timestamp = characteristics.get(
            "last_observation_time"
        )

        if first_timestamp is None:
            characteristics["first_observation_time"] = timestamp
        elif timestamp < first_timestamp:
            characteristics["first_observation_time"] = timestamp

        if last_timestamp is None:
            characteristics["last_observation_time"] = timestamp
        elif timestamp > last_timestamp:
            characteristics["last_observation_time"] = timestamp

        first_timestamp = characteristics.get(
            "first_observation_time"
        )

        last_timestamp = characteristics.get(
            "last_observation_time"
        )

        if first_timestamp is not None and last_timestamp is not None:
            characteristics["duration_seconds"] = (
                last_timestamp - first_timestamp
            ).total_seconds()

    def _update_sequential_characteristics(
        self,
        pattern: CandidatePattern,
        observation: Dict[str, Any],
    ) -> None:
        """
        Incrementally update sequential characteristics from an
        interpreted behavioral observation.
        """

        operation_type = observation.get("operation_type")

        if operation_type is None:
            return

        sequence_entry = {
            "operation_type": operation_type,
            "timestamp": observation.get("timestamp"),
        }

        pattern.sequential_characteristics.append(
            sequence_entry
        )

    def _update_contextual_characteristics(
        self,
        pattern: CandidatePattern,
        context: Optional[Dict[str, Any]],
    ) -> None:
        """
        Incrementally update contextual characteristics from the
        latest behavioral context.
        """

        if not context:
            return

        pattern.contextual_characteristics.update(context)

    def _update_relationship_characteristics(
        self,
        pattern: CandidatePattern,
        relationships: Optional[List[Dict[str, Any]]],
    ) -> None:
        """
        Incrementally incorporate interpreted behavioral relationships
        into the Candidate Pattern.
        """

        if not relationships:
            return

        for relationship in relationships:
            if not isinstance(relationship, dict):
                continue

            if relationship not in pattern.relationship_characteristics:
                pattern.relationship_characteristics.append(
                    relationship.copy()
                )

    def _update_session_characteristics(
        self,
        pattern: CandidatePattern,
    ) -> None:
        """
        Incrementally update session-level characteristics of the
        Candidate Pattern.
        """

        characteristics = pattern.session_characteristics

        characteristics["session_id"] = pattern.session_id
        characteristics["user_id"] = pattern.user_id
        characteristics["session_start_time"] = (
            pattern.session_start_time
        )
        characteristics["observation_count"] = (
            pattern.observation_count()
        )

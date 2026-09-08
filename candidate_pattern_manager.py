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

    def getBehavioralSummary(
        self,
        session_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Return a detached behavioral summary of the active
        Candidate Pattern.

        This is read-only output for downstream behavioral
        intelligence components.
        """

        pattern = self.getCurrentPattern(session_id)

        if pattern is None:
            return None

        return {
            "session_id": pattern.session_id,
            "user_id": pattern.user_id,
            "session_start_time": pattern.session_start_time,
            "session_end_time": pattern.session_end_time,
            "session_duration_seconds": (
                pattern.session_duration_seconds
            ),
            "observation_count": pattern.observation_count(),
            "operational_characteristics": copy.deepcopy(
                pattern.operational_characteristics
            ),
            "temporal_characteristics": copy.deepcopy(
                pattern.temporal_characteristics
            ),
            "sequential_characteristics": copy.deepcopy(
                pattern.sequential_characteristics
            ),
            "contextual_characteristics": copy.deepcopy(
                pattern.contextual_characteristics
            ),
            "relationship_characteristics": copy.deepcopy(
                pattern.relationship_characteristics
            ),
            "session_characteristics": copy.deepcopy(
                pattern.session_characteristics
            ),
        }

    def getPatternMetadata(
        self,
        session_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Return detached metadata describing the current
        Candidate Pattern state.

        Downstream modules receive a read-only representation.
        """

        pattern = self.getCurrentPattern(session_id)

        if pattern is None:
            return None

        metadata = pattern.metadata

        return {
            "status": metadata.status,
            "observation_count": metadata.observation_count,
            "complete": metadata.complete,
            "interrupted": metadata.interrupted,
            "finalized_at": metadata.finalized_at,
            "session_start_time": pattern.session_start_time,
            "session_end_time": pattern.session_end_time,
            "session_duration_seconds": (
                pattern.session_duration_seconds
            ),
        }

    def getEvaluationSnapshot(
        self,
        session_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Return a detached evaluation view of the active
        Candidate Pattern.

        This combines the read-only outputs required by the
        evaluation stage without allowing downstream modules
        to modify active Candidate Pattern state.
        """

        pattern = self.getCurrentPattern(session_id)

        if pattern is None:
            return None

        return {
            "candidate_pattern": copy.deepcopy(pattern),
            "behavioral_summary": self.getBehavioralSummary(
                session_id
            ),
            "pattern_metadata": self.getPatternMetadata(
                session_id
            ),
        }

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

            if not self._is_chronologically_valid(
                pattern,
                observation,
            ):
                return pattern

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
                self._refine_context(
                    pattern,
                    context,
                )

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

    def completeSession(
        self,
        session_id: str,
        session_end_time: Optional[datetime] = None,
    ) -> Optional[CandidatePattern]:
        """
        Mark the active session as completed and record its
        end time and duration.

        This method records session completion but does not
        persist or hand off the Final Pattern by itself.
        """

        pattern = self.getCurrentPattern(session_id)

        if pattern is None:
            return None

        if pattern.metadata.interrupted:
            return pattern

        if pattern.metadata.status == PatternStatus.COMPLETED:
            return pattern

        if session_end_time is None:
            session_end_time = datetime.now()

        if (
            pattern.session_start_time is not None
            and session_end_time < pattern.session_start_time
        ):
            return pattern

        pattern.session_end_time = session_end_time

        if pattern.session_start_time is not None:
            pattern.session_duration_seconds = (
                session_end_time
                - pattern.session_start_time
            ).total_seconds()
        else:
            pattern.session_duration_seconds = 0.0

        pattern.temporal_characteristics[
            "session_end_time"
        ] = session_end_time

        pattern.temporal_characteristics[
            "session_duration_seconds"
        ] = pattern.session_duration_seconds

        pattern.session_characteristics[
            "session_end_time"
        ] = session_end_time

        pattern.session_characteristics[
            "session_length_seconds"
        ] = pattern.session_duration_seconds

        return pattern

    def finalizePattern(
        self,
        session_id: str,
    ) -> Optional[CandidatePattern]:
        """
        Finalize the active Candidate Pattern.

        If the session has not already been explicitly completed,
        finalization records the current time as the session end.

        Empty or interrupted sessions cannot produce Final Patterns.
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
        previous_session_end = pattern.session_end_time
        previous_session_duration = (
            pattern.session_duration_seconds
        )
        previous_temporal = copy.deepcopy(
            pattern.temporal_characteristics
        )
        previous_session_characteristics = copy.deepcopy(
            pattern.session_characteristics
        )

        try:
            if pattern.session_end_time is None:
                self.completeSession(session_id)

            if pattern.session_end_time is None:
                return pattern

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
            pattern.session_end_time = previous_session_end
            pattern.session_duration_seconds = (
                previous_session_duration
            )

            pattern.temporal_characteristics.clear()
            pattern.temporal_characteristics.update(
                previous_temporal
            )

            pattern.session_characteristics.clear()
            pattern.session_characteristics.update(
                previous_session_characteristics
            )

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

    def _is_chronologically_valid(
        self,
        pattern: CandidatePattern,
        observation: Dict[str, Any],
    ) -> bool:
        """
        Verify that a new behavioral observation does not move
        the Candidate Pattern backwards in time.

        Candidate Pattern evolution is chronological.
        Historical observations are never reordered.
        """

        timestamp = observation.get("timestamp")

        if timestamp is None:
            return False

        if not pattern.timeline.observations:
            return True

        last_observation = pattern.timeline.observations[-1]
        last_timestamp = last_observation.get("timestamp")

        if last_timestamp is None:
            return True

        return timestamp >= last_timestamp

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
        Incrementally maintain operational characteristics.

        Tracks:
        - total operations
        - operation counts
        - operation frequencies
        - operation distribution
        - unique operation types

        Existing behavioral knowledge is retained and only
        extended/refined by each accepted observation.
        """

        operation_type = observation.get("operation_type")

        characteristics = pattern.operational_characteristics

        total_operations = (
            characteristics.get(
                "total_operations",
                0,
            )
            + 1
        )

        characteristics["total_operations"] = (
            total_operations
        )

        operation_counts = characteristics.setdefault(
            "operation_counts",
            {},
        )

        if operation_type is None:
            characteristics["unique_operation_types"] = len(
                operation_counts
            )
            return

        operation_type = str(operation_type)

        operation_counts[operation_type] = (
            operation_counts.get(
                operation_type,
                0,
            )
            + 1
        )

        characteristics["unique_operation_types"] = len(
            operation_counts
        )

        # Frequency represents the number of occurrences
        # of every operation type.
        characteristics["operation_frequency"] = (
            dict(operation_counts)
        )

        # Distribution represents the normalized proportion
        # of every operation type within the session so far.
        operation_distribution = {}

        for current_operation, count in operation_counts.items():
            operation_distribution[current_operation] = (
                count / total_operations
            )

        characteristics["operation_distribution"] = (
            operation_distribution
        )

    def _update_temporal_characteristics(
        self,
        pattern: CandidatePattern,
        observation: Dict[str, Any],
    ) -> None:
        """
        Incrementally maintain temporal behavioral characteristics.

        The Candidate Pattern tracks:
        - observation timing
        - time between operations
        - session duration
        - active time
        - idle time
        - burst activity
        - continuous activity
        - working rhythm

        Updates are incremental and preserve chronological history.
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

        # First behavioral observation.
        if first_timestamp is None:
            characteristics["first_observation_time"] = timestamp
            characteristics["last_observation_time"] = timestamp

            characteristics["time_between_operations"] = []
            characteristics["idle_intervals"] = []
            characteristics["operation_intervals"] = []

            characteristics["active_time_seconds"] = 0.0
            characteristics["idle_time_seconds"] = 0.0
            characteristics["duration_seconds"] = 0.0

            characteristics["burst_count"] = 0
            characteristics["continuous_activity"] = False
            characteristics["working_rhythm"] = {
                "observation_count": 1,
                "average_interval_seconds": 0.0,
                "min_interval_seconds": 0.0,
                "max_interval_seconds": 0.0,
            }

            return

        # Chronological validation is already enforced by
        # CandidatePatternManager.updatePattern().
        if timestamp < last_timestamp:
            return

        interval_seconds = (
            timestamp - last_timestamp
        ).total_seconds()

        characteristics.setdefault(
            "time_between_operations",
            [],
        ).append(interval_seconds)

        characteristics.setdefault(
            "operation_intervals",
            [],
        ).append(interval_seconds)

        # Update session bounds.
        characteristics["last_observation_time"] = timestamp

        duration_seconds = (
            timestamp
            - first_timestamp
        ).total_seconds()

        characteristics["duration_seconds"] = duration_seconds

        # Treat an interval as idle when it exceeds the
        # inactivity threshold supplied by the observation.
        idle_threshold = observation.get(
            "idle_threshold_seconds",
            60.0,
        )

        try:
            idle_threshold = float(idle_threshold)
        except (TypeError, ValueError):
            idle_threshold = 60.0

        if interval_seconds > idle_threshold:
            characteristics.setdefault(
                "idle_intervals",
                [],
            ).append(interval_seconds)

            characteristics["idle_time_seconds"] = (
                characteristics.get(
                    "idle_time_seconds",
                    0.0,
                )
                + interval_seconds
            )
        else:
            characteristics["active_time_seconds"] = (
                characteristics.get(
                    "active_time_seconds",
                    0.0,
                )
                + interval_seconds
            )

        intervals = characteristics.get(
            "time_between_operations",
            [],
        )

        if intervals:
            average_interval = (
                sum(intervals)
                / len(intervals)
            )

            min_interval = min(intervals)
            max_interval = max(intervals)
        else:
            average_interval = 0.0
            min_interval = 0.0
            max_interval = 0.0

        characteristics["working_rhythm"] = {
            "observation_count": pattern.observation_count(),
            "average_interval_seconds": average_interval,
            "min_interval_seconds": min_interval,
            "max_interval_seconds": max_interval,
        }

        # A burst is a short interval between consecutive
        # behavioral observations.
        burst_threshold = observation.get(
            "burst_threshold_seconds",
            5.0,
        )

        try:
            burst_threshold = float(
                burst_threshold
            )
        except (TypeError, ValueError):
            burst_threshold = 5.0

        if interval_seconds <= burst_threshold:
            characteristics["burst_count"] = (
                characteristics.get(
                    "burst_count",
                    0,
                )
                + 1
            )

        characteristics["burst_activity"] = (
            characteristics.get(
                "burst_count",
                0,
            )
            > 0
        )

        characteristics["continuous_activity"] = (
            len(intervals) > 0
            and all(
                interval <= idle_threshold
                for interval in intervals
            )
        )

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

    def _refine_context(
        self,
        pattern: CandidatePattern,
        context: Dict[str, Any],
    ) -> None:
        """
        Incrementally refine contextual understanding.

        The latest contextual value remains directly accessible,
        while previous contextual observations are preserved in
        refinement history.

        Existing contextual knowledge is never discarded.
        """

        if not context:
            return

        for key, new_value in context.items():
            history_key = f"{key}__history"
            count_key = f"{key}__observation_count"

            history = pattern.context.values.setdefault(
                history_key,
                [],
            )

            observation_count = pattern.context.values.get(
                count_key,
                0,
            )

            if not history:
                history.append(
                    {
                        "value": copy.deepcopy(new_value),
                        "superseded_by": None,
                    }
                )
            else:
                previous_entry = history[-1]

                if previous_entry["value"] != new_value:
                    previous_entry["superseded_by"] = (
                        copy.deepcopy(new_value)
                    )

                    history.append(
                        {
                            "value": copy.deepcopy(new_value),
                            "superseded_by": None,
                        }
                    )

            pattern.context.values[key] = (
                copy.deepcopy(new_value)
            )

            pattern.context.values[count_key] = (
                observation_count + 1
            )

    def _update_contextual_characteristics(
        self,
        pattern: CandidatePattern,
        context: Optional[Dict[str, Any]],
    ) -> None:
        """
        Maintain the latest contextual characteristics.

        Contextual characteristics remain a direct representation
        of the latest contextual understanding.

        Historical refinement information is maintained separately
        inside BehavioralContext.
        """

        if not context:
            return

        for key, value in context.items():
            pattern.contextual_characteristics[key] = (
                copy.deepcopy(value)
            )

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
        Incrementally maintain session-level behavioral
        characteristics.
        """

        characteristics = pattern.session_characteristics

        observation_count = pattern.observation_count()

        characteristics["session_id"] = pattern.session_id
        characteristics["user_id"] = pattern.user_id

        characteristics["session_start_time"] = (
            pattern.session_start_time
        )

        characteristics["observation_count"] = (
            observation_count
        )

        temporal = pattern.temporal_characteristics

        characteristics["session_length_seconds"] = (
            temporal.get(
                "duration_seconds",
                0.0,
            )
        )

        operation_counts = pattern.operational_characteristics.get(
            "operation_counts",
            {},
        )

        characteristics["operation_diversity"] = len(
            operation_counts
        )

        duration_seconds = temporal.get(
            "duration_seconds",
            0.0,
        )

        if duration_seconds > 0:
            characteristics["behavioral_density"] = (
                observation_count
                / duration_seconds
            )
        else:
            characteristics["behavioral_density"] = (
                float(observation_count)
            )

        if observation_count <= 1:
            characteristics["behavioral_consistency"] = 1.0
        else:
            intervals = temporal.get(
                "time_between_operations",
                [],
            )

            if not intervals:
                characteristics[
                    "behavioral_consistency"
                ] = 1.0
            else:
                average_interval = (
                    sum(intervals)
                    / len(intervals)
                )

                if average_interval == 0:
                    consistency = 1.0
                else:
                    deviation = sum(
                        abs(
                            interval
                            - average_interval
                        )
                        for interval in intervals
                    ) / len(intervals)

                    consistency = max(
                        0.0,
                        1.0
                        - (
                            deviation
                            / average_interval
                        ),
                    )

                characteristics[
                    "behavioral_consistency"
                ] = consistency

        # Task complexity is represented as the number of
        # distinct operation types and the number of
        # observed behavioral relationships.
        relationship_count = len(
            pattern.relationship_characteristics
        )

        characteristics["task_complexity"] = {
            "operation_diversity": (
                characteristics[
                    "operation_diversity"
                ]
            ),
            "relationship_count": relationship_count,
        }

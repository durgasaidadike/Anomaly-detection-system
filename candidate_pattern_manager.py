from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

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

    def __init__(self) -> None:
        """
        Initialize the Candidate Pattern Manager.
        """

        self._active_patterns: Dict[str, CandidatePattern] = {}

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

    def updatePattern(
        self,
        session_id: str,
        observation: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[CandidatePattern]:
        """
        Incrementally update the active Candidate Pattern.

        The observation must represent interpreted behavioral
        information rather than a raw filesystem event.
        """

        pattern = self.getCurrentPattern(session_id)

        if pattern is None:
            return None

        if not isinstance(observation, dict):
            return pattern

        try:
            if self._is_duplicate_observation(pattern, observation):
                return pattern

            self._validate_observation(observation)

            previous_status = pattern.metadata.status

            pattern.add_observation(observation)

            if context:
                pattern.context.update(context)

            if previous_status == PatternStatus.INITIALIZING:
                pattern.metadata.status = PatternStatus.LEARNING

            return pattern

        except Exception:
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

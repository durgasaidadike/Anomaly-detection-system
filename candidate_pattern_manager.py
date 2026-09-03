from __future__ import annotations

from datetime import datetime
from typing import Dict, Optional

from candidate_pattern_models import CandidatePattern


class CandidatePatternManager:
    """
    Manages active Candidate Patterns for running sessions.

    The manager owns creation of Candidate Patterns and keeps
    temporary active-session state in memory.
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
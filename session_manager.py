
from __future__ import annotations
import logging
from datetime import datetime, timezone
from typing import Callable, Dict, Optional
from uuid import uuid4

from session_models import Session, SessionMetadata
logger = logging.getLogger(__name__)

class SessionManager:
    """
    PRISM Module 03 - Session Manager.

    Converts normalized filesystem events into contextual
    behavioral sessions.

    Responsibilities:
    - Create sessions.
    - Track active sessions.
    - Update active sessions.
    - Maintain session metadata.
    - Detect session completion.
    - Forward sessions to the Behavior Analyzer.

    This module does NOT:
    - Perform anomaly detection.
    - Perform ML inference.
    - Build behavioral patterns.
    - Persist historical sessions.
    - Access MongoDB.
    """

    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"

    def __init__(
        self,
        idle_timeout_seconds: Optional[float] = None,
        session_sink: Optional[Callable[[Session], None]] = None
    ):
        """
        Initialize the Session Manager.

        idle_timeout_seconds is intentionally configurable.
        The Session Manager does not assume an architectural
        timeout value that is not defined by the specification.
        """
        self.idle_timeout_seconds = idle_timeout_seconds
        self.session_sink = session_sink
        self.active_sessions: Dict[str, Session] = {}

    @staticmethod
    def _generate_session_id() -> str:
        """
        Generate a unique identifier for a new session.
        """

        return str(uuid4())

    def create_session(
        self,
        event,
        timestamp: Optional[datetime] = None
    ) -> Session:
        """
        Create a new active session from a normalized event.
        """

        event_timestamp = timestamp or getattr(
            event,
            "timestamp",
            None
        )

        if event_timestamp is None:
            event_timestamp = datetime.now(timezone.utc)

        session_id = self._generate_session_id()

        metadata = SessionMetadata(
            session_id=session_id,
            start_time=event_timestamp,
            last_activity=event_timestamp,
            event_count=0,
            status=self.ACTIVE
        )

        session = Session(
            metadata=metadata
        )

        session.append_event(
            event,
            event_timestamp
        )
        self.forward_session(session)

        self.active_sessions[session_id] = session

        return session

    def get_active_session(
        self,
        session_id: str
    ) -> Optional[Session]:
        """
        Return an active session by its identifier.
        """

        return self.active_sessions.get(session_id)

    def forward_session(self, session: Session) -> None:
        """
        Forward a session to the configured downstream consumer.

        The Session Manager does not know whether the consumer is
        the Behavior Analyzer or another integration component.
        """

        if self.session_sink is None:
            return

        self.session_sink(session)

    def update_session(
        self,
        session_id: str,
        event,
        timestamp: Optional[datetime] = None
    ) -> Optional[Session]:
        """
        Add a normalized event to an existing active session.

        Returns:
            Updated Session if successful.
            None if the session does not exist or an update fails.
        """

        session = self.get_active_session(session_id)

        if session is None:
            logger.warning(
                "Cannot update session '%s': session not found.",
                session_id
            )
            return None

        if session.metadata.status != self.ACTIVE:
            logger.warning(
                "Cannot update session '%s': session is not active.",
                session_id
            )
            return None

        event_timestamp = timestamp or getattr(
            event,
            "timestamp",
            None
        )

        if event_timestamp is None:
            event_timestamp = datetime.now(timezone.utc)

        try:
            session.append_event(
                event,
                event_timestamp
            )

            self.forward_session(session)

            return session

        except Exception:
            logger.exception(
                "Failed to update session '%s'. "
                "Active session has been preserved.",
                session_id
            )
            return None

    def process_event(
        self,
        event,
        session_id: Optional[str] = None
    ) -> Session:
        """
        Process a normalized event.

        If a valid active session_id is supplied, the event
        is appended to that session.

        Otherwise, a new session is created.
        """

        if session_id is not None:
            session = self.update_session(
                session_id,
                event
            )

            if session is not None:
                return session

        return self.create_session(event)

    def close_session(
        self,
        session_id: str,
        end_time: Optional[datetime] = None
    ) -> Optional[Session]:
        """
        Complete an active session.

        The completed session is removed from the active-session
        registry and returned to the caller for downstream
        processing.
        """

        session = self.get_active_session(session_id)

        if session is None:
            return None

        if session.metadata.status != self.ACTIVE:
            return None

        completion_time = end_time or session.metadata.last_activity

        session.metadata.end_time = completion_time
        session.metadata.status = self.COMPLETED
        del self.active_sessions[session_id]

        self.forward_session(session)

        return session

    def close_corrupted_session(
        self,
        session_id: str
    ) -> Optional[Session]:
        """
        Safely close an invalid or corrupted active session.

        The session is removed from active session tracking,
        marked as completed, and forwarded downstream.
        """

        session = self.get_active_session(session_id)

        if session is None:
            logger.warning(
                "Cannot close corrupted session '%s': "
                "session not found.",
                session_id
            )
            return None

        try:
            session.metadata.status = self.COMPLETED
            session.metadata.end_time = session.metadata.last_activity

            del self.active_sessions[session_id]

            self.forward_session(session)

            logger.warning(
                "Corrupted session '%s' was safely closed.",
                session_id
            )

            return session

        except Exception:
            logger.exception(
                "Failed to safely close corrupted session '%s'.",
                session_id
            )
            return None

    def is_session_expired(
        self,
        session: Session,
        current_time: Optional[datetime] = None
    ) -> bool:
        """
        Determine whether a session has exceeded the configured
        idle timeout.

        Returns False when no idle timeout has been configured.
        """

        if self.idle_timeout_seconds is None:
            return False

        if session.metadata.status != self.ACTIVE:
            return False

        now = current_time or datetime.now(timezone.utc)

        idle_duration = (
            now - session.metadata.last_activity
        ).total_seconds()

        return idle_duration >= self.idle_timeout_seconds

    def check_expired_sessions(
        self,
        current_time: Optional[datetime] = None
    ) -> list[Session]:
        """
        Close all active sessions that have exceeded the
        configured idle timeout.

        Returns:
            List of sessions that were completed.
        """

        if self.idle_timeout_seconds is None:
            return []

        now = current_time or datetime.now(timezone.utc)

        expired_sessions = []

        for session_id, session in list(
            self.active_sessions.items()
        ):
            if self.is_session_expired(
                session,
                now
            ):
                completed = self.close_session(
                    session_id,
                    now
                )

                if completed is not None:
                    expired_sessions.append(completed)

        return expired_sessions
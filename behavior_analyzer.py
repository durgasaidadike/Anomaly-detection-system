from __future__ import annotations

import logging
from collections import Counter
from typing import Any, Dict, List, Optional

from session_models import Session, SessionMetadata


logger = logging.getLogger(__name__)


class BehaviorAnalyzer:
    """
    PRISM Module 04 - Behavior Analyzer.

    Interprets completed or active user sessions and converts
    filesystem activity into behavioral understanding.

    Responsibilities:
    - Interpret session activity.
    - Analyze behavioral context.
    - Generate behavioral signals.
    - Extract behavioral characteristics.
    - Produce a session behavior summary.

    This module does NOT:
    - Perform ML inference.
    - Make final anomaly decisions.
    - Create final patterns.
    - Persist behavioral history.
    - Access MongoDB.
    """

    def __init__(
        self,
        observation_sink: Optional[Any] = None,
    ):
        """
        Initialize the Behavior Analyzer.

        observation_sink is an optional downstream handoff
        supplied by the orchestration layer.
        """
        self.observation_sink = observation_sink

    def forward_observation(
        self,
        observation: Dict[str, Any],
    ) -> bool:
        """
        Forward a behavioral observation to the downstream
        Candidate Pattern Manager boundary.

        Returns True when forwarding succeeds or when no sink
        has been configured.
        """
        if self.observation_sink is None:
            return True

        try:
            self.observation_sink(observation)
            return True

        except Exception:
            logger.exception(
                "Failed to forward behavioral observation for session '%s'.",
                observation.get("session_id"),
            )
            return False

    def analyzeSession(
        self,
        session: Session,
        metadata: Optional[SessionMetadata] = None,
    ) -> Dict[str, Any]:
        """
        Analyze a session and return behavioral understanding.

        Partial behavioral information is returned whenever possible.
        """
        result: Dict[str, Any] = {
            "session_id": self._get_session_id(session),
            "behavioral_signals": [],
            "behavioral_context": {},
            "session_behavior_summary": {},
        }

        try:
            result["behavioral_context"] = self._interpret_context(
                session,
                metadata,
            )
        except Exception:
            logger.exception(
                "Failed to interpret behavioral context for session '%s'.",
                self._get_session_id(session),
            )

        try:
            result["behavioral_signals"] = self.generateBehaviorSignals(
                session,
                metadata,
            )
        except Exception:
            logger.exception(
                "Failed to generate behavioral signals for session '%s'.",
                self._get_session_id(session),
            )

        try:
            result["session_behavior_summary"] = self.summarizeBehavior(
                session,
                metadata,
            )
        except Exception:
            logger.exception(
                "Failed to summarize behavior for session '%s'.",
                self._get_session_id(session),
            )

        try:
            self.forward_observation(result)
        except Exception:
            logger.exception(
                "Unexpected error while forwarding observation for session '%s'.",
                self._get_session_id(session),
            )

        return result

    def _interpret_context(
        self,
        session: Session,
        metadata: Optional[SessionMetadata] = None,
    ) -> Dict[str, Any]:
        """
        Extract behavioral context from the session.

        This method describes what happened during the session.
        It does not determine whether the behavior is normal or
        abnormal.
        """
        events = self._get_events(session)

        context: Dict[str, Any] = {
            "event_count": len(events),
            "operation_types": [],
            "unique_paths": 0,
            "unique_extensions": [],
            "directories": [],
        }

        if not events:
            context["session_state"] = "EMPTY"
            return context

        operation_types = Counter()
        paths = set()
        extensions = set()
        directories = set()

        for event in events:
            event_type = self._get_value(
                event,
                "event_type",
                "operation_type",
            )

            if event_type:
                operation_types[str(event_type)] += 1

            source_path = self._get_value(
                event,
                "source_path",
                "file_path",
            )

            destination_path = self._get_value(
                event,
                "destination_path",
            )

            if source_path:
                paths.add(str(source_path))

            if destination_path:
                paths.add(str(destination_path))

            extension = self._get_value(
                event,
                "extension",
                "file_extension",
            )

            if extension:
                extensions.add(str(extension).lower())

            directory = self._get_value(
                event,
                "directory",
            )

            if directory:
                directories.add(str(directory))

        context["operation_types"] = dict(operation_types)
        context["unique_paths"] = len(paths)
        context["unique_extensions"] = sorted(extensions)
        context["directories"] = sorted(directories)
        context["session_state"] = self._session_state(session)

        return context

    @staticmethod
    def _get_events(session: Session) -> List[Any]:
        """
        Safely retrieve the events associated with a session.
        """
        events = getattr(session, "events", None)

        if events is None:
            return []

        return list(events)

    @staticmethod
    def _get_value(
        event: Any,
        *field_names: str,
    ) -> Any:
        """
        Read a field from either an object or mapping.

        This keeps the analyzer tolerant of the normalized
        event representation used by upstream modules.
        """
        for field_name in field_names:
            if isinstance(event, dict):
                if field_name in event:
                    return event[field_name]

            value = getattr(event, field_name, None)

            if value is not None:
                return value

        return None

    @staticmethod
    def _session_state(session: Session) -> str:
        """
        Return the current session state from session metadata.
        """
        return BehaviorAnalyzer._get_session_status(session)

    @staticmethod
    def _get_session_id(session: Session) -> Optional[str]:
        """
        Safely retrieve the session identifier from session metadata.
        """
        metadata = getattr(session, "metadata", None)

        if metadata is None:
            return None

        return getattr(metadata, "session_id", None)

    @staticmethod
    def _get_session_status(session: Session) -> str:
        """
        Safely retrieve the session status from session metadata.
        """
        metadata = getattr(session, "metadata", None)

        if metadata is None:
            return "UNKNOWN"

        return str(
            getattr(
                metadata,
                "status",
                "UNKNOWN",
            )
        )

    def generateBehaviorSignals(
        self,
        session: Session,
        metadata: Optional[SessionMetadata] = None,
    ) -> List[Dict[str, Any]]:
        """
        Generate descriptive behavioral signals from a session.

        Signals describe observable characteristics of the session.
        They are not anomaly decisions or ML scores.
        """
        events = self._get_events(session)

        if not events:
            return [
                {
                    "signal_type": "EMPTY_SESSION",
                    "value": True,
                    "description": "Session contains no events.",
                }
            ]

        signals: List[Dict[str, Any]] = []

        operation_counts = Counter()
        extensions = set()
        directories = set()

        for event in events:
            event_type = self._get_value(
                event,
                "event_type",
                "operation_type",
            )

            if event_type:
                operation_counts[str(event_type)] += 1

            extension = self._get_value(
                event,
                "extension",
                "file_extension",
            )

            if extension:
                extensions.add(str(extension).lower())

            directory = self._get_value(
                event,
                "directory",
            )

            if directory:
                directories.add(str(directory))

        for operation_type, count in operation_counts.items():
            signals.append(
                {
                    "signal_type": "OPERATION_ACTIVITY",
                    "operation_type": operation_type,
                    "count": count,
                }
            )

        if len(extensions) == 1:
            signals.append(
                {
                    "signal_type": "EXTENSION_CONCENTRATION",
                    "extension_count": 1,
                    "extensions": sorted(extensions),
                }
            )
        elif len(extensions) > 1:
            signals.append(
                {
                    "signal_type": "EXTENSION_DIVERSITY",
                    "extension_count": len(extensions),
                    "extensions": sorted(extensions),
                }
            )

        if len(directories) == 1:
            signals.append(
                {
                    "signal_type": "DIRECTORY_CONCENTRATION",
                    "directory_count": 1,
                }
            )
        elif len(directories) > 1:
            signals.append(
                {
                    "signal_type": "DIRECTORY_DIVERSITY",
                    "directory_count": len(directories),
                }
            )

        if len(events) == 1:
            signals.append(
                {
                    "signal_type": "SHORT_SESSION",
                    "event_count": 1,
                }
            )

        return signals

    def summarizeBehavior(
        self,
        session: Session,
        metadata: Optional[SessionMetadata] = None,
    ) -> Dict[str, Any]:
        """
        Build a compact behavioral summary for downstream processing.

        The summary describes the session and does not make an
        anomaly or risk decision.
        """
        events = self._get_events(session)

        if not events:
            return {
                "session_id": self._get_session_id(session),
                "event_count": 0,
                "session_state": "EMPTY",
                "primary_operations": [],
                "characteristics": {},
            }

        operation_counts = Counter()
        unique_paths = set()
        unique_extensions = set()
        unique_directories = set()

        for event in events:
            event_type = self._get_value(
                event,
                "event_type",
                "operation_type",
            )

            if event_type:
                operation_counts[str(event_type)] += 1

            source_path = self._get_value(
                event,
                "source_path",
                "file_path",
            )

            destination_path = self._get_value(
                event,
                "destination_path",
            )

            if source_path:
                unique_paths.add(str(source_path))

            if destination_path:
                unique_paths.add(str(destination_path))

            extension = self._get_value(
                event,
                "extension",
                "file_extension",
            )

            if extension:
                unique_extensions.add(str(extension).lower())

            directory = self._get_value(
                event,
                "directory",
            )

            if directory:
                unique_directories.add(str(directory))

        primary_operations = [
            operation
            for operation, _ in operation_counts.most_common()
        ]

        return {
            "session_id": self._get_session_id(session),
            "event_count": len(events),
            "session_state": self._session_state(session),
            "primary_operations": primary_operations,
            "characteristics": {
                "operation_counts": dict(operation_counts),
                "unique_paths": len(unique_paths),
                "unique_extensions": sorted(unique_extensions),
                "unique_directories": sorted(unique_directories),
            },
        }

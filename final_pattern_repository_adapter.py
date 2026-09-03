from __future__ import annotations

from typing import Any, Dict, Optional

from candidate_pattern_models import (
    CandidatePattern,
)
from pattern_repository import store_pattern


class FinalPatternRepositoryAdapter:
    """
    Adapts a completed Candidate Pattern to the existing
    record-oriented Pattern Repository.

    The adapter owns translation only. Persistence remains the
    responsibility of Pattern Repository.
    """

    OPERATION_TYPE_MAP = {
        "CREATE": "CREATED",
        "CREATED": "CREATED",
        "MODIFY": "MODIFIED",
        "MODIFIED": "MODIFIED",
        "DELETE": "DELETED",
        "DELETED": "DELETED",
        "MOVE": "MOVED",
        "MOVED": "MOVED",
        "RENAME": "RENAMED",
        "RENAMED": "RENAMED",
        "EXTENSION_CHANGE": "EXTENSION_CHANGED",
        "EXTENSION_CHANGED": "EXTENSION_CHANGED",
        "COPY": "COPIED",
        "COPIED": "COPIED",
    }

    def store(
        self,
        pattern: CandidatePattern,
    ) -> bool:
        """
        Store the observations from a completed Candidate Pattern.

        Only structurally valid completed patterns are accepted.
        """

        if not self._validate_final_pattern(pattern):
            return False

        try:
            for observation in pattern.timeline.observations:
                repository_record = self._to_repository_record(
                    observation
                )

                if repository_record is None:
                    return False

                store_pattern(repository_record)

            return True

        except Exception:
            return False

    def _validate_final_pattern(
        self,
        pattern: CandidatePattern,
    ) -> bool:
        """
        Validate the structural requirements of a Final Pattern
        before it crosses into the historical repository.
        """

        if pattern is None:
            return False

        if not pattern.metadata.complete:
            return False

        if pattern.is_empty():
            return False

        if not pattern.session_id:
            return False

        if not isinstance(pattern.timeline.observations, list):
            return False

        for observation in pattern.timeline.observations:
            if not isinstance(observation, dict):
                return False

            operation_type = observation.get("operation_type")
            timestamp = observation.get("timestamp")

            if operation_type is None:
                return False

            if timestamp is None:
                return False

            if self.OPERATION_TYPE_MAP.get(
                str(operation_type).upper()
            ) is None:
                return False

        return True

    def _to_repository_record(
        self,
        observation: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        Translate one Candidate Pattern observation into the
        record structure expected by Pattern Repository.
        """

        if not isinstance(observation, dict):
            return None

        operation_type = observation.get("operation_type")

        if operation_type is None:
            return None

        normalized_operation_type = self.OPERATION_TYPE_MAP.get(
            str(operation_type).upper()
        )

        if normalized_operation_type is None:
            return None

        return {
            "event_type": normalized_operation_type,
            "file_extension": observation.get(
                "file_extension",
                "",
            ),
            "directory": observation.get(
                "directory",
                "",
            ),
            "event_hour": observation.get(
                "event_hour",
                0,
            ),
            "file_size": observation.get(
                "file_size",
                0,
            ),
        }

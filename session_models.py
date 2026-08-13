from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class SessionMetadata:
    """
    Metadata describing a behavioral session.
    """

    session_id: str

    start_time: datetime

    last_activity: datetime

    event_count: int = 0

    status: str = "ACTIVE"

    end_time: Optional[datetime] = None


@dataclass
class Session:
    """
    Represents a contextual sequence of normalized filesystem events.
    """

    metadata: SessionMetadata

    events: List[Any] = field(default_factory=list)

    context: Dict[str, Any] = field(default_factory=dict)

    def append_event(
        self,
        event: Any,
        timestamp: datetime
    ) -> None:
        """
        Append an event and update session activity metadata.
        """

        self.events.append(event)

        self.metadata.event_count += 1

        self.metadata.last_activity = timestamp
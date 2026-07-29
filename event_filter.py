"""
Module 02 - Event Filter

Responsible for validating, filtering, and normalizing
filesystem events before they enter the Session Manager.

This module is intentionally stateless.
"""
from __future__ import annotations
from pathlib import Path
from typing import Optional
from watcher import RawEvent
import logging

logger = logging.getLogger(__name__)

IGNORED_EXTENSIONS = {
    ".tmp"
}


IGNORED_FILES = {
    "desktop.ini",
    "thumbs.db"
}


class EventFilter:
    """
    Stateless Event Filter.

    Responsibilities:
    - Validate incoming RawEvent objects.
    - Ignore temporary/system events.
    - Normalize event structure.
    - Forward only clean events.

    This module MUST NOT:
    - Perform behavior analysis
    - Maintain user sessions
    - Train ML models
    - Access databases
    """

    VALID_EVENT_TYPES = {
        "CREATED",
        "MODIFIED",
        "DELETED",
        "MOVED",
        "RENAMED",
        "EXTENSION_CHANGED",
    }

    def process(self, event: RawEvent) -> Optional[RawEvent]:
        """
        Main entry point for the Event Filter.
        """

        if not self.validate_event(event):
            logger.debug("Rejected invalid event: %s", event)
            return None

        if self.filter_noise(event):
            logger.debug("Filtered noisy event: %s", event.source_path)
            return None

        event = self.verify_metadata(event)

        if event is None:
            logger.debug("Metadata verification failed.")
            return None

        event = self.normalize_event(event)
        logger.debug("Forwarding event: %s", event.file_name)
        return self.forward_event(event)

    def validate_event(self, event: RawEvent) -> bool:
        """
        Validates whether the incoming RawEvent is suitable
        for further processing.
        """

        if event is None:
            return False

        if event.event_type.upper() not in self.VALID_EVENT_TYPES:
            return False

        if not event.source_path:
            return False

        if not str(event.source_path).strip():
            return False

        return True

    def filter_noise(self, event: RawEvent) -> bool:
        """
        Returns True if the event should be ignored.
        """

        path = Path(event.source_path)

        filename = path.name.lower()
        extension = path.suffix.lower()

        # Ignore hidden temporary Office files
        if filename.startswith(("~", ".$")):
            return True

        if filename in IGNORED_FILES:
            return True

        if extension in IGNORED_EXTENSIONS:
            return True

        return False

    def verify_metadata(self, event: RawEvent) -> Optional[RawEvent]:
        """
        Ensures the event contains the minimum metadata
        required by downstream modules.
        """

        if event.timestamp is None:
            return None

        if not event.file_name:
            event.file_name = Path(event.source_path).name

        if not event.extension:
            event.extension = Path(event.source_path).suffix.lower()

        if not event.directory:
            event.directory = str(Path(event.source_path).parent)

        return event


    def normalize_event(self, event: RawEvent) -> RawEvent:
        """
        Normalizes event fields into a consistent format.
        """

        event.event_type = event.event_type.upper()

        event.extension = (
            event.extension.lower()
            if event.extension
            else ""
        )
        return event

    def forward_event(self, event: RawEvent) -> RawEvent:
        """
        Returns the processed event.

        This method exists as the official hand-off point to the
        next pipeline stage (Session Manager).
        """
        return event

"""
Architectural Note
-----------------

This module intentionally remains stateless.

Behavioral duplicate detection is not implemented here because
it requires historical context across multiple events.

Higher-level event correlation belongs to downstream
stateful modules.
"""

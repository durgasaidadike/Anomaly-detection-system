from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Callable, Dict, Optional, Tuple
import logging
from watchdog.events import (
    FileSystemEventHandler,
    FileSystemEvent,
    FileMovedEvent,
)
from watchdog.observers import Observer

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class RawEvent:
    """
    Standardized filesystem event forwarded
    to the Event Filter.
    """

    timestamp: str
    event_type: str
    source_path: str
    destination_path: Optional[str]
    file_name: str
    extension: str
    directory: str
    is_directory: bool
    file_size: int

    def to_dict(self) -> dict:
        return asdict(self)


class EventDispatcher:
    """
    Responsible only for forwarding RawEvent
    objects to the next pipeline stage.
    """

    def __init__(self, callback: Callable[[RawEvent], None]) -> None:
        self._callback = callback

    def dispatch(self, event: RawEvent) -> None:
        try:
            self._callback(event)
        except Exception:
            logger.exception("Failed to dispatch RawEvent.")
            raise


class WatchdogEventHandler(FileSystemEventHandler):
    """
    Converts native Watchdog events into
    standardized RawEvent objects.
    """

    def __init__(self, dispatcher: EventDispatcher) -> None:
        super().__init__()
        self._dispatcher = dispatcher

    def _build_raw_event(
        self,
        event: FileSystemEvent,
        event_type: str,
        destination_path: Optional[str] = None,
    ) -> RawEvent:
        source = Path(event.src_path)

        effective_path = Path(destination_path) if destination_path else source

        try:
            if effective_path.exists() and effective_path.is_file():
                size = effective_path.stat().st_size
            else:
                size = 0
        except OSError:
            size = 0

        return RawEvent(
            timestamp=datetime.now().astimezone().isoformat(),
            event_type=event_type,
            source_path=str(source),
            destination_path=destination_path,
            file_name=effective_path.name,
            extension=effective_path.suffix,
            directory=str(effective_path.parent),
            is_directory=event.is_directory,
            file_size=size,
        )

    def _forward(self, raw_event: RawEvent) -> None:
        logger.debug(
            "Forwarding %s event : %s", raw_event.event_type, raw_event.source_path
        )
        self._dispatcher.dispatch(raw_event)

    def on_created(self, event: FileSystemEvent) -> None:
        self._forward(self._build_raw_event(event, "CREATED"))

    def on_modified(self, event: FileSystemEvent) -> None:
        self._forward(self._build_raw_event(event, "MODIFIED"))

    def on_deleted(self, event: FileSystemEvent) -> None:
        self._forward(self._build_raw_event(event, "DELETED"))

    def on_moved(self, event: FileMovedEvent) -> None:
        self._forward(self._build_raw_event(event, "MOVED", event.dest_path))


class WatchdogManager:
    """
    Controls the lifecycle of the filesystem observer.

    Responsibilities:
        • Register directories
        • Start monitoring
        • Stop monitoring
        • Restart monitoring
        • Graceful shutdown

    Does NOT perform:
        • Event filtering
        • Behaviour analysis
        • ML
        • Database operations
    """

    def __init__(
        self,
        callback: Callable[[RawEvent], None],
        observer_factory: Callable[[], Observer] = Observer,
    ) -> None:
        self._observer_factory = observer_factory
        self._observer = self._observer_factory()
        self._dispatcher = EventDispatcher(callback)
        self._handler = WatchdogEventHandler(self._dispatcher)
        self._registered_directories: Dict[str, bool] = {}
        self._running = False
        self._lock = Lock()

    @property
    def running(self) -> bool:
        return self._running

    @property
    def monitored_directories(self) -> Tuple[str, ...]:
        return tuple(self._registered_directories.keys())

    def add_directory(self, directory: str, recursive: bool = True) -> None:
        path = Path(directory)

        if not path.exists():
            raise InvalidDirectoryError(f"Directory does not exist: {directory}")

        if not path.is_dir():
            raise InvalidDirectoryError(f"Not a directory: {directory}")

        resolved = str(path.resolve())

        if resolved in self._registered_directories:
            raise DirectoryAlreadyRegistered(resolved)

        self._observer.schedule(self._handler, resolved, recursive=recursive)

        self._registered_directories[resolved] = recursive

        logger.info("Registered directory: %s", resolved)

    def start_monitoring(self) -> None:
        with self._lock:
            if self._running:
                raise WatchdogAlreadyRunning("Watchdog is already running.")

            if not self._registered_directories:
                raise NoDirectoryRegisteredError("No directories registered.")

            self._observer.start()
            self._running = True
            logger.info("Filesystem monitoring started.")

    def stop_monitoring(self) -> None:
        with self._lock:
            if not self._running:
                raise WatchdogNotRunning("Watchdog is not running.")

            logger.info("Stopping filesystem monitoring...")

            self._observer.stop()
            self._observer.join()
            self._running = False
            logger.info("Filesystem monitoring stopped.")

    def restart(self) -> None:
        logger.info("Restarting Watchdog...")

        directories = list(self._registered_directories.items())

        if self._running:
            self.stop_monitoring()

        self._observer = self._observer_factory()
        self._handler = WatchdogEventHandler(self._dispatcher)

        self._registered_directories.clear()

        for directory, recursive in directories:
            self.add_directory(directory, recursive)

        self.start_monitoring()
        logger.info("Watchdog restarted.")

    def wait(self) -> None:
        if not self._running:
            raise WatchdogNotRunning("Watchdog is not running.")

        try:
            self._observer.join()
        except Exception:
            logger.exception("Observer terminated unexpectedly.")
            raise

    def shutdown(self) -> None:
        logger.info("Initiating Watchdog shutdown...")

        try:
            if self._running:
                self.stop_monitoring()
        finally:
            self._registered_directories.clear()
            logger.info("Watchdog shutdown completed.")


@dataclass(frozen=True, slots=True)
class WatchdogConfig:
    """
    Configuration for WatchdogManager.
    """

    recursive: bool = True


class WatchdogException(Exception):
    """Base exception for Watchdog."""


class WatchdogAlreadyRunning(WatchdogException):
    pass


class WatchdogNotRunning(WatchdogException):
    pass


class DirectoryAlreadyRegistered(WatchdogException):
    pass


class DirectoryNotRegistered(WatchdogException):
    pass


class InvalidDirectoryError(WatchdogException):
    pass


class NoDirectoryRegisteredError(WatchdogException):
    pass

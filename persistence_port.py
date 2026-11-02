from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict


class PersistencePort(ABC):
    """
    PRISM Module 17
    Persistence Port Contract

    Abstract interface for all persistence operations.
    Concrete implementations (e.g., MongoDB, filesystem, in-memory)
    must implement this contract.

    This port enforces separation of concerns:
    - Business logic depends on this port, not concrete implementations
    - No direct PyMongo or database imports outside the implementation
    - Architecture tests enforce this boundary
    """

    @abstractmethod
    def save_event(self, event_data: Dict[str, Any]) -> str:
        """
        Persist an event to storage.

        Args:
            event_data: Dictionary containing event information

        Returns:
            str: Unique identifier for the persisted event
        """
        pass

    @abstractmethod
    def save_baseline_entry(self, entry_data: Dict[str, Any]) -> str:
        """
        Persist a baseline inventory entry to storage.

        Args:
            entry_data: Dictionary containing baseline entry information

        Returns:
            str: Unique identifier for the persisted entry
        """
        pass

    @abstractmethod
    def save_directory_snapshot(self, snapshot_data: Dict[str, Any]) -> str:
        """
        Persist a directory snapshot to storage.

        Args:
            snapshot_data: Dictionary containing directory snapshot information

        Returns:
            str: Unique identifier for the persisted snapshot
        """
        pass

    @abstractmethod
    def save_validation_result(self, validation_data: Dict[str, Any]) -> str:
        """
        Persist a directory validation result to storage.

        Args:
            validation_data: Dictionary containing validation result information

        Returns:
            str: Unique identifier for the persisted validation result
        """
        pass

    @abstractmethod
    def save_watcher_registration(self, registration_data: Dict[str, Any]) -> str:
        """
        Persist a watcher registration to storage.

        Args:
            registration_data: Dictionary containing watcher registration information

        Returns:
            str: Unique identifier for the persisted registration
        """
        pass

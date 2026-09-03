from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class PatternStatus(str, Enum):
    """
    Lifecycle states for a Candidate Pattern.
    """

    INITIALIZING = "Initializing"
    LEARNING = "Learning"
    EVALUATING = "Evaluating"
    FINALIZING = "Finalizing"
    COMPLETED = "Completed"

@dataclass
class BehavioralTimeline:
    """
    Chronological sequence of behavioral observations.
    """

    observations: List[Dict[str, Any]] = field(default_factory=list)

    def add_observation(
        self,
        observation: Dict[str, Any],
    ) -> None:
        """
        Add a behavioral observation to the timeline.
        """

        self.observations.append(observation)

    def __len__(self) -> int:
        """
        Return the number of stored observations.
        """

        return len(self.observations)

    def clear(self) -> None:
        """
        Remove all observations.
        """

        self.observations.clear()


@dataclass
class BehavioralContext:
    """
    Accumulated contextual understanding of a Candidate Pattern.

    New observations update the latest understanding of context.
    """

    values: Dict[str, Any] = field(default_factory=dict)

    def update(
        self,
        values: Dict[str, Any],
    ) -> None:
        """
        Update contextual values with the latest understanding.
        """

        self.values.update(values)

    def clear(self) -> None:
        """
        Remove all contextual information.
        """

        self.values.clear()


@dataclass
class PatternMetadata:
    """
    Metadata describing the current state of a Candidate Pattern.
    """

    status: PatternStatus = PatternStatus.INITIALIZING
    observation_count: int = 0
    complete: bool = False
    interrupted: bool = False
    finalized_at: Optional[datetime] = None


@dataclass
class CandidatePattern:
    """
    Evolving behavioral representation of an active session.

    The Candidate Pattern is temporary active-session state.
    Only successfully finalized patterns proceed toward the
    Pattern Repository.
    """

    session_id: str
    user_id: Optional[str] = None
    session_start_time: Optional[datetime] = None

    timeline: BehavioralTimeline = field(
        default_factory=BehavioralTimeline
    )

    context: BehavioralContext = field(
        default_factory=BehavioralContext
    )

    operational_characteristics: Dict[str, Any] = field(
        default_factory=dict
    )

    temporal_characteristics: Dict[str, Any] = field(
        default_factory=dict
    )

    sequential_characteristics: List[Dict[str, Any]] = field(
        default_factory=list
    )

    contextual_characteristics: Dict[str, Any] = field(
        default_factory=dict
    )

    relationship_characteristics: List[Dict[str, Any]] = field(
        default_factory=list
    )

    session_characteristics: Dict[str, Any] = field(
        default_factory=dict
    )

    metadata: PatternMetadata = field(
        default_factory=PatternMetadata
    )

    def is_empty(self) -> bool:
        """
        Return True when the Candidate Pattern has no observations.
        """

        return self.observation_count() == 0

    def observation_count(self) -> int:
        """
        Return the number of behavioral observations.
        """

        return len(self.timeline)

    def add_observation(
        self,
        observation: Dict[str, Any],
    ) -> None:
        """
        Add an observation and update metadata.
        """

        self.timeline.add_observation(observation)
        self.metadata.observation_count = self.observation_count()

    def mark_interrupted(self) -> None:
        """
        Mark the Candidate Pattern as interrupted.
        """

        self.metadata.interrupted = True

    def mark_finalized(
        self,
        finalized_at: Optional[datetime] = None,
    ) -> None:
        """
        Mark the Candidate Pattern as finalized.
        """

        self.metadata.status = PatternStatus.FINALIZING
        self.metadata.complete = True
        self.metadata.finalized_at = (
            finalized_at if finalized_at is not None else datetime.now()
        )

    def mark_completed(self) -> None:
        """
        Mark the Candidate Pattern as completed.
        """

        self.metadata.status = PatternStatus.COMPLETED
        self.metadata.complete = True
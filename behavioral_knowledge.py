from __future__ import annotations

import copy
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Tuple


@dataclass
class BehavioralKnowledge:
    """
    Mutable aggregate representing learned knowledge about a behavioral
    blueprint.

    Unlike FinalPattern, this object represents consolidated knowledge
    and is therefore allowed to evolve as repeated behavior is observed.
    """

    knowledge_id: str
    user_id: Optional[str]
    behavior_key: Tuple

    representative_pattern_id: str

    occurrence_count: int = 1

    confidence_score: Optional[float] = None
    stability_score: Optional[float] = None

    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None

    def record_occurrence(
        self,
        observed_at: Optional[datetime] = None,
    ) -> None:
        """
        Record another occurrence of the same behavioral blueprint.
        """

        self.occurrence_count += 1

        if observed_at is None:
            observed_at = datetime.now()

        if self.first_seen is None:
            self.first_seen = observed_at

        if (
            self.last_seen is None
            or observed_at > self.last_seen
        ):
            self.last_seen = observed_at

    def update_metrics(
        self,
        confidence_score: Optional[float] = None,
        stability_score: Optional[float] = None,
    ) -> None:
        """
        Update intelligence metrics when explicitly supplied.

        The calculation of these metrics is intentionally outside this
        model because the architecture does not define their mathematical
        formulas here.
        """

        if confidence_score is not None:
            self.confidence_score = confidence_score

        if stability_score is not None:
            self.stability_score = stability_score

    def snapshot(self) -> "BehavioralKnowledge":
        """
        Return an independent snapshot of the current learned knowledge.
        """

        return copy.deepcopy(self)

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from behavioral_knowledge import BehavioralKnowledge
from final_pattern_models import FinalPattern


class SearchOutcome(str, Enum):
    """
    Outcome of a repository behavioral search.
    """

    NO_MATCH = "NO_MATCH"
    EXACT_MATCH = "EXACT_MATCH"


@dataclass(frozen=True)
class RepositorySearchResult:
    """
    Represents the result of searching the repository for a behavior.
    """

    matched: bool

    outcome: SearchOutcome

    representative_pattern: Optional[
        FinalPattern
    ] = None

    behavioral_knowledge: Optional[
        BehavioralKnowledge
    ] = None

    @classmethod
    def no_match(
        cls,
    ) -> "RepositorySearchResult":
        return cls(
            matched=False,
            outcome=SearchOutcome.NO_MATCH,
        )

    @classmethod
    def match(
        cls,
        representative_pattern: FinalPattern,
        behavioral_knowledge: BehavioralKnowledge,
    ) -> "RepositorySearchResult":
        return cls(
            matched=True,
            outcome=SearchOutcome.EXACT_MATCH,
            representative_pattern=representative_pattern,
            behavioral_knowledge=behavioral_knowledge,
        )

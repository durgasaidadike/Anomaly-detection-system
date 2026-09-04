from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from behavioral_knowledge import BehavioralKnowledge
from final_pattern_models import FinalPattern


@dataclass(frozen=True)
class RepositorySearchResult:
    """
    Represents the result of searching the repository for a behavior.

    A matched result contains the representative historical
    FinalPattern and the corresponding consolidated BehavioralKnowledge.
    """

    matched: bool

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
        """
        Create an unmatched repository search result.
        """

        return cls(
            matched=False,
            representative_pattern=None,
            behavioral_knowledge=None,
        )

    @classmethod
    def match(
        cls,
        representative_pattern: FinalPattern,
        behavioral_knowledge: BehavioralKnowledge,
    ) -> "RepositorySearchResult":
        """
        Create a matched repository search result.
        """

        return cls(
            matched=True,
            representative_pattern=representative_pattern,
            behavioral_knowledge=behavioral_knowledge,
        )

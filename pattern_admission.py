from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class PatternAdmissionAction(str, Enum):
    """
    Repository action already decided by the behavioral intelligence layer.

    The repository trusts the action only. Similarity, drift, and
    confidence evaluation remain outside the repository boundary.
    """

    STORE_NEW = "store_new"
    RECORD_OCCURRENCE = "record_occurrence"
    REJECT = "reject"


@dataclass(frozen=True)
class PatternAdmissionDecision:
    """
    Immutable admission decision handed to the Final Pattern Repository.
    """

    action: PatternAdmissionAction
    target_pattern_id: Optional[str] = None
    reason: Optional[str] = None

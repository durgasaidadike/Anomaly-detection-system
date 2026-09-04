from __future__ import annotations

import copy
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class FinalPattern:
    """
    Immutable historical representation of a completed behavioral pattern.

    A FinalPattern represents one finalized behavioral observation and must
    not be mutated after creation.
    """

    pattern_id: str
    session_id: str
    user_id: Optional[str]
    created_at: datetime

    observations: List[Dict[str, Any]] = field(default_factory=list)

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

    observation_count: int = 0

    def snapshot(self) -> "FinalPattern":
        """
        Return an independent copy of this historical pattern.
        """
        return copy.deepcopy(self)

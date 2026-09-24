from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class PatternReference:
    """
    Immutable logical reference to a historical FinalPattern.

    A PatternReference carries only the traceability metadata required
    to resolve the referenced FinalPattern. It is deliberately not a
    second copy of the whole FinalPattern.
    """

    pattern_id: str
    session_id: str
    user_id: Optional[str]
    created_at: datetime

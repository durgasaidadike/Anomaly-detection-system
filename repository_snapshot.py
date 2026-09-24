from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass(frozen=True)
class RepositorySnapshot:
    """
    Detached logical container for recoverable repository state.

    This is a logical state container, not a database document. Physical
    persistence of repository state is intentionally handled elsewhere.
    """

    patterns: List[Any]
    knowledge: List[Any]
    pattern_index: Dict[Any, str]
    user_pattern_index: Dict[Any, List[str]]
    session_pattern_index: Dict[str, str]
    recorded_pattern_ids: List[str]
    recorded_occurrence_ids: List[str]
    occurrence_behavior_keys: Dict[str, Any]
    baseline_pattern_ids: Dict[Any, str]

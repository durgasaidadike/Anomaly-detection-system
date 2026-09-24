from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Set

from behavioral_knowledge import BehavioralKnowledge
from final_pattern_models import FinalPattern


REPOSITORY_SNAPSHOT_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class RepositorySnapshot:
    """
    Detached logical representation of complete repository state.

    This is a logical recovery contract only. It performs no
    serialization and addresses no physical persistence layer.

    ``schema_version`` describes this repository-state contract. It is
    deliberately separate from ``FinalPattern.pattern_version``, which
    describes the behavioral pattern content itself. The two versioning
    concepts must never be merged.
    """

    schema_version: int

    patterns: Dict[str, FinalPattern]

    pattern_index: Dict[Any, str]

    knowledge: Dict[str, BehavioralKnowledge]

    recorded_pattern_ids: Set[str]

    recorded_occurrence_ids: Set[str]

    occurrence_behavior_keys: Dict[
        str,
        Any,
    ]

    user_pattern_index: Dict[
        str,
        List[str],
    ]

    session_pattern_index: Dict[
        str,
        str,
    ]

    baseline_pattern_ids: Dict[
        str,
        str,
    ]


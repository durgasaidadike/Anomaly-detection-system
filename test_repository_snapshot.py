from __future__ import annotations

from typing import Optional

import pytest

from datetime import datetime

from behavioral_identity import BehavioralIdentity
from final_pattern_models import FinalPattern
from final_pattern_repository import FinalPatternRepository
from repository_persistence import RepositoryPersistence
from repository_snapshot import (
    REPOSITORY_SNAPSHOT_SCHEMA_VERSION,
    RepositorySnapshot,
)


def _build_final_pattern(
    *,
    pattern_id: str = "pattern-1",
    session_id: str = "session-1",
    operation_type: str = "CREATE",
    user_id: str = "user-1",
) -> FinalPattern:
    return FinalPattern(
        pattern_id=pattern_id,
        session_id=session_id,
        user_id=user_id,
        created_at=datetime(2026, 9, 4, 10, 0, 0),
        observations=[
            {
                "operation_type": operation_type,
                "timestamp": datetime(2026, 9, 4, 10, 0, 0),
                "file_extension": ".py",
                "directory": "/project",
            }
        ],
        observation_count=1,
    )




class MemoryRepositoryPersistence:
    """In-memory reference implementation of RepositoryPersistence."""

    def __init__(self) -> None:
        self._stored_snapshot: Optional[RepositorySnapshot] = None

    def save(self, snapshot: RepositorySnapshot) -> bool:
        self._stored_snapshot = snapshot
        return True

    def load(self) -> Optional[RepositorySnapshot]:
        return self._stored_snapshot


def test_snapshot_round_trip_restores_complete_state():
    repo = FinalPatternRepository()
    pattern_a = _build_final_pattern(pattern_id="p-1", user_id="u-1")
    pattern_b = _build_final_pattern(
        pattern_id="p-2",
        session_id="session-2",
        user_id="u-1",
        operation_type="DELETE",
    )

    occurrence_a = _build_final_pattern(
        pattern_id="occ-1",
        session_id="session-occ-1",
        user_id="u-1",
    )

    assert repo.store(pattern_a) is True
    assert repo.store(pattern_b) is True
    assert repo.record_occurrence(
        "p-1",
        occurrence_a,
    ) is True

    snapshot = repo.create_snapshot()
    assert snapshot.schema_version == REPOSITORY_SNAPSHOT_SCHEMA_VERSION
    assert "p-1" in snapshot.patterns
    assert "p-2" in snapshot.patterns

    # Restore into fresh repository
    restored_repo = FinalPatternRepository()
    assert restored_repo.restore_snapshot(snapshot) is True

    # Validate state matches
    assert restored_repo.count() == 2
    assert restored_repo.contains("p-1") is True
    assert restored_repo.contains("p-2") is True
    assert restored_repo.get_baseline_pattern("u-1").pattern_id == "p-1"

    # Validate search rebinds and functions correctly
    result = restored_repo.search(pattern_a)
    assert result.matched is True
    assert result.behavioral_knowledge is not None
    assert result.behavioral_knowledge.occurrence_count == 2



def test_snapshot_preserves_indexes_and_baseline():
    repo = FinalPatternRepository()
    p1 = _build_final_pattern(
        pattern_id="p-1",
        session_id="session-alice",
        user_id="alice",
    )
    p2 = _build_final_pattern(
        pattern_id="p-2",
        session_id="session-bob",
        user_id="bob",
    )

    repo.store(p1)
    repo.store(p2)

    snapshot = repo.create_snapshot()
    assert snapshot.baseline_pattern_ids == {
        "alice": "p-1",
        "bob": "p-2",
    }
    assert "alice" in snapshot.user_pattern_index
    assert "bob" in snapshot.user_pattern_index
    assert snapshot.user_pattern_index["alice"] == ["p-1"]

    new_repo = FinalPatternRepository()
    assert new_repo.restore_snapshot(snapshot) is True
    assert new_repo.get_baseline_pattern("alice").pattern_id == "p-1"
    assert new_repo.get_baseline_pattern("bob").pattern_id == "p-2"


def test_snapshot_rejection_for_corrupted_payload():
    repo = FinalPatternRepository()
    pattern = _build_final_pattern()
    repo.store(pattern)

    valid_snapshot = repo.create_snapshot()

    bad_version = RepositorySnapshot(
        schema_version=999,
        patterns=valid_snapshot.patterns,
        pattern_index=valid_snapshot.pattern_index,
        knowledge=valid_snapshot.knowledge,
        recorded_pattern_ids=valid_snapshot.recorded_pattern_ids,
        recorded_occurrence_ids=valid_snapshot.recorded_occurrence_ids,
        occurrence_behavior_keys=valid_snapshot.occurrence_behavior_keys,
        user_pattern_index=valid_snapshot.user_pattern_index,
        session_pattern_index=valid_snapshot.session_pattern_index,
        baseline_pattern_ids=valid_snapshot.baseline_pattern_ids,
    )
    assert repo.validate_snapshot(bad_version) is False
    assert repo.restore_snapshot(bad_version) is False

    mismatched_pattern_dict = RepositorySnapshot(
        schema_version=REPOSITORY_SNAPSHOT_SCHEMA_VERSION,
        patterns={"mismatched-key": pattern},
        pattern_index=valid_snapshot.pattern_index,
        knowledge=valid_snapshot.knowledge,
        recorded_pattern_ids=valid_snapshot.recorded_pattern_ids,
        recorded_occurrence_ids=valid_snapshot.recorded_occurrence_ids,
        occurrence_behavior_keys=valid_snapshot.occurrence_behavior_keys,
        user_pattern_index=valid_snapshot.user_pattern_index,
        session_pattern_index=valid_snapshot.session_pattern_index,
        baseline_pattern_ids=valid_snapshot.baseline_pattern_ids,
    )
    assert repo.validate_snapshot(mismatched_pattern_dict) is False
    assert repo.restore_snapshot(mismatched_pattern_dict) is False

    assert repo.count() == 1
    assert repo.contains("pattern-1") is True


def test_snapshot_is_detached_from_repository():
    repo = FinalPatternRepository()
    pattern = _build_final_pattern(pattern_id="p-1", user_id="u-1")
    repo.store(pattern)

    snapshot = repo.create_snapshot()

    snapshot.patterns["tampered"] = _build_final_pattern(pattern_id="tampered")
    snapshot.recorded_pattern_ids.add("tampered")
    snapshot.user_pattern_index["u-1"].append("tampered")

    assert repo.count() == 1
    assert repo.contains("tampered") is False
    history = repo.get_behavior_history("u-1")
    assert len(history) == 1
    assert history[0].pattern_id == "p-1"


def test_repository_persistence_protocol_compliance():
    persistence: RepositoryPersistence = MemoryRepositoryPersistence()
    repo = FinalPatternRepository()
    pattern = _build_final_pattern()
    repo.store(pattern)

    snapshot = repo.create_snapshot()
    assert persistence.save(snapshot) is True

    loaded_snapshot = persistence.load()
    assert loaded_snapshot is not None
    assert loaded_snapshot.schema_version == REPOSITORY_SNAPSHOT_SCHEMA_VERSION

    restored_repo = FinalPatternRepository()
    assert restored_repo.restore_snapshot(loaded_snapshot) is True
    assert restored_repo.contains("pattern-1") is True

    result = restored_repo.search(pattern)
    assert result.matched is True
    assert result.behavioral_knowledge is not None

from datetime import datetime, timedelta, timezone
import copy
from dataclasses import replace

from candidate_pattern_manager import CandidatePatternManager
from final_pattern_repository import FinalPatternRepository
from final_pattern_repository_adapter import (
    FinalPatternRepositoryAdapter,
)


def build_manager_with_repository(
    repository,
):
    adapter = FinalPatternRepositoryAdapter(
        repository=repository,
    )

    manager = CandidatePatternManager(
        final_pattern_handler=adapter.store,
    )

    return manager


def populate_candidate(
    manager,
    session_id,
    start_time,
):
    manager.createPattern(
        session_id=session_id,
        user_id="user-001",
        session_start_time=start_time,
    )

    manager.updatePattern(
        session_id,
        {
            "signal_type": "EDITING_WORKFLOW",
            "operation_type": "CREATED",
            "timestamp": start_time,
        },
        context={
            "working_directory": "/workspace",
            "workflow_stage": "creation",
        },
        relationships=[],
    )

    manager.updatePattern(
        session_id,
        {
            "signal_type": "EDITING_WORKFLOW",
            "operation_type": "MODIFIED",
            "timestamp": start_time + timedelta(seconds=2),
        },
        context={
            "working_directory": "/workspace",
            "workflow_stage": "editing",
        },
        relationships=[
            {
                "relationship_type": "SEQUENTIAL",
                "from_operation": "CREATED",
                "to_operation": "MODIFIED",
            }
        ],
    )


def test_manager_finalization_reaches_repository():
    start = datetime(
        2026,
        1,
        1,
        10,
        0,
        0,
        tzinfo=timezone.utc,
    )

    session_id = "repository-handoff-001"

    repository = FinalPatternRepository()
    manager = build_manager_with_repository(repository)

    populate_candidate(
        manager,
        session_id,
        start,
    )

    manager.completeSession(
        session_id,
        session_end_time=start + timedelta(seconds=5),
    )

    finalized = manager.finalizePattern(session_id)

    assert finalized is not None
    assert finalized.metadata.complete is True

    assert repository.count() == 1
    assert repository.knowledge_count() == 1
    assert repository.validate_integrity() is True


def test_repository_stores_final_pattern_not_live_candidate():
    start = datetime(
        2026,
        1,
        1,
        10,
        0,
        0,
        tzinfo=timezone.utc,
    )

    session_id = "repository-handoff-002"

    repository = FinalPatternRepository()
    manager = build_manager_with_repository(repository)

    populate_candidate(
        manager,
        session_id,
        start,
    )

    manager.completeSession(
        session_id,
        session_end_time=start + timedelta(seconds=5),
    )

    finalized = manager.finalizePattern(session_id)

    assert finalized is not None

    stored_patterns = repository.get_all()

    assert len(stored_patterns) == 1

    stored = stored_patterns[0]

    assert stored.session_id == session_id
    assert stored.observation_count == finalized.observation_count()
    assert stored is not finalized


def test_repository_isolated_from_live_candidate_mutation():
    start = datetime(
        2026,
        1,
        1,
        10,
        0,
        0,
        tzinfo=timezone.utc,
    )

    session_id = "repository-handoff-003"

    repository = FinalPatternRepository()
    manager = build_manager_with_repository(repository)

    populate_candidate(
        manager,
        session_id,
        start,
    )

    manager.completeSession(
        session_id,
        session_end_time=start + timedelta(seconds=5),
    )

    finalized = manager.finalizePattern(session_id)

    assert finalized is not None

    stored_before = repository.get_all()[0]

    finalized.timeline.observations.clear()
    finalized.operational_characteristics.clear()
    finalized.relationship_characteristics.clear()

    stored_after = repository.get_all()[0]

    assert len(stored_after.observations) == (
        len(stored_before.observations)
    )

    assert stored_after.operational_characteristics == (
        stored_before.operational_characteristics
    )

    assert stored_after.relationship_characteristics == (
        stored_before.relationship_characteristics
    )

    assert repository.validate_integrity() is True


def test_repeated_behavior_strengthens_repository_knowledge():
    start = datetime(
        2026,
        1,
        1,
        10,
        0,
        0,
        tzinfo=timezone.utc,
    )

    repository = FinalPatternRepository()
    manager_a = build_manager_with_repository(repository)
    manager_b = build_manager_with_repository(repository)

    session_a = "repository-repeat-001"
    session_b = "repository-repeat-002"

    populate_candidate(
        manager_a,
        session_a,
        start,
    )

    populate_candidate(
        manager_b,
        session_b,
        start + timedelta(hours=1),
    )

    manager_a.completeSession(
        session_a,
        session_end_time=start + timedelta(seconds=5),
    )

    manager_b.completeSession(
        session_b,
        session_end_time=start + timedelta(hours=1, seconds=5),
    )

    finalized_a = manager_a.finalizePattern(session_a)

    assert finalized_a is not None
    assert repository.count() == 1
    assert repository.knowledge_count() == 1

    finalized_b = manager_b.finalizePattern(session_b)

    assert finalized_b is not None

    assert repository.count() == 1
    assert repository.knowledge_count() == 1

    knowledge = repository.get_all_knowledge()

    assert len(knowledge) == 1
    assert knowledge[0].occurrence_count == 2

    assert repository.validate_integrity() is True


def test_repeated_behavior_does_not_create_orphan_recorded_pattern_id():
    start = datetime(
        2026,
        1,
        1,
        10,
        0,
        0,
        tzinfo=timezone.utc,
    )

    repository = FinalPatternRepository()
    manager_a = build_manager_with_repository(repository)
    manager_b = build_manager_with_repository(repository)

    session_a = "repository-integrity-001"
    session_b = "repository-integrity-002"

    populate_candidate(
        manager_a,
        session_a,
        start,
    )

    populate_candidate(
        manager_b,
        session_b,
        start + timedelta(hours=1),
    )

    manager_a.completeSession(
        session_a,
        session_end_time=start + timedelta(seconds=5),
    )

    manager_b.completeSession(
        session_b,
        session_end_time=start + timedelta(hours=1, seconds=5),
    )

    assert manager_a.finalizePattern(session_a) is not None
    assert manager_b.finalizePattern(session_b) is not None

    assert repository.count() == 1
    assert repository.knowledge_count() == 1

    assert repository.validate_integrity() is True


def test_repeated_behavior_same_pattern_id_is_idempotent():
    start = datetime(
        2026,
        1,
        1,
        10,
        0,
        0,
        tzinfo=timezone.utc,
    )

    repository = FinalPatternRepository()

    manager_a = build_manager_with_repository(repository)
    manager_b = build_manager_with_repository(repository)

    session_a = "repository-idempotent-001"
    session_b = "repository-idempotent-002"

    populate_candidate(
        manager_a,
        session_a,
        start,
    )

    populate_candidate(
        manager_b,
        session_b,
        start + timedelta(hours=1),
    )

    manager_a.completeSession(
        session_a,
        session_end_time=start + timedelta(seconds=5),
    )

    manager_b.completeSession(
        session_b,
        session_end_time=start + timedelta(hours=1, seconds=5),
    )

    finalized_a = manager_a.finalizePattern(session_a)
    finalized_b = manager_b.finalizePattern(session_b)

    assert finalized_a is not None
    assert finalized_b is not None

    assert repository.count() == 1
    assert repository.knowledge_count() == 1

    knowledge = repository.get_all_knowledge()

    assert len(knowledge) == 1
    assert knowledge[0].occurrence_count == 2

    occurrence_count_before = (
        knowledge[0].occurrence_count
    )

    # Get the actual FinalPattern that was stored in the repository
    stored_patterns = repository.get_all()
    assert len(stored_patterns) == 1

    # Re-submitting the same FinalPattern must be idempotent.
    assert repository.store(stored_patterns[0]) is True

    knowledge_after = (
        repository.get_all_knowledge()
    )

    assert len(knowledge_after) == 1
    assert (
        knowledge_after[0].occurrence_count
        == occurrence_count_before
    )

    assert repository.count() == 1
    assert repository.knowledge_count() == 1
    assert repository.validate_integrity() is True


def test_repeated_occurrence_id_cannot_be_reused_for_different_behavior():
    start = datetime(
        2026,
        1,
        1,
        10,
        0,
        0,
        tzinfo=timezone.utc,
    )

    repository = FinalPatternRepository()

    manager_a = build_manager_with_repository(repository)
    manager_b = build_manager_with_repository(repository)

    session_a = "repository-reuse-001"
    session_b = "repository-reuse-002"

    populate_candidate(
        manager_a,
        session_a,
        start,
    )

    populate_candidate(
        manager_b,
        session_b,
        start + timedelta(hours=1),
    )

    manager_a.completeSession(
        session_a,
        session_end_time=start + timedelta(seconds=5),
    )

    manager_b.completeSession(
        session_b,
        session_end_time=start + timedelta(hours=1, seconds=5),
    )

    finalized_a = manager_a.finalizePattern(session_a)
    finalized_b = manager_b.finalizePattern(session_b)

    assert finalized_a is not None
    assert finalized_b is not None

    assert repository.count() == 1
    assert repository.knowledge_count() == 1

    knowledge_before = repository.get_all_knowledge()
    assert knowledge_before[0].occurrence_count == 2

    # Get the actual FinalPattern from the repository to test ID reuse
    stored_patterns = repository.get_all()
    assert len(stored_patterns) == 1

    # Reusing the repeated occurrence's ID for different behavior
    # must be rejected.
    reused_pattern = copy.deepcopy(stored_patterns[0])

    # Mutate fields that participate in behavioral identity.
    reused_pattern.observations[0]["operation_type"] = "DELETE"

    assert reused_pattern.pattern_id == stored_patterns[0].pattern_id
    assert repository.store(reused_pattern) is False

    knowledge_after = repository.get_all_knowledge()

    assert knowledge_after[0].occurrence_count == 2
    assert repository.count() == 1
    assert repository.knowledge_count() == 1
    assert repository.validate_integrity() is True


def test_repository_get_returns_detached_final_pattern():
    start = datetime(
        2026,
        1,
        1,
        10,
        0,
        0,
        tzinfo=timezone.utc,
    )

    repository = FinalPatternRepository()
    manager = build_manager_with_repository(repository)

    session_id = "repository-mutation-001"

    populate_candidate(
        manager,
        session_id,
        start,
    )

    manager.completeSession(
        session_id,
        session_end_time=start + timedelta(seconds=5),
    )

    finalized = manager.finalizePattern(session_id)

    assert finalized is not None

    stored_patterns = repository.get_all()

    assert len(stored_patterns) == 1

    stored = stored_patterns[0]

    assert stored is not finalized

    original_operation = (
        stored.observations[0]["operation_type"]
    )

    stored.observations[0]["operation_type"] = "DELETE"

    reread = repository.get(stored.pattern_id)

    assert reread is not None
    assert (
        reread.observations[0]["operation_type"]
        == original_operation
    )

    assert repository.validate_integrity() is True


def test_repository_get_knowledge_returns_detached_snapshot():
    start = datetime(
        2026,
        1,
        1,
        10,
        0,
        0,
        tzinfo=timezone.utc,
    )

    repository = FinalPatternRepository()
    manager = build_manager_with_repository(repository)

    session_id = "repository-knowledge-mutation-001"

    populate_candidate(
        manager,
        session_id,
        start,
    )

    manager.completeSession(
        session_id,
        session_end_time=start + timedelta(seconds=5),
    )

    finalized = manager.finalizePattern(session_id)

    assert finalized is not None

    stored_knowledge = repository.get_all_knowledge()

    assert len(stored_knowledge) == 1

    snapshot = stored_knowledge[0]
    original_count = snapshot.occurrence_count

    snapshot.occurrence_count = 999

    reread = repository.get_all_knowledge()

    assert len(reread) == 1
    assert reread[0].occurrence_count == original_count

    assert repository.validate_integrity() is True


def test_repository_failed_store_does_not_leave_partial_state():
    repository = FinalPatternRepository()

    initial_patterns = repository.get_all()
    initial_knowledge = repository.get_all_knowledge()

    assert initial_patterns == []
    assert initial_knowledge == []
    assert repository.count() == 0
    assert repository.knowledge_count() == 0
    assert repository.validate_integrity() is True

    # Invalid object must be rejected without changing repository state.
    result = repository.store(object())

    assert result is False

    assert repository.count() == 0
    assert repository.knowledge_count() == 0
    assert repository.get_all() == []
    assert repository.get_all_knowledge() == []
    assert repository.validate_integrity() is True


def test_repository_internal_failure_does_not_leave_partial_state(monkeypatch):
    start = datetime(
        2026,
        1,
        1,
        10,
        0,
        0,
        tzinfo=timezone.utc,
    )

    repository = FinalPatternRepository()
    manager = build_manager_with_repository(repository)

    session_id = "repository-transaction-001"

    populate_candidate(
        manager,
        session_id,
        start,
    )

    manager.completeSession(
        session_id,
        session_end_time=start + timedelta(seconds=5),
    )

    finalized_candidate = manager.finalizePattern(session_id)

    assert finalized_candidate is not None

    stored_patterns = repository.get_all()

    assert len(stored_patterns) == 1

    existing_pattern = stored_patterns[0]

    # Start with a known-good repository state.
    assert repository.count() == 1
    assert repository.knowledge_count() == 1
    assert repository.validate_integrity() is True

    original_patterns = repository.get_all()
    original_knowledge = repository.get_all_knowledge()

    # Force a failure while the repository is creating knowledge
    # for a genuinely new behavioral identity.
    def failing_create(*args, **kwargs):
        raise RuntimeError(
            "forced repository knowledge creation failure"
        )

    monkeypatch.setattr(
        repository,
        "_create_behavioral_knowledge",
        failing_create,
    )

    # Create another valid FinalPattern with a distinct identity.
    # We need to ensure the behavioral key is different by changing operation type
    new_observations = copy.deepcopy(
        existing_pattern.observations
    )

    new_observations[0] = copy.deepcopy(
        new_observations[0]
    )

    new_observations[0]["operation_type"] = "DELETE"

    new_pattern = replace(
        existing_pattern,
        pattern_id=(
            f"{existing_pattern.pattern_id}-new"
        ),
        observations=new_observations,
    )

    result = repository.store(new_pattern)

    assert result is False

    # Repository must remain exactly as it was before
    # the failed operation.
    assert repository.count() == 1
    assert repository.knowledge_count() == 1
    assert repository.validate_integrity() is True

    current_patterns = repository.get_all()
    current_knowledge = repository.get_all_knowledge()

    assert current_patterns == original_patterns
    assert current_knowledge == original_knowledge


def test_repeated_behavior_failure_does_not_leave_partial_state(
    monkeypatch,
):
    start = datetime(
        2026,
        1,
        1,
        10,
        0,
        0,
        tzinfo=timezone.utc,
    )

    repository = FinalPatternRepository()
    manager = build_manager_with_repository(repository)

    first_session_id = "repository-repeat-failure-001"

    populate_candidate(
        manager,
        first_session_id,
        start,
    )

    manager.completeSession(
        first_session_id,
        session_end_time=start + timedelta(seconds=5),
    )

    finalized_candidate = manager.finalizePattern(
        first_session_id
    )

    assert finalized_candidate is not None

    assert repository.count() == 1
    assert repository.knowledge_count() == 1
    assert repository.validate_integrity() is True

    stored_pattern = repository.get_all()[0]

    original_patterns = repository.get_all()
    original_knowledge = repository.get_all_knowledge()

    knowledge_before = repository.find_knowledge(
        stored_pattern
    )

    assert knowledge_before is not None

    occurrence_count_before = (
        knowledge_before.occurrence_count
    )

    # Since find_knowledge returns a snapshot, we need to monkeypatch
    # the actual knowledge object in the repository
    knowledge_id = f"knowledge-{stored_pattern.pattern_id}"
    actual_knowledge = repository._knowledge[knowledge_id]

    original_record_occurrence = (
        actual_knowledge.record_occurrence
    )

    def failing_record_occurrence(*args, **kwargs):
        raise RuntimeError(
            "forced repeated-behavior failure"
        )

    monkeypatch.setattr(
        actual_knowledge,
        "record_occurrence",
        failing_record_occurrence,
    )

    repeated_pattern = replace(
        stored_pattern,
        # Use a different pattern ID to trigger repeated behavior with different ID
        pattern_id=f"{stored_pattern.pattern_id}-repeat",
        created_at=start + timedelta(minutes=1),
    )

    result = repository.store(
        repeated_pattern
    )

    assert result is False

    assert repository.count() == 1
    assert repository.knowledge_count() == 1
    assert repository.validate_integrity() is True

    knowledge_after = repository.find_knowledge(
        stored_pattern
    )

    assert knowledge_after is not None

    assert (
        knowledge_after.occurrence_count
        == occurrence_count_before
    )

    assert (
        repeated_pattern.pattern_id
        not in repository._recorded_occurrence_ids
    )

    assert repository.get_all() == original_patterns
    assert repository.get_all_knowledge() == original_knowledge


def test_repeated_behavior_occurrence_registration_failure_is_atomic(
    monkeypatch,
):
    start = datetime(
        2026,
        1,
        1,
        10,
        0,
        0,
        tzinfo=timezone.utc,
    )

    repository = FinalPatternRepository()
    manager = build_manager_with_repository(repository)

    first_session_id = (
        "repository-occurrence-atomicity-001"
    )

    populate_candidate(
        manager,
        first_session_id,
        start,
    )

    manager.completeSession(
        first_session_id,
        session_end_time=start + timedelta(seconds=5),
    )

    finalized_candidate = manager.finalizePattern(
        first_session_id
    )

    assert finalized_candidate is not None

    assert repository.count() == 1
    assert repository.knowledge_count() == 1
    assert repository.validate_integrity() == True

    stored_pattern = repository.get_all()[0]

    knowledge_before = repository.find_knowledge(
        stored_pattern
    )

    assert knowledge_before is not None

    occurrence_count_before = (
        knowledge_before.occurrence_count
    )

    original_patterns = repository.get_all()
    original_knowledge = repository.get_all_knowledge()
    original_occurrence_ids = set(
        repository._recorded_occurrence_ids
    )

    class FailingOccurrenceSet(set):
        def add(self, value):
            raise RuntimeError(
                "forced occurrence registration failure"
            )

    failing_occurrence_ids = FailingOccurrenceSet(
        original_occurrence_ids
    )

    monkeypatch.setattr(
        repository,
        "_recorded_occurrence_ids",
        failing_occurrence_ids,
    )

    repeated_pattern = replace(
        stored_pattern,
        pattern_id=(
            f"{stored_pattern.pattern_id}-atomicity"
        ),
        created_at=start + timedelta(minutes=1),
    )

    result = repository.store(
        repeated_pattern
    )

    assert result is False

    # The historical pattern set must be unchanged.
    assert repository.count() == 1
    assert repository.get_all() == original_patterns

    # The knowledge aggregate must also be unchanged.
    assert repository.knowledge_count() == 1

    knowledge_after = repository.find_knowledge(
        stored_pattern
    )

    assert knowledge_after is not None

    assert (
        knowledge_after.occurrence_count
        == occurrence_count_before
    )

    assert (
        repository.get_all_knowledge()
        == original_knowledge
    )

    # The failed occurrence must not be considered recorded.
    assert (
        repeated_pattern.pattern_id
        not in repository._recorded_occurrence_ids
    )

    assert repository.validate_integrity() is True
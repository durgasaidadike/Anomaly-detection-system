from datetime import datetime

from behavioral_knowledge import BehavioralKnowledge


def build_knowledge():
    return BehavioralKnowledge(
        knowledge_id="knowledge-1",
        user_id="user-1",
        behavior_key=(
            "user-1",
            ("CREATE", "MODIFY"),
            (".py", ".py"),
            ("/project", "/project"),
        ),
        representative_pattern_id="pattern-1",
        occurrence_count=1,
        first_seen=datetime(
            2026,
            9,
            1,
            10,
            0,
            0,
        ),
        last_seen=datetime(
            2026,
            9,
            1,
            10,
            0,
            0,
        ),
    )


def test_initial_knowledge_has_one_occurrence():
    knowledge = build_knowledge()

    assert knowledge.occurrence_count == 1
    assert knowledge.knowledge_id == "knowledge-1"
    assert knowledge.representative_pattern_id == "pattern-1"


def test_record_occurrence_increments_count():
    knowledge = build_knowledge()

    knowledge.record_occurrence(
        datetime(
            2026,
            9,
            2,
            10,
            0,
            0,
        )
    )

    assert knowledge.occurrence_count == 2


def test_record_occurrence_updates_last_seen():
    knowledge = build_knowledge()

    new_time = datetime(
        2026,
        9,
        2,
        10,
        0,
        0,
    )

    knowledge.record_occurrence(new_time)

    assert knowledge.last_seen == new_time


def test_record_occurrence_does_not_move_last_seen_backwards():
    knowledge = build_knowledge()

    older_time = datetime(
        2026,
        8,
        1,
        10,
        0,
        0,
    )

    knowledge.record_occurrence(older_time)

    assert knowledge.occurrence_count == 2
    assert knowledge.last_seen == datetime(
        2026,
        9,
        1,
        10,
        0,
        0,
    )


def test_record_occurrence_sets_first_seen_when_missing():
    knowledge = build_knowledge()

    knowledge.first_seen = None
    observed_at = datetime(
        2026,
        9,
        3,
        12,
        0,
        0,
    )

    knowledge.record_occurrence(observed_at)

    assert knowledge.first_seen == observed_at


def test_update_confidence_metric():
    knowledge = build_knowledge()

    knowledge.update_metrics(
        confidence_score=0.9,
    )

    assert knowledge.confidence_score == 0.9


def test_update_stability_metric():
    knowledge = build_knowledge()

    knowledge.update_metrics(
        stability_score=0.8,
    )

    assert knowledge.stability_score == 0.8


def test_metrics_can_be_updated_together():
    knowledge = build_knowledge()

    knowledge.update_metrics(
        confidence_score=0.9,
        stability_score=0.85,
    )

    assert knowledge.confidence_score == 0.9
    assert knowledge.stability_score == 0.85


def test_partial_metric_update_preserves_other_metric():
    knowledge = build_knowledge()

    knowledge.update_metrics(
        confidence_score=0.9,
        stability_score=0.85,
    )

    knowledge.update_metrics(
        confidence_score=0.95,
    )

    assert knowledge.confidence_score == 0.95
    assert knowledge.stability_score == 0.85


def test_snapshot_is_independent():
    knowledge = build_knowledge()

    snapshot = knowledge.snapshot()

    assert snapshot == knowledge
    assert snapshot is not knowledge


def test_snapshot_changes_do_not_modify_original():
    knowledge = build_knowledge()

    snapshot = knowledge.snapshot()

    snapshot.occurrence_count = 10

    assert knowledge.occurrence_count == 1
    assert snapshot.occurrence_count == 10

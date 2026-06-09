"""Tests for backend Backlog Authority domain objects."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from meridian_core.backlog import (
    BacklogBlockedStatus,
    BacklogImportCandidate,
    BacklogItem,
    BacklogItemState,
    BacklogOwner,
    BacklogPriority,
    BacklogQuery,
    BacklogScope,
    BacklogSource,
    BacklogValidationError,
    approve_backlog_item,
    archive_backlog_item,
    capture_backlog_item,
    convert_backlog_item_to_task_draft,
    defer_backlog_item,
    deny_backlog_item,
    import_backlog_candidates,
    link_backlog_item_scope,
    load_backlog,
    modify_backlog_item,
    query_backlog,
    reject_backlog_item,
    save_backlog,
    to_goal_objective_ref,
)


NOW = datetime(2026, 6, 9, 8, 0, tzinfo=timezone.utc)


@pytest.fixture
def scope():
    return BacklogScope(
        project_id="meridian-v2",
        project_name="Meridian V2",
        initiative_id="backend-authority",
    )


def make_item(scope, item_id="bak-1", title="Backlog authority"):
    return capture_backlog_item(
        item_id=item_id,
        title=title,
        body_summary="Create reviewed backend authority for backlog records.",
        source=BacklogSource.USER,
        source_ref=f"user://capture/{item_id}",
        created_by="prime",
        scope=scope,
        priority=BacklogPriority.HIGH,
        owner=BacklogOwner.BUILD,
        acceptance_criteria=("records are auditable",),
        timestamp=NOW,
    )


def test_capture_records_source_timestamp_revision_and_audit(scope):
    item = make_item(scope)
    data = item.to_dict()

    assert item.state == BacklogItemState.CAPTURED
    assert item.source == BacklogSource.USER
    assert item.source_ref == "user://capture/bak-1"
    assert item.created_at == NOW
    assert item.revision == 1
    assert item.revisions[0].title == "Backlog authority"
    assert item.audit_trail[0].action.value == "capture"
    assert data["scope"]["project_id"] == "meridian-v2"


def test_modify_persists_revision_history_and_reload(tmp_path, scope):
    item = make_item(scope)
    modified = modify_backlog_item(
        item,
        updated_by="prime",
        title="Backlog authority V1",
        acceptance_criteria=("records are auditable", "edits persist"),
        priority=BacklogPriority.URGENT,
        evidence_refs=("proof://backlog/modify",),
        timestamp=NOW + timedelta(minutes=5),
    )
    path = tmp_path / "backlog.json"

    save_backlog(path, (modified,))
    loaded = load_backlog(path)

    assert modified.revision == 2
    assert [revision.version for revision in modified.revisions] == [1, 2]
    assert loaded == (modified,)
    assert loaded[0].title == "Backlog authority V1"
    assert loaded[0].acceptance_criteria == ("records are auditable", "edits persist")


def test_approve_convert_to_task_and_goal_projection(scope):
    item = make_item(scope)
    approved = approve_backlog_item(
        item,
        approved_by="prime",
        evidence_refs=("proof://backlog/approve",),
        timestamp=NOW + timedelta(minutes=10),
    )
    converted, draft = convert_backlog_item_to_task_draft(
        approved,
        task_id="task-bak-1",
        converted_by="prime",
        proof_expectation="pytest plus FileMap proof",
        risk_tier=2,
        timestamp=NOW + timedelta(minutes=15),
    )
    objective_ref = to_goal_objective_ref(converted)

    assert approved.state == BacklogItemState.APPROVED
    assert converted.state == BacklogItemState.TASK_DRAFTED
    assert draft.item_id == converted.item_id
    assert draft.owner == BacklogOwner.BUILD
    assert draft.project_id == "meridian-v2"
    assert draft.proof_expectation == "pytest plus FileMap proof"
    assert objective_ref.to_safe_dict() == {
        "id": "bak-1",
        "label": "Backlog authority",
        "source": "backlog",
    }


def test_approve_requires_evidence_refs(scope):
    with pytest.raises(BacklogValidationError, match="requires evidence_refs"):
        approve_backlog_item(
            make_item(scope),
            approved_by="prime",
            evidence_refs=(),
            timestamp=NOW,
        )


def test_goal_projection_bounds_valid_backlog_title(scope):
    item = make_item(scope, item_id="bak-long", title=f"{'Long title ' * 13}".strip())

    objective_ref = to_goal_objective_ref(item)

    assert len(objective_ref.label) == 120
    assert objective_ref.label.endswith("...")
    assert objective_ref.to_safe_dict()["source"] == "backlog"


def test_convert_requires_approved_state(scope):
    item = make_item(scope)

    with pytest.raises(BacklogValidationError, match="only approved"):
        convert_backlog_item_to_task_draft(
            item,
            task_id="task-bak-1",
            converted_by="prime",
            proof_expectation="pytest",
            risk_tier=1,
            timestamp=NOW,
        )


def test_task_drafted_item_cannot_return_to_approved(scope):
    approved = approve_backlog_item(
        make_item(scope),
        approved_by="prime",
        evidence_refs=("proof://backlog/approve",),
        timestamp=NOW,
    )
    converted, _draft = convert_backlog_item_to_task_draft(
        approved,
        task_id="task-bak-1",
        converted_by="prime",
        proof_expectation="pytest",
        risk_tier=1,
        timestamp=NOW,
    )

    with pytest.raises(BacklogValidationError, match="captured or deferred"):
        approve_backlog_item(
            converted,
            approved_by="prime",
            evidence_refs=("proof://backlog/reapprove",),
            timestamp=NOW,
        )

    with pytest.raises(BacklogValidationError, match="task-drafted"):
        reject_backlog_item(
            converted,
            rejected_by="prime",
            reason="cannot reroute converted task",
            timestamp=NOW,
        )

    with pytest.raises(BacklogValidationError, match="task-drafted"):
        defer_backlog_item(
            converted,
            deferred_by="prime",
            reason="cannot reroute converted task",
            deferred_until=NOW + timedelta(days=1),
            timestamp=NOW,
        )


def test_rejected_item_must_be_modified_before_approval(scope):
    rejected = reject_backlog_item(
        make_item(scope),
        rejected_by="prime",
        reason="needs clearer scope",
        timestamp=NOW,
    )

    with pytest.raises(BacklogValidationError, match="captured or deferred"):
        approve_backlog_item(
            rejected,
            approved_by="prime",
            evidence_refs=("proof://backlog/approve",),
            timestamp=NOW,
        )

    reopened = modify_backlog_item(
        rejected,
        updated_by="prime",
        body_summary="Create reviewed backend authority after scope update.",
        timestamp=NOW + timedelta(minutes=1),
    )
    approved = approve_backlog_item(
        reopened,
        approved_by="prime",
        evidence_refs=("proof://backlog/approve-reopened",),
        timestamp=NOW + timedelta(minutes=2),
    )

    assert reopened.state == BacklogItemState.CAPTURED
    assert approved.state == BacklogItemState.APPROVED


def test_deferred_until_clears_when_item_leaves_deferred(scope):
    deferred = defer_backlog_item(
        make_item(scope),
        deferred_by="prime",
        reason="wait for proof",
        deferred_until=NOW + timedelta(days=1),
        timestamp=NOW,
    )
    approved = approve_backlog_item(
        deferred,
        approved_by="prime",
        evidence_refs=("proof://backlog/deferred-approved",),
        timestamp=NOW + timedelta(minutes=1),
    )
    rejected = reject_backlog_item(
        deferred,
        rejected_by="prime",
        reason="out of scope",
        timestamp=NOW + timedelta(minutes=2),
    )
    archived = archive_backlog_item(
        deferred,
        archived_by="prime",
        reason="superseded",
        timestamp=NOW + timedelta(minutes=3),
    )
    recaptured = modify_backlog_item(
        rejected,
        updated_by="prime",
        title="Recaptured backlog authority",
        timestamp=NOW + timedelta(minutes=4),
    )

    assert deferred.deferred_until == NOW + timedelta(days=1)
    assert approved.deferred_until is None
    assert rejected.deferred_until is None
    assert archived.deferred_until is None
    assert recaptured.state == BacklogItemState.CAPTURED
    assert recaptured.deferred_until is None


def test_reject_and_defer_are_auditable_without_delete(scope):
    item = make_item(scope)
    rejected = reject_backlog_item(
        item,
        rejected_by="prime",
        reason="outside v2 scope",
        timestamp=NOW + timedelta(minutes=20),
    )
    denied = deny_backlog_item(
        item,
        denied_by="prime",
        reason="outside v2 scope",
        timestamp=NOW + timedelta(minutes=22),
    )
    deferred = defer_backlog_item(
        item,
        deferred_by="prime",
        reason="wait for upstream proof",
        deferred_until=NOW + timedelta(days=7),
        timestamp=NOW + timedelta(minutes=25),
    )

    assert rejected.state == BacklogItemState.REJECTED
    assert rejected.audit_trail[-1].reason == "outside v2 scope"
    assert denied.state == BacklogItemState.REJECTED
    assert denied.audit_trail[-1].action.value == "reject"
    assert deferred.state == BacklogItemState.DEFERRED
    assert deferred.deferred_until == NOW + timedelta(days=7)
    assert deferred.audit_trail[-1].reason == "wait for upstream proof"
    assert rejected.item_id == item.item_id
    assert deferred.item_id == item.item_id


def test_link_project_initiative_and_archive_inspectability(scope):
    item = make_item(scope)
    linked_scope = BacklogScope(
        project_id="meridian-v2",
        project_name="Meridian V2",
        initiative_id="runtime-authority",
        venture_id="meridian",
    )
    linked = link_backlog_item_scope(
        item,
        linked_scope,
        linked_by="prime",
        evidence_refs=("proof://scope/link",),
        timestamp=NOW + timedelta(minutes=30),
    )
    archived = archive_backlog_item(
        linked,
        archived_by="prime",
        reason="superseded by task",
        timestamp=NOW + timedelta(minutes=35),
    )

    assert linked.scope.initiative_id == "runtime-authority"
    assert archived.state == BacklogItemState.ARCHIVED
    assert archived.archived_by == "prime"
    assert archived.archive_reason == "superseded by task"
    assert archived.audit_trail[-1].action.value == "archive"
    assert archived.revisions

    with pytest.raises(BacklogValidationError, match="archived"):
        modify_backlog_item(archived, updated_by="prime", title="cannot edit")

    with pytest.raises(BacklogValidationError, match="archived"):
        archive_backlog_item(archived, archived_by="prime", reason="again")


def test_archived_records_require_actor_reason_on_reload(scope):
    archived = archive_backlog_item(
        make_item(scope),
        archived_by="prime",
        reason="superseded",
        timestamp=NOW,
    )
    missing_actor = archived.to_dict()
    missing_actor["archived_by"] = None
    missing_reason = archived.to_dict()
    missing_reason["archive_reason"] = None

    with pytest.raises(BacklogValidationError, match="archived_by"):
        from meridian_core.backlog import BacklogItem

        BacklogItem.from_dict(missing_actor)

    with pytest.raises(BacklogValidationError, match="archive_reason"):
        from meridian_core.backlog import BacklogItem

        BacklogItem.from_dict(missing_reason)


def test_reload_rejects_stale_editable_revision_snapshot(scope):
    item = modify_backlog_item(
        make_item(scope),
        updated_by="prime",
        title="Reviewed backlog authority",
        timestamp=NOW + timedelta(minutes=1),
    )
    stale_title = item.to_dict()
    stale_title["title"] = "Tampered backlog authority"
    bad_count = item.to_dict()
    bad_count["revision"] = item.revision + 1

    with pytest.raises(BacklogValidationError, match="editable backlog fields"):
        BacklogItem.from_dict(stale_title)

    with pytest.raises(BacklogValidationError, match="revision history length"):
        BacklogItem.from_dict(bad_count)


def test_reload_rejects_missing_audit_history(scope):
    missing_audit = make_item(scope).to_dict()
    missing_audit["audit_trail"] = []

    with pytest.raises(BacklogValidationError, match="audit history"):
        BacklogItem.from_dict(missing_audit)


def test_import_candidates_preserve_polaris_provenance_without_writeback():
    batch = import_backlog_candidates(
        batch_id="polaris-import-1",
        imported_by="prime",
        source=BacklogSource.POLARIS,
        candidates=(
            BacklogImportCandidate(
                candidate_id="polaris-1",
                title="Import candidate",
                source=BacklogSource.POLARIS,
                source_ref="polaris://feature/1",
                dedupe_key="feature-1",
                body_summary="Candidate imported for review.",
            ),
        ),
        timestamp=NOW,
    )

    assert batch.source == BacklogSource.POLARIS
    assert batch.writes_back_to_source is False
    assert batch.candidates[0].source_ref == "polaris://feature/1"
    assert batch.to_dict()["writes_back_to_source"] is False


def test_import_batch_rejects_source_writeback():
    candidate = BacklogImportCandidate(
        candidate_id="polaris-1",
        title="Import candidate",
        source=BacklogSource.POLARIS,
        source_ref="polaris://feature/1",
        dedupe_key="feature-1",
    )

    with pytest.raises(BacklogValidationError, match="cannot write back"):
        from meridian_core.backlog import BacklogImportBatch

        BacklogImportBatch(
            batch_id="polaris-import-1",
            imported_by="prime",
            imported_at=NOW,
            source=BacklogSource.POLARIS,
            candidates=(candidate,),
            writes_back_to_source=True,
        )


def test_import_batch_rejects_mixed_source_candidates():
    with pytest.raises(BacklogValidationError, match="source must match"):
        from meridian_core.backlog import BacklogImportBatch

        BacklogImportBatch(
            batch_id="mixed-import-1",
            imported_by="prime",
            imported_at=NOW,
            source=BacklogSource.POLARIS,
            candidates=(
                BacklogImportCandidate(
                    candidate_id="user-1",
                    title="Mixed source",
                    source=BacklogSource.USER,
                    source_ref="user://capture/1",
                    dedupe_key="user-1",
                ),
            ),
        )


def test_query_filters_real_fields_and_hides_archived_by_default(scope):
    item_a = approve_backlog_item(
        make_item(scope, item_id="bak-a", title="Backlog intake"),
        approved_by="prime",
        evidence_refs=("proof://approve/a",),
        timestamp=NOW,
    )
    item_b = modify_backlog_item(
        make_item(scope, item_id="bak-b", title="Crosscheck authority"),
        updated_by="prime",
        owner=BacklogOwner.AEGIS,
        blocked_status=BacklogBlockedStatus.BLOCKED,
        priority=BacklogPriority.NORMAL,
        timestamp=NOW,
    )
    item_c = archive_backlog_item(
        make_item(scope, item_id="bak-c", title="Old backlog task"),
        archived_by="prime",
        reason="done",
        timestamp=NOW,
    )

    results = query_backlog(
        (item_a, item_b, item_c),
        BacklogQuery(
            project_id="meridian-v2",
            owners=(BacklogOwner.AEGIS,),
            blocked_statuses=(BacklogBlockedStatus.BLOCKED,),
        ),
    )
    with_archived = query_backlog(
        (item_a, item_b, item_c),
        BacklogQuery(include_archived=True, text="old"),
    )

    assert results == (item_b,)
    assert with_archived == (item_c,)


@pytest.mark.parametrize(
    "unsafe_value",
    (
        "SECRET_RAW_PROMPT",
        "credential=openai",
        "token=abc123",
        "provider response body",
        "worker chat excerpt",
        "transcript excerpt",
        r"C:\Users\scott\Meridian",
        "/Users/scott/Meridian",
        "./runtime/queue.json",
        "../private/backlog.json",
        "docs/backlog.md",
    ),
)
def test_display_safety_rejects_unsafe_text_and_refs(scope, unsafe_value):
    with pytest.raises(BacklogValidationError):
        capture_backlog_item(
            item_id="unsafe",
            title="Unsafe item",
            body_summary=unsafe_value,
            source=BacklogSource.USER,
            source_ref="user://capture/unsafe",
            created_by="prime",
            scope=scope,
            timestamp=NOW,
        )

    with pytest.raises(BacklogValidationError):
        capture_backlog_item(
            item_id="unsafe-ref",
            title="Unsafe ref",
            body_summary="safe summary",
            source=BacklogSource.USER,
            source_ref=unsafe_value,
            created_by="prime",
            scope=scope,
            timestamp=NOW,
        )

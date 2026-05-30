"""Tests for the Review Console slice (meridian_core/review_console.py)."""

from __future__ import annotations

import pytest

from meridian_core.review_console import (
    ReviewConsoleAction,
    ReviewConsoleItem,
    ReviewConsoleResponse,
    ReviewConsoleItemStatus,
    ReviewConsoleItemType,
    ReviewConsoleSeverity,
    ReviewConsoleQueue,
    make_approval_gate,
    make_cross_check_item,
    make_plan_review_item,
    make_system_finding,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _cross(id: str = "cc-1", title: str = "Boundary mismatch", content: str = "relay.py:12") -> ReviewConsoleItem:
    return make_cross_check_item(id, title, content)


def _gate(id: str = "gate-1", title: str = "Approve release?", content: str = "PR #42") -> ReviewConsoleItem:
    return make_approval_gate(id, title, content)


def _finding(id: str = "sf-1", title: str = "Relay Go", content: str = "Relay harness online") -> ReviewConsoleItem:
    return make_system_finding(id, title, content)


# ---------------------------------------------------------------------------
# Cross-check item
# ---------------------------------------------------------------------------


class TestCrossCheckItem:
    def test_item_type_is_cross_check(self):
        assert _cross().item_type is ReviewConsoleItemType.CROSS_CHECK

    def test_cross_check_belongs_to_review_console(self):
        queue = ReviewConsoleQueue()
        item = _cross()
        queue.enqueue(item)
        assert item in queue.items

    def test_cross_check_is_automatic_by_default(self):
        assert _cross().is_automatic is True

    def test_cross_check_can_be_non_automatic(self):
        item = make_cross_check_item("cc-2", "Manual check", "notes", is_automatic=False)
        assert item.is_automatic is False

    def test_cross_check_does_not_require_response(self):
        assert _cross().requires_response is False

    def test_cross_check_is_promptable(self):
        assert _cross().promptable is True

    def test_cross_check_has_inspect_action(self):
        assert ReviewConsoleAction.INSPECT in _cross().suggested_actions

    def test_cross_check_has_acknowledge_action(self):
        assert ReviewConsoleAction.ACKNOWLEDGE in _cross().suggested_actions

    def test_cross_check_default_severity_is_info(self):
        assert _cross().severity is ReviewConsoleSeverity.INFO

    def test_cross_check_severity_override(self):
        item = make_cross_check_item("cc-3", "Critical mismatch", "", severity=ReviewConsoleSeverity.ERROR)
        assert item.severity is ReviewConsoleSeverity.ERROR


# ---------------------------------------------------------------------------
# Plan review item
# ---------------------------------------------------------------------------


class TestPlanReviewItem:
    def test_item_type_is_plan_review(self):
        item = make_plan_review_item("pr-1", "Build plan", "Phase 1 details")
        assert item.item_type is ReviewConsoleItemType.PLAN_REVIEW

    def test_plan_review_is_promptable(self):
        item = make_plan_review_item("pr-1", "Build plan", "")
        assert item.promptable is True

    def test_plan_review_does_not_require_response_by_default(self):
        item = make_plan_review_item("pr-1", "Build plan", "")
        assert item.requires_response is False

    def test_plan_review_has_inspect_action(self):
        item = make_plan_review_item("pr-1", "Build plan", "")
        assert ReviewConsoleAction.INSPECT in item.suggested_actions

    def test_plan_review_has_approve_action(self):
        item = make_plan_review_item("pr-1", "Build plan", "")
        assert ReviewConsoleAction.APPROVE in item.suggested_actions


# ---------------------------------------------------------------------------
# Approval gate
# ---------------------------------------------------------------------------


class TestApprovalGate:
    def test_item_type_is_approval_gate(self):
        assert _gate().item_type is ReviewConsoleItemType.APPROVAL_GATE

    def test_approval_gate_requires_response(self):
        assert _gate().requires_response is True

    def test_approval_gate_is_promptable(self):
        assert _gate().promptable is True

    def test_approval_gate_has_approve_action(self):
        assert ReviewConsoleAction.APPROVE in _gate().suggested_actions

    def test_approval_gate_has_reject_action(self):
        assert ReviewConsoleAction.REJECT in _gate().suggested_actions

    def test_approval_gate_has_modify_action(self):
        assert ReviewConsoleAction.MODIFY in _gate().suggested_actions

    def test_approval_gate_default_severity_is_warning(self):
        assert _gate().severity is ReviewConsoleSeverity.WARNING

    def test_approval_gate_not_automatic(self):
        assert _gate().is_automatic is False


# ---------------------------------------------------------------------------
# System finding
# ---------------------------------------------------------------------------


class TestSystemFinding:
    def test_item_type_is_system_finding(self):
        assert _finding().item_type is ReviewConsoleItemType.SYSTEM_FINDING

    def test_system_finding_is_not_promptable(self):
        assert _finding().promptable is False

    def test_system_finding_does_not_require_response(self):
        assert _finding().requires_response is False

    def test_system_finding_is_automatic(self):
        assert _finding().is_automatic is True

    def test_system_finding_has_acknowledge_action(self):
        assert ReviewConsoleAction.ACKNOWLEDGE in _finding().suggested_actions

    def test_system_finding_distinguishable_from_gate(self):
        gate = _gate()
        finding = _finding()
        assert gate.requires_response is not finding.requires_response
        assert gate.promptable is not finding.promptable


# ---------------------------------------------------------------------------
# Promptable flag
# ---------------------------------------------------------------------------


class TestPromptable:
    def test_cross_check_is_promptable(self):
        assert _cross().promptable is True

    def test_approval_gate_is_promptable(self):
        assert _gate().promptable is True

    def test_system_finding_is_not_promptable(self):
        assert _finding().promptable is False

    def test_promptable_item_can_be_created_directly(self):
        item = ReviewConsoleItem(
            id="x",
            item_type=ReviewConsoleItemType.ARTIFACT,
            severity=ReviewConsoleSeverity.INFO,
            title="Some artifact",
            content="",
            promptable=True,
            is_automatic=False,
            requires_response=False,
        )
        assert item.promptable is True


# ---------------------------------------------------------------------------
# ReviewConsoleQueue — enqueue and pending
# ---------------------------------------------------------------------------


class TestQueue:
    def test_empty_queue_has_no_items(self):
        assert ReviewConsoleQueue().items == []

    def test_enqueue_adds_item(self):
        queue = ReviewConsoleQueue()
        item = _cross()
        queue.enqueue(item)
        assert item in queue.items

    def test_enqueue_assigns_sequence(self):
        queue = ReviewConsoleQueue()
        item = _cross()
        queue.enqueue(item)
        assert item.sequence >= 0

    def test_enqueue_sequence_is_monotonically_increasing(self):
        queue = ReviewConsoleQueue()
        items = [_cross(f"cc-{i}", f"item {i}", "") for i in range(5)]
        for item in items:
            queue.enqueue(item)
        seqs = [i.sequence for i in queue.items]
        assert seqs == sorted(seqs)
        assert len(set(seqs)) == len(seqs)

    def test_pending_returns_all_pending_items(self):
        queue = ReviewConsoleQueue()
        queue.enqueue(_cross("a", "A", ""))
        queue.enqueue(_cross("b", "B", ""))
        assert len(queue.pending()) == 2

    def test_pending_excludes_responded_items(self):
        queue = ReviewConsoleQueue()
        item = _cross()
        queue.enqueue(item)
        item.status = ReviewConsoleItemStatus.RESPONDED
        assert item not in queue.pending()

    def test_pending_excludes_acknowledged_items(self):
        queue = ReviewConsoleQueue()
        item = _cross()
        queue.enqueue(item)
        item.status = ReviewConsoleItemStatus.ACKNOWLEDGED
        assert item not in queue.pending()

    def test_pending_excludes_dismissed_items(self):
        queue = ReviewConsoleQueue()
        item = _cross()
        queue.enqueue(item)
        item.status = ReviewConsoleItemStatus.DISMISSED
        assert item not in queue.pending()


# ---------------------------------------------------------------------------
# Pending items sort deterministically
# ---------------------------------------------------------------------------


class TestPendingOrder:
    def test_pending_sorted_by_sequence(self):
        queue = ReviewConsoleQueue()
        for i in range(5):
            queue.enqueue(_cross(f"id-{i}", f"item {i}", ""))
        pending = queue.pending()
        seqs = [i.sequence for i in pending]
        assert seqs == sorted(seqs)

    def test_pending_is_deterministic_across_calls(self):
        queue = ReviewConsoleQueue()
        for i in range(3):
            queue.enqueue(_cross(f"id-{i}", f"item {i}", ""))
        assert [i.id for i in queue.pending()] == [i.id for i in queue.pending()]

    def test_mixed_types_preserve_insertion_order_in_pending(self):
        queue = ReviewConsoleQueue()
        queue.enqueue(_cross("cc-1", "cross check", ""))
        queue.enqueue(_gate("gate-1", "gate", ""))
        queue.enqueue(_finding("sf-1", "finding", ""))
        ids = [i.id for i in queue.pending()]
        assert ids == ["cc-1", "gate-1", "sf-1"]


# ---------------------------------------------------------------------------
# Informational vs gated distinction
# ---------------------------------------------------------------------------


class TestInformationalVsGated:
    def test_pending_gates_contains_required_response_items(self):
        queue = ReviewConsoleQueue()
        queue.enqueue(_gate())
        queue.enqueue(_cross())
        gates = queue.pending_gates()
        assert any(i.item_type is ReviewConsoleItemType.APPROVAL_GATE for i in gates)

    def test_pending_gates_excludes_informational_items(self):
        queue = ReviewConsoleQueue()
        queue.enqueue(_gate("gate-1", "gate", ""))
        queue.enqueue(_cross("cc-1", "cross", ""))
        gates = queue.pending_gates()
        assert all(i.requires_response for i in gates)

    def test_informational_contains_non_response_items(self):
        queue = ReviewConsoleQueue()
        queue.enqueue(_gate("gate-1", "gate", ""))
        queue.enqueue(_cross("cc-1", "cross", ""))
        queue.enqueue(_finding("sf-1", "finding", ""))
        info = queue.informational()
        assert all(not i.requires_response for i in info)
        assert len(info) == 2

    def test_informational_excludes_gates(self):
        queue = ReviewConsoleQueue()
        queue.enqueue(_gate())
        queue.enqueue(_finding())
        info = queue.informational()
        assert not any(i.item_type is ReviewConsoleItemType.APPROVAL_GATE for i in info)


# ---------------------------------------------------------------------------
# Item type and severity are explicit enums
# ---------------------------------------------------------------------------


class TestExplicitEnums:
    def test_item_type_is_enum_instance(self):
        assert isinstance(_cross().item_type, ReviewConsoleItemType)

    def test_severity_is_enum_instance(self):
        assert isinstance(_cross().severity, ReviewConsoleSeverity)

    def test_status_is_enum_instance(self):
        assert isinstance(_cross().status, ReviewConsoleItemStatus)

    def test_all_item_types_are_reachable(self):
        expected = {
            ReviewConsoleItemType.CROSS_CHECK,
            ReviewConsoleItemType.PLAN_REVIEW,
            ReviewConsoleItemType.PROOF,
            ReviewConsoleItemType.SYSTEM_FINDING,
            ReviewConsoleItemType.ARTIFACT,
            ReviewConsoleItemType.APPROVAL_GATE,
            ReviewConsoleItemType.COMPARISON,
        }
        assert set(ReviewConsoleItemType) == expected

    def test_all_severities_are_reachable(self):
        expected = {
            ReviewConsoleSeverity.INFO,
            ReviewConsoleSeverity.WARNING,
            ReviewConsoleSeverity.ERROR,
            ReviewConsoleSeverity.CRITICAL,
        }
        assert set(ReviewConsoleSeverity) == expected

    def test_all_actions_are_reachable(self):
        expected = {
            ReviewConsoleAction.APPROVE,
            ReviewConsoleAction.REJECT,
            ReviewConsoleAction.MODIFY,
            ReviewConsoleAction.INSPECT,
            ReviewConsoleAction.ACKNOWLEDGE,
        }
        assert set(ReviewConsoleAction) == expected

    def test_default_status_is_pending(self):
        assert _cross().status is ReviewConsoleItemStatus.PENDING


# ---------------------------------------------------------------------------
# Pre-populated queue sequence safety
# ---------------------------------------------------------------------------


class TestQueueSequenceSafety:
    def test_prepopulated_queue_continues_sequence_after_max(self):
        existing = _cross("pre-1", "pre", "")
        existing.sequence = 10
        queue = ReviewConsoleQueue(items=[existing])
        new_item = _cross("new-1", "new", "")
        queue.enqueue(new_item)
        assert new_item.sequence == 11

    def test_prepopulated_queue_no_collision(self):
        items = []
        for i in range(3):
            item = _cross(f"pre-{i}", f"pre {i}", "")
            item.sequence = i * 5
            items.append(item)
        queue = ReviewConsoleQueue(items=items)
        new_item = _cross("new-1", "new", "")
        queue.enqueue(new_item)
        all_seqs = [i.sequence for i in queue.items]
        assert len(set(all_seqs)) == len(all_seqs)


# ---------------------------------------------------------------------------
# Queue response handling
# ---------------------------------------------------------------------------


class TestQueueResponses:
    def test_get_returns_item_by_id(self):
        queue = ReviewConsoleQueue()
        item = _cross("cc-find", "find me", "")
        queue.enqueue(item)
        assert queue.get("cc-find") is item

    def test_get_unknown_returns_none(self):
        assert ReviewConsoleQueue().get("missing") is None

    def test_require_unknown_raises_key_error(self):
        with pytest.raises(KeyError, match="missing"):
            ReviewConsoleQueue().require("missing")

    def test_respond_approve_marks_gate_responded(self):
        queue = ReviewConsoleQueue()
        item = _gate("gate-approve", "approve?", "")
        queue.enqueue(item)
        response = queue.respond("gate-approve", ReviewConsoleAction.APPROVE, "approved")
        assert item.status is ReviewConsoleItemStatus.RESPONDED
        assert isinstance(response, ReviewConsoleResponse)

    def test_respond_returns_response_record(self):
        queue = ReviewConsoleQueue()
        queue.enqueue(_gate("gate-response", "approve?", ""))
        response = queue.respond("gate-response", ReviewConsoleAction.REJECT, "not ready")
        assert response.item_id == "gate-response"
        assert response.action is ReviewConsoleAction.REJECT
        assert response.note == "not ready"

    def test_response_note_is_stripped(self):
        queue = ReviewConsoleQueue()
        queue.enqueue(_gate("gate-note", "approve?", ""))
        response = queue.respond("gate-note", ReviewConsoleAction.MODIFY, "  revise scope  ")
        assert response.note == "revise scope"

    def test_acknowledge_marks_item_acknowledged(self):
        queue = ReviewConsoleQueue()
        item = _cross("cc-ack", "ack", "")
        queue.enqueue(item)
        queue.acknowledge("cc-ack")
        assert item.status is ReviewConsoleItemStatus.ACKNOWLEDGED

    def test_acknowledged_item_leaves_pending(self):
        queue = ReviewConsoleQueue()
        item = _cross("cc-ack", "ack", "")
        queue.enqueue(item)
        queue.acknowledge("cc-ack")
        assert item not in queue.pending()

    def test_dismiss_marks_item_dismissed(self):
        queue = ReviewConsoleQueue()
        item = _cross("cc-dismiss", "dismiss", "")
        queue.enqueue(item)
        returned = queue.dismiss("cc-dismiss")
        assert item.status is ReviewConsoleItemStatus.DISMISSED
        assert returned is item

    def test_dismissed_item_leaves_pending(self):
        queue = ReviewConsoleQueue()
        item = _cross("cc-dismiss", "dismiss", "")
        queue.enqueue(item)
        queue.dismiss("cc-dismiss")
        assert item not in queue.pending()

    def test_respond_non_promptable_item_raises(self):
        queue = ReviewConsoleQueue()
        queue.enqueue(_finding("sys-1", "system", ""))
        with pytest.raises(ValueError, match="not promptable"):
            queue.respond("sys-1", ReviewConsoleAction.ACKNOWLEDGE)

    def test_respond_disallowed_action_raises(self):
        queue = ReviewConsoleQueue()
        queue.enqueue(_cross("cc-no", "cross", ""))
        with pytest.raises(ValueError, match="not allowed"):
            queue.respond("cc-no", ReviewConsoleAction.APPROVE)

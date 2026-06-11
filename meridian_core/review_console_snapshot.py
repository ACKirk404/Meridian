"""Backend snapshot for the Review Console surface shown in the UI."""

from datetime import datetime, timezone

from .review_console import (
    ReviewConsoleQueue,
    make_approval_gate,
    make_comparison_item,
    make_cross_check_item,
    make_plan_review_item,
    make_system_finding,
)

SNAPSHOT_VERSION = "review-console-snapshot-v1"


def review_console_snapshot() -> dict:
    """Return a display-safe Review Console queue snapshot."""
    observed_at = datetime(2026, 6, 7, 19, 0, tzinfo=timezone.utc)
    queue = _sample_queue()
    pending = queue.pending()
    pending_gates = queue.pending_gates()
    informational = queue.informational()
    return {
        "version": SNAPSHOT_VERSION,
        "source": "meridian_core.review_console_snapshot.review_console_snapshot",
        "harness": "Arbiter / Review Console",
        "summary": (
            "Review Console carries cross-checks, proof items, plan reviews, "
            "system findings, and approval gates outside the main Orchestrator Queue."
        ),
        "display_only": True,
        "mutation_authorized": False,
        "response_authorized": False,
        "execution_controls_visible": False,
        "raw_item_content_visible": False,
        "raw_worker_chat_visible": False,
        "queue": {
            "pending_count": len(pending),
            "pending_gate_count": len(pending_gates),
            "informational_count": len(informational),
            "items": [_safe_item(item) for item in pending],
        },
        "guardrails": [
            "display_only",
            "no_console_response_route",
            "no_approval_buttons",
            "no_raw_item_content",
            "no_raw_worker_chat",
            "no_branch_or_worktree_movement",
        ],
        "timestamp": observed_at.isoformat(),
    }


def _sample_queue() -> ReviewConsoleQueue:
    queue = ReviewConsoleQueue()
    queue.enqueue(
        make_cross_check_item(
            "rc-cross-check-ui",
            "Aegis cross-check needs inspection",
            "aegis-proof-ref:ui-cross-check",
        )
    )
    queue.enqueue(
        make_plan_review_item(
            "rc-plan-ui",
            "UI backend catch-up plan",
            "plan-ref:electron-ui-backend-catch-up",
        )
    )
    queue.enqueue(
        make_approval_gate(
            "rc-gate-ui",
            "Human gate required before live-control command staging",
            "gate-ref:vulcan-live-control",
        )
    )
    queue.enqueue(
        make_comparison_item(
            "rc-compare-ui",
            "Reviewer disagrees with builder on route-confidence posture",
            "comparison-ref:relay-independent-review",
        )
    )
    queue.enqueue(
        make_system_finding(
            "rc-system-ui",
            "Beacon liveness route is display-only",
            "system-ref:beacon-liveness",
        )
    )
    return queue


def _safe_item(item) -> dict:
    content_present = bool(item.content)
    return {
        "id": item.id,
        "item_type": item.item_type.value,
        "severity": item.severity.value,
        "title": item.title,
        "owner_harness": item.owner_harness,
        "content_present": content_present,
        "content_label": "<review_content>" if content_present else "none",
        "content_length": len(item.content) if content_present else 0,
        "promptable": item.promptable,
        "is_automatic": item.is_automatic,
        "requires_response": item.requires_response,
        "suggested_actions": [action.value for action in item.suggested_actions],
        "status": item.status.value,
        "sequence": item.sequence,
    }


def main() -> None:
    import json

    print(json.dumps(review_console_snapshot(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

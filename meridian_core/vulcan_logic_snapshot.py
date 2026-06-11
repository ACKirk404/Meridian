"""Backend snapshot for Vulcan Session Lifecycle logic shown in the harness UI."""

from datetime import datetime, timedelta, timezone

from .beacon import (
    live_state_advisory_evidence,
    recovery_readiness_advisory_evidence,
)
from .session_lifecycle import (
    HarnessRole,
    HealthState,
    OperationScope,
    PermissionContext,
    PermissionState,
    ProofState,
    ReviewCadenceState,
    SessionLifecycleState,
    SessionStatus,
    WorkflowResultKind,
    build_session_live_state_advisory_projection,
    build_session_live_state_evidence,
    evaluate_live_control_permission_gate,
    export_session_runtime_state_for_workflow_recovery,
    gather_prime_autonomy_input,
    summarize_recovery_readiness,
    summarize_session_permission_state,
    summarize_workflow_work_order_recovery,
)

SNAPSHOT_VERSION = "vulcan-session-lifecycle-v1"


def vulcan_logic_snapshot() -> dict:
    """Return the Vulcan capability list used by Bifrost's visible harness."""
    runtime_sample = _runtime_sample()
    return {
        "version": SNAPSHOT_VERSION,
        "source": "meridian_core.vulcan_logic_snapshot.vulcan_logic_snapshot",
        "harness": "Vulcan / Session Lifecycle",
        "summary": "Vulcan owns live session lifecycle, User Session targets, stale target guards, and session grouping behavior.",
        "display_only": True,
        "mutation_authorized": False,
        "execution_controls_visible": False,
        "raw_worker_chat_visible": False,
        "raw_filesystem_paths_visible": False,
        "runtime_sample": runtime_sample,
        "capabilitySections": [
            {
                "title": "Vulcan Job",
                "summary": "Keep session targets explicit, live, recoverable, and separate from Compass project context.",
                "rows": [
                    {"key": "owns", "value": "live session identity, lifecycle state, command plans, target persistence, stale target guard, lifecycle grouping"},
                    {"key": "does not own", "value": "Prime project context, model/vendor routing, portfolio boundary"},
                    {"key": "drift guard", "value": "User prompts require a bridge-confirmed live session target before send"},
                ],
            },
            {
                "title": "Session Definition Logic",
                "summary": "A session is a runtime work container, not a project, repo, initiative, or durable memory record.",
                "rows": [
                    {"key": "session", "value": "live or archived execution context with id, role, model, worktree, branch, queue, proof state, blocker state"},
                    {"key": "project relation", "value": "session may be assigned to a project but does not define project scope"},
                    {"key": "worktree relation", "value": "worktree/branch are runtime isolation evidence and command-plan boundaries"},
                    {"key": "proof relation", "value": "session can produce proof, but Aegis/review owns proof acceptance"},
                ],
            },
            {
                "title": "Lifecycle State Logic",
                "summary": "Vulcan names what each session is doing before any command can be proposed.",
                "rows": [
                    {"key": "states", "value": "starting, polling, running, waiting, blocked, review_gated, capacity_limited, stale, stopped, archived"},
                    {"key": "required evidence", "value": "queue file, worktree, branch, model, last read/write/prompt, proof state, blocker summary"},
                    {"key": "display rule", "value": "Bifrost shows typed state summaries, not raw worker chat"},
                ],
            },
            {
                "title": "Command Plan Logic",
                "summary": "Vulcan turns session operations into typed, auditable plans before execution.",
                "rows": [
                    {"key": "intents", "value": "spawn, watch, poll_queue, steer, stop_request, transfer, archive, restart, resteer, recover_from_limit, request_human_gate"},
                    {"key": "plan fields", "value": "target, reason, expected transition, evidence refs, queue, worktree/branch, gate result, executability"},
                    {"key": "human gate", "value": "branch movement, destructive actions, account-risking actions, and permission-boundary crossings stay non-executable until approved"},
                ],
            },
            {
                "title": "User Session Independence",
                "summary": "Changing Compass project context does not select, clear, send to, or retarget a User Session.",
                "rows": [
                    {"key": "User target key", "value": "meridian.user-session.target.v1"},
                    {"key": "project key", "value": "meridian.session.project"},
                    {"key": "routing rule", "value": "User prompts require a bridge-confirmed live session target"},
                ],
            },
            {
                "title": "Project-Aware Session Grouping",
                "summary": "User Sessions remain grouped by project while the active Compass project is visibly marked.",
                "rows": [
                    {"key": "complete list", "value": "all routable live Meridian worktree sessions remain visible"},
                    {"key": "active marker", "value": "matching project optgroup is labeled active project"},
                    {"key": "empty project", "value": "status shows no live sessions for selected project without faking sessions"},
                ],
            },
            {
                "title": "Stale Target Guard",
                "summary": "Closed or unavailable targets are visible blockers, not silent reroutes.",
                "rows": [
                    {"key": "unavailable label", "value": "Selected session unavailable"},
                    {"key": "status text", "value": "selected session unavailable"},
                    {"key": "send behavior", "value": "blocked with readable target error"},
                ],
            },
            {
                "title": "Lifecycle Boundary",
                "summary": "Session lifecycle controls are separate from project selection and archive/delete actions.",
                "rows": [
                    {"key": "project switch", "value": "does not close, archive, delete, or stop a session"},
                    {"key": "reset/reload", "value": "preserve live worktree sessions and archive state"},
                    {"key": "future work", "value": "write-through close, archive-on-close, and stop-before-close remain explicit Vulcan items"},
                ],
            },
            {
                "title": "Cross-Harness Relationship Logic",
                "summary": "Vulcan provides runtime session truth to other harnesses without taking over their decisions.",
                "rows": [
                    {"key": "Prime", "value": "Prime proposes or approves high-level session actions"},
                    {"key": "Beacon", "value": "Beacon observes heartbeat/liveness; Vulcan records lifecycle state and recovery options"},
                    {"key": "Relay", "value": "Relay chooses model/vendor/session route; Vulcan confirms target session existence and state"},
                    {"key": "Compass", "value": "Compass defines project context; Vulcan confirms live sessions assigned to that context"},
                    {"key": "Aegis", "value": "Aegis gates risky session command plans before execution"},
                ],
            },
        ],
    }


def _runtime_sample() -> dict:
    """Build a deterministic display-only sample from reviewed runtime APIs."""
    observed_at = datetime(2026, 6, 7, 18, 0, tzinfo=timezone.utc)
    session = _sample_session(observed_at)
    live_evidence = build_session_live_state_evidence(
        session,
        timestamp=observed_at,
    )
    live_projection = build_session_live_state_advisory_projection(
        live_evidence,
        timestamp=observed_at,
    )
    permission_summary = summarize_session_permission_state(
        session,
        approvals_pending=(("session-ui-live-build-2", "aegis-command-plan-review"),),
        timestamp=observed_at,
    )
    workflow_summary = summarize_workflow_work_order_recovery(
        session,
        work_order_id="workflow-ui-live-state",
        heartbeat_emitted_at=observed_at - timedelta(minutes=12),
        result_kind=WorkflowResultKind.PENDING,
        timestamp=observed_at,
    )
    runtime_export = export_session_runtime_state_for_workflow_recovery(
        session,
        permission_summary=permission_summary,
        workflow_recovery_summary=workflow_summary,
        timestamp=observed_at,
    )
    permission_gate = evaluate_live_control_permission_gate(
        session,
        runtime_export,
        timestamp=observed_at,
    )
    recovery_readiness = summarize_recovery_readiness(
        runtime_export,
        permission_gate,
        timestamp=observed_at,
    )
    beacon_live_state = live_state_advisory_evidence(
        live_projection,
        now=observed_at,
    )
    beacon_readiness = recovery_readiness_advisory_evidence(
        recovery_readiness,
        now=observed_at,
    )
    autonomy_input = gather_prime_autonomy_input(
        sessions=(session,),
        queues_by_harness={session.harness_role.value: (session.assigned_queue_file,)},
        approvals_pending=(("session-ui-live-build-2", "aegis-command-plan-review"),),
        restart_resteer_findings=tuple(permission_summary.restart_resteer_findings),
        recent_completions=("session-ui-prev-build-1:archived", "session-ui-prev-build-0:closed"),
        timestamp=observed_at,
    )

    return {
        "session_live_state_evidence": live_evidence.to_dict(),
        "session_live_state_projection": live_projection.to_dict(),
        "permission_summary": {
            "session_id": permission_summary.session_id,
            "permission_state": permission_summary.permission_state.value,
            "can_accept_work": permission_summary.can_accept_work,
            "blockers": list(permission_summary.blockers),
            "review_gate_blockers": list(permission_summary.review_gate_blockers),
            "restart_resteer_findings": [
                finding.finding_type.value
                for finding in permission_summary.restart_resteer_findings
            ],
        },
        "workflow_recovery": workflow_summary.to_dict(),
        "runtime_state_export": runtime_export.to_dict(),
        "prime_autonomy_input": {
            "current_session_ids": [session.session_id for session in autonomy_input.current_sessions],
            "queues_by_harness": {harness: list(queue_files) for harness, queue_files in autonomy_input.queues_by_harness},
            "approvals_pending": list(autonomy_input.approvals_pending),
            "restart_resteer_findings": [
                finding.finding_type.value for finding in autonomy_input.restart_resteer_findings
            ],
            "recent_completions": list(autonomy_input.recent_completions),
            "permission_summaries": [
                {
                    "session_id": summary.session_id,
                    "permission_state": summary.permission_state.value,
                    "approved_operations": [operation.value for operation in summary.approved_operations],
                    "blockers": list(summary.blockers),
                    "approvals_pending": list(summary.approvals_pending),
                    "review_gate_blockers": list(summary.review_gate_blockers),
                    "restart_resteer_findings": [
                        finding.finding_type.value for finding in summary.restart_resteer_findings
                    ],
                    "can_accept_work": summary.can_accept_work,
                    "timestamp": summary.timestamp.isoformat(),
                }
                for summary in autonomy_input.permission_summaries
            ],
            "timestamp": autonomy_input.timestamp.isoformat(),
        },
        "live_control_permission_gate": permission_gate.to_dict(),
        "recovery_readiness": recovery_readiness.to_dict(),
        "beacon_advisories": [
            beacon_live_state.to_dict(),
            beacon_readiness.to_dict(),
        ],
        "display_contract": {
            "display_only": True,
            "mutation_authorized": False,
            "execution_controls_visible": False,
            "raw_worker_chat_visible": False,
            "raw_filesystem_paths_visible": False,
        },
    }


def _sample_session(observed_at: datetime) -> SessionLifecycleState:
    """Create a deterministic session snapshot without exposing local paths."""
    permission_context = PermissionContext(
        approved_by="prime",
        approval_scope=frozenset({OperationScope.RESTART}),
        escalation_gate=False,
        escalation_reason=None,
        branch_permission_state=PermissionState.LOCKED_BY_DEFAULT,
        approved_by_secondary=None,
        unlock_expiry=None,
        task_scope=None,
        last_permission_change=observed_at - timedelta(minutes=45),
    )
    return SessionLifecycleState(
        session_id="session-ui-live-build-2",
        session_name="Build 2 UI Integration",
        project_name="Meridian",
        project_path="project-ref:meridian",
        harness_role=HarnessRole.UI,
        assigned_queue_file="live-build-2",
        model_provider="codex",
        model_name="gpt-5.3-codex-spark",
        status=SessionStatus.STALE,
        worktree_path="worktree-ref:ui-live-build-2",
        branch_name="main",
        current_task_id="ui-backend-catch-up",
        last_queue_read_at=observed_at - timedelta(minutes=16),
        last_queue_write_at=observed_at - timedelta(minutes=21),
        last_prompt_sent_at=observed_at - timedelta(minutes=42),
        last_prompt_payload_size=1840,
        review_cadence_state=ReviewCadenceState.PENDING,
        proof_state=ProofState.WORKTREE_VERIFIED,
        health_state=HealthState.STALE,
        blocker_summary="Recovery staging requires Aegis review.",
        permission_context=permission_context,
    )


def main() -> None:
    import json

    print(json.dumps(vulcan_logic_snapshot(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

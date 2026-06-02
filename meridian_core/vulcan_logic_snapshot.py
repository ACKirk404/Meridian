"""Backend snapshot for Vulcan Session Lifecycle logic shown in the harness UI."""

SNAPSHOT_VERSION = "vulcan-session-lifecycle-v1"


def vulcan_logic_snapshot() -> dict:
    """Return the Vulcan capability list used by Bifrost's visible harness."""
    return {
        "version": SNAPSHOT_VERSION,
        "source": "meridian_core.vulcan_logic_snapshot.vulcan_logic_snapshot",
        "harness": "Vulcan / Session Lifecycle",
        "summary": "Vulcan owns live session lifecycle, User Session targets, stale target guards, and session grouping behavior.",
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


def main() -> None:
    import json

    print(json.dumps(vulcan_logic_snapshot(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

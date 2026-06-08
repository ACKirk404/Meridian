"""Backend snapshot for Beacon liveness and advisory evidence shown in the UI."""

from datetime import datetime, timezone
from pathlib import Path

from .beacon import LivenessTarget, check_harness_liveness

SNAPSHOT_VERSION = "beacon-liveness-v1"


def beacon_liveness_snapshot() -> dict:
    """Return a display-safe Beacon liveness/advisory snapshot."""
    observed_at = datetime(2026, 6, 7, 18, 30, tzinfo=timezone.utc)
    targets = (
        LivenessTarget(
            "beacon-ui-contract",
            Path("runtime-sentinel") / "beacon-ui-contract.sentinel",
            stale_after_seconds=300,
        ),
    )
    heartbeats = check_harness_liveness(targets, now=observed_at)
    return {
        "version": SNAPSHOT_VERSION,
        "source": "meridian_core.beacon_liveness_snapshot.beacon_liveness_snapshot",
        "harness": "Beacon / Liveness",
        "summary": (
            "Beacon converts sentinel freshness and Session Lifecycle advisory "
            "evidence into display-safe heartbeat/readiness signals."
        ),
        "display_only": True,
        "mutation_authorized": False,
        "execution_controls_visible": False,
        "raw_worker_chat_visible": False,
        "raw_filesystem_paths_visible": False,
        "observation_mode": "contract_sample:no_live_sentinels_configured",
        "heartbeats": [_safe_heartbeat(heartbeat) for heartbeat in heartbeats],
        "advisory_families": [
            "command_plan",
            "permission_summary",
            "workflow_recovery",
            "runtime_state",
            "recovery_readiness",
            "command_plan_staging",
            "live_state",
            "v2_command_plan_preview",
            "deepseek_validation",
        ],
        "guardrails": [
            "display_only",
            "no_session_control",
            "no_process_inspection",
            "no_model_calls",
            "no_branch_or_worktree_movement",
            "no_raw_sentinel_paths",
            "no_raw_worker_chat",
        ],
    }


def _safe_heartbeat(heartbeat) -> dict:
    """Project a Beacon Heartbeat without raw sentinel paths."""
    blockers = []
    for blocker in heartbeat.blockers:
        if "missing sentinel" in blocker:
            blockers.append("missing sentinel")
        elif "stale for" in blocker:
            blockers.append("stale sentinel")
        else:
            blockers.append("heartbeat blocker")
    return {
        "harness_id": heartbeat.harness_id,
        "status": heartbeat.status.value,
        "current_work_present": bool(heartbeat.current_work),
        "current_work_label": "<sentinel_path>" if heartbeat.current_work else "none",
        "last_event": _safe_last_event(heartbeat.last_event),
        "blockers": blockers,
        "updated_at": heartbeat.updated_at.isoformat(),
    }


def _safe_last_event(last_event: str) -> str:
    if "sentinel updated" in last_event:
        return last_event
    if "liveness sentinel missing" in last_event:
        return "liveness sentinel missing"
    return "heartbeat event"


def main() -> None:
    import json

    print(json.dumps(beacon_liveness_snapshot(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

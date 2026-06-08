"""Backend snapshot for the planning-only Federation harness surface."""

SNAPSHOT_VERSION = "federation-horizon-v1"


def federation_horizon_snapshot() -> dict:
    """Return the reviewed planning-only Federation boundary for the UI."""
    return {
        "version": SNAPSHOT_VERSION,
        "source": "docs/federation-harness-horizon.md",
        "harness": "Federation / Horizon",
        "summary": (
            "Federation is the horizon harness for connecting one Meridian to "
            "another Meridian through explicit consent, typed handoffs, and "
            "local proof boundaries. V2 defines the architecture only."
        ),
        "display_only": True,
        "planning_only": True,
        "runtime_authorized": False,
        "mutation_authorized": False,
        "network_protocol_authorized": False,
        "remote_execution_authorized": False,
        "shared_state_authorized": False,
        "raw_memory_visible": False,
        "raw_queue_visible": False,
        "raw_worker_chat_visible": False,
        "raw_filesystem_paths_visible": False,
        "owner": {
            "harness_owner": "Federation Harness",
            "supervising_intelligence": "Prime",
            "safety_gate": "Aegis",
            "ui_surface": "Bifrost harness panel",
        },
        "safe_discovery_fields": [
            "instance name",
            "user-approved project alias",
            "supported harness capabilities",
            "accepted work-order shapes",
            "public proof/result schema versions",
        ],
        "unsafe_by_default": [
            "raw memory stores",
            "raw queue files",
            "raw worker transcripts",
            "filesystem paths beyond the approved project alias",
            "credentials or vendor account state",
        ],
        "permission_boundaries": [
            "no cross-Meridian action without explicit consent",
            "no silent branch movement",
            "no shared worktree",
            "no hidden account-based automation",
            "no implicit durable memory import",
            "no remote execution without a typed work order and proof return",
        ],
        "handoff_packet_types": [
            "ProjectSummary",
            "TaskRequest",
            "ProofPacket",
            "ReviewResult",
            "RefusalOrBlocker",
        ],
        "panel_implications": [
            "known Meridian instances",
            "permission state",
            "active handoffs",
            "pending proof packets",
            "blocked/refused requests",
            "recent federation events",
        ],
        "out_of_v2_scope": [
            "network protocol",
            "authentication implementation",
            "marketplace/public registry",
            "shared mutable project state",
            "cross-account automation",
            "live multi-user editing",
        ],
    }


def main() -> None:
    import json

    print(json.dumps(federation_horizon_snapshot(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

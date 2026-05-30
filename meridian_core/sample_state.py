"""
Sample portfolio, heartbeat, and provider adapter state.

Used for tests and early demos. Not production data.
Initiatives include Meridian itself, Advanced AI Concepts, and CareGuide.
"""

from __future__ import annotations

from .models import (
    AdapterTier,
    Heartbeat,
    HeartbeatStatus,
    Initiative,
    MoveKind,
    NextMove,
    Objective,
    Portfolio,
    Project,
    Proof,
    ProviderAdapter,
    Task,
    Venture,
)


def make_sample_portfolio() -> Portfolio:
    # --- Initiative: Meridian V0 ---
    meridian_initiative = Initiative(
        id="init_meridian_v0",
        title="Build Meridian V0",
        description=(
            "Prove the local orchestrator model: portfolio state, harness heartbeat, "
            "kernel decision loop, session injection, and Scott bottleneck queue."
        ),
        objectives=[
            Objective(
                id="obj_meridian_core",
                title="Build meridian_core skeleton",
                description="Typed domain objects, decision engine, events, injections, and tests.",
                success_criteria=[
                    "meridian_core package is importable",
                    "Decision loop produces next moves and bottlenecks from sample state",
                    "Blocked harness produces injection or bottleneck",
                    "All tests pass",
                ],
            ),
        ],
        tasks=[
            Task(
                id="task_meridian_core_skeleton",
                title="Create meridian_core Python package",
                description="models.py, sample_state.py, decisions.py, events.py, injections.py",
                objective_id="obj_meridian_core",
                status="in_progress",
            ),
        ],
        next_moves=[
            NextMove(
                id="move_build_core",
                description="Build meridian_core Python skeleton with domain objects, decision engine, and tests",
                kind=MoveKind.AUTONOMOUS,
                objective_id="obj_meridian_core",
                proof_required=True,
                proof=Proof(
                    id="proof_tests_pass",
                    description="pytest test suite passes",
                    proof_type="test",
                    command="pytest tests/",
                    verified=False,
                ),
                reason="First coding milestone — proves the shape of the local brain",
            ),
        ],
    )

    meridian_project = Project(
        id="proj_meridian",
        title="Meridian",
        description="Local proactive portfolio orchestrator",
        repo_url="https://github.com/AesopScott/Meridian.git",
        local_path="C:\\Users\\scott\\Code\\Meridian",
        initiatives=[meridian_initiative],
    )

    # --- Initiative: Advanced AI Concepts event operations ---
    aaic_initiative = Initiative(
        id="init_aaic_events",
        title="Improve Advanced AI Concepts event operations",
        description="Automate Meetup event copying and reduce Scott's manual coordination overhead.",
        objectives=[
            Objective(
                id="obj_aaic_copy_events",
                title="Automate Meetup event copying",
                description="Events propagate to multiple Meetup groups without manual re-entry.",
                success_criteria=[
                    "Events are copied without creating duplicates",
                    "Copy automation respects scheduling conflicts",
                ],
            ),
        ],
        next_moves=[
            NextMove(
                id="move_aaic_choose_approach",
                description="Choose between Meetup API, scraping, and Zapier for event copy automation",
                kind=MoveKind.SCOTT_REQUIRED,
                objective_id="obj_aaic_copy_events",
                reason=(
                    "Different approaches have meaningfully different cost and terms trade-offs; "
                    "Scott should decide before any implementation begins."
                ),
            ),
        ],
    )

    aaic_venture = Venture(
        id="venture_aaic",
        title="Advanced AI Concepts",
        description="AI community, meetups, and education venture",
        projects=[
            Project(
                id="proj_aaic_ops",
                title="AAIC Operations",
                description="Event management and community operations",
                initiatives=[aaic_initiative],
            ),
        ],
    )

    # --- Initiative: CareGuide production readiness ---
    careguide_initiative = Initiative(
        id="init_careguide_prod",
        title="Prepare CareGuide for production",
        description="Advance CareGuide toward a production-ready state and public launch.",
        objectives=[
            Objective(
                id="obj_careguide_stage",
                title="Promote CareGuide to staging",
                description="All critical tests pass; stage environment is healthy.",
                success_criteria=[
                    "CI passes",
                    "Stage environment responds to health check",
                    "No critical review findings remain open",
                ],
            ),
        ],
        next_moves=[
            NextMove(
                id="move_careguide_review",
                description="Run /review-pr on open CareGuide PRs",
                kind=MoveKind.AUTONOMOUS,
                objective_id="obj_careguide_stage",
                proof_required=False,
                reason="Safe autonomous move — review reads only, does not modify the project",
            ),
        ],
    )

    careguide_venture = Venture(
        id="venture_careguide",
        title="CareGuide",
        description="Healthcare navigation product",
        projects=[
            Project(
                id="proj_careguide_app",
                title="CareGuide App",
                description="Healthcare navigation app and backend",
                initiatives=[careguide_initiative],
            ),
        ],
    )

    return Portfolio(
        ventures=[aaic_venture, careguide_venture],
        projects=[meridian_project],
    )


def make_sample_heartbeats() -> list[Heartbeat]:
    return [
        Heartbeat(
            harness_id="agent_harness",
            status=HeartbeatStatus.ALIVE,
            current_work=None,
            last_event="Idle — ready for next directive",
            blockers=[],
        ),
        Heartbeat(
            harness_id="memory_harness",
            status=HeartbeatStatus.BUSY,
            current_work="Indexing recent session events",
            last_event="Indexed 12 new memories",
            blockers=[],
        ),
        Heartbeat(
            harness_id="git_harness",
            status=HeartbeatStatus.BLOCKED,
            current_work="Waiting to push branch",
            last_event="Push failed: remote rejected",
            blockers=["authentication token expired", "remote branch protection rule"],
        ),
    ]


def make_sample_adapters() -> list[ProviderAdapter]:
    return [
        ProviderAdapter(
            id="adapter_anthropic_api",
            name="Anthropic API",
            provider="Anthropic",
            tier=AdapterTier.OFFICIAL_API_SUPPORTED,
            description="Official Anthropic API — BYOK",
            enabled_for_public_build=True,
        ),
        ProviderAdapter(
            id="adapter_openrouter",
            name="OpenRouter",
            provider="OpenRouter",
            tier=AdapterTier.OFFICIAL_API_SUPPORTED,
            description="Multi-provider routing via official API",
            enabled_for_public_build=True,
        ),
        ProviderAdapter(
            id="adapter_ollama",
            name="Ollama",
            provider="Local",
            tier=AdapterTier.LOCAL_MODEL_SUPPORTED,
            description="Local model inference via Ollama",
            enabled_for_public_build=True,
        ),
        ProviderAdapter(
            id="adapter_claude_cli",
            name="Claude Code CLI",
            provider="Anthropic",
            tier=AdapterTier.EXPERIMENTAL_USER_CONFIGURED,
            description=(
                "Claude Code CLI session automation — experimental, "
                "user must comply with Anthropic terms."
            ),
            enabled_for_public_build=False,
        ),
        ProviderAdapter(
            id="adapter_codex_cli",
            name="Codex CLI",
            provider="OpenAI",
            tier=AdapterTier.EXPERIMENTAL_USER_CONFIGURED,
            description=(
                "Codex CLI session automation — experimental, "
                "user must comply with OpenAI terms."
            ),
            enabled_for_public_build=False,
        ),
        ProviderAdapter(
            id="adapter_claude_consumer",
            name="Claude.ai Consumer Web",
            provider="Anthropic",
            tier=AdapterTier.DISABLED_FOR_PUBLIC_BUILD,
            description="Consumer web automation — not for use in public build.",
            enabled_for_public_build=False,
        ),
    ]

"""
Meridian local brain skeleton.

Proactive portfolio orchestrator core — domain objects, decision engine,
events, and session injection modeling. No real model calls or UI yet.
"""

from .models import (
    Portfolio,
    Venture,
    Project,
    Initiative,
    Objective,
    Task,
    NextMove,
    Harness,
    Heartbeat,
    Workflow,
    Decision,
    ScottBottleneck,
    Proof,
    Artifact,
    SessionInjection,
    ProviderAdapter,
    HeartbeatStatus,
    InjectionMode,
    AdapterTier,
    Priority,
    MoveKind,
)
from .decisions import run_decision_loop, DecisionResult
from .events import EventRecorder, Event, EventKind
from .injections import make_injection
from .intention import (
    ObjectiveStage,
    MissionObjectiveLine,
    ProgressIntention,
    build_progress_intention,
)
from .mission import (
    load_mission,
    find_mission_file,
    Mission,
    MissionLoadError,
)
from .wake import build_wake_brief, WakeBrief, WakeLine, WakeStatus
from .objectives import get_mission_objectives, format_mission_objectives_text
from .risk import RiskTier, RiskMode, RiskAssessment, assess_tier, assess_blocked_action
from .relay import (
    RoutingMode,
    ModelRole,
    ContextStrategy,
    CostPosture,
    RelayLane,
    RelayRoute,
    route_from_tier,
    route_from_assessment,
)
from .aegis import (
    EvidenceType,
    EvidenceStatus,
    EvidenceSeverity,
    AegisEvidence,
    ProofTrail,
    evidence_from_cross_check,
)
from .review_console import (
    ReviewConsoleItemType,
    ReviewConsoleSeverity,
    ReviewConsoleAction,
    ReviewConsoleItemStatus,
    ReviewConsoleItem,
    ReviewConsoleResponse,
    ReviewConsoleQueue,
    make_cross_check_item,
    make_plan_review_item,
    make_approval_gate,
    make_system_finding,
    make_prompt_metrics_finding,
)
from .builds import (
    HarnessMaturity,
    HarnessBuild,
    MeridianBuild,
    BuildRegistry,
    make_initial_registry,
)
from .filemap import FileMapEntry, FileMap, FileArea, make_default_map
from .council import (
    CouncilRole,
    CouncilPosition,
    CouncilPlan,
    default_council_positions,
    council_plan_for_tier,
)
from .prompt_budget import (
    PromptBudgetTier,
    PromptBudget,
    PromptBudgetPlan,
    prompt_budget_for_risk_tier,
)
from .prompt_metrics import (
    PromptMetricSample,
    PromptMetricSummary,
    PromptPerformanceStatus,
    summarize_prompt_metrics,
)

__all__ = [
    # -- Core domain models --------------------------------------------------
    "Portfolio",
    "Venture",
    "Project",
    "Initiative",
    "Objective",
    "Task",
    "NextMove",
    "Harness",
    "Heartbeat",
    "Workflow",
    "Decision",
    "ScottBottleneck",
    "Proof",
    "Artifact",
    "SessionInjection",
    "ProviderAdapter",
    "HeartbeatStatus",
    "InjectionMode",
    "AdapterTier",
    "Priority",
    "MoveKind",
    # -- Decision loop --------------------------------------------------------
    "run_decision_loop",
    "DecisionResult",
    # -- Events and injections ------------------------------------------------
    "EventRecorder",
    "Event",
    "EventKind",
    "make_injection",
    # -- Progress intention / Compass -----------------------------------------
    "ObjectiveStage",
    "MissionObjectiveLine",
    "ProgressIntention",
    "build_progress_intention",
    # -- Mission boot ---------------------------------------------------------
    "load_mission",
    "find_mission_file",
    "Mission",
    "MissionLoadError",
    # -- Wake sequence --------------------------------------------------------
    "build_wake_brief",
    "WakeBrief",
    "WakeLine",
    "WakeStatus",
    # -- Mission objectives ---------------------------------------------------
    "get_mission_objectives",
    "format_mission_objectives_text",
    # -- Risk tier engine -----------------------------------------------------
    "RiskTier",
    "RiskMode",
    "RiskAssessment",
    "assess_tier",
    "assess_blocked_action",
    # -- Relay routing --------------------------------------------------------
    "RoutingMode",
    "ModelRole",
    "ContextStrategy",
    "CostPosture",
    "RelayLane",
    "RelayRoute",
    "route_from_tier",
    "route_from_assessment",
    # -- Aegis / proof harness ------------------------------------------------
    "EvidenceType",
    "EvidenceStatus",
    "EvidenceSeverity",
    "AegisEvidence",
    "ProofTrail",
    "evidence_from_cross_check",
    # -- Review Console -------------------------------------------------------
    "ReviewConsoleItemType",
    "ReviewConsoleSeverity",
    "ReviewConsoleAction",
    "ReviewConsoleItemStatus",
    "ReviewConsoleItem",
    "ReviewConsoleResponse",
    "ReviewConsoleQueue",
    "make_cross_check_item",
    "make_plan_review_item",
    "make_approval_gate",
    "make_system_finding",
    "make_prompt_metrics_finding",
    # -- Build and maturity registry ------------------------------------------
    "HarnessMaturity",
    "HarnessBuild",
    "MeridianBuild",
    "BuildRegistry",
    "make_initial_registry",
    # -- File map knowledge tracker -------------------------------------------
    "FileMapEntry",
    "FileMap",
    "FileArea",
    "make_default_map",
    # -- Council cognition ----------------------------------------------------
    "CouncilRole",
    "CouncilPosition",
    "CouncilPlan",
    "default_council_positions",
    "council_plan_for_tier",
    # -- Relay prompt budget --------------------------------------------------
    "PromptBudgetTier",
    "PromptBudget",
    "PromptBudgetPlan",
    "prompt_budget_for_risk_tier",
    # -- Relay prompt metrics -------------------------------------------------
    "PromptMetricSample",
    "PromptMetricSummary",
    "PromptPerformanceStatus",
    "summarize_prompt_metrics",
]

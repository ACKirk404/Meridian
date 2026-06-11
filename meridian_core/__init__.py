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
    VendorRouteKind,
    AccessRouteClass,
    SessionAction,
    RouteTrustState,
    RelayLane,
    RelayRouteAudit,
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
from .evidence_safety import (
    EvidenceSafetyCategory,
    EvidenceSafetyFinding,
    EvidenceSafetyProof,
    EvidenceSafetySeverity,
    EvidenceSafetyStatus,
    scan_evidence_artifact,
    scan_evidence_artifacts,
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
from .prompt_packet import (
    PromptPacket,
    PromptPacketValidationError,
    build_prompt_packet,
)
from .beacon import LivenessTarget, check_harness_liveness
from .planning import (
    PlanningAnswer,
    PlanningQuestion,
    PlanningRecommendation,
    PlanningBrief,
    PlanningContext,
    build_planning_brief,
)

from .cockpit_state import (
    CockpitStatus,
    QueuePolicy,
    ProgressEventCategory,
    EventSeverity,
    LaneCockpitStatus,
    LaneSummary,
    ProgressEvent,
    PrimeCockpitSnapshot,
    sort_lanes,
    filter_events,
    lane_summary_counts,
)
from .cockpit_provider import (
    build_snapshot,
    demo_snapshot,
)
from .cognition_policy import (
    CognitionActionType,
    CognitionLane,
    CognitionDecision,
    CognitionPolicy,
    CognitionPolicyResult,
    cognition_policy_for_tier,
    evaluate_cognition_policy,
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
    "VendorRouteKind",
    "AccessRouteClass",
    "SessionAction",
    "RouteTrustState",
    "RelayLane",
    "RelayRouteAudit",
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
    "EvidenceSafetyCategory",
    "EvidenceSafetyFinding",
    "EvidenceSafetyProof",
    "EvidenceSafetySeverity",
    "EvidenceSafetyStatus",
    "scan_evidence_artifact",
    "scan_evidence_artifacts",
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
    # -- Prompt packet --------------------------------------------------------
    "PromptPacket",
    "PromptPacketValidationError",
    "build_prompt_packet",
    # -- Beacon liveness -----------------------------------------------------
    "LivenessTarget",
    "check_harness_liveness",
    # -- Planning harness ----------------------------------------------------
    "PlanningAnswer",
    "PlanningQuestion",
    "PlanningRecommendation",
    "PlanningBrief",
    "PlanningContext",
    "build_planning_brief",
    # -- Cockpit state --------------------------------------------------------
    "CockpitStatus",
    "QueuePolicy",
    "ProgressEventCategory",
    "EventSeverity",
    "LaneCockpitStatus",
    "LaneSummary",
    "ProgressEvent",
    "PrimeCockpitSnapshot",
    "sort_lanes",
    "filter_events",
    "lane_summary_counts",
    # -- Cockpit provider ----------------------------------------------------
    "build_snapshot",
    "demo_snapshot",
    # -- V2 Cognition policy --------------------------------------------------
    "CognitionActionType",
    "CognitionLane",
    "CognitionDecision",
    "CognitionPolicy",
    "CognitionPolicyResult",
    "cognition_policy_for_tier",
    "evaluate_cognition_policy",
]

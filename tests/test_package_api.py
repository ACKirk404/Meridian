"""Import smoke tests for Meridian's intentional package-root API."""

from __future__ import annotations

import meridian_core


def test_package_all_is_unique():
    assert len(meridian_core.__all__) == len(set(meridian_core.__all__))


def test_core_decision_api_exports():
    from meridian_core import DecisionResult, Event, EventKind, EventRecorder, make_injection
    from meridian_core import run_decision_loop

    assert DecisionResult
    assert Event
    assert EventKind
    assert EventRecorder
    assert make_injection
    assert run_decision_loop


def test_mission_wake_and_compass_exports():
    from meridian_core import Mission, MissionLoadError, ObjectiveStage, ProgressIntention
    from meridian_core import build_progress_intention, build_wake_brief
    from meridian_core import find_mission_file, format_mission_objectives_text
    from meridian_core import get_mission_objectives, load_mission

    assert Mission
    assert MissionLoadError
    assert ObjectiveStage
    assert ProgressIntention
    assert build_progress_intention
    assert build_wake_brief
    assert find_mission_file
    assert format_mission_objectives_text
    assert get_mission_objectives
    assert load_mission


def test_risk_relay_aegis_review_console_exports():
    from meridian_core import AegisEvidence, EvidenceSeverity, ProofTrail, RelayRoute
    from meridian_core import AccessRouteClass, RelayRouteAudit, RouteTrustState
    from meridian_core import ReviewConsoleItem, ReviewConsoleQueue, ReviewConsoleResponse
    from meridian_core import RiskTier, SessionAction, VendorRouteKind
    from meridian_core import assess_blocked_action, assess_tier, evidence_from_cross_check
    from meridian_core import make_approval_gate, route_from_tier

    assert AccessRouteClass
    assert AegisEvidence
    assert EvidenceSeverity
    assert ProofTrail
    assert RelayRouteAudit
    assert RelayRoute
    assert ReviewConsoleItem
    assert ReviewConsoleQueue
    assert ReviewConsoleResponse
    assert RouteTrustState
    assert RiskTier
    assert SessionAction
    assert VendorRouteKind
    assert assess_blocked_action
    assert assess_tier
    assert evidence_from_cross_check
    assert make_approval_gate
    assert route_from_tier


def test_evidence_safety_exports():
    from meridian_core import (
        EvidenceSafetyCategory,
        EvidenceSafetyFinding,
        EvidenceSafetyProof,
        EvidenceSafetySeverity,
        EvidenceSafetyStatus,
        scan_evidence_artifact,
        scan_evidence_artifacts,
    )

    assert EvidenceSafetyCategory
    assert EvidenceSafetyFinding
    assert EvidenceSafetyProof
    assert EvidenceSafetySeverity
    assert EvidenceSafetyStatus
    assert scan_evidence_artifact
    assert scan_evidence_artifacts

    for name in (
        "EvidenceSafetyCategory",
        "EvidenceSafetyFinding",
        "EvidenceSafetyProof",
        "EvidenceSafetySeverity",
        "EvidenceSafetyStatus",
        "scan_evidence_artifact",
        "scan_evidence_artifacts",
    ):
        assert name in meridian_core.__all__, f"{name} missing from __all__"


def test_prompt_metrics_bridge_exports():
    from meridian_core import make_prompt_metrics_finding

    assert make_prompt_metrics_finding


def test_cross_check_authority_exports():
    from meridian_core import (
        CrossCheckDisposition,
        CrossCheckDispositionAction,
        CrossCheckFinding,
        CrossCheckFindingStatus,
        CrossCheckRepairRoute,
        CrossCheckRunRequest,
        CrossCheckRunResult,
        CrossCheckRunStatus,
        CrossCheckSeverity,
        CrossCheckValidationError,
        CrossCheckVerificationRequest,
        CrossCheckVerificationResult,
        dispose_finding,
        execute_cross_check,
        rerun_verification,
        route_finding_for_repair,
    )

    assert CrossCheckDisposition
    assert CrossCheckDispositionAction
    assert CrossCheckFinding
    assert CrossCheckFindingStatus
    assert CrossCheckRepairRoute
    assert CrossCheckRunRequest
    assert CrossCheckRunResult
    assert CrossCheckRunStatus
    assert CrossCheckSeverity
    assert CrossCheckValidationError
    assert CrossCheckVerificationRequest
    assert CrossCheckVerificationResult
    assert dispose_finding
    assert execute_cross_check
    assert rerun_verification
    assert route_finding_for_repair

    for name in (
        "CrossCheckDisposition",
        "CrossCheckFinding",
        "CrossCheckRunRequest",
        "CrossCheckVerificationResult",
        "execute_cross_check",
        "rerun_verification",
    ):
        assert name in meridian_core.__all__, f"{name} missing from __all__"


def test_build_and_filemap_exports():
    from meridian_core import BuildRegistry, FileArea, FileMap, FileMapEntry
    from meridian_core import HarnessBuild, HarnessMaturity, make_default_map
    from meridian_core import make_initial_registry

    assert BuildRegistry
    assert FileArea
    assert FileMap
    assert FileMapEntry
    assert HarnessBuild
    assert HarnessMaturity
    assert make_default_map
    assert make_initial_registry


def test_council_exports():
    from meridian_core import CouncilPlan, CouncilPosition, CouncilRole
    from meridian_core import council_plan_for_tier, default_council_positions

    assert CouncilPlan
    assert CouncilPosition
    assert CouncilRole
    assert council_plan_for_tier
    assert default_council_positions


def test_prompt_budget_exports():
    from meridian_core import PromptBudget, PromptBudgetPlan, PromptBudgetTier
    from meridian_core import prompt_budget_for_risk_tier

    assert PromptBudget
    assert PromptBudgetPlan
    assert PromptBudgetTier
    assert prompt_budget_for_risk_tier


def test_prompt_metrics_exports():
    from meridian_core import PromptMetricSample, PromptMetricSummary, PromptPerformanceStatus
    from meridian_core import summarize_prompt_metrics

    assert PromptMetricSample
    assert PromptMetricSummary
    assert PromptPerformanceStatus
    assert summarize_prompt_metrics


def test_prompt_packet_exports():
    from meridian_core import PromptPacket, PromptPacketValidationError, build_prompt_packet

    assert PromptPacket
    assert PromptPacketValidationError
    assert build_prompt_packet
    assert "PromptPacket" in meridian_core.__all__
    assert "PromptPacketValidationError" in meridian_core.__all__
    assert "build_prompt_packet" in meridian_core.__all__


def test_beacon_exports():
    from meridian_core import LivenessTarget, check_harness_liveness

    assert LivenessTarget
    assert check_harness_liveness
    assert "LivenessTarget" in meridian_core.__all__
    assert "check_harness_liveness" in meridian_core.__all__


def test_planning_exports():
    from meridian_core import PlanningAnswer, PlanningBrief, PlanningContext
    from meridian_core import PlanningQuestion, PlanningRecommendation, build_planning_brief

    assert PlanningAnswer
    assert PlanningBrief
    assert PlanningContext
    assert PlanningQuestion
    assert PlanningRecommendation
    assert build_planning_brief
    assert "PlanningBrief" in meridian_core.__all__
    assert "build_planning_brief" in meridian_core.__all__


def test_session_lifecycle_close_write_through_exports():
    from meridian_core import (
        CloseArchiveWriteThroughAction,
        ObsidianCaptureResult,
        SessionCloseWriteThroughRequest,
        SessionCloseWriteThroughResult,
        SessionWriteThroughResult,
        close_session_with_write_through,
    )

    assert CloseArchiveWriteThroughAction
    assert ObsidianCaptureResult
    assert SessionCloseWriteThroughRequest
    assert SessionCloseWriteThroughResult
    assert SessionWriteThroughResult
    assert close_session_with_write_through
    for name in (
        "CloseArchiveWriteThroughAction",
        "ObsidianCaptureResult",
        "SessionCloseWriteThroughRequest",
        "SessionCloseWriteThroughResult",
        "SessionWriteThroughResult",
        "close_session_with_write_through",
    ):
        assert name in meridian_core.__all__, f"{name} missing from __all__"


def test_backlog_authority_exports():
    from meridian_core import (
        BacklogBlockedStatus,
        BacklogImportBatch,
        BacklogImportCandidate,
        BacklogItem,
        BacklogItemState,
        BacklogOwner,
        BacklogPriority,
        BacklogQuery,
        BacklogScope,
        BacklogSource,
        BacklogTaskDraft,
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

    assert BacklogBlockedStatus
    assert BacklogImportBatch
    assert BacklogImportCandidate
    assert BacklogItem
    assert BacklogItemState
    assert BacklogOwner
    assert BacklogPriority
    assert BacklogQuery
    assert BacklogScope
    assert BacklogSource
    assert BacklogTaskDraft
    assert BacklogValidationError
    assert approve_backlog_item
    assert archive_backlog_item
    assert capture_backlog_item
    assert convert_backlog_item_to_task_draft
    assert defer_backlog_item
    assert deny_backlog_item
    assert import_backlog_candidates
    assert link_backlog_item_scope
    assert load_backlog
    assert modify_backlog_item
    assert query_backlog
    assert reject_backlog_item
    assert save_backlog
    assert to_goal_objective_ref
    for name in (
        "BacklogItem",
        "BacklogItemState",
        "BacklogScope",
        "BacklogTaskDraft",
        "capture_backlog_item",
        "query_backlog",
    ):
        assert name in meridian_core.__all__, f"{name} missing from __all__"


def test_internal_helpers_are_not_root_exports():
    assert "_TIER_SEMANTICS" not in meridian_core.__all__
    assert "_ROUTING_TABLE" not in meridian_core.__all__
    assert "_SEVERITY_MAP" not in meridian_core.__all__


def test_voice_io_authority_exports():
    from meridian_core import (
        VoiceCommandFamily,
        VoiceCommandIntent,
        VoiceIntentFamily,
        VoiceMode,
        VoiceOutputJob,
        VoiceOutputStatus,
        VoicePrivacyLevel,
        VoiceProviderCapability,
        VoiceRuntimeState,
        VoiceTranscriptDraft,
        VoiceTrustState,
        VoiceValidationError,
        apply_transcript_correction,
        build_voice_runtime_state,
        create_output_job,
        create_transcript_draft,
        interrupt_output_job,
        mute_output_job,
        normalize_voice_intent,
        recognize_voice_command_intent,
    )

    assert VoiceCommandFamily
    assert VoiceCommandIntent
    assert VoiceIntentFamily
    assert VoiceMode
    assert VoiceOutputJob
    assert VoiceOutputStatus
    assert VoicePrivacyLevel
    assert VoiceProviderCapability
    assert VoiceRuntimeState
    assert VoiceTranscriptDraft
    assert VoiceTrustState
    assert VoiceValidationError
    assert apply_transcript_correction
    assert build_voice_runtime_state
    assert create_output_job
    assert create_transcript_draft
    assert interrupt_output_job
    assert mute_output_job
    assert normalize_voice_intent
    assert recognize_voice_command_intent
    for name in (
        "VoiceCommandFamily",
        "VoiceCommandIntent",
        "VoiceRuntimeState",
        "VoiceTranscriptDraft",
        "VoiceValidationError",
        "build_voice_runtime_state",
        "create_transcript_draft",
        "normalize_voice_intent",
        "recognize_voice_command_intent",
    ):
        assert name in meridian_core.__all__, f"{name} missing from __all__"


def test_routine_authority_exports():
    from meridian_core import (
        PrimeRoutineReview,
        RoutineDefinition,
        RoutineReviewDisposition,
        RoutineReviewSource,
        RoutineRunPlan,
        RoutineRunPlanStatus,
        RoutineState,
        RoutineTrigger,
        RoutineTriggerKind,
        RoutineValidationError,
        create_routine,
        plan_routine_run,
        review_routine_result,
        set_routine_enabled,
    )

    assert PrimeRoutineReview
    assert RoutineDefinition
    assert RoutineReviewDisposition
    assert RoutineReviewSource
    assert RoutineRunPlan
    assert RoutineRunPlanStatus
    assert RoutineState
    assert RoutineTrigger
    assert RoutineTriggerKind
    assert RoutineValidationError
    assert create_routine
    assert plan_routine_run
    assert review_routine_result
    assert set_routine_enabled
    for name in (
        "PrimeRoutineReview",
        "RoutineDefinition",
        "RoutineReviewDisposition",
        "RoutineReviewSource",
        "RoutineRunPlan",
        "RoutineState",
        "RoutineTrigger",
        "RoutineValidationError",
        "create_routine",
        "plan_routine_run",
        "review_routine_result",
        "set_routine_enabled",
    ):
        assert name in meridian_core.__all__, f"{name} missing from __all__"


def test_session_archive_authority_exports():
    from meridian_core import (
        ArchiveCatalogEntry,
        ArchiveReloadPlan,
        ArchiveRunAgainPlan,
        ArchivedSessionRecord,
        SessionArchivePlanStatus,
        SessionArchiveValidationError,
        TranscriptAccessHandle,
        TranscriptAccessMode,
        archive_record_from_close_result,
        authorize_transcript_access,
        catalog_entry_from_record,
        plan_archive_reload,
        plan_archive_run_again,
    )

    assert ArchiveCatalogEntry
    assert ArchiveReloadPlan
    assert ArchiveRunAgainPlan
    assert ArchivedSessionRecord
    assert SessionArchivePlanStatus
    assert SessionArchiveValidationError
    assert TranscriptAccessHandle
    assert TranscriptAccessMode
    assert archive_record_from_close_result
    assert authorize_transcript_access
    assert catalog_entry_from_record
    assert plan_archive_reload
    assert plan_archive_run_again
    for name in (
        "ArchiveCatalogEntry",
        "ArchiveReloadPlan",
        "ArchiveRunAgainPlan",
        "ArchivedSessionRecord",
        "SessionArchiveValidationError",
        "TranscriptAccessHandle",
        "archive_record_from_close_result",
        "authorize_transcript_access",
        "plan_archive_reload",
        "plan_archive_run_again",
    ):
        assert name in meridian_core.__all__, f"{name} missing from __all__"


def test_cockpit_state_exports():
    from meridian_core import (
        CockpitStatus,
        EventSeverity,
        LaneCockpitStatus,
        LaneSummary,
        ProgressEvent,
        ProgressEventCategory,
        PrimeCockpitSnapshot,
        QueuePolicy,
        filter_events,
        lane_summary_counts,
        sort_lanes,
    )

    assert CockpitStatus
    assert EventSeverity
    assert LaneCockpitStatus
    assert LaneSummary
    assert ProgressEvent
    assert ProgressEventCategory
    assert PrimeCockpitSnapshot
    assert QueuePolicy
    assert filter_events
    assert lane_summary_counts
    assert sort_lanes

    for name in (
        "CockpitStatus", "QueuePolicy", "ProgressEventCategory", "EventSeverity",
        "LaneCockpitStatus", "LaneSummary", "ProgressEvent", "PrimeCockpitSnapshot",
        "sort_lanes", "filter_events", "lane_summary_counts",
    ):
        assert name in meridian_core.__all__, f"{name} missing from __all__"


def test_cockpit_state_private_not_exported():
    assert "_LANE_STATUS_ORDER" not in meridian_core.__all__

def test_cockpit_provider_exports():
    from meridian_core import build_snapshot, demo_snapshot

    assert build_snapshot
    assert demo_snapshot
    assert "build_snapshot" in __import__("meridian_core").__all__
    assert "demo_snapshot" in __import__("meridian_core").__all__

    snap = demo_snapshot()
    assert snap.project == "Meridian"
    assert snap.bearing == "V1 Bifrost"


def test_v2_cognition_policy_exports():
    from meridian_core import (
        CognitionActionType,
        CognitionLane,
        CognitionDecision,
        CognitionPolicy,
        CognitionPolicyResult,
        cognition_policy_for_tier,
        evaluate_cognition_policy,
    )

    assert CognitionActionType
    assert CognitionLane
    assert CognitionDecision
    assert CognitionPolicy
    assert CognitionPolicyResult
    assert cognition_policy_for_tier
    assert evaluate_cognition_policy

    for name in (
        "CognitionActionType",
        "CognitionLane",
        "CognitionDecision",
        "CognitionPolicy",
        "CognitionPolicyResult",
        "cognition_policy_for_tier",
        "evaluate_cognition_policy",
    ):
        assert name in meridian_core.__all__, f"{name} missing from __all__"

    policy = cognition_policy_for_tier(1)
    assert isinstance(policy, CognitionPolicy)
    assert policy.risk_tier == 1
    assert policy.action_type == CognitionActionType.BUILD

    result = evaluate_cognition_policy(1)
    assert isinstance(result, CognitionPolicyResult)
    assert result.can_dispatch


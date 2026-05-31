"""Prime restart/resteer domain objects and deterministic evaluator.

This module is intentionally pure. It does not inspect processes, edit queue
files, move branches, or launch applications. It evaluates a lane operating
frame and returns typed findings plus the safest next recovery action.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class LaneRole(Enum):
    BUILD = "build"
    REVIEW = "review"
    COORDINATOR = "coordinator"
    PROOF = "proof"
    OBSERVER = "observer"


class QuotaState(Enum):
    AVAILABLE = "available"
    LIMITED = "limited"
    BLOCKED = "blocked"
    UNKNOWN = "unknown"


class HealthFindingKind(Enum):
    EMPTY_QUEUE = "empty_queue"
    STALE_ACTIVE_TASK = "stale_active_task"
    POLLING_BUT_NOT_EXECUTING = "polling_but_not_executing"
    EXECUTING_BUT_NOT_COMMITTING = "executing_but_not_committing"
    WRONG_QUEUE = "wrong_queue"
    REVIEW_LANE_READING_BUILD_QUEUE = "review_lane_reading_build_queue"
    BUILD_LANE_READING_REVIEW_QUEUE = "build_lane_reading_review_queue"
    SHARED_WORKTREE = "shared_worktree"
    MAIN_WORKTREE_VIOLATION = "main_worktree_violation"
    BRANCH_MOVEMENT_ATTEMPT = "branch_movement_attempt"
    UNCOMMITTED_DRIFT = "uncommitted_drift"
    CROSS_LANE_CONTAMINATION = "cross_lane_contamination"
    QUOTA_BLOCKED = "quota_blocked"
    MODEL_MISMATCH = "model_mismatch"
    LAUNCH_POPUP = "launch_popup"
    ELECTRON_START_FAILURE = "electron_start_failure"
    PUSH_FAILURE = "push_failure"
    PROOF_BLOCKED = "proof_blocked"
    REVIEW_BACKLOG = "review_backlog"
    OBSIDIAN_DIVERGENCE = "obsidian_divergence"


class FindingSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    BLOCKING = "blocking"
    ESCALATE = "escalate"


class RecoveryActionKind(Enum):
    RESTART = "restart"
    RESTEER = "resteer"
    ESCALATE = "escalate"
    NONE = "none"


class RestartKind(Enum):
    REANCHOR_QUEUE = "reanchor_queue"
    REQUIRE_UNIQUE_WORKTREE = "require_unique_worktree"
    CLEAR_STALE_TASK = "clear_stale_task"
    REISSUE_ACTIVE_TASK = "reissue_active_task"
    RELAUNCH_APP = "relaunch_app"
    REOPEN_SESSION = "reopen_session"
    PULL_AND_RECHECK = "pull_and_recheck"
    COMMIT_OR_REPORT_DRIFT = "commit_or_report_drift"


class ResteerKind(Enum):
    QUEUE_NEXT_TASK = "queue_next_task"
    ROUTE_REVIEW = "route_review"
    ROUTE_PROOF_REPAIR = "route_proof_repair"
    SWITCH_MODEL_FAMILY = "switch_model_family"
    UPDATE_MEMORY = "update_memory"


@dataclass(frozen=True)
class LaneOperatingFrame:
    lane_id: str
    lane_role: LaneRole
    assigned_queue_path: str
    worktree_path: str
    branch_name: str = ""
    allowed_paths: tuple[str, ...] = ()
    active_task_id: str = ""
    next_candidate_id: str = ""
    review_gate_id: str = ""
    cadence_counter: int = 0
    last_read_at: str = ""
    last_write_at: str = ""
    last_commit: str = ""
    model_family: str = ""
    quota_state: QuotaState = QuotaState.UNKNOWN
    current_queue_path: str = ""
    expected_queue_path: str = ""
    repo_root_path: str = ""
    attempted_branch_movement: bool = False
    has_uncommitted_drift: bool = False
    has_cross_lane_contamination: bool = False
    has_launch_popup: bool = False
    has_electron_start_failure: bool = False
    has_push_failure: bool = False
    has_proof_block: bool = False
    has_review_backlog: bool = False
    has_obsidian_divergence: bool = False


@dataclass(frozen=True)
class PrimeHealthFinding:
    finding_id: str
    lane_id: str
    kind: HealthFindingKind
    severity: FindingSeverity
    summary: str
    evidence: str
    recommended_action: RecoveryActionKind


@dataclass(frozen=True)
class RestartDirective:
    directive_id: str
    lane_id: str
    reason_finding_ids: tuple[str, ...]
    restart_kind: RestartKind
    target_queue_path: str
    target_worktree_path: str
    frame_message: str
    must_pull_before_work: bool = True
    must_report_worktree: bool = True
    allowed_paths: tuple[str, ...] = ()


@dataclass(frozen=True)
class ResteerDirective:
    directive_id: str
    lane_id: str
    reason_finding_ids: tuple[str, ...]
    resteer_kind: ResteerKind
    new_task_id: str
    new_task_summary: str
    risk_tier: int
    required_review_gate: str = ""
    required_proof: str = ""
    allowed_paths: tuple[str, ...] = ()
    completion_proof: str = ""


@dataclass(frozen=True)
class EscalationGate:
    gate_id: str
    lane_id: str
    reason_finding_ids: tuple[str, ...]
    reason: str
    evidence: str
    options: tuple[str, ...]
    default_recommendation: str


RecoveryDirective = RestartDirective | ResteerDirective | EscalationGate | None


def evaluate_lane_frame(
    frame: LaneOperatingFrame,
    peer_frames: tuple[LaneOperatingFrame, ...] = (),
) -> tuple[PrimeHealthFinding, ...]:
    """Return typed health findings for one lane frame.

    The evaluator is deterministic and intentionally conservative. Safety and
    proof findings are blocking/escalating; throughput findings request a
    resteer but do not imply unsafe state.
    """
    findings: list[PrimeHealthFinding] = []

    def add(
        kind: HealthFindingKind,
        severity: FindingSeverity,
        summary: str,
        evidence: str,
        action: RecoveryActionKind,
    ) -> None:
        findings.append(
            PrimeHealthFinding(
                finding_id=f"{frame.lane_id}:{kind.value}",
                lane_id=frame.lane_id,
                kind=kind,
                severity=severity,
                summary=summary,
                evidence=evidence,
                recommended_action=action,
            )
        )

    expected_queue = frame.expected_queue_path or frame.assigned_queue_path
    current_queue = frame.current_queue_path or frame.assigned_queue_path

    if _same_path(frame.worktree_path, frame.repo_root_path) and frame.repo_root_path:
        add(
            HealthFindingKind.MAIN_WORKTREE_VIOLATION,
            FindingSeverity.ESCALATE,
            "worker lane is operating in the main repo worktree",
            frame.worktree_path,
            RecoveryActionKind.ESCALATE,
        )

    for peer in peer_frames:
        if peer.lane_id != frame.lane_id and _same_path(peer.worktree_path, frame.worktree_path):
            add(
                HealthFindingKind.SHARED_WORKTREE,
                FindingSeverity.ESCALATE,
                "lane shares a worktree with another lane",
                f"{frame.worktree_path} also reported by {peer.lane_id}",
                RecoveryActionKind.ESCALATE,
            )
            break

    if frame.attempted_branch_movement:
        add(
            HealthFindingKind.BRANCH_MOVEMENT_ATTEMPT,
            FindingSeverity.ESCALATE,
            "lane attempted branch movement without Prime/Scott permission",
            frame.branch_name,
            RecoveryActionKind.ESCALATE,
        )

    if frame.has_uncommitted_drift:
        add(
            HealthFindingKind.UNCOMMITTED_DRIFT,
            FindingSeverity.BLOCKING,
            "lane has uncommitted drift and must commit or report before new work",
            frame.worktree_path,
            RecoveryActionKind.RESTART,
        )

    if frame.has_cross_lane_contamination:
        add(
            HealthFindingKind.CROSS_LANE_CONTAMINATION,
            FindingSeverity.BLOCKING,
            "lane touched files outside its ownership boundary",
            ", ".join(frame.allowed_paths),
            RecoveryActionKind.ESCALATE,
        )

    if frame.has_proof_block:
        add(
            HealthFindingKind.PROOF_BLOCKED,
            FindingSeverity.BLOCKING,
            "Aegis proof blocks new work for this lane",
            frame.review_gate_id or frame.active_task_id,
            RecoveryActionKind.RESTEER,
        )

    if frame.lane_role is LaneRole.REVIEW and _looks_like_build_queue(current_queue):
        add(
            HealthFindingKind.REVIEW_LANE_READING_BUILD_QUEUE,
            FindingSeverity.BLOCKING,
            "review lane is reading a build queue as executable source",
            current_queue,
            RecoveryActionKind.RESTART,
        )
    elif frame.lane_role is LaneRole.BUILD and _looks_like_review_queue(current_queue):
        add(
            HealthFindingKind.BUILD_LANE_READING_REVIEW_QUEUE,
            FindingSeverity.BLOCKING,
            "build lane is reading a review queue as executable source",
            current_queue,
            RecoveryActionKind.RESTART,
        )
    elif expected_queue and current_queue != expected_queue:
        add(
            HealthFindingKind.WRONG_QUEUE,
            FindingSeverity.BLOCKING,
            "lane is polling a queue other than its assigned queue",
            f"current={current_queue}; expected={expected_queue}",
            RecoveryActionKind.RESTART,
        )

    if frame.quota_state is QuotaState.BLOCKED:
        add(
            HealthFindingKind.QUOTA_BLOCKED,
            FindingSeverity.WARNING,
            "lane model/account quota is blocked",
            frame.model_family or "unknown model family",
            RecoveryActionKind.RESTEER,
        )

    if frame.has_launch_popup:
        add(
            HealthFindingKind.LAUNCH_POPUP,
            FindingSeverity.WARNING,
            "lane or app reported a launch popup",
            frame.lane_id,
            RecoveryActionKind.RESTART,
        )

    if frame.has_electron_start_failure:
        add(
            HealthFindingKind.ELECTRON_START_FAILURE,
            FindingSeverity.WARNING,
            "Electron start failed or app executable was not found",
            frame.lane_id,
            RecoveryActionKind.RESTART,
        )

    if frame.has_push_failure:
        add(
            HealthFindingKind.PUSH_FAILURE,
            FindingSeverity.BLOCKING,
            "lane has committed locally but failed to push",
            frame.last_commit,
            RecoveryActionKind.RESTART,
        )

    if frame.cadence_counter >= 3:
        add(
            HealthFindingKind.REVIEW_BACKLOG,
            FindingSeverity.BLOCKING,
            "lane reached the three-change Codex review cadence",
            str(frame.cadence_counter),
            RecoveryActionKind.RESTEER,
        )

    if frame.lane_role is LaneRole.BUILD and not frame.active_task_id and not frame.next_candidate_id:
        add(
            HealthFindingKind.EMPTY_QUEUE,
            FindingSeverity.WARNING,
            "build queue has no active task and no next candidate",
            frame.assigned_queue_path,
            RecoveryActionKind.RESTEER,
        )

    if frame.has_obsidian_divergence:
        add(
            HealthFindingKind.OBSIDIAN_DIVERGENCE,
            FindingSeverity.WARNING,
            "repo state moved without matching Obsidian build note",
            frame.last_commit,
            RecoveryActionKind.RESTEER,
        )

    return tuple(findings)


def choose_recovery_action(
    frame: LaneOperatingFrame,
    findings: tuple[PrimeHealthFinding, ...],
) -> RecoveryDirective:
    """Choose the safest Prime action for the current findings."""
    if not findings:
        return None

    for finding in findings:
        if finding.kind in {
            HealthFindingKind.SHARED_WORKTREE,
            HealthFindingKind.MAIN_WORKTREE_VIOLATION,
            HealthFindingKind.BRANCH_MOVEMENT_ATTEMPT,
            HealthFindingKind.CROSS_LANE_CONTAMINATION,
        }:
            return EscalationGate(
                gate_id=f"{frame.lane_id}:escalate",
                lane_id=frame.lane_id,
                reason_finding_ids=(finding.finding_id,),
                reason=finding.summary,
                evidence=finding.evidence,
                options=("wait", "assign fresh worktree", "ask Scott"),
                default_recommendation="ask Scott before allowing more writes",
            )

    proof = _first(findings, HealthFindingKind.PROOF_BLOCKED)
    if proof is not None:
        return ResteerDirective(
            directive_id=f"{frame.lane_id}:proof-repair",
            lane_id=frame.lane_id,
            reason_finding_ids=(proof.finding_id,),
            resteer_kind=ResteerKind.ROUTE_PROOF_REPAIR,
            new_task_id="proof-repair",
            new_task_summary="Route Aegis proof repair before assigning new work.",
            risk_tier=3,
            required_proof="Aegis proof clearance",
            allowed_paths=frame.allowed_paths,
            completion_proof="Aegis proof trail passes",
        )

    review = _first(findings, HealthFindingKind.REVIEW_BACKLOG)
    if review is not None:
        return ResteerDirective(
            directive_id=f"{frame.lane_id}:review-gate",
            lane_id=frame.lane_id,
            reason_finding_ids=(review.finding_id,),
            resteer_kind=ResteerKind.ROUTE_REVIEW,
            new_task_id="codex-review-cadence",
            new_task_summary="Route lane to Codex review before further build work.",
            risk_tier=2,
            required_review_gate="Codex review cadence",
            allowed_paths=frame.allowed_paths,
            completion_proof="Codex review result recorded",
        )

    restart = _first_action(findings, RecoveryActionKind.RESTART)
    if restart is not None:
        restart_kind = RestartKind.REANCHOR_QUEUE
        if restart.kind is HealthFindingKind.UNCOMMITTED_DRIFT:
            restart_kind = RestartKind.COMMIT_OR_REPORT_DRIFT
        elif restart.kind is HealthFindingKind.PUSH_FAILURE:
            restart_kind = RestartKind.PULL_AND_RECHECK
        elif restart.kind in {
            HealthFindingKind.LAUNCH_POPUP,
            HealthFindingKind.ELECTRON_START_FAILURE,
        }:
            restart_kind = RestartKind.RELAUNCH_APP

        return RestartDirective(
            directive_id=f"{frame.lane_id}:restart",
            lane_id=frame.lane_id,
            reason_finding_ids=(restart.finding_id,),
            restart_kind=restart_kind,
            target_queue_path=frame.expected_queue_path or frame.assigned_queue_path,
            target_worktree_path=frame.worktree_path,
            frame_message=restart.summary,
            allowed_paths=frame.allowed_paths,
        )

    quota = _first(findings, HealthFindingKind.QUOTA_BLOCKED)
    if quota is not None:
        return ResteerDirective(
            directive_id=f"{frame.lane_id}:quota-resteer",
            lane_id=frame.lane_id,
            reason_finding_ids=(quota.finding_id,),
            resteer_kind=ResteerKind.SWITCH_MODEL_FAMILY,
            new_task_id="quota-resteer",
            new_task_summary="Do not reissue the same model-family work while quota is blocked.",
            risk_tier=1,
            allowed_paths=frame.allowed_paths,
            completion_proof="lane confirms available model family or waits for reset",
        )

    empty = _first(findings, HealthFindingKind.EMPTY_QUEUE)
    if empty is not None:
        return ResteerDirective(
            directive_id=f"{frame.lane_id}:queue-next",
            lane_id=frame.lane_id,
            reason_finding_ids=(empty.finding_id,),
            resteer_kind=ResteerKind.QUEUE_NEXT_TASK,
            new_task_id="next-candidate-required",
            new_task_summary="Assign one active executable task and one next candidate.",
            risk_tier=1,
            allowed_paths=frame.allowed_paths,
            completion_proof="queue has active task and next candidate",
        )

    obsidian = _first(findings, HealthFindingKind.OBSIDIAN_DIVERGENCE)
    if obsidian is not None:
        return ResteerDirective(
            directive_id=f"{frame.lane_id}:memory-update",
            lane_id=frame.lane_id,
            reason_finding_ids=(obsidian.finding_id,),
            resteer_kind=ResteerKind.UPDATE_MEMORY,
            new_task_id="obsidian-memory-update",
            new_task_summary="Update Obsidian build note before continuing.",
            risk_tier=1,
            allowed_paths=frame.allowed_paths,
            completion_proof="Obsidian note records latest commit",
        )

    return None


def _same_path(left: str, right: str) -> bool:
    return bool(left and right) and left.rstrip("\\/").lower() == right.rstrip("\\/").lower()


def _looks_like_build_queue(path: str) -> bool:
    return "live-build-" in path.replace("\\", "/").lower()


def _looks_like_review_queue(path: str) -> bool:
    return "live-codex-reviews" in path.replace("\\", "/").lower()


def _first(
    findings: tuple[PrimeHealthFinding, ...],
    kind: HealthFindingKind,
) -> PrimeHealthFinding | None:
    return next((finding for finding in findings if finding.kind is kind), None)


def _first_action(
    findings: tuple[PrimeHealthFinding, ...],
    action: RecoveryActionKind,
) -> PrimeHealthFinding | None:
    return next(
        (finding for finding in findings if finding.recommended_action is action),
        None,
    )

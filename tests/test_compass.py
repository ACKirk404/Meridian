"""Tests for Compass project definition runtime."""

from __future__ import annotations

import json
from dataclasses import FrozenInstanceError

import pytest

from meridian_core.compass import (
    ProjectBoundsDecision,
    ProjectBoundsEvaluation,
    ProjectBoundsRequest,
    ProjectDefinition,
    ProjectDifferenceDecision,
    ProjectDifferenceEvaluation,
    ProjectDifferenceEvidence,
    ProjectDifferenceProfile,
    ProjectHandoffDecision,
    ProjectHandoffEvaluation,
    ProjectHandoffRequest,
    ProjectIdentityCandidate,
    ProjectIdentityDecision,
    ProjectIdentityEvaluation,
    ProjectIdentityNeighbor,
    ProjectRelationshipRefs,
    ProjectScopeCandidate,
    ProjectScopeDecision,
    ProjectScopeEvaluation,
    define_project,
    evaluate_cross_project_handoff,
    evaluate_project_bounds,
    evaluate_project_difference,
    evaluate_project_identity,
    evaluate_project_scope,
    project_bounds_request_dict_keys,
    project_bounds_request_kinds,
    project_bounds_result_dict_keys,
    project_difference_evidence_dict_keys,
    project_difference_profile_dict_keys,
    project_difference_profile_from_definition,
    project_difference_result_dict_keys,
    project_definition_dict_keys,
    project_definition_fingerprint,
    project_handoff_request_dict_keys,
    project_handoff_result_dict_keys,
    project_identity_candidate_dict_keys,
    project_identity_candidate_from_definition,
    project_identity_neighbor_dict_keys,
    project_identity_result_dict_keys,
    project_scope_result_dict_keys,
)


def _project(**overrides) -> ProjectDefinition:
    base = {
        "project_id": "meridian-v2",
        "title": "Meridian V2",
        "outcome": "Prime can coordinate V2 harness runtime without project drift.",
        "context": (
            "Compass owns project identity and bearing.",
            "V2 runtime stays pure until reviewed.",
        ),
        "artifacts": (
            "docs/v2-progress-tracker.md",
            "meridian_core/compass.py",
        ),
        "objectives": (
            "Define project runtime identity.",
            "Keep repo, venture, and session relationships explicit.",
        ),
        "tasks": (
            "Create pure domain object.",
            "Add deterministic serialization tests.",
        ),
        "proof_trail": (
            "docs/harness-stage-checklist.md#Compass",
            "tests/test_compass.py",
        ),
        "repo_refs": ("repo:C:/Users/scott/Code/Meridian-Worktrees/build-4-aegis",),
        "venture_refs": ("venture:Meridian",),
        "session_refs": ("session:build-4-aegis",),
    }
    base.update(overrides)
    return define_project(**base)


def _candidate(**overrides) -> ProjectScopeCandidate:
    base = {
        "project_id": "meridian-v2",
        "subject_kind": "artifact",
        "subject_ref": "meridian_core/compass.py",
        "evidence_refs": ("proof:scope-check",),
    }
    base.update(overrides)
    return ProjectScopeCandidate(**base)


def _difference_profile(**overrides) -> ProjectDifferenceProfile:
    base = {
        "project_id": "meridian-v2",
        "mission_bearing": "Ship Meridian V2 project-boundary runtime.",
        "objectives": (
            "Define project runtime identity.",
            "Keep repo, venture, and session relationships explicit.",
        ),
        "artifacts": (
            "docs/v2-progress-tracker.md",
            "meridian_core/compass.py",
        ),
        "memory_pins": ("memory:compass-definition-runtime",),
        "blockers": ("blocker:none",),
        "proof_expectations": ("pytest:tests/test_compass.py",),
        "repo_refs": ("repo:C:/Users/scott/Code/Meridian-Worktrees/build-4-aegis",),
        "venture_refs": ("venture:Meridian",),
    }
    base.update(overrides)
    return ProjectDifferenceProfile(**base)


def _other_difference_profile(**overrides) -> ProjectDifferenceProfile:
    base = {
        "project_id": "meridian-ui-review",
        "mission_bearing": "Expose reviewed command staging controls.",
        "objectives": (
            "Render command staging review evidence.",
            "Keep execution behind a human gate.",
        ),
        "artifacts": (
            "bifrost/ui/command_staging.py",
            "docs/live-build-3.md",
        ),
        "memory_pins": ("memory:command-staging-ui-review",),
        "blockers": ("blocker:needs-ui-review",),
        "proof_expectations": ("pytest:tests/test_bifrost.py",),
        "repo_refs": ("repo:C:/Users/scott/Code/Meridian-Worktrees/build-4-aegis",),
        "venture_refs": ("venture:Meridian",),
    }
    base.update(overrides)
    return ProjectDifferenceProfile(**base)


def _handoff_request(**overrides) -> ProjectHandoffRequest:
    base = {
        "source_project_id": "meridian-v2",
        "target_project_id": "meridian-ui-review",
        "reason_category": "proof_packet",
        "payload_type": "proof_refs",
        "payload_summary_refs": ("proof-summary:compass-project-difference",),
        "evidence_refs": ("proof:cross-project-handoff",),
        "approval_required": True,
        "approval_refs": ("approval:build-4-coordinator",),
        "raw_context_blocked": True,
    }
    base.update(overrides)
    return ProjectHandoffRequest(**base)


class TestProjectRelationshipRefs:
    def test_relationship_refs_are_frozen(self):
        refs = ProjectRelationshipRefs(
            repo_refs=("repo:meridian",),
            venture_refs=("venture:meridian",),
            session_refs=("session:build-4",),
        )
        with pytest.raises(FrozenInstanceError):
            refs.repo_refs = ("repo:other",)  # type: ignore[misc]

    def test_relationship_refs_serialize_stably(self):
        refs = ProjectRelationshipRefs(
            repo_refs=("repo:meridian",),
            venture_refs=("venture:meridian",),
            session_refs=("session:build-4",),
        )
        assert tuple(refs.to_dict().keys()) == (
            "repo_refs",
            "venture_refs",
            "session_refs",
        )

    def test_repo_refs_are_required(self):
        with pytest.raises(ValueError, match="repo_refs"):
            ProjectRelationshipRefs(repo_refs=(), venture_refs=("venture:meridian",))

    def test_venture_refs_are_required(self):
        with pytest.raises(ValueError, match="venture_refs"):
            ProjectRelationshipRefs(repo_refs=("repo:meridian",), venture_refs=())

    def test_session_refs_may_be_empty(self):
        refs = ProjectRelationshipRefs(
            repo_refs=("repo:meridian",),
            venture_refs=("venture:meridian",),
        )
        assert refs.session_refs == ()


class TestProjectDefinition:
    def test_project_definition_is_frozen(self):
        project = _project()
        with pytest.raises(FrozenInstanceError):
            project.title = "Other"  # type: ignore[misc]

    def test_define_project_returns_project_definition(self):
        assert isinstance(_project(), ProjectDefinition)

    def test_required_identity_fields_are_preserved(self):
        project = _project()
        assert project.project_id == "meridian-v2"
        assert project.title == "Meridian V2"
        assert "Prime can coordinate" in project.outcome

    def test_required_body_fields_are_tuples(self):
        project = _project()
        assert isinstance(project.context, tuple)
        assert isinstance(project.artifacts, tuple)
        assert isinstance(project.objectives, tuple)
        assert isinstance(project.tasks, tuple)
        assert isinstance(project.proof_trail, tuple)

    def test_relationship_refs_preserve_repo_venture_and_session(self):
        refs = _project().relationship_refs
        assert refs.repo_refs == ("repo:C:/Users/scott/Code/Meridian-Worktrees/build-4-aegis",)
        assert refs.venture_refs == ("venture:Meridian",)
        assert refs.session_refs == ("session:build-4-aegis",)

    def test_to_dict_has_stable_top_level_keys(self):
        project = _project()
        assert tuple(project.to_dict().keys()) == project_definition_dict_keys()

    def test_to_dict_is_json_serializable(self):
        payload = _project().to_dict()
        encoded = json.dumps(payload, sort_keys=True)
        assert "meridian-v2" in encoded
        assert "relationship_refs" in encoded

    def test_serialization_is_deterministic(self):
        project = _project()
        assert project.to_dict() == project.to_dict()
        assert _project().to_dict() == _project().to_dict()

    def test_fingerprint_is_deterministic(self):
        project = _project()
        assert project.fingerprint() == project.fingerprint()
        assert project.fingerprint() == project_definition_fingerprint(project)

    def test_fingerprint_changes_when_project_changes(self):
        assert _project().fingerprint() != _project(tasks=("Different task",)).fingerprint()

    @pytest.mark.parametrize(
        "field",
        (
            "project_id",
            "title",
            "outcome",
        ),
    )
    def test_required_text_fields_reject_blank_values(self, field):
        with pytest.raises(ValueError, match=field):
            _project(**{field: "   "})

    @pytest.mark.parametrize(
        "field",
        (
            "context",
            "artifacts",
            "objectives",
            "tasks",
            "proof_trail",
        ),
    )
    def test_required_sequence_fields_reject_empty_values(self, field):
        with pytest.raises(ValueError, match=field):
            _project(**{field: ()})

    def test_relationship_refs_type_is_required(self):
        with pytest.raises(ValueError, match="relationship_refs"):
            ProjectDefinition(
                project_id="proj",
                title="Project",
                outcome="Outcome",
                context=("Context",),
                artifacts=("Artifact",),
                objectives=("Objective",),
                tasks=("Task",),
                proof_trail=("Proof",),
                relationship_refs={"repo_refs": ("repo",)},  # type: ignore[arg-type]
            )

    def test_list_inputs_are_normalized_to_tuples(self):
        project = _project(
            context=["Context"],
            artifacts=["Artifact"],
            objectives=["Objective"],
            tasks=["Task"],
            proof_trail=["Proof"],
            repo_refs=["repo:meridian"],
            venture_refs=["venture:meridian"],
            session_refs=["session:build-4"],
        )
        assert project.context == ("Context",)
        assert project.artifacts == ("Artifact",)
        assert project.relationship_refs.repo_refs == ("repo:meridian",)

    def test_no_cross_project_handoff_fields_are_present(self):
        payload = _project().to_dict()
        assert "source_project" not in payload
        assert "target_project" not in payload
        assert "handoff" not in payload


class TestProjectScopeCandidate:
    def test_scope_candidate_is_frozen(self):
        candidate = _candidate()
        with pytest.raises(FrozenInstanceError):
            candidate.subject_ref = "other"  # type: ignore[misc]

    def test_scope_candidate_serializes_stably(self):
        candidate = _candidate()
        assert tuple(candidate.to_dict().keys()) == (
            "project_id",
            "subject_kind",
            "subject_ref",
            "evidence_refs",
            "ambiguity_reason",
        )

    def test_scope_candidate_allows_missing_project_for_blocker_path(self):
        candidate = _candidate(project_id=None)
        assert candidate.project_id is None


class TestProjectScopeEvaluation:
    def test_known_artifact_is_in_scope(self):
        result = evaluate_project_scope(_project(), _candidate())
        assert result.decision is ProjectScopeDecision.IN_SCOPE
        assert result.matched_refs == ("meridian_core/compass.py",)
        assert result.blockers == ()

    def test_known_context_is_in_scope(self):
        result = evaluate_project_scope(
            _project(),
            _candidate(
                subject_kind="context",
                subject_ref="Compass owns project identity and bearing.",
            ),
        )
        assert result.decision is ProjectScopeDecision.IN_SCOPE

    def test_known_objective_is_in_scope(self):
        result = evaluate_project_scope(
            _project(),
            _candidate(
                subject_kind="objective",
                subject_ref="Define project runtime identity.",
            ),
        )
        assert result.decision is ProjectScopeDecision.IN_SCOPE

    def test_known_task_is_in_scope(self):
        result = evaluate_project_scope(
            _project(),
            _candidate(
                subject_kind="task",
                subject_ref="Create pure domain object.",
            ),
        )
        assert result.decision is ProjectScopeDecision.IN_SCOPE

    def test_known_proof_is_in_scope(self):
        result = evaluate_project_scope(
            _project(),
            _candidate(
                subject_kind="proof",
                subject_ref="tests/test_compass.py",
            ),
        )
        assert result.decision is ProjectScopeDecision.IN_SCOPE

    def test_repo_relationship_ref_is_in_scope(self):
        result = evaluate_project_scope(
            _project(),
            _candidate(
                subject_kind="repo",
                subject_ref="repo:C:/Users/scott/Code/Meridian-Worktrees/build-4-aegis",
            ),
        )
        assert result.decision is ProjectScopeDecision.IN_SCOPE

    def test_venture_relationship_ref_is_in_scope(self):
        result = evaluate_project_scope(
            _project(),
            _candidate(subject_kind="venture", subject_ref="venture:Meridian"),
        )
        assert result.decision is ProjectScopeDecision.IN_SCOPE

    def test_session_relationship_ref_is_in_scope(self):
        result = evaluate_project_scope(
            _project(),
            _candidate(subject_kind="session", subject_ref="session:build-4-aegis"),
        )
        assert result.decision is ProjectScopeDecision.IN_SCOPE

    def test_unknown_artifact_is_out_of_scope(self):
        result = evaluate_project_scope(
            _project(),
            _candidate(subject_ref="docs/other-project.md"),
        )
        assert result.decision is ProjectScopeDecision.OUT_OF_SCOPE
        assert result.blockers == ("subject_not_in_project_boundary",)

    def test_missing_project_identity_blocks(self):
        result = evaluate_project_scope(_project(), _candidate(project_id=None))
        assert result.decision is ProjectScopeDecision.BLOCKED
        assert result.blockers == ("missing_project_identity",)

    def test_project_identity_mismatch_blocks(self):
        result = evaluate_project_scope(_project(), _candidate(project_id="polaris"))
        assert result.decision is ProjectScopeDecision.BLOCKED
        assert result.blockers == ("project_identity_mismatch",)

    def test_missing_scope_evidence_blocks(self):
        result = evaluate_project_scope(_project(), _candidate(evidence_refs=()))
        assert result.decision is ProjectScopeDecision.BLOCKED
        assert result.blockers == ("missing_scope_evidence_refs",)

    def test_unknown_subject_kind_returns_compass_question(self):
        result = evaluate_project_scope(
            _project(),
            _candidate(subject_kind="mystery", subject_ref="maybe-related"),
        )
        assert result.decision is ProjectScopeDecision.AMBIGUOUS
        assert result.compass_question is not None
        assert "known subject kind" in result.compass_question
        assert result.to_dict()["execution_authorized"] is False

    def test_ambiguous_subject_returns_compass_question(self):
        result = evaluate_project_scope(
            _project(),
            _candidate(
                subject_kind="ambiguous",
                subject_ref="shared repo note",
                ambiguity_reason="same repo but unclear project",
            ),
        )
        assert result.decision is ProjectScopeDecision.AMBIGUOUS
        assert result.compass_question is not None
        assert "shared repo note" in result.compass_question
        assert result.to_dict()["execution_authorized"] is False

    def test_scope_result_serializes_stably(self):
        result = evaluate_project_scope(_project(), _candidate())
        assert tuple(result.to_dict().keys()) == project_scope_result_dict_keys()

    def test_scope_result_is_json_serializable(self):
        result = evaluate_project_scope(_project(), _candidate())
        encoded = json.dumps(result.to_dict(), sort_keys=True)
        assert "in_scope" in encoded
        assert "execution_authorized" in encoded

    def test_scope_result_is_deterministic(self):
        project = _project()
        candidate = _candidate()
        assert evaluate_project_scope(project, candidate) == evaluate_project_scope(
            project,
            candidate,
        )

    def test_scope_evaluation_type_is_required(self):
        with pytest.raises(ValueError, match="decision"):
            ProjectScopeEvaluation(
                decision="in_scope",  # type: ignore[arg-type]
                project_id="meridian-v2",
                subject_kind="artifact",
                subject_ref="meridian_core/compass.py",
                evidence_refs=("proof",),
            )

    def test_scope_runtime_does_not_emit_cross_project_handoff_fields(self):
        payload = evaluate_project_scope(_project(), _candidate()).to_dict()
        assert "source_project" not in payload
        assert "target_project" not in payload
        assert "handoff" not in payload


class TestProjectDifferenceRuntime:
    def test_difference_profile_is_frozen(self):
        profile = _difference_profile()
        with pytest.raises(FrozenInstanceError):
            profile.project_id = "other"  # type: ignore[misc]

    def test_difference_profile_serializes_stably(self):
        assert tuple(_difference_profile().to_dict().keys()) == (
            project_difference_profile_dict_keys()
        )

    def test_difference_profile_is_json_serializable(self):
        encoded = json.dumps(_difference_profile().to_dict(), sort_keys=True)
        assert "mission_bearing" in encoded
        assert "memory_pins" in encoded

    def test_difference_profile_can_be_derived_from_project_definition(self):
        project = _project()
        profile = project_difference_profile_from_definition(
            project,
            mission_bearing="Ship Compass project definition runtime.",
            memory_pins=("memory:project-definition",),
            blockers=("blocker:none",),
            proof_expectations=("pytest:tests/test_compass.py",),
        )
        assert profile.project_id == project.project_id
        assert profile.objectives == project.objectives
        assert profile.artifacts == project.artifacts
        assert profile.repo_refs == project.relationship_refs.repo_refs
        assert profile.venture_refs == project.relationship_refs.venture_refs

    def test_same_profile_returns_same_project_without_merge_authority(self):
        result = evaluate_project_difference(
            _difference_profile(),
            _difference_profile(),
            evidence_refs=("proof:difference-profile",),
        )
        assert result.decision is ProjectDifferenceDecision.SAME_PROJECT
        assert result.difference_evidence == ()
        assert result.to_dict()["merge_authorized"] is False

    def test_same_repo_does_not_imply_same_project(self):
        result = evaluate_project_difference(
            _difference_profile(),
            _other_difference_profile(venture_refs=("venture:Other",)),
            evidence_refs=("proof:same-repo-different-bearing",),
        )
        assert result.decision is ProjectDifferenceDecision.DISTINCT
        assert result.shared_relationship_refs == (
            "repo:C:/Users/scott/Code/Meridian-Worktrees/build-4-aegis",
        )
        assert "mission_bearing" in _difference_fields(result)

    def test_same_venture_does_not_imply_same_project(self):
        result = evaluate_project_difference(
            _difference_profile(repo_refs=("repo:other",)),
            _other_difference_profile(repo_refs=("repo:another",)),
            evidence_refs=("proof:same-venture-different-bearing",),
        )
        assert result.decision is ProjectDifferenceDecision.DISTINCT
        assert result.shared_relationship_refs == ("venture:Meridian",)
        assert "objectives" in _difference_fields(result)

    def test_visible_difference_evidence_covers_all_requested_fields(self):
        result = evaluate_project_difference(
            _difference_profile(),
            _other_difference_profile(),
            evidence_refs=("proof:all-difference-fields",),
        )
        assert result.decision is ProjectDifferenceDecision.DISTINCT
        assert _difference_fields(result) == {
            "mission_bearing",
            "objectives",
            "artifacts",
            "memory_pins",
            "blockers",
            "proof_expectations",
        }

    def test_difference_evidence_serializes_stably(self):
        evidence = ProjectDifferenceEvidence(
            field="mission_bearing",
            left=("left bearing",),
            right=("right bearing",),
        )
        assert tuple(evidence.to_dict().keys()) == project_difference_evidence_dict_keys()

    def test_difference_result_serializes_stably(self):
        result = evaluate_project_difference(
            _difference_profile(),
            _other_difference_profile(),
            evidence_refs=("proof:shape",),
        )
        assert tuple(result.to_dict().keys()) == project_difference_result_dict_keys()

    def test_difference_result_is_json_serializable(self):
        result = evaluate_project_difference(
            _difference_profile(),
            _other_difference_profile(),
            evidence_refs=("proof:json",),
        )
        encoded = json.dumps(result.to_dict(), sort_keys=True)
        assert "distinct" in encoded
        assert "difference_evidence" in encoded

    def test_difference_result_is_deterministic(self):
        left = _difference_profile()
        right = _other_difference_profile()
        assert evaluate_project_difference(
            left,
            right,
            evidence_refs=("proof:deterministic",),
        ) == evaluate_project_difference(
            left,
            right,
            evidence_refs=("proof:deterministic",),
        )

    def test_missing_difference_evidence_blocks(self):
        result = evaluate_project_difference(
            _difference_profile(),
            _other_difference_profile(),
            evidence_refs=(),
        )
        assert result.decision is ProjectDifferenceDecision.BLOCKED
        assert "missing_project_difference_evidence_refs" in result.blockers
        assert result.compass_question is not None

    def test_missing_project_identity_blocks(self):
        result = evaluate_project_difference(
            _difference_profile(project_id=None),
            _other_difference_profile(),
            evidence_refs=("proof:missing-id",),
        )
        assert result.decision is ProjectDifferenceDecision.BLOCKED
        assert "missing_left_project_id" in result.blockers

    @pytest.mark.parametrize(
        "field",
        (
            "mission_bearing",
            "objectives",
            "artifacts",
            "memory_pins",
            "blockers",
            "proof_expectations",
        ),
    )
    def test_missing_required_difference_field_blocks(self, field):
        missing = None if field == "mission_bearing" else ()
        result = evaluate_project_difference(
            _difference_profile(**{field: missing}),
            _other_difference_profile(),
            evidence_refs=("proof:missing-field",),
        )
        assert result.decision is ProjectDifferenceDecision.BLOCKED
        assert f"missing_left_{field}" in result.blockers

    def test_ambiguous_difference_returns_compass_question_instead_of_merge(self):
        result = evaluate_project_difference(
            _difference_profile(project_id="meridian-v2-a"),
            _difference_profile(project_id="meridian-v2-b"),
            evidence_refs=("proof:ambiguous-identities",),
        )
        assert result.decision is ProjectDifferenceDecision.AMBIGUOUS
        assert result.blockers == ("ambiguous_project_difference_evidence",)
        assert result.compass_question is not None
        assert result.to_dict()["merge_authorized"] is False

    def test_difference_evaluation_type_is_required(self):
        with pytest.raises(ValueError, match="decision"):
            ProjectDifferenceEvaluation(
                decision="distinct",  # type: ignore[arg-type]
                left_project_id="left",
                right_project_id="right",
                evidence_refs=("proof",),
            )

    def test_difference_runtime_does_not_emit_cross_project_handoff_fields(self):
        payload = evaluate_project_difference(
            _difference_profile(),
            _other_difference_profile(),
            evidence_refs=("proof:no-handoff",),
        ).to_dict()
        assert "source_project" not in payload
        assert "target_project" not in payload
        assert "handoff" not in payload
        assert "execution_authorized" not in payload


def _difference_fields(result: ProjectDifferenceEvaluation) -> set[str]:
    return {evidence.field for evidence in result.difference_evidence}


class TestProjectHandoffRuntime:
    def test_handoff_request_is_frozen(self):
        request = _handoff_request()
        with pytest.raises(FrozenInstanceError):
            request.reason_category = "status_summary"  # type: ignore[misc]

    def test_handoff_request_serializes_stably(self):
        assert tuple(_handoff_request().to_dict().keys()) == (
            project_handoff_request_dict_keys()
        )

    def test_handoff_request_is_json_serializable(self):
        encoded = json.dumps(_handoff_request().to_dict(), sort_keys=True)
        assert "proof_packet" in encoded
        assert "payload_summary_refs" in encoded

    def test_distinct_project_handoff_can_be_review_ready(self):
        result = evaluate_cross_project_handoff(
            _difference_profile(),
            _other_difference_profile(),
            _handoff_request(),
        )
        assert result.decision is ProjectHandoffDecision.REVIEW_READY
        assert result.project_difference_decision is ProjectDifferenceDecision.DISTINCT
        assert result.to_dict()["review_ready"] is True
        assert result.to_dict()["execution_authorized"] is False

    def test_same_repo_and_venture_do_not_block_distinct_handoff(self):
        result = evaluate_cross_project_handoff(
            _difference_profile(),
            _other_difference_profile(),
            _handoff_request(),
        )
        assert result.decision is ProjectHandoffDecision.REVIEW_READY
        assert result.shared_relationship_refs == (
            "repo:C:/Users/scott/Code/Meridian-Worktrees/build-4-aegis",
            "venture:Meridian",
        )

    def test_same_project_identity_blocks_handoff(self):
        result = evaluate_cross_project_handoff(
            _difference_profile(),
            _difference_profile(),
            _handoff_request(target_project_id="meridian-v2"),
        )
        assert result.decision is ProjectHandoffDecision.BLOCKED
        assert "source_target_not_distinct" in result.blockers
        assert result.to_dict()["review_ready"] is False

    def test_missing_source_project_identity_blocks_handoff(self):
        result = evaluate_cross_project_handoff(
            _difference_profile(project_id=None),
            _other_difference_profile(),
            _handoff_request(source_project_id=None),
        )
        assert result.decision is ProjectHandoffDecision.BLOCKED
        assert "missing_source_project_id" in result.blockers
        assert "missing_source_project_profile_id" in result.blockers

    def test_missing_target_project_identity_blocks_handoff(self):
        result = evaluate_cross_project_handoff(
            _difference_profile(),
            _other_difference_profile(project_id=None),
            _handoff_request(target_project_id=None),
        )
        assert result.decision is ProjectHandoffDecision.BLOCKED
        assert "missing_target_project_id" in result.blockers
        assert "missing_target_project_profile_id" in result.blockers

    def test_project_identity_mismatch_blocks_handoff(self):
        result = evaluate_cross_project_handoff(
            _difference_profile(),
            _other_difference_profile(),
            _handoff_request(source_project_id="wrong-source"),
        )
        assert result.decision is ProjectHandoffDecision.BLOCKED
        assert "source_project_identity_mismatch" in result.blockers

    def test_missing_handoff_evidence_blocks_review(self):
        result = evaluate_cross_project_handoff(
            _difference_profile(),
            _other_difference_profile(),
            _handoff_request(evidence_refs=()),
        )
        assert result.decision is ProjectHandoffDecision.BLOCKED
        assert "missing_handoff_evidence_refs" in result.blockers

    def test_missing_payload_summary_refs_blocks_review(self):
        result = evaluate_cross_project_handoff(
            _difference_profile(),
            _other_difference_profile(),
            _handoff_request(payload_summary_refs=()),
        )
        assert result.decision is ProjectHandoffDecision.BLOCKED
        assert "missing_payload_summary_refs" in result.blockers

    def test_missing_required_approval_refs_blocks_review(self):
        result = evaluate_cross_project_handoff(
            _difference_profile(),
            _other_difference_profile(),
            _handoff_request(approval_refs=()),
        )
        assert result.decision is ProjectHandoffDecision.BLOCKED
        assert "missing_required_approval_refs" in result.blockers

    def test_approval_can_be_marked_not_required(self):
        result = evaluate_cross_project_handoff(
            _difference_profile(),
            _other_difference_profile(),
            _handoff_request(approval_required=False, approval_refs=()),
        )
        assert result.decision is ProjectHandoffDecision.REVIEW_READY
        assert result.approval_required is False

    @pytest.mark.parametrize(
        ("field", "value", "blocker"),
        (
            ("payload_type", "raw_prompt", "raw_context_payload_type_blocked"),
            (
                "evidence_refs",
                ("raw_prompt:full prompt text",),
                "raw_context_evidence_ref_blocked",
            ),
            (
                "payload_summary_refs",
                ("transcript:full transcript text",),
                "raw_context_payload_summary_ref_blocked",
            ),
            (
                "approval_refs",
                ("conversation:approval said in chat",),
                "raw_context_approval_ref_blocked",
            ),
        ),
    )
    def test_raw_context_bleed_is_blocked(self, field, value, blocker):
        result = evaluate_cross_project_handoff(
            _difference_profile(),
            _other_difference_profile(),
            _handoff_request(**{field: value}),
        )
        assert result.decision is ProjectHandoffDecision.BLOCKED
        assert blocker in result.blockers

    def test_handoff_result_redacts_raw_context_ref_fields(self):
        result = evaluate_cross_project_handoff(
            _difference_profile(),
            _other_difference_profile(),
            _handoff_request(
                evidence_refs=("proof:cross-project-handoff", "raw_context:evidence"),
                payload_summary_refs=(
                    "proof-summary:compass-project-difference",
                    "transcript:payload details",
                ),
                approval_refs=("approval:build-4-coordinator", "conversation:approval"),
            ),
        )
        payload = result.to_dict()
        encoded = json.dumps(payload, sort_keys=True)

        assert result.decision is ProjectHandoffDecision.BLOCKED
        assert "raw_context_evidence_ref_blocked" in result.blockers
        assert "raw_context_payload_summary_ref_blocked" in result.blockers
        assert "raw_context_approval_ref_blocked" in result.blockers
        assert payload["evidence_refs"] == (
            "proof:cross-project-handoff",
            "<redacted_raw_context>",
        )
        assert payload["payload_summary_refs"] == (
            "proof-summary:compass-project-difference",
            "<redacted_raw_context>",
        )
        assert payload["approval_refs"] == (
            "approval:build-4-coordinator",
            "<redacted_raw_context>",
        )
        assert "raw_context:evidence" not in encoded
        assert "transcript:payload details" not in encoded
        assert "conversation:approval" not in encoded

    def test_raw_context_block_flag_is_required(self):
        result = evaluate_cross_project_handoff(
            _difference_profile(),
            _other_difference_profile(),
            _handoff_request(raw_context_blocked=False),
        )
        assert result.decision is ProjectHandoffDecision.BLOCKED
        assert "raw_context_bleed_not_blocked" in result.blockers

    def test_unknown_reason_category_blocks_review(self):
        result = evaluate_cross_project_handoff(
            _difference_profile(),
            _other_difference_profile(),
            _handoff_request(reason_category="mystery"),
        )
        assert result.decision is ProjectHandoffDecision.BLOCKED
        assert "unknown_handoff_reason_category" in result.blockers

    def test_unknown_payload_type_blocks_review(self):
        result = evaluate_cross_project_handoff(
            _difference_profile(),
            _other_difference_profile(),
            _handoff_request(payload_type="full_context_blob"),
        )
        assert result.decision is ProjectHandoffDecision.BLOCKED
        assert "unknown_handoff_payload_type" in result.blockers

    def test_ambiguous_project_difference_returns_compass_question(self):
        result = evaluate_cross_project_handoff(
            _difference_profile(project_id="meridian-v2-a"),
            _difference_profile(project_id="meridian-v2-b"),
            _handoff_request(
                source_project_id="meridian-v2-a",
                target_project_id="meridian-v2-b",
            ),
        )
        assert result.decision is ProjectHandoffDecision.AMBIGUOUS
        assert result.compass_question is not None
        assert result.to_dict()["review_ready"] is False

    def test_handoff_result_serializes_stably(self):
        result = evaluate_cross_project_handoff(
            _difference_profile(),
            _other_difference_profile(),
            _handoff_request(),
        )
        assert tuple(result.to_dict().keys()) == project_handoff_result_dict_keys()

    def test_handoff_result_is_json_serializable(self):
        result = evaluate_cross_project_handoff(
            _difference_profile(),
            _other_difference_profile(),
            _handoff_request(),
        )
        encoded = json.dumps(result.to_dict(), sort_keys=True)
        assert "review_ready" in encoded
        assert "execution_authorized" in encoded

    def test_handoff_result_is_deterministic(self):
        source = _difference_profile()
        target = _other_difference_profile()
        request = _handoff_request()
        assert evaluate_cross_project_handoff(
            source,
            target,
            request,
        ) == evaluate_cross_project_handoff(
            source,
            target,
            request,
        )

    def test_handoff_evaluation_type_is_required(self):
        with pytest.raises(ValueError, match="decision"):
            ProjectHandoffEvaluation(
                decision="review_ready",  # type: ignore[arg-type]
                source_project_id="source",
                target_project_id="target",
                reason_category="proof_packet",
                payload_type="proof_refs",
                payload_summary_refs=("summary",),
                evidence_refs=("proof",),
                approval_required=False,
            )

    def test_handoff_payload_does_not_serialize_raw_context_keys(self):
        payload = evaluate_cross_project_handoff(
            _difference_profile(),
            _other_difference_profile(),
            _handoff_request(),
        ).to_dict()
        assert "raw_prompt" not in payload
        assert "transcript" not in payload
        assert "free_form_context" not in payload
        assert "session_retargeting" not in payload


def _identity_candidate(**overrides) -> ProjectIdentityCandidate:
    base = {
        "project_id": "meridian-v2",
        "title": "Meridian V2",
        "outcome": "Prime can coordinate V2 harness runtime without project drift.",
        "mission_bearing": "Ship Meridian V2 project-boundary runtime.",
        "repo_refs": ("repo:C:/Users/scott/Code/Meridian-Worktrees/build-4-aegis",),
        "venture_refs": ("venture:Meridian",),
        "session_refs": ("session:build-4-aegis",),
        "evidence_refs": ("proof:project-identity-check",),
        "neighbors": (),
    }
    base.update(overrides)
    return ProjectIdentityCandidate(**base)


def _identity_neighbor(**overrides) -> ProjectIdentityNeighbor:
    base = {
        "project_id": "meridian-ui-review",
        "mission_bearing": "Expose reviewed command staging controls.",
        "repo_refs": ("repo:C:/Users/scott/Code/Meridian-Worktrees/build-4-aegis",),
        "venture_refs": ("venture:Meridian",),
        "session_refs": ("session:build-4-aegis",),
    }
    base.update(overrides)
    return ProjectIdentityNeighbor(**base)


class TestProjectIdentityNeighbor:
    def test_neighbor_is_frozen(self):
        neighbor = _identity_neighbor()
        with pytest.raises(FrozenInstanceError):
            neighbor.project_id = "other"  # type: ignore[misc]

    def test_neighbor_serializes_stably(self):
        assert tuple(_identity_neighbor().to_dict().keys()) == (
            project_identity_neighbor_dict_keys()
        )

    def test_neighbor_project_id_is_required(self):
        with pytest.raises(ValueError, match="project_id"):
            ProjectIdentityNeighbor(
                project_id="",
                mission_bearing="bearing",
            )

    def test_neighbor_mission_bearing_is_required(self):
        with pytest.raises(ValueError, match="mission_bearing"):
            ProjectIdentityNeighbor(
                project_id="other",
                mission_bearing="",
            )


class TestProjectIdentityCandidate:
    def test_candidate_is_frozen(self):
        candidate = _identity_candidate()
        with pytest.raises(FrozenInstanceError):
            candidate.project_id = "other"  # type: ignore[misc]

    def test_candidate_serializes_stably(self):
        assert tuple(_identity_candidate().to_dict().keys()) == (
            project_identity_candidate_dict_keys()
        )

    def test_candidate_is_json_serializable(self):
        encoded = json.dumps(_identity_candidate().to_dict(), sort_keys=True)
        assert "mission_bearing" in encoded
        assert "evidence_refs" in encoded

    def test_neighbors_must_be_project_identity_neighbor(self):
        with pytest.raises(ValueError, match="neighbors"):
            ProjectIdentityCandidate(
                project_id="meridian-v2",
                title="Meridian V2",
                outcome="outcome",
                mission_bearing="bearing",
                repo_refs=("repo:meridian",),
                venture_refs=("venture:meridian",),
                neighbors=("not-a-neighbor",),  # type: ignore[arg-type]
            )

    def test_candidate_can_be_built_from_project_definition(self):
        project = _project()
        candidate = project_identity_candidate_from_definition(
            project,
            mission_bearing="Ship Meridian V2 project-boundary runtime.",
            evidence_refs=("proof:project-identity-from-definition",),
        )
        assert candidate.project_id == project.project_id
        assert candidate.title == project.title
        assert candidate.outcome == project.outcome
        assert candidate.repo_refs == project.relationship_refs.repo_refs
        assert candidate.venture_refs == project.relationship_refs.venture_refs
        assert candidate.session_refs == project.relationship_refs.session_refs


class TestProjectIdentityRuntime:
    def test_complete_distinct_identity_is_defined(self):
        result = evaluate_project_identity(_identity_candidate())
        assert result.decision is ProjectIdentityDecision.DEFINED
        assert result.project_id == "meridian-v2"
        assert result.blockers == ()
        assert result.compass_question is None
        assert result.to_dict()["execution_authorized"] is False

    def test_missing_project_id_is_blocked(self):
        result = evaluate_project_identity(_identity_candidate(project_id=None))
        assert result.decision is ProjectIdentityDecision.BLOCKED
        assert "missing_project_id" in result.blockers

    def test_missing_title_is_blocked(self):
        result = evaluate_project_identity(_identity_candidate(title=None))
        assert result.decision is ProjectIdentityDecision.BLOCKED
        assert "missing_title" in result.blockers

    def test_missing_outcome_is_blocked(self):
        result = evaluate_project_identity(_identity_candidate(outcome=None))
        assert result.decision is ProjectIdentityDecision.BLOCKED
        assert "missing_outcome" in result.blockers

    def test_missing_mission_bearing_is_blocked(self):
        result = evaluate_project_identity(_identity_candidate(mission_bearing=None))
        assert result.decision is ProjectIdentityDecision.BLOCKED
        assert "missing_mission_bearing" in result.blockers

    def test_missing_repo_refs_is_blocked(self):
        result = evaluate_project_identity(_identity_candidate(repo_refs=()))
        assert result.decision is ProjectIdentityDecision.BLOCKED
        assert "missing_repo_refs" in result.blockers

    def test_missing_venture_refs_is_blocked(self):
        result = evaluate_project_identity(_identity_candidate(venture_refs=()))
        assert result.decision is ProjectIdentityDecision.BLOCKED
        assert "missing_venture_refs" in result.blockers

    def test_missing_evidence_refs_is_blocked(self):
        result = evaluate_project_identity(_identity_candidate(evidence_refs=()))
        assert result.decision is ProjectIdentityDecision.BLOCKED
        assert "missing_evidence_refs" in result.blockers

    def test_raw_context_evidence_ref_is_blocked(self):
        result = evaluate_project_identity(
            _identity_candidate(evidence_refs=("raw_prompt:full prompt text",)),
        )
        assert result.decision is ProjectIdentityDecision.BLOCKED
        assert "raw_context_evidence_ref_blocked" in result.blockers

    def test_blocked_result_surfaces_compass_question(self):
        result = evaluate_project_identity(_identity_candidate(project_id=None))
        assert result.compass_question is not None
        assert "Compass needs" in result.compass_question

    def test_shared_repo_with_distinct_bearing_stays_defined(self):
        neighbor = _identity_neighbor(
            project_id="meridian-ui-review",
            mission_bearing="Expose reviewed command staging controls.",
            repo_refs=(
                "repo:C:/Users/scott/Code/Meridian-Worktrees/build-4-aegis",
            ),
            venture_refs=("venture:Other",),
            session_refs=(),
        )
        result = evaluate_project_identity(
            _identity_candidate(neighbors=(neighbor,)),
        )
        assert result.decision is ProjectIdentityDecision.DEFINED
        assert result.shared_repo_refs == (
            "repo:C:/Users/scott/Code/Meridian-Worktrees/build-4-aegis",
        )
        assert "meridian-ui-review" in result.distinguishing_neighbors
        assert result.collapsing_neighbors == ()
        assert result.blockers == ()

    def test_shared_venture_with_distinct_bearing_stays_defined(self):
        neighbor = _identity_neighbor(
            project_id="meridian-ui-review",
            mission_bearing="Expose reviewed command staging controls.",
            repo_refs=("repo:other",),
            venture_refs=("venture:Meridian",),
            session_refs=(),
        )
        result = evaluate_project_identity(
            _identity_candidate(neighbors=(neighbor,)),
        )
        assert result.decision is ProjectIdentityDecision.DEFINED
        assert result.shared_venture_refs == ("venture:Meridian",)
        assert "meridian-ui-review" in result.distinguishing_neighbors
        assert result.collapsing_neighbors == ()

    def test_shared_session_with_distinct_bearing_stays_defined(self):
        neighbor = _identity_neighbor(
            project_id="meridian-ui-review",
            mission_bearing="Expose reviewed command staging controls.",
            repo_refs=("repo:other",),
            venture_refs=("venture:Other",),
            session_refs=("session:build-4-aegis",),
        )
        result = evaluate_project_identity(
            _identity_candidate(neighbors=(neighbor,)),
        )
        assert result.decision is ProjectIdentityDecision.DEFINED
        assert result.shared_session_refs == ("session:build-4-aegis",)
        assert "meridian-ui-review" in result.distinguishing_neighbors
        assert result.collapsing_neighbors == ()

    def test_shared_refs_with_same_bearing_collapse_returns_compass_question(self):
        neighbor = _identity_neighbor(
            project_id="meridian-shadow",
            mission_bearing="Ship Meridian V2 project-boundary runtime.",
            repo_refs=(
                "repo:C:/Users/scott/Code/Meridian-Worktrees/build-4-aegis",
            ),
            venture_refs=("venture:Meridian",),
            session_refs=(),
        )
        result = evaluate_project_identity(
            _identity_candidate(neighbors=(neighbor,)),
        )
        assert result.decision is ProjectIdentityDecision.AMBIGUOUS
        assert "meridian-shadow" in result.collapsing_neighbors
        assert "project_identity_collapse_risk" in result.blockers
        assert result.compass_question is not None
        assert "distinguishing mission bearing" in result.compass_question
        assert result.to_dict()["execution_authorized"] is False

    def test_same_project_id_neighbor_collapses(self):
        neighbor = _identity_neighbor(
            project_id="meridian-v2",
            mission_bearing="Different bearing but same identity label.",
            repo_refs=(
                "repo:C:/Users/scott/Code/Meridian-Worktrees/build-4-aegis",
            ),
            venture_refs=("venture:Meridian",),
        )
        result = evaluate_project_identity(
            _identity_candidate(neighbors=(neighbor,)),
        )
        assert result.decision is ProjectIdentityDecision.AMBIGUOUS
        assert "meridian-v2" in result.collapsing_neighbors

    def test_unrelated_neighbor_is_ignored(self):
        neighbor = _identity_neighbor(
            project_id="polaris-orchestrator",
            mission_bearing="Coordinate Polaris sessions.",
            repo_refs=("repo:C:/Users/scott/Code/Polaris-lab",),
            venture_refs=("venture:Polaris",),
            session_refs=("session:polaris-coordinator",),
        )
        result = evaluate_project_identity(
            _identity_candidate(neighbors=(neighbor,)),
        )
        assert result.decision is ProjectIdentityDecision.DEFINED
        assert result.shared_repo_refs == ()
        assert result.shared_venture_refs == ()
        assert result.shared_session_refs == ()
        assert result.distinguishing_neighbors == ()
        assert result.collapsing_neighbors == ()

    def test_multiple_neighbors_can_mix_distinct_and_collapsing(self):
        distinct_neighbor = _identity_neighbor(
            project_id="meridian-ui-review",
            mission_bearing="Expose reviewed command staging controls.",
            repo_refs=(
                "repo:C:/Users/scott/Code/Meridian-Worktrees/build-4-aegis",
            ),
            venture_refs=("venture:Meridian",),
        )
        collapsing_neighbor = _identity_neighbor(
            project_id="meridian-shadow",
            mission_bearing="Ship Meridian V2 project-boundary runtime.",
            repo_refs=(
                "repo:C:/Users/scott/Code/Meridian-Worktrees/build-4-aegis",
            ),
            venture_refs=("venture:Meridian",),
        )
        result = evaluate_project_identity(
            _identity_candidate(
                neighbors=(distinct_neighbor, collapsing_neighbor),
            ),
        )
        assert result.decision is ProjectIdentityDecision.AMBIGUOUS
        assert "meridian-ui-review" in result.distinguishing_neighbors
        assert "meridian-shadow" in result.collapsing_neighbors

    def test_identity_result_serializes_stably(self):
        result = evaluate_project_identity(_identity_candidate())
        assert tuple(result.to_dict().keys()) == project_identity_result_dict_keys()

    def test_identity_result_is_json_serializable(self):
        result = evaluate_project_identity(_identity_candidate())
        encoded = json.dumps(result.to_dict(), sort_keys=True)
        assert "defined" in encoded
        assert "execution_authorized" in encoded

    def test_identity_result_is_deterministic(self):
        candidate = _identity_candidate()
        assert evaluate_project_identity(candidate) == evaluate_project_identity(
            candidate,
        )

    def test_identity_evaluation_type_is_required(self):
        with pytest.raises(ValueError, match="decision"):
            ProjectIdentityEvaluation(
                decision="defined",  # type: ignore[arg-type]
                project_id="meridian-v2",
                title="Meridian V2",
                outcome="outcome",
                mission_bearing="bearing",
                evidence_refs=("proof",),
            )

    def test_identity_runtime_does_not_emit_handoff_or_scope_fields(self):
        payload = evaluate_project_identity(_identity_candidate()).to_dict()
        assert "source_project_id" not in payload
        assert "target_project_id" not in payload
        assert "subject_kind" not in payload
        assert "subject_ref" not in payload
        assert "review_ready" not in payload
        assert "merge_authorized" not in payload

    def test_identity_runtime_does_not_emit_raw_context_keys(self):
        payload = evaluate_project_identity(_identity_candidate()).to_dict()
        assert "raw_prompt" not in payload
        assert "transcript" not in payload
        assert "free_form_context" not in payload

    def test_execution_is_never_authorized(self):
        defined = evaluate_project_identity(_identity_candidate()).to_dict()
        blocked = evaluate_project_identity(
            _identity_candidate(project_id=None),
        ).to_dict()
        neighbor = _identity_neighbor(
            mission_bearing="Ship Meridian V2 project-boundary runtime.",
            repo_refs=(
                "repo:C:/Users/scott/Code/Meridian-Worktrees/build-4-aegis",
            ),
            venture_refs=("venture:Meridian",),
        )
        ambiguous = evaluate_project_identity(
            _identity_candidate(neighbors=(neighbor,)),
        ).to_dict()
        assert defined["execution_authorized"] is False
        assert blocked["execution_authorized"] is False
        assert ambiguous["execution_authorized"] is False


class TestProjectIdentityBearingNormalization:
    """Codex Review B repair: bearing comparison must catch case/punctuation/whitespace collisions."""

    @pytest.mark.parametrize(
        "neighbor_bearing",
        (
            "ship meridian v2 project-boundary runtime.",
            "Ship Meridian V2 Project-Boundary Runtime",
            "  Ship Meridian V2 project-boundary runtime!",
            "Ship  Meridian   V2 project-boundary runtime.",
            "Ship Meridian V2 project-boundary runtime...",
            "SHIP MERIDIAN V2 PROJECT-BOUNDARY RUNTIME",
        ),
    )
    def test_normalized_bearing_collisions_return_ambiguous(self, neighbor_bearing):
        neighbor = _identity_neighbor(
            project_id="meridian-shadow",
            mission_bearing=neighbor_bearing,
            repo_refs=(
                "repo:C:/Users/scott/Code/Meridian-Worktrees/build-4-aegis",
            ),
            venture_refs=("venture:Meridian",),
        )
        result = evaluate_project_identity(
            _identity_candidate(neighbors=(neighbor,)),
        )
        assert result.decision is ProjectIdentityDecision.AMBIGUOUS
        assert "meridian-shadow" in result.collapsing_neighbors
        assert "project_identity_collapse_risk" in result.blockers
        assert result.to_dict()["execution_authorized"] is False

    def test_distinct_bearing_after_normalization_stays_defined(self):
        neighbor = _identity_neighbor(
            project_id="meridian-ui-review",
            mission_bearing="Ship Meridian V3 project-boundary runtime.",
            repo_refs=(
                "repo:C:/Users/scott/Code/Meridian-Worktrees/build-4-aegis",
            ),
            venture_refs=("venture:Meridian",),
        )
        result = evaluate_project_identity(
            _identity_candidate(neighbors=(neighbor,)),
        )
        assert result.decision is ProjectIdentityDecision.DEFINED
        assert "meridian-ui-review" in result.distinguishing_neighbors
        assert result.collapsing_neighbors == ()


class TestProjectIdentityBoundedDistinction:
    """Codex Review B repair: richer bounded identity evidence must keep distinct projects distinct."""

    @staticmethod
    def _shared_bearing_neighbor(**overrides) -> ProjectIdentityNeighbor:
        base = {
            "project_id": "meridian-shadow",
            "mission_bearing": "ship meridian v2 project-boundary runtime",
            "repo_refs": (
                "repo:C:/Users/scott/Code/Meridian-Worktrees/build-4-aegis",
            ),
            "venture_refs": ("venture:Meridian",),
        }
        base.update(overrides)
        return ProjectIdentityNeighbor(**base)

    def test_bearing_collision_with_distinct_title_stays_defined(self):
        neighbor = self._shared_bearing_neighbor(
            title="Meridian V2 Shadow Project",
        )
        result = evaluate_project_identity(
            _identity_candidate(neighbors=(neighbor,)),
        )
        assert result.decision is ProjectIdentityDecision.DEFINED
        assert "meridian-shadow" in result.distinguishing_neighbors
        assert result.collapsing_neighbors == ()
        assert result.to_dict()["execution_authorized"] is False

    def test_bearing_collision_with_distinct_outcome_stays_defined(self):
        neighbor = self._shared_bearing_neighbor(
            outcome="Shadow project explores parallel boundary runtime experiments.",
        )
        result = evaluate_project_identity(
            _identity_candidate(neighbors=(neighbor,)),
        )
        assert result.decision is ProjectIdentityDecision.DEFINED
        assert "meridian-shadow" in result.distinguishing_neighbors
        assert result.collapsing_neighbors == ()

    def test_bearing_collision_with_distinct_context_stays_defined(self):
        candidate = _identity_candidate(
            context=("Compass owns project identity and bearing.",),
            neighbors=(
                self._shared_bearing_neighbor(
                    context=("Shadow runtime explores parallel boundary checks.",),
                ),
            ),
        )
        result = evaluate_project_identity(candidate)
        assert result.decision is ProjectIdentityDecision.DEFINED
        assert "meridian-shadow" in result.distinguishing_neighbors
        assert result.collapsing_neighbors == ()

    def test_bearing_collision_with_distinct_artifacts_stays_defined(self):
        candidate = _identity_candidate(
            artifacts=("meridian_core/compass.py",),
            neighbors=(
                self._shared_bearing_neighbor(
                    artifacts=("meridian_core/shadow_runtime.py",),
                ),
            ),
        )
        result = evaluate_project_identity(candidate)
        assert result.decision is ProjectIdentityDecision.DEFINED
        assert "meridian-shadow" in result.distinguishing_neighbors

    def test_bearing_collision_with_distinct_objectives_stays_defined(self):
        candidate = _identity_candidate(
            objectives=("Define project runtime identity.",),
            neighbors=(
                self._shared_bearing_neighbor(
                    objectives=("Explore shadow boundary identity hypothesis.",),
                ),
            ),
        )
        result = evaluate_project_identity(candidate)
        assert result.decision is ProjectIdentityDecision.DEFINED
        assert "meridian-shadow" in result.distinguishing_neighbors

    def test_bearing_collision_with_distinct_tasks_stays_defined(self):
        candidate = _identity_candidate(
            tasks=("Create pure domain object.",),
            neighbors=(
                self._shared_bearing_neighbor(
                    tasks=("Prototype shadow comparison harness.",),
                ),
            ),
        )
        result = evaluate_project_identity(candidate)
        assert result.decision is ProjectIdentityDecision.DEFINED
        assert "meridian-shadow" in result.distinguishing_neighbors

    def test_bearing_collision_with_distinct_proof_trail_stays_defined(self):
        candidate = _identity_candidate(
            proof_trail=("tests/test_compass.py",),
            neighbors=(
                self._shared_bearing_neighbor(
                    proof_trail=("tests/test_shadow_runtime.py",),
                ),
            ),
        )
        result = evaluate_project_identity(candidate)
        assert result.decision is ProjectIdentityDecision.DEFINED
        assert "meridian-shadow" in result.distinguishing_neighbors

    def test_all_bounded_fields_matching_truly_collapses(self):
        bounded = {
            "title": "Meridian V2",
            "outcome": "Prime can coordinate V2 harness runtime without project drift.",
            "context": (
                "Compass owns project identity and bearing.",
                "V2 runtime stays pure until reviewed.",
            ),
            "artifacts": (
                "docs/v2-progress-tracker.md",
                "meridian_core/compass.py",
            ),
            "objectives": (
                "Define project runtime identity.",
                "Keep repo, venture, and session relationships explicit.",
            ),
            "tasks": (
                "Create pure domain object.",
                "Add deterministic serialization tests.",
            ),
            "proof_trail": (
                "docs/harness-stage-checklist.md#Compass",
                "tests/test_compass.py",
            ),
        }
        candidate = _identity_candidate(
            **{
                key: value
                for key, value in bounded.items()
                if key not in ("title", "outcome")
            },
            neighbors=(
                self._shared_bearing_neighbor(**bounded),
            ),
        )
        result = evaluate_project_identity(candidate)
        assert result.decision is ProjectIdentityDecision.AMBIGUOUS
        assert "meridian-shadow" in result.collapsing_neighbors
        assert result.distinguishing_neighbors == ()
        assert "project_identity_collapse_risk" in result.blockers
        assert result.to_dict()["execution_authorized"] is False

    def test_bounded_tuple_comparison_is_order_insensitive(self):
        neighbor = self._shared_bearing_neighbor(
            artifacts=("meridian_core/compass.py", "docs/v2-progress-tracker.md"),
        )
        candidate = _identity_candidate(
            artifacts=("docs/v2-progress-tracker.md", "meridian_core/compass.py"),
            neighbors=(neighbor,),
        )
        result = evaluate_project_identity(candidate)
        assert result.decision is ProjectIdentityDecision.AMBIGUOUS
        assert "meridian-shadow" in result.collapsing_neighbors

    def test_neighbor_without_bounded_fields_falls_back_to_bearing_only(self):
        neighbor = self._shared_bearing_neighbor()
        candidate = _identity_candidate(
            title="Meridian V2",
            outcome="Distinct outcome but neighbor carries no bounded evidence.",
            neighbors=(neighbor,),
        )
        result = evaluate_project_identity(candidate)
        assert result.decision is ProjectIdentityDecision.AMBIGUOUS
        assert "meridian-shadow" in result.collapsing_neighbors

    def test_one_sided_bounded_fields_do_not_distinguish(self):
        """One-sided bounded evidence cannot prove distinction.

        Candidate populates ``objectives`` while neighbor populates ``artifacts``;
        neither field is set on both sides, so neither can serve as evidence of
        distinct identity. With matching bearings and no two-sided distinguishing
        field, the result must collapse rather than silently distinguish.
        """
        neighbor = self._shared_bearing_neighbor(
            artifacts=("meridian_core/shadow_runtime.py",),
        )
        candidate = _identity_candidate(
            objectives=("Define project runtime identity.",),
            neighbors=(neighbor,),
        )
        result = evaluate_project_identity(candidate)
        assert result.decision is ProjectIdentityDecision.AMBIGUOUS
        assert "meridian-shadow" in result.collapsing_neighbors

    def test_two_sided_distinguishing_field_overrides_one_sided_fields(self):
        """A both-sided distinguishing field keeps neighbor distinct even when other fields are one-sided."""
        neighbor = self._shared_bearing_neighbor(
            artifacts=("meridian_core/shadow_runtime.py",),
            objectives=("Explore shadow boundary identity hypothesis.",),
        )
        candidate = _identity_candidate(
            artifacts=("meridian_core/compass.py",),
            objectives=("Define project runtime identity.",),
            tasks=("Create pure domain object.",),
            neighbors=(neighbor,),
        )
        result = evaluate_project_identity(candidate)
        assert result.decision is ProjectIdentityDecision.DEFINED
        assert "meridian-shadow" in result.distinguishing_neighbors
        assert result.collapsing_neighbors == ()

    def test_neighbor_richer_fields_serialize_stably(self):
        neighbor = ProjectIdentityNeighbor(
            project_id="meridian-shadow",
            mission_bearing="ship meridian v2 project-boundary runtime",
            title="Meridian Shadow",
            outcome="Shadow outcome.",
            context=("ctx",),
            artifacts=("artifact",),
            objectives=("objective",),
            tasks=("task",),
            proof_trail=("proof",),
            repo_refs=("repo:meridian",),
            venture_refs=("venture:Meridian",),
        )
        assert tuple(neighbor.to_dict().keys()) == project_identity_neighbor_dict_keys()

    def test_candidate_richer_fields_serialize_stably(self):
        candidate = _identity_candidate(
            context=("ctx",),
            artifacts=("artifact",),
            objectives=("objective",),
            tasks=("task",),
            proof_trail=("proof",),
        )
        assert tuple(candidate.to_dict().keys()) == project_identity_candidate_dict_keys()

    def test_candidate_from_definition_passes_bounded_fields(self):
        project = _project()
        candidate = project_identity_candidate_from_definition(
            project,
            mission_bearing="Ship Meridian V2 project-boundary runtime.",
            evidence_refs=("proof:from-definition-bounded",),
        )
        assert candidate.context == project.context
        assert candidate.artifacts == project.artifacts
        assert candidate.objectives == project.objectives
        assert candidate.tasks == project.tasks
        assert candidate.proof_trail == project.proof_trail


def _bounds_request(**overrides) -> ProjectBoundsRequest:
    base = {
        "project_id": "meridian-v2",
        "request_kind": "feature_change",
        "request_ref": "request:add-deterministic-test",
        "candidates": (
            ProjectScopeCandidate(
                project_id="meridian-v2",
                subject_kind="artifact",
                subject_ref="meridian_core/compass.py",
                evidence_refs=("proof:bounds-artifact",),
            ),
        ),
        "repo_refs": ("repo:C:/Users/scott/Code/Meridian-Worktrees/build-4-aegis",),
        "venture_refs": ("venture:Meridian",),
        "session_refs": ("session:build-4-aegis",),
        "evidence_refs": ("proof:bounds-request",),
    }
    base.update(overrides)
    return ProjectBoundsRequest(**base)


def _in_scope_candidate(**overrides) -> ProjectScopeCandidate:
    base = {
        "project_id": "meridian-v2",
        "subject_kind": "artifact",
        "subject_ref": "meridian_core/compass.py",
        "evidence_refs": ("proof:bounds-in",),
    }
    base.update(overrides)
    return ProjectScopeCandidate(**base)


def _out_of_scope_candidate(**overrides) -> ProjectScopeCandidate:
    base = {
        "project_id": "meridian-v2",
        "subject_kind": "artifact",
        "subject_ref": "bifrost/ui/command_staging.py",
        "evidence_refs": ("proof:bounds-out",),
    }
    base.update(overrides)
    return ProjectScopeCandidate(**base)


def _ambiguous_candidate(**overrides) -> ProjectScopeCandidate:
    base = {
        "project_id": "meridian-v2",
        "subject_kind": "ambiguous",
        "subject_ref": "shared repo note",
        "evidence_refs": ("proof:bounds-ambiguous",),
        "ambiguity_reason": "same repo but unclear project",
    }
    base.update(overrides)
    return ProjectScopeCandidate(**base)


def _blocked_candidate(**overrides) -> ProjectScopeCandidate:
    base = {
        "project_id": "polaris-orchestrator",
        "subject_kind": "artifact",
        "subject_ref": "polaris/some.py",
        "evidence_refs": ("proof:bounds-blocked",),
    }
    base.update(overrides)
    return ProjectScopeCandidate(**base)


class TestProjectBoundsRequest:
    def test_request_is_frozen(self):
        request = _bounds_request()
        with pytest.raises(FrozenInstanceError):
            request.request_kind = "scope_inquiry"  # type: ignore[misc]

    def test_request_serializes_stably(self):
        assert tuple(_bounds_request().to_dict().keys()) == (
            project_bounds_request_dict_keys()
        )

    def test_request_is_json_serializable(self):
        encoded = json.dumps(_bounds_request().to_dict(), sort_keys=True)
        assert "request_kind" in encoded
        assert "candidates" in encoded

    def test_request_ref_is_required(self):
        with pytest.raises(ValueError, match="request_ref"):
            ProjectBoundsRequest(
                project_id="meridian-v2",
                request_kind="feature_change",
                request_ref="",
                candidates=(_in_scope_candidate(),),
                evidence_refs=("proof:bounds",),
            )

    def test_request_kind_is_required(self):
        with pytest.raises(ValueError, match="request_kind"):
            ProjectBoundsRequest(
                project_id="meridian-v2",
                request_kind="",
                request_ref="request:test",
                candidates=(_in_scope_candidate(),),
                evidence_refs=("proof:bounds",),
            )

    def test_candidates_must_be_project_scope_candidate(self):
        with pytest.raises(ValueError, match="candidates"):
            ProjectBoundsRequest(
                project_id="meridian-v2",
                request_kind="feature_change",
                request_ref="request:test",
                candidates=("not-a-candidate",),  # type: ignore[arg-type]
                evidence_refs=("proof:bounds",),
            )


class TestProjectBoundsRuntime:
    def test_all_in_scope_subjects_return_in_scope(self):
        result = evaluate_project_bounds(
            _project(),
            _bounds_request(
                candidates=(
                    _in_scope_candidate(),
                    _in_scope_candidate(
                        subject_kind="proof",
                        subject_ref="tests/test_compass.py",
                    ),
                ),
            ),
        )
        assert result.decision is ProjectBoundsDecision.IN_SCOPE
        assert "meridian_core/compass.py" in result.in_scope_refs
        assert "tests/test_compass.py" in result.in_scope_refs
        assert result.out_of_scope_refs == ()
        assert result.blockers == ()
        assert result.to_dict()["execution_authorized"] is False

    def test_all_out_of_scope_subjects_return_out_of_scope(self):
        result = evaluate_project_bounds(
            _project(),
            _bounds_request(
                candidates=(
                    _out_of_scope_candidate(),
                    _out_of_scope_candidate(
                        subject_ref="docs/live-build-3.md",
                    ),
                ),
            ),
        )
        assert result.decision is ProjectBoundsDecision.OUT_OF_SCOPE
        assert result.in_scope_refs == ()
        assert "bifrost/ui/command_staging.py" in result.out_of_scope_refs
        assert "docs/live-build-3.md" in result.out_of_scope_refs
        assert result.compass_question is not None
        assert "redirected" in result.compass_question

    def test_mixed_subjects_return_partial_scope(self):
        result = evaluate_project_bounds(
            _project(),
            _bounds_request(
                candidates=(
                    _in_scope_candidate(),
                    _out_of_scope_candidate(),
                ),
            ),
        )
        assert result.decision is ProjectBoundsDecision.PARTIAL_SCOPE
        assert "meridian_core/compass.py" in result.in_scope_refs
        assert "bifrost/ui/command_staging.py" in result.out_of_scope_refs
        assert result.compass_question is not None
        assert "mixed scope" in result.compass_question

    def test_missing_request_project_id_blocks(self):
        result = evaluate_project_bounds(
            _project(),
            _bounds_request(project_id=None),
        )
        assert result.decision is ProjectBoundsDecision.BLOCKED
        assert "missing_request_project_id" in result.blockers
        assert result.to_dict()["execution_authorized"] is False

    def test_project_identity_mismatch_blocks(self):
        result = evaluate_project_bounds(
            _project(),
            _bounds_request(
                project_id="polaris-orchestrator",
                candidates=(
                    _in_scope_candidate(project_id="polaris-orchestrator"),
                ),
            ),
        )
        assert result.decision is ProjectBoundsDecision.BLOCKED
        assert "project_identity_mismatch" in result.blockers

    def test_empty_candidates_blocks(self):
        result = evaluate_project_bounds(
            _project(),
            _bounds_request(candidates=()),
        )
        assert result.decision is ProjectBoundsDecision.BLOCKED
        assert "missing_request_candidates" in result.blockers

    def test_missing_evidence_refs_blocks(self):
        result = evaluate_project_bounds(
            _project(),
            _bounds_request(evidence_refs=()),
        )
        assert result.decision is ProjectBoundsDecision.BLOCKED
        assert "missing_request_evidence_refs" in result.blockers

    def test_raw_context_evidence_ref_blocks(self):
        result = evaluate_project_bounds(
            _project(),
            _bounds_request(evidence_refs=("raw_prompt:full prompt text",)),
        )
        assert result.decision is ProjectBoundsDecision.BLOCKED
        assert "raw_context_evidence_ref_blocked" in result.blockers

    def test_unknown_request_kind_returns_compass_question(self):
        result = evaluate_project_bounds(
            _project(),
            _bounds_request(request_kind="unknown_kind"),
        )
        assert result.decision is ProjectBoundsDecision.AMBIGUOUS
        assert "unknown_bounds_request_kind" in result.blockers
        assert result.compass_question is not None
        assert "unknown_kind" in result.compass_question

    def test_explicit_ambiguous_request_kind_returns_compass_question(self):
        result = evaluate_project_bounds(
            _project(),
            _bounds_request(
                request_kind="ambiguous",
                ambiguity_reason="caller could not classify request",
            ),
        )
        assert result.decision is ProjectBoundsDecision.AMBIGUOUS
        assert "ambiguous_bounds_request" in result.blockers
        assert result.compass_question is not None
        assert "caller could not classify request" in result.compass_question

    def test_blocked_subject_blocks_bounds(self):
        result = evaluate_project_bounds(
            _project(),
            _bounds_request(
                candidates=(
                    _in_scope_candidate(),
                    _blocked_candidate(),
                ),
            ),
        )
        assert result.decision is ProjectBoundsDecision.BLOCKED
        assert "candidate_blocked" in result.blockers
        assert "polaris/some.py" in result.blocked_refs
        assert result.compass_question is not None

    def test_ambiguous_subject_returns_compass_question(self):
        result = evaluate_project_bounds(
            _project(),
            _bounds_request(
                candidates=(
                    _in_scope_candidate(),
                    _ambiguous_candidate(),
                ),
            ),
        )
        assert result.decision is ProjectBoundsDecision.AMBIGUOUS
        assert "candidate_ambiguous" in result.blockers
        assert "shared repo note" in result.ambiguous_refs
        assert result.compass_question is not None

    def test_shared_repo_venture_session_surfaced_not_collapsed(self):
        result = evaluate_project_bounds(
            _project(),
            _bounds_request(),
        )
        assert result.decision is ProjectBoundsDecision.IN_SCOPE
        assert (
            "repo:C:/Users/scott/Code/Meridian-Worktrees/build-4-aegis"
            in result.shared_relationship_refs
        )
        assert "venture:Meridian" in result.shared_relationship_refs
        assert "session:build-4-aegis" in result.shared_relationship_refs

    def test_non_shared_envelope_does_not_surface_shared_refs(self):
        result = evaluate_project_bounds(
            _project(),
            _bounds_request(
                repo_refs=("repo:unrelated",),
                venture_refs=("venture:Other",),
                session_refs=("session:other-session",),
            ),
        )
        assert result.shared_relationship_refs == ()

    def test_candidate_decisions_record_per_subject_outcomes(self):
        result = evaluate_project_bounds(
            _project(),
            _bounds_request(
                candidates=(
                    _in_scope_candidate(),
                    _out_of_scope_candidate(),
                ),
            ),
        )
        decisions = {
            entry["subject_ref"]: entry["decision"]
            for entry in result.candidate_decisions
        }
        assert decisions["meridian_core/compass.py"] == "in_scope"
        assert decisions["bifrost/ui/command_staging.py"] == "out_of_scope"

    def test_bounds_result_serializes_stably(self):
        result = evaluate_project_bounds(_project(), _bounds_request())
        assert tuple(result.to_dict().keys()) == project_bounds_result_dict_keys()

    def test_bounds_result_is_json_serializable(self):
        result = evaluate_project_bounds(_project(), _bounds_request())
        encoded = json.dumps(result.to_dict(), sort_keys=True)
        assert "in_scope" in encoded
        assert "execution_authorized" in encoded

    def test_bounds_result_is_deterministic(self):
        project = _project()
        request = _bounds_request()
        assert evaluate_project_bounds(project, request) == evaluate_project_bounds(
            project,
            request,
        )

    def test_bounds_evaluation_decision_type_required(self):
        with pytest.raises(ValueError, match="decision"):
            ProjectBoundsEvaluation(
                decision="in_scope",  # type: ignore[arg-type]
                project_id="meridian-v2",
                request_kind="feature_change",
                request_ref="request:test",
            )

    def test_bounds_runtime_does_not_emit_identity_or_handoff_fields(self):
        payload = evaluate_project_bounds(_project(), _bounds_request()).to_dict()
        assert "mission_bearing" not in payload
        assert "distinguishing_neighbors" not in payload
        assert "collapsing_neighbors" not in payload
        assert "source_project_id" not in payload
        assert "target_project_id" not in payload
        assert "review_ready" not in payload
        assert "merge_authorized" not in payload

    def test_bounds_runtime_does_not_emit_raw_context_keys(self):
        payload = evaluate_project_bounds(_project(), _bounds_request()).to_dict()
        assert "raw_prompt" not in payload
        assert "transcript" not in payload
        assert "free_form_context" not in payload

    def test_execution_is_never_authorized_across_branches(self):
        defined = evaluate_project_bounds(_project(), _bounds_request()).to_dict()
        partial = evaluate_project_bounds(
            _project(),
            _bounds_request(
                candidates=(
                    _in_scope_candidate(),
                    _out_of_scope_candidate(),
                ),
            ),
        ).to_dict()
        out_of_scope = evaluate_project_bounds(
            _project(),
            _bounds_request(candidates=(_out_of_scope_candidate(),)),
        ).to_dict()
        ambiguous = evaluate_project_bounds(
            _project(),
            _bounds_request(request_kind="unknown_kind"),
        ).to_dict()
        blocked = evaluate_project_bounds(
            _project(),
            _bounds_request(project_id=None),
        ).to_dict()
        for payload in (defined, partial, out_of_scope, ambiguous, blocked):
            assert payload["execution_authorized"] is False

    def test_request_kinds_exposes_known_set(self):
        kinds = project_bounds_request_kinds()
        assert "feature_change" in kinds
        assert "scope_inquiry" in kinds
        assert "boundary_extension" in kinds
        assert "context_load" in kinds
        assert "task_addition" in kinds
        assert "evidence_attach" in kinds
        assert "ambiguous" in kinds
        # frozen set: cannot be mutated by callers
        with pytest.raises(AttributeError):
            kinds.add("rogue_kind")  # type: ignore[attr-defined]

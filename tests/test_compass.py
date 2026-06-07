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
        # execution_authorized is REQUIRED by the coordinator-promoted
        # Compass Project Difference Runtime directive — always serialized as
        # False to mirror scope/bounds/identity/handoff invariants.
        assert payload["execution_authorized"] is False
        assert payload["merge_authorized"] is False


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

    @pytest.mark.parametrize(
        "raw_ref",
        (
            "raw_prompt:full prompt text",
            "raw_transcript:session log",
            "free_form_context:scratch notes",
            "transcript:full conversation",
            "conversation:approval said in chat",
            "provider_response:streamed body",
        ),
    )
    def test_raw_context_in_candidate_evidence_refs_blocks(self, raw_ref):
        """Self-review repair: raw-context refs hidden in subject candidate evidence must also block.

        Without this, the bounds runtime's request-level raw-context guard could
        be bypassed by stashing the raw payload on a per-subject candidate.
        """
        candidate_with_raw = _in_scope_candidate(
            evidence_refs=("proof:legit-evidence", raw_ref),
        )
        result = evaluate_project_bounds(
            _project(),
            _bounds_request(candidates=(candidate_with_raw,)),
        )
        assert result.decision is ProjectBoundsDecision.BLOCKED
        assert "raw_context_candidate_evidence_ref_blocked" in result.blockers
        assert result.to_dict()["execution_authorized"] is False

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


class TestProjectScopeRawContextGuard:
    """Codex Review B repair: raw-context evidence must fail closed at the scope layer.

    Prior to this repair, direct callers of ``evaluate_project_scope`` could
    pass ``evidence_refs=("raw_prompt:full prompt text",)`` and receive
    ``IN_SCOPE`` with the raw payload preserved in the serialized result.
    The outer bounds-runtime guard only protected callers that reached scope
    through ``evaluate_project_bounds``. This class proves the scope layer now
    blocks + redacts raw-context evidence for ALL callers and that safe
    evidence still passes.
    """

    @pytest.mark.parametrize(
        "raw_ref",
        (
            "raw_prompt:full prompt text",
            "raw_transcript:session log",
            "free_form_context:scratch notes",
            "transcript:full conversation",
            "conversation:approval said in chat",
            "provider_response:streamed body",
            "raw_context:everything",
            "prompt:user asked X",
            "line1\nline2 — embedded newline",
        ),
    )
    def test_raw_context_evidence_blocks_in_scope_match(self, raw_ref):
        """Even a candidate whose subject IS in the project boundary must fail closed."""
        candidate = ProjectScopeCandidate(
            project_id="meridian-v2",
            subject_kind="artifact",
            subject_ref="meridian_core/compass.py",  # IS in project artifacts
            evidence_refs=(raw_ref,),
        )
        result = evaluate_project_scope(_project(), candidate)
        assert result.decision is ProjectScopeDecision.BLOCKED
        assert "raw_context_evidence_ref_blocked" in result.blockers
        assert result.to_dict()["execution_authorized"] is False

    @pytest.mark.parametrize(
        "raw_ref",
        (
            "raw_prompt:full prompt text",
            "raw_transcript:session log",
            "free_form_context:scratch notes",
            "transcript:full conversation",
            "conversation:approval said in chat",
            "provider_response:streamed body",
        ),
    )
    def test_raw_context_evidence_does_not_leak_in_serialization(self, raw_ref):
        candidate = ProjectScopeCandidate(
            project_id="meridian-v2",
            subject_kind="artifact",
            subject_ref="meridian_core/compass.py",
            evidence_refs=(raw_ref, "proof:safe-evidence"),
        )
        payload = evaluate_project_scope(_project(), candidate).to_dict()
        # Raw payload text must not appear anywhere in the serialized result.
        encoded = json.dumps(payload, sort_keys=True)
        assert raw_ref not in encoded
        # Safe evidence still serialized.
        assert "proof:safe-evidence" in payload["evidence_refs"]
        # Redaction marker appears in place of the raw ref.
        assert "<redacted_raw_context>" in payload["evidence_refs"]

    def test_mixed_raw_and_safe_evidence_blocks_and_partially_redacts(self):
        candidate = ProjectScopeCandidate(
            project_id="meridian-v2",
            subject_kind="artifact",
            subject_ref="meridian_core/compass.py",
            evidence_refs=(
                "proof:safe-evidence",
                "raw_prompt:full prompt text",
                "proof:another-safe",
                "transcript:meeting notes",
            ),
        )
        result = evaluate_project_scope(_project(), candidate)
        assert result.decision is ProjectScopeDecision.BLOCKED
        assert "raw_context_evidence_ref_blocked" in result.blockers
        # Safe refs preserved in order; raw refs redacted in-place.
        assert result.evidence_refs == (
            "proof:safe-evidence",
            "<redacted_raw_context>",
            "proof:another-safe",
            "<redacted_raw_context>",
        )

    def test_safe_evidence_refs_still_return_in_scope(self):
        """Repair must not over-trigger: legitimate evidence still passes."""
        candidate = ProjectScopeCandidate(
            project_id="meridian-v2",
            subject_kind="artifact",
            subject_ref="meridian_core/compass.py",
            evidence_refs=("proof:legit-evidence", "tests/test_compass.py"),
        )
        result = evaluate_project_scope(_project(), candidate)
        assert result.decision is ProjectScopeDecision.IN_SCOPE
        assert result.evidence_refs == (
            "proof:legit-evidence",
            "tests/test_compass.py",
        )
        assert result.to_dict()["execution_authorized"] is False

    def test_safe_out_of_scope_subject_still_returns_out_of_scope(self):
        """The new raw-context guard must not change normal out-of-scope behavior."""
        candidate = ProjectScopeCandidate(
            project_id="meridian-v2",
            subject_kind="artifact",
            subject_ref="bifrost/ui/command_staging.py",  # NOT in project artifacts
            evidence_refs=("proof:legit-evidence",),
        )
        result = evaluate_project_scope(_project(), candidate)
        assert result.decision is ProjectScopeDecision.OUT_OF_SCOPE

    def test_bounds_runtime_still_blocks_raw_candidate_evidence_via_request_layer(self):
        """The bounds-layer pre-check (cc584318f) still fires before the scope-layer check.

        evaluate_project_bounds rejects raw candidate evidence at the request
        layer with ``raw_context_candidate_evidence_ref_blocked`` BEFORE
        iterating into evaluate_project_scope. This test confirms that
        defense-in-depth: the bounds layer catches it first.
        """
        candidate = ProjectScopeCandidate(
            project_id="meridian-v2",
            subject_kind="artifact",
            subject_ref="meridian_core/compass.py",
            evidence_refs=("raw_prompt:full prompt text",),
        )
        result = evaluate_project_bounds(
            _project(),
            _bounds_request(candidates=(candidate,)),
        )
        assert result.decision is ProjectBoundsDecision.BLOCKED
        # The request-level guard runs first and emits its own blocker name.
        assert "raw_context_candidate_evidence_ref_blocked" in result.blockers
        assert result.to_dict()["execution_authorized"] is False

    def test_scope_guard_independent_of_subject_match(self):
        """Raw-context guard must run BEFORE subject-kind/ref matching.

        Otherwise a caller could craft an unknown subject_kind to short-circuit
        the AMBIGUOUS path and still leak the raw payload through the result.
        """
        candidate = ProjectScopeCandidate(
            project_id="meridian-v2",
            subject_kind="artifact",
            subject_ref="not-actually-in-project",
            evidence_refs=("raw_prompt:full prompt text",),
        )
        result = evaluate_project_scope(_project(), candidate)
        assert result.decision is ProjectScopeDecision.BLOCKED
        assert result.blockers == ("raw_context_evidence_ref_blocked",)
        # Raw ref redacted even though it would never have reached IN_SCOPE.
        assert "<redacted_raw_context>" in result.evidence_refs
        assert "raw_prompt:full prompt text" not in result.evidence_refs

    def test_scope_blocked_serialization_is_json_safe_with_redaction(self):
        candidate = ProjectScopeCandidate(
            project_id="meridian-v2",
            subject_kind="artifact",
            subject_ref="meridian_core/compass.py",
            evidence_refs=("raw_prompt:secret payload",),
        )
        encoded = json.dumps(
            evaluate_project_scope(_project(), candidate).to_dict(),
            sort_keys=True,
        )
        assert "<redacted_raw_context>" in encoded
        assert "secret payload" not in encoded
        assert "raw_prompt:secret" not in encoded


class TestProjectScopeSubjectFieldRawContextGuard:
    """Cadence 3/3 self-review repair: subject_ref and ambiguity_reason must
    also be scanned for raw context.

    Before this repair, the scope-layer raw-context guard only checked
    candidate.evidence_refs. A caller could put a raw_prompt:/transcript:/
    free_form_context:/conversation:/provider_response: payload into
    candidate.subject_ref (or candidate.ambiguity_reason) and the AMBIGUOUS
    branch would interpolate it into compass_question, leaking the raw
    payload into to_dict()['compass_question'] and json.dumps output even
    though evidence_refs were safe.

    Reproducer (before fix):
      ProjectScopeCandidate(
          project_id='meridian-v2',
          subject_kind='ambiguous',
          subject_ref='raw_prompt:secret subject content',
          evidence_refs=('proof:safe',),
          ambiguity_reason='reason text',
      )
      -> AMBIGUOUS with compass_question="Compass question: should
         'raw_prompt:secret subject content' belong to meridian-v2? reason text"
      -> JSON contained 'secret subject content'.
    """

    @pytest.mark.parametrize(
        "raw_subject_ref",
        (
            "raw_prompt:secret subject content",
            "raw_transcript:session log",
            "free_form_context:scratch notes",
            "transcript:full conversation",
            "conversation:approval said in chat",
            "provider_response:streamed body",
            "raw_context:everything",
            "prompt:user asked X",
            "line1\nline2 — embedded newline",
        ),
    )
    def test_raw_context_in_subject_ref_blocks_and_redacts(self, raw_subject_ref):
        """Hits the AMBIGUOUS path that previously leaked, now redirected to BLOCKED."""
        candidate = ProjectScopeCandidate(
            project_id="meridian-v2",
            subject_kind="ambiguous",
            subject_ref=raw_subject_ref,
            evidence_refs=("proof:safe",),
            ambiguity_reason="some reason",
        )
        result = evaluate_project_scope(_project(), candidate)
        assert result.decision is ProjectScopeDecision.BLOCKED
        assert "raw_context_subject_field_blocked" in result.blockers
        assert result.subject_ref == "<redacted_raw_context>"
        # to_dict and json.dumps must not contain raw payload.
        payload = result.to_dict()
        assert payload["subject_ref"] == "<redacted_raw_context>"
        encoded = json.dumps(payload, sort_keys=True)
        assert raw_subject_ref not in encoded
        assert "<redacted_raw_context>" in encoded
        assert payload["execution_authorized"] is False

    @pytest.mark.parametrize(
        "raw_ambiguity_reason",
        (
            "raw_prompt:secret reason content",
            "transcript:secret meeting reason",
            "free_form_context:secret notes reason",
            "conversation:secret chat reason",
            "provider_response:secret response reason",
            "raw_context:everything reason",
        ),
    )
    def test_raw_context_in_ambiguity_reason_blocks_and_redacts(self, raw_ambiguity_reason):
        candidate = ProjectScopeCandidate(
            project_id="meridian-v2",
            subject_kind="ambiguous",
            subject_ref="meridian_core/compass.py",
            evidence_refs=("proof:safe",),
            ambiguity_reason=raw_ambiguity_reason,
        )
        result = evaluate_project_scope(_project(), candidate)
        assert result.decision is ProjectScopeDecision.BLOCKED
        assert "raw_context_subject_field_blocked" in result.blockers
        # ambiguity_reason is not serialized in the result (it lived only on
        # the candidate). What matters is the AMBIGUOUS branch never ran, so
        # the raw payload was never interpolated into compass_question. Result
        # carries no compass_question and the raw text is absent from JSON.
        encoded = json.dumps(result.to_dict(), sort_keys=True)
        assert raw_ambiguity_reason not in encoded
        assert result.compass_question is None

    def test_raw_context_in_subject_ref_independent_of_subject_kind(self):
        """Even a non-ambiguous subject_kind must block: the leak would also have
        surfaced via the AMBIGUOUS unknown-subject-kind path's `subject_ref!r`
        interpolation if a caller passed a non-recognized subject_kind.
        """
        candidate = ProjectScopeCandidate(
            project_id="meridian-v2",
            subject_kind="artifact",  # known kind, would otherwise reach IN_SCOPE or OUT_OF_SCOPE
            subject_ref="raw_prompt:secret subject content",
            evidence_refs=("proof:safe",),
        )
        result = evaluate_project_scope(_project(), candidate)
        assert result.decision is ProjectScopeDecision.BLOCKED
        assert "raw_context_subject_field_blocked" in result.blockers
        assert result.subject_ref == "<redacted_raw_context>"

    def test_raw_context_in_both_subject_ref_and_evidence_refs_blocks(self):
        """Evidence-refs check runs FIRST; subject_ref check runs SECOND. When
        both carry raw context, evidence-refs blocker wins (subject_ref check
        is masked by the earlier return). This documents the precedence
        without leaking the raw payload either way.
        """
        candidate = ProjectScopeCandidate(
            project_id="meridian-v2",
            subject_kind="ambiguous",
            subject_ref="raw_prompt:secret subject",
            evidence_refs=("raw_prompt:secret evidence",),
        )
        result = evaluate_project_scope(_project(), candidate)
        assert result.decision is ProjectScopeDecision.BLOCKED
        # evidence_refs blocker runs first.
        assert "raw_context_evidence_ref_blocked" in result.blockers
        encoded = json.dumps(result.to_dict(), sort_keys=True)
        assert "secret evidence" not in encoded
        assert "secret subject" not in encoded
        assert result.subject_ref == "<redacted_raw_context>"
        # If callers fix evidence_refs and retry, the subject-field guard still
        # fires directly and preserves the same no-raw-output invariant.
        retry = evaluate_project_scope(
            _project(),
            ProjectScopeCandidate(
                project_id="meridian-v2",
                subject_kind="ambiguous",
                subject_ref="raw_prompt:secret subject",
                evidence_refs=("proof:safe",),
            ),
        )
        assert retry.decision is ProjectScopeDecision.BLOCKED
        assert "raw_context_subject_field_blocked" in retry.blockers
        retry_encoded = json.dumps(retry.to_dict(), sort_keys=True)
        assert "secret subject" not in retry_encoded

    def test_safe_subject_ref_and_reason_still_reach_ambiguous(self):
        """Regression: legitimate AMBIGUOUS path with safe subject_ref still
        produces AMBIGUOUS with the interpolated compass_question. The new
        guard must not over-trigger.
        """
        candidate = ProjectScopeCandidate(
            project_id="meridian-v2",
            subject_kind="ambiguous",
            subject_ref="shared repo note",
            evidence_refs=("proof:safe",),
            ambiguity_reason="same repo but unclear project",
        )
        result = evaluate_project_scope(_project(), candidate)
        assert result.decision is ProjectScopeDecision.AMBIGUOUS
        assert "shared repo note" in result.compass_question
        assert "same repo but unclear project" in result.compass_question

    def test_safe_subject_ref_still_reaches_in_scope(self):
        """Regression: the new guard must not block legitimate IN_SCOPE matches."""
        candidate = ProjectScopeCandidate(
            project_id="meridian-v2",
            subject_kind="artifact",
            subject_ref="meridian_core/compass.py",
            evidence_refs=("proof:safe",),
        )
        result = evaluate_project_scope(_project(), candidate)
        assert result.decision is ProjectScopeDecision.IN_SCOPE

    def test_scope_blocked_subject_field_serializes_stably(self):
        candidate = ProjectScopeCandidate(
            project_id="meridian-v2",
            subject_kind="ambiguous",
            subject_ref="raw_prompt:secret",
            evidence_refs=("proof:safe",),
        )
        result = evaluate_project_scope(_project(), candidate)
        assert tuple(result.to_dict().keys()) == project_scope_result_dict_keys()

    def test_bounds_aggregation_uses_redacted_scope_subject_refs(self):
        """Regression for Codex Review B: bounds must not rebuild refs from raw candidates."""
        request = _bounds_request(
            candidates=(
                ProjectScopeCandidate(
                    project_id="meridian-v2",
                    subject_kind="ambiguous",
                    subject_ref="raw_prompt:secret subject content",
                    evidence_refs=("proof:safe",),
                    ambiguity_reason="raw_prompt:secret reason content",
                ),
            )
        )

        result = evaluate_project_bounds(_project(), request)
        payload = result.to_dict()
        encoded = json.dumps(payload, sort_keys=True)

        assert result.decision is ProjectBoundsDecision.BLOCKED
        assert result.blocked_refs == ("<redacted_raw_context>",)
        assert result.candidate_decisions == (
            {
                "subject_kind": "ambiguous",
                "subject_ref": "<redacted_raw_context>",
                "decision": "blocked",
            },
        )
        assert "secret subject content" not in encoded
        assert "secret reason content" not in encoded
        assert "<redacted_raw_context>" in encoded


class TestProjectDifferenceRawContextGuard:
    """Coordinator-promoted: Project Difference Runtime must fail closed on raw context.

    Mirrors the scope and bounds-layer block+redact pattern. evaluate_project_difference
    rejects raw-context payload smuggled through evidence_refs OR any profile text/ref
    field BEFORE comparing the two profiles, and the serialized result redacts
    evidence_refs so the raw payload never appears in to_dict() output. Existing
    same-repo/same-venture distinctness still holds (covered by the prior
    TestProjectDifferenceRuntime tests).
    """

    @pytest.mark.parametrize(
        "raw_ref",
        (
            "raw_prompt:full prompt text",
            "raw_transcript:session log",
            "free_form_context:scratch notes",
            "transcript:full conversation",
            "conversation:approval said in chat",
            "provider_response:streamed body",
            "raw_context:everything",
            "line1\nline2 — embedded newline",
        ),
    )
    def test_raw_context_in_evidence_refs_blocks_difference(self, raw_ref):
        result = evaluate_project_difference(
            _difference_profile(),
            _other_difference_profile(),
            evidence_refs=(raw_ref, "proof:safe-cmp"),
        )
        assert result.decision is ProjectDifferenceDecision.BLOCKED
        assert "raw_context_evidence_ref_blocked" in result.blockers
        # Raw ref redacted in serialized evidence_refs; safe ref preserved.
        assert "<redacted_raw_context>" in result.evidence_refs
        assert raw_ref not in result.evidence_refs
        assert "proof:safe-cmp" in result.evidence_refs
        assert result.to_dict()["execution_authorized"] is False
        assert result.to_dict()["merge_authorized"] is False

    @pytest.mark.parametrize(
        "raw_ref",
        (
            "raw_prompt:full prompt text",
            "raw_transcript:session log",
            "free_form_context:scratch notes",
            "transcript:full conversation",
            "conversation:approval said in chat",
            "provider_response:streamed body",
        ),
    )
    def test_raw_context_serialization_does_not_leak_payload(self, raw_ref):
        result = evaluate_project_difference(
            _difference_profile(),
            _other_difference_profile(),
            evidence_refs=(raw_ref, "proof:safe-cmp"),
        )
        encoded = json.dumps(result.to_dict(), sort_keys=True)
        assert raw_ref not in encoded
        assert "<redacted_raw_context>" in encoded

    def test_raw_context_in_left_mission_bearing_blocks(self):
        result = evaluate_project_difference(
            _difference_profile(mission_bearing="raw_prompt:secret left bearing"),
            _other_difference_profile(),
            evidence_refs=("proof:difference",),
        )
        assert result.decision is ProjectDifferenceDecision.BLOCKED
        assert "raw_context_in_left_mission_bearing_blocked" in result.blockers
        # Raw text from mission_bearing must NOT appear in serialized payload.
        encoded = json.dumps(result.to_dict(), sort_keys=True)
        assert "raw_prompt:secret left bearing" not in encoded

    def test_raw_context_in_right_mission_bearing_blocks(self):
        result = evaluate_project_difference(
            _difference_profile(),
            _other_difference_profile(mission_bearing="transcript:secret right bearing"),
            evidence_refs=("proof:difference",),
        )
        assert result.decision is ProjectDifferenceDecision.BLOCKED
        assert "raw_context_in_right_mission_bearing_blocked" in result.blockers

    @pytest.mark.parametrize(
        "field",
        (
            "objectives",
            "artifacts",
            "memory_pins",
            "blockers",
            "proof_expectations",
            "repo_refs",
            "venture_refs",
        ),
    )
    def test_raw_context_in_left_profile_tuple_field_blocks(self, field):
        overrides = {field: ("raw_prompt:smuggled payload",)}
        result = evaluate_project_difference(
            _difference_profile(**overrides),
            _other_difference_profile(),
            evidence_refs=("proof:difference",),
        )
        assert result.decision is ProjectDifferenceDecision.BLOCKED
        assert f"raw_context_in_left_{field}_blocked" in result.blockers
        encoded = json.dumps(result.to_dict(), sort_keys=True)
        assert "smuggled payload" not in encoded

    @pytest.mark.parametrize(
        "field",
        (
            "objectives",
            "artifacts",
            "memory_pins",
            "blockers",
            "proof_expectations",
            "repo_refs",
            "venture_refs",
        ),
    )
    def test_raw_context_in_right_profile_tuple_field_blocks(self, field):
        overrides = {field: ("transcript:smuggled payload",)}
        result = evaluate_project_difference(
            _difference_profile(),
            _other_difference_profile(**overrides),
            evidence_refs=("proof:difference",),
        )
        assert result.decision is ProjectDifferenceDecision.BLOCKED
        assert f"raw_context_in_right_{field}_blocked" in result.blockers

    def test_raw_context_guard_runs_before_required_field_blockers(self):
        """Raw-context guard precedes missing-field blockers so raw payload cannot
        sneak past via a profile that is also incomplete.
        """
        result = evaluate_project_difference(
            _difference_profile(
                mission_bearing="raw_prompt:secret",
                objectives=(),  # also incomplete
            ),
            _other_difference_profile(),
            evidence_refs=("proof:difference",),
        )
        assert result.decision is ProjectDifferenceDecision.BLOCKED
        # Raw-context blockers fire; missing-field blockers do NOT appear in
        # this result because the guard short-circuited before that check.
        assert "raw_context_in_left_mission_bearing_blocked" in result.blockers
        assert "missing_left_objectives" not in result.blockers

    def test_multiple_raw_context_sites_aggregate_into_blockers(self):
        result = evaluate_project_difference(
            _difference_profile(mission_bearing="raw_prompt:left secret"),
            _other_difference_profile(objectives=("transcript:right secret",)),
            evidence_refs=("free_form_context:evidence secret",),
        )
        assert result.decision is ProjectDifferenceDecision.BLOCKED
        assert "raw_context_evidence_ref_blocked" in result.blockers
        assert "raw_context_in_left_mission_bearing_blocked" in result.blockers
        assert "raw_context_in_right_objectives_blocked" in result.blockers

    def test_safe_inputs_still_distinguish_after_guard_added(self):
        """Regression: the new guard must not over-trigger on legitimate inputs."""
        result = evaluate_project_difference(
            _difference_profile(),
            _other_difference_profile(),
            evidence_refs=("proof:safe-cmp",),
        )
        assert result.decision is ProjectDifferenceDecision.DISTINCT
        assert "mission_bearing" in _difference_fields(result)
        assert result.to_dict()["execution_authorized"] is False
        assert result.to_dict()["merge_authorized"] is False

    def test_safe_inputs_same_profile_still_collapse_after_guard_added(self):
        """Regression: SAME_PROJECT path still reachable when bearings match."""
        result = evaluate_project_difference(
            _difference_profile(),
            _difference_profile(),
            evidence_refs=("proof:same",),
        )
        assert result.decision is ProjectDifferenceDecision.SAME_PROJECT
        assert result.to_dict()["execution_authorized"] is False

    def test_shared_repo_does_not_imply_same_project_under_raw_guard(self):
        """Regression: same-repo/different-bearing still returns DISTINCT after the
        raw-context guard is added (no silent merge on shared envelope).
        """
        result = evaluate_project_difference(
            _difference_profile(),
            _other_difference_profile(venture_refs=("venture:Other",)),
            evidence_refs=("proof:same-repo-different-bearing",),
        )
        assert result.decision is ProjectDifferenceDecision.DISTINCT
        assert result.shared_relationship_refs == (
            "repo:C:/Users/scott/Code/Meridian-Worktrees/build-4-aegis",
        )

    def test_shared_venture_does_not_imply_same_project_under_raw_guard(self):
        result = evaluate_project_difference(
            _difference_profile(repo_refs=("repo:other",)),
            _other_difference_profile(repo_refs=("repo:another",)),
            evidence_refs=("proof:same-venture-different-bearing",),
        )
        assert result.decision is ProjectDifferenceDecision.DISTINCT
        assert result.shared_relationship_refs == ("venture:Meridian",)

    def test_raw_context_blocked_result_serializes_stably(self):
        result = evaluate_project_difference(
            _difference_profile(),
            _other_difference_profile(),
            evidence_refs=("raw_prompt:secret",),
        )
        assert tuple(result.to_dict().keys()) == project_difference_result_dict_keys()

    def test_shared_relationship_refs_redacted_when_raw_context_shared(self):
        """Self-review repair: when both sides smuggle the same raw-context ref
        through repo_refs/venture_refs, the BLOCKED result must NOT leak the
        raw payload through shared_relationship_refs in the serialized output.
        """
        smuggled = "raw_prompt:smuggled-via-shared-repo"
        result = evaluate_project_difference(
            _difference_profile(repo_refs=(smuggled,)),
            _other_difference_profile(repo_refs=(smuggled,)),
            evidence_refs=("proof:cmp",),
        )
        assert result.decision is ProjectDifferenceDecision.BLOCKED
        assert "raw_context_in_left_repo_refs_blocked" in result.blockers
        assert "raw_context_in_right_repo_refs_blocked" in result.blockers
        # Redacted in dataclass field.
        assert smuggled not in result.shared_relationship_refs
        assert "<redacted_raw_context>" in result.shared_relationship_refs
        # Redacted in serialization (no raw payload anywhere).
        encoded = json.dumps(result.to_dict(), sort_keys=True)
        assert "smuggled-via-shared-repo" not in encoded
        assert "<redacted_raw_context>" in encoded

    def test_shared_relationship_refs_redacted_when_raw_context_shared_via_venture(self):
        smuggled = "transcript:smuggled-via-shared-venture"
        result = evaluate_project_difference(
            _difference_profile(venture_refs=(smuggled,)),
            _other_difference_profile(venture_refs=(smuggled,)),
            evidence_refs=("proof:cmp",),
        )
        assert result.decision is ProjectDifferenceDecision.BLOCKED
        encoded = json.dumps(result.to_dict(), sort_keys=True)
        assert "smuggled-via-shared-venture" not in encoded
        # Safe shared refs (e.g. the venture:Meridian intersection) must still
        # appear non-redacted.
        assert "<redacted_raw_context>" in result.shared_relationship_refs

    def test_execution_never_authorized_across_difference_branches(self):
        distinct = evaluate_project_difference(
            _difference_profile(),
            _other_difference_profile(),
            evidence_refs=("proof:cmp",),
        ).to_dict()
        same = evaluate_project_difference(
            _difference_profile(),
            _difference_profile(),
            evidence_refs=("proof:cmp",),
        ).to_dict()
        raw_blocked = evaluate_project_difference(
            _difference_profile(),
            _other_difference_profile(),
            evidence_refs=("raw_prompt:secret",),
        ).to_dict()
        missing_blocked = evaluate_project_difference(
            _difference_profile(project_id=None),
            _other_difference_profile(),
            evidence_refs=("proof:cmp",),
        ).to_dict()
        for payload in (distinct, same, raw_blocked, missing_blocked):
            assert payload["execution_authorized"] is False
            assert payload["merge_authorized"] is False


class TestProjectIdentityRawContextRedaction:
    """Codex Review B repair: raw-context evidence_refs on the identity BLOCKED
    path must be redacted in ProjectIdentityEvaluation.to_dict().

    Prior to the repair, evaluate_project_identity() detected raw-context refs
    via _project_identity_blockers and returned BLOCKED with
    ``raw_context_evidence_ref_blocked`` in blockers — but the result preserved
    ``candidate.evidence_refs`` verbatim, so to_dict()["evidence_refs"] still
    leaked the raw prompt/transcript/free-form-context payload. This mirrored
    the scope-layer bypass Codex Review B caught in cd20be9c3 and the
    difference-layer bypass repaired in df8120b49.
    """

    @pytest.mark.parametrize(
        "raw_ref",
        (
            "raw_prompt:secret prompt body",
            "raw_transcript:session log",
            "free_form_context:scratch notes",
            "transcript:full conversation",
            "conversation:approval said in chat",
            "provider_response:streamed body",
            "raw_context:everything",
            "prompt:user asked X",
            "line1\nline2 — embedded newline",
        ),
    )
    def test_raw_context_evidence_ref_redacted_in_blocked_serialization(self, raw_ref):
        result = evaluate_project_identity(
            _identity_candidate(evidence_refs=(raw_ref,)),
        )
        assert result.decision is ProjectIdentityDecision.BLOCKED
        assert "raw_context_evidence_ref_blocked" in result.blockers
        # Dataclass field redacted.
        assert raw_ref not in result.evidence_refs
        assert "<redacted_raw_context>" in result.evidence_refs
        # Serialized output redacted (no raw payload anywhere in JSON).
        payload = result.to_dict()
        assert raw_ref not in payload["evidence_refs"]
        assert "<redacted_raw_context>" in payload["evidence_refs"]
        encoded = json.dumps(payload, sort_keys=True)
        assert raw_ref not in encoded
        assert "<redacted_raw_context>" in encoded
        assert payload["execution_authorized"] is False

    def test_mixed_safe_and_raw_evidence_refs_partially_redacted(self):
        result = evaluate_project_identity(
            _identity_candidate(
                evidence_refs=(
                    "proof:safe-evidence-one",
                    "raw_prompt:secret prompt body",
                    "proof:safe-evidence-two",
                    "transcript:meeting notes",
                ),
            ),
        )
        assert result.decision is ProjectIdentityDecision.BLOCKED
        assert "raw_context_evidence_ref_blocked" in result.blockers
        # Safe refs preserved in order; raw refs redacted in-place.
        assert result.evidence_refs == (
            "proof:safe-evidence-one",
            "<redacted_raw_context>",
            "proof:safe-evidence-two",
            "<redacted_raw_context>",
        )
        encoded = json.dumps(result.to_dict(), sort_keys=True)
        assert "secret prompt body" not in encoded
        assert "meeting notes" not in encoded
        assert "proof:safe-evidence-one" in encoded
        assert "proof:safe-evidence-two" in encoded

    def test_safe_evidence_refs_pass_through_unchanged_on_other_blocker_paths(self):
        """Regression: the redaction call must not over-trigger on BLOCKED paths
        that fire for other reasons (e.g. missing project_id). Safe evidence
        refs should still appear in the serialized BLOCKED result so reviewers
        see the supplied proof trail.
        """
        result = evaluate_project_identity(
            _identity_candidate(
                project_id=None,  # forces BLOCKED via missing_project_id
                evidence_refs=("proof:safe-evidence", "tests/test_compass.py"),
            ),
        )
        assert result.decision is ProjectIdentityDecision.BLOCKED
        assert "missing_project_id" in result.blockers
        assert "raw_context_evidence_ref_blocked" not in result.blockers
        assert result.evidence_refs == (
            "proof:safe-evidence",
            "tests/test_compass.py",
        )

    def test_safe_evidence_refs_still_define_project_identity(self):
        """Regression: legitimate evidence still reaches DEFINED, not BLOCKED."""
        result = evaluate_project_identity(
            _identity_candidate(
                evidence_refs=("proof:legit", "tests/test_compass.py"),
            ),
        )
        assert result.decision is ProjectIdentityDecision.DEFINED
        assert result.evidence_refs == (
            "proof:legit",
            "tests/test_compass.py",
        )

    def test_existing_identity_blockers_preserved_alongside_redaction(self):
        """Multiple blocker conditions: required-field blockers + raw-context
        guard fire together; raw payload is still redacted in serialization.
        """
        result = evaluate_project_identity(
            _identity_candidate(
                title=None,  # missing_title
                evidence_refs=("raw_prompt:secret prompt body",),
            ),
        )
        assert result.decision is ProjectIdentityDecision.BLOCKED
        assert "missing_title" in result.blockers
        assert "raw_context_evidence_ref_blocked" in result.blockers
        encoded = json.dumps(result.to_dict(), sort_keys=True)
        assert "secret prompt body" not in encoded
        assert "<redacted_raw_context>" in encoded

    def test_blocked_redacted_result_serializes_stably(self):
        result = evaluate_project_identity(
            _identity_candidate(evidence_refs=("raw_prompt:secret",)),
        )
        assert tuple(result.to_dict().keys()) == project_identity_result_dict_keys()

    def test_execution_never_authorized_on_redacted_blocked_path(self):
        result = evaluate_project_identity(
            _identity_candidate(evidence_refs=("raw_prompt:secret",)),
        )
        assert result.to_dict()["execution_authorized"] is False


class TestProjectIdentityNeighborProjectIdRedaction:
    """Cadence 3/3 self-review repair: neighbor.project_id raw context leaked
    via collapsing_neighbors / distinguishing_neighbors lists and via the
    AMBIGUOUS compass_question's `list(collapsing)` interpolation.

    Reproducer (before fix):
      neighbor = ProjectIdentityNeighbor(
          project_id='raw_prompt:secret-neighbor-project-id-payload',
          mission_bearing='Ship Meridian V2 project-boundary runtime.',  # collides
          ...,
      )
      candidate = ...same bearing...
      evaluate_project_identity(candidate).collapsing_neighbors
        -> ('raw_prompt:secret-neighbor-project-id-payload',)
      compass_question contained 'raw_prompt:secret-neighbor-project-id-payload'
      json.dumps contained 'secret-neighbor'.
    """

    @staticmethod
    def _colliding_neighbor(project_id: str) -> ProjectIdentityNeighbor:
        return ProjectIdentityNeighbor(
            project_id=project_id,
            mission_bearing="Ship Meridian V2 project-boundary runtime.",
            repo_refs=(
                "repo:C:/Users/scott/Code/Meridian-Worktrees/build-4-aegis",
            ),
            venture_refs=("venture:Meridian",),
        )

    @pytest.mark.parametrize(
        "raw_project_id",
        (
            "raw_prompt:secret-neighbor-payload",
            "raw_transcript:secret-neighbor-session-log",
            "free_form_context:secret-neighbor-notes",
            "transcript:secret-neighbor-conversation",
            "conversation:secret-neighbor-chat",
            "provider_response:secret-neighbor-body",
            "raw_context:secret-neighbor-everything",
        ),
    )
    def test_raw_context_in_neighbor_project_id_redacted_in_collapsing(
        self, raw_project_id
    ):
        candidate = _identity_candidate(
            neighbors=(self._colliding_neighbor(raw_project_id),),
        )
        result = evaluate_project_identity(candidate)
        assert result.decision is ProjectIdentityDecision.AMBIGUOUS
        assert raw_project_id not in result.collapsing_neighbors
        assert "<redacted_raw_context>" in result.collapsing_neighbors
        encoded = json.dumps(result.to_dict(), sort_keys=True)
        assert raw_project_id not in encoded
        assert "<redacted_raw_context>" in encoded

    def test_raw_context_in_neighbor_project_id_redacted_in_compass_question(self):
        candidate = _identity_candidate(
            neighbors=(
                self._colliding_neighbor(
                    "raw_prompt:secret-neighbor-leak-via-question"
                ),
            ),
        )
        result = evaluate_project_identity(candidate)
        assert result.compass_question is not None
        assert "secret-neighbor-leak-via-question" not in result.compass_question
        assert "<redacted_raw_context>" in result.compass_question

    def test_raw_context_in_neighbor_project_id_redacted_in_distinguishing(self):
        """DEFINED path (distinct bearing) also redacts neighbor project_id."""
        neighbor = ProjectIdentityNeighbor(
            project_id="raw_prompt:secret-distinguishing-neighbor",
            mission_bearing="A genuinely different bearing for the neighbor.",
            repo_refs=(
                "repo:C:/Users/scott/Code/Meridian-Worktrees/build-4-aegis",
            ),
            venture_refs=("venture:Other",),
        )
        candidate = _identity_candidate(neighbors=(neighbor,))
        result = evaluate_project_identity(candidate)
        assert result.decision is ProjectIdentityDecision.DEFINED
        assert "raw_prompt:secret-distinguishing-neighbor" not in (
            result.distinguishing_neighbors
        )
        assert "<redacted_raw_context>" in result.distinguishing_neighbors
        encoded = json.dumps(result.to_dict(), sort_keys=True)
        assert "secret-distinguishing-neighbor" not in encoded

    def test_safe_neighbor_project_ids_pass_through_unchanged(self):
        """Regression: legitimate neighbors still appear unredacted."""
        candidate = _identity_candidate(
            neighbors=(self._colliding_neighbor("meridian-shadow"),),
        )
        result = evaluate_project_identity(candidate)
        assert result.decision is ProjectIdentityDecision.AMBIGUOUS
        assert result.collapsing_neighbors == ("meridian-shadow",)
        assert "meridian-shadow" in result.compass_question
        assert "<redacted_raw_context>" not in result.collapsing_neighbors

    def test_mixed_safe_and_raw_neighbors_partially_redacted(self):
        candidate = _identity_candidate(
            neighbors=(
                self._colliding_neighbor("meridian-safe-shadow"),
                self._colliding_neighbor("raw_prompt:secret-second-neighbor"),
            ),
        )
        result = evaluate_project_identity(candidate)
        assert result.decision is ProjectIdentityDecision.AMBIGUOUS
        assert "meridian-safe-shadow" in result.collapsing_neighbors
        assert "<redacted_raw_context>" in result.collapsing_neighbors
        encoded = json.dumps(result.to_dict(), sort_keys=True)
        assert "secret-second-neighbor" not in encoded
        assert "meridian-safe-shadow" in encoded

    def test_neighbor_redacted_result_serializes_stably(self):
        candidate = _identity_candidate(
            neighbors=(
                self._colliding_neighbor("raw_prompt:secret-stable-shape"),
            ),
        )
        result = evaluate_project_identity(candidate)
        assert tuple(result.to_dict().keys()) == project_identity_result_dict_keys()
        assert result.to_dict()["execution_authorized"] is False


class TestProjectBoundsSharedRelationshipRefsRedaction:
    """Cadence 3/3 self-review repair: bounds shared_relationship_refs carried
    raw payload when both project.relationship_refs AND request envelope
    contained the same raw-context entry — parallel of the difference-layer
    df8120b49 leak but on the bounds runtime, and reachable on ALL bounds
    decision branches (IN_SCOPE / OUT_OF_SCOPE / PARTIAL_SCOPE / AMBIGUOUS /
    BLOCKED), not just BLOCKED.
    """

    @staticmethod
    def _project_with_raw_repo(raw_ref: str) -> ProjectDefinition:
        return define_project(
            project_id="meridian-v2",
            title="Meridian V2",
            outcome="Outcome.",
            context=("ctx",),
            artifacts=("meridian_core/compass.py",),
            objectives=("obj",),
            tasks=("task",),
            proof_trail=("proof",),
            repo_refs=(raw_ref,),
            venture_refs=("venture:Meridian",),
        )

    @staticmethod
    def _request_with_raw_repo(raw_ref: str) -> ProjectBoundsRequest:
        return ProjectBoundsRequest(
            project_id="meridian-v2",
            request_kind="feature_change",
            request_ref="request:test-bounds-shared",
            candidates=(
                ProjectScopeCandidate(
                    project_id="meridian-v2",
                    subject_kind="artifact",
                    subject_ref="meridian_core/compass.py",
                    evidence_refs=("proof:safe",),
                ),
            ),
            repo_refs=(raw_ref,),
            venture_refs=("venture:Meridian",),
            evidence_refs=("proof:bounds",),
        )

    @pytest.mark.parametrize(
        "raw_ref",
        (
            "raw_prompt:secret-shared-repo",
            "raw_transcript:secret-shared-repo",
            "free_form_context:secret-shared-repo",
            "transcript:secret-shared-repo",
            "conversation:secret-shared-repo",
            "provider_response:secret-shared-repo",
        ),
    )
    def test_raw_context_in_shared_repo_ref_redacted_in_bounds_result(self, raw_ref):
        project = self._project_with_raw_repo(raw_ref)
        request = self._request_with_raw_repo(raw_ref)
        result = evaluate_project_bounds(project, request)
        # Bounds reaches IN_SCOPE on the safe artifact subject.
        assert result.decision is ProjectBoundsDecision.IN_SCOPE
        # shared_relationship_refs MUST NOT carry the raw payload.
        assert raw_ref not in result.shared_relationship_refs
        assert "<redacted_raw_context>" in result.shared_relationship_refs
        # Safe venture intersection still appears unredacted.
        assert "venture:Meridian" in result.shared_relationship_refs
        # JSON output has no raw payload.
        encoded = json.dumps(result.to_dict(), sort_keys=True)
        assert "secret-shared-repo" not in encoded
        assert "<redacted_raw_context>" in encoded
        assert result.to_dict()["execution_authorized"] is False

    def test_raw_context_in_shared_venture_ref_redacted_in_bounds_result(self):
        project = define_project(
            project_id="meridian-v2",
            title="Meridian V2",
            outcome="Outcome.",
            context=("ctx",),
            artifacts=("meridian_core/compass.py",),
            objectives=("obj",),
            tasks=("task",),
            proof_trail=("proof",),
            repo_refs=("repo:safe",),
            venture_refs=("transcript:secret-shared-venture",),
        )
        request = ProjectBoundsRequest(
            project_id="meridian-v2",
            request_kind="feature_change",
            request_ref="request:test-shared-venture",
            candidates=(
                ProjectScopeCandidate(
                    project_id="meridian-v2",
                    subject_kind="artifact",
                    subject_ref="meridian_core/compass.py",
                    evidence_refs=("proof:safe",),
                ),
            ),
            repo_refs=("repo:safe",),
            venture_refs=("transcript:secret-shared-venture",),
            evidence_refs=("proof:bounds",),
        )
        result = evaluate_project_bounds(project, request)
        assert result.decision is ProjectBoundsDecision.IN_SCOPE
        encoded = json.dumps(result.to_dict(), sort_keys=True)
        assert "secret-shared-venture" not in encoded
        assert "<redacted_raw_context>" in encoded

    def test_safe_shared_relationship_refs_pass_through_unchanged(self):
        """Regression: legitimate shared refs still appear unredacted."""
        project = define_project(
            project_id="meridian-v2",
            title="Meridian V2",
            outcome="Outcome.",
            context=("ctx",),
            artifacts=("meridian_core/compass.py",),
            objectives=("obj",),
            tasks=("task",),
            proof_trail=("proof",),
            repo_refs=("repo:safe",),
            venture_refs=("venture:Meridian",),
        )
        request = ProjectBoundsRequest(
            project_id="meridian-v2",
            request_kind="feature_change",
            request_ref="request:test-safe-shared",
            candidates=(
                ProjectScopeCandidate(
                    project_id="meridian-v2",
                    subject_kind="artifact",
                    subject_ref="meridian_core/compass.py",
                    evidence_refs=("proof:safe",),
                ),
            ),
            repo_refs=("repo:safe",),
            venture_refs=("venture:Meridian",),
            evidence_refs=("proof:bounds",),
        )
        result = evaluate_project_bounds(project, request)
        assert result.decision is ProjectBoundsDecision.IN_SCOPE
        assert "repo:safe" in result.shared_relationship_refs
        assert "venture:Meridian" in result.shared_relationship_refs
        assert "<redacted_raw_context>" not in result.shared_relationship_refs

    def test_bounds_evidence_refs_also_redacted_in_shared_path(self):
        """Defense-in-depth: when shared_relationship_refs are redacted, the
        bounds request.evidence_refs must also be redacted in the same result
        path so a caller cannot leak via that field either.
        """
        project = define_project(
            project_id="meridian-v2",
            title="Meridian V2",
            outcome="Outcome.",
            context=("ctx",),
            artifacts=("meridian_core/compass.py",),
            objectives=("obj",),
            tasks=("task",),
            proof_trail=("proof",),
            repo_refs=("repo:safe",),
            venture_refs=("venture:Meridian",),
        )
        request = ProjectBoundsRequest(
            project_id="meridian-v2",
            request_kind="feature_change",
            request_ref="request:test-evidence-redact",
            candidates=(
                ProjectScopeCandidate(
                    project_id="meridian-v2",
                    subject_kind="artifact",
                    subject_ref="meridian_core/compass.py",
                    evidence_refs=("proof:safe",),
                ),
            ),
            repo_refs=("repo:safe",),
            venture_refs=("venture:Meridian",),
            # Raw context in request envelope evidence_refs.
            evidence_refs=("raw_prompt:secret-bounds-evidence",),
        )
        # NOTE: request envelope raw-context evidence triggers BLOCKED via the
        # request-level guard before reaching _bounds_result's redaction.
        result = evaluate_project_bounds(project, request)
        assert result.decision is ProjectBoundsDecision.BLOCKED
        assert "raw_context_evidence_ref_blocked" in result.blockers
        encoded = json.dumps(result.to_dict(), sort_keys=True)
        assert "secret-bounds-evidence" not in encoded


class TestProjectBoundsRequestLevelRedaction:
    """Coordinator-promoted repair: bounds request-level raw context must never
    reach serialization.

    Codex review found three reproducers on main where bounds request-level
    fields leaked raw prompt/transcript/free-form context/conversation/
    provider-response payload despite the bounds runtime claiming to redact:

    1. ``request.evidence_refs=('raw_prompt:secret...',)`` with
       ``request_kind='task_addition'`` → BLOCKED with the right blocker, but
       ``result.to_dict()['evidence_refs']`` still contained the raw payload
       (already fixed earlier in _bounds_result's evidence_refs redaction).
    2. ``request.request_ref='raw_prompt:secret request ref'`` → IN_SCOPE
       result preserved the raw payload in ``request_ref``.
    3. ``request.request_kind='ambiguous'`` + ``ambiguity_reason='raw_prompt:
       secret ambiguity reason'`` → AMBIGUOUS result interpolated the raw
       payload into ``compass_question``.

    Repair: new raw-context guard on ``request.request_ref`` and
    ``request.ambiguity_reason`` runs BEFORE the AMBIGUOUS interpolation
    paths and returns BLOCKED with the new ``raw_context_request_field_blocked``
    blocker. ``_bounds_result`` also routes ``request.request_ref`` through
    ``_redact_raw_context_refs`` so any other path can't leak via that field.
    """

    @staticmethod
    def _project() -> ProjectDefinition:
        return define_project(
            project_id="meridian-v2",
            title="Meridian V2",
            outcome="Outcome.",
            context=("ctx",),
            artifacts=("meridian_core/compass.py",),
            objectives=("obj",),
            tasks=("task",),
            proof_trail=("proof",),
            repo_refs=("repo:safe",),
            venture_refs=("venture:Meridian",),
        )

    @staticmethod
    def _safe_candidate() -> ProjectScopeCandidate:
        return ProjectScopeCandidate(
            project_id="meridian-v2",
            subject_kind="artifact",
            subject_ref="meridian_core/compass.py",
            evidence_refs=("proof:safe",),
        )

    @pytest.mark.parametrize(
        "raw_ref",
        (
            "raw_prompt:secret bounds request evidence",
            "raw_transcript:secret evidence",
            "free_form_context:secret evidence",
            "transcript:secret evidence",
            "conversation:secret evidence",
            "provider_response:secret evidence",
        ),
    )
    def test_reproducer_1_raw_evidence_refs_redacted_in_blocked_result(self, raw_ref):
        """Reproducer 1 (from coordinator directive): raw_prompt: in
        request.evidence_refs MUST be redacted in BLOCKED to_dict() output.
        """
        request = ProjectBoundsRequest(
            project_id="meridian-v2",
            request_kind="task_addition",
            request_ref="request:test-1",
            candidates=(self._safe_candidate(),),
            evidence_refs=(raw_ref,),
        )
        result = evaluate_project_bounds(self._project(), request)
        assert result.decision is ProjectBoundsDecision.BLOCKED
        assert "raw_context_evidence_ref_blocked" in result.blockers
        # to_dict()['evidence_refs'] does NOT contain raw payload.
        payload = result.to_dict()
        assert raw_ref not in payload["evidence_refs"]
        assert "<redacted_raw_context>" in payload["evidence_refs"]
        # No raw payload anywhere in JSON.
        encoded = json.dumps(payload, sort_keys=True)
        assert raw_ref not in encoded
        assert "<redacted_raw_context>" in encoded
        assert payload["execution_authorized"] is False

    @pytest.mark.parametrize(
        "raw_ref",
        (
            "raw_prompt:secret request ref",
            "raw_transcript:secret request ref",
            "free_form_context:secret request ref",
            "transcript:secret request ref",
            "conversation:secret request ref",
            "provider_response:secret request ref",
        ),
    )
    def test_reproducer_2_raw_request_ref_redirected_to_blocked_with_redaction(
        self, raw_ref
    ):
        """Reproducer 2 (from coordinator directive): raw context in
        request_ref MUST never reach IN_SCOPE / OUT_OF_SCOPE / AMBIGUOUS with
        the raw payload preserved. The new guard returns BLOCKED with
        request_ref redacted.
        """
        request = ProjectBoundsRequest(
            project_id="meridian-v2",
            request_kind="task_addition",
            request_ref=raw_ref,
            candidates=(self._safe_candidate(),),
            evidence_refs=("proof:request",),
        )
        result = evaluate_project_bounds(self._project(), request)
        assert result.decision is ProjectBoundsDecision.BLOCKED
        assert "raw_context_request_field_blocked" in result.blockers
        # request_ref redacted in dataclass field.
        assert raw_ref not in result.request_ref
        assert result.request_ref == "<redacted_raw_context>"
        # to_dict()['request_ref'] also redacted.
        payload = result.to_dict()
        assert payload["request_ref"] == "<redacted_raw_context>"
        encoded = json.dumps(payload, sort_keys=True)
        assert raw_ref not in encoded
        assert "<redacted_raw_context>" in encoded
        assert payload["execution_authorized"] is False

    @pytest.mark.parametrize(
        "raw_reason",
        (
            "raw_prompt:secret ambiguity reason",
            "raw_transcript:secret ambiguity reason",
            "free_form_context:secret ambiguity reason",
            "transcript:secret ambiguity reason",
            "conversation:secret ambiguity reason",
            "provider_response:secret ambiguity reason",
        ),
    )
    def test_reproducer_3_raw_ambiguity_reason_redirected_to_blocked(self, raw_reason):
        """Reproducer 3 (from coordinator directive): raw context in
        ambiguity_reason MUST never reach AMBIGUOUS result where
        compass_question interpolates it. The new guard returns BLOCKED
        BEFORE the AMBIGUOUS branch runs.
        """
        request = ProjectBoundsRequest(
            project_id="meridian-v2",
            request_kind="ambiguous",
            request_ref="request:test-3",
            candidates=(self._safe_candidate(),),
            evidence_refs=("proof:safe",),
            ambiguity_reason=raw_reason,
        )
        result = evaluate_project_bounds(self._project(), request)
        assert result.decision is ProjectBoundsDecision.BLOCKED
        assert "raw_context_request_field_blocked" in result.blockers
        # No raw payload in compass_question or anywhere else.
        encoded = json.dumps(result.to_dict(), sort_keys=True)
        assert raw_reason not in encoded
        assert result.to_dict()["execution_authorized"] is False

    def test_safe_request_ref_and_ambiguity_reason_still_reach_ambiguous(self):
        """Regression: legitimate AMBIGUOUS request with safe request_ref and
        safe ambiguity_reason still produces AMBIGUOUS with the interpolated
        compass_question. The new guard must not over-trigger.
        """
        request = ProjectBoundsRequest(
            project_id="meridian-v2",
            request_kind="ambiguous",
            request_ref="request:legitimate-ambiguous",
            candidates=(self._safe_candidate(),),
            evidence_refs=("proof:safe",),
            ambiguity_reason="caller could not classify this request",
        )
        result = evaluate_project_bounds(self._project(), request)
        assert result.decision is ProjectBoundsDecision.AMBIGUOUS
        assert "ambiguous_bounds_request" in result.blockers
        assert result.compass_question is not None
        assert "request:legitimate-ambiguous" in result.compass_question
        assert "caller could not classify this request" in result.compass_question
        assert result.request_ref == "request:legitimate-ambiguous"

    def test_safe_in_scope_request_preserves_safe_request_ref(self):
        """Regression: safe IN_SCOPE result preserves the safe request_ref
        unchanged in to_dict() output.
        """
        request = ProjectBoundsRequest(
            project_id="meridian-v2",
            request_kind="feature_change",
            request_ref="request:safe-in-scope",
            candidates=(self._safe_candidate(),),
            evidence_refs=("proof:bounds",),
        )
        result = evaluate_project_bounds(self._project(), request)
        assert result.decision is ProjectBoundsDecision.IN_SCOPE
        assert result.request_ref == "request:safe-in-scope"
        assert "<redacted_raw_context>" not in result.request_ref

    def test_request_field_guard_runs_before_ambiguous_kind_check(self):
        """Ordering invariant: raw-context guard on request_ref runs BEFORE
        the ``request_kind == 'ambiguous'`` AMBIGUOUS branch so the AMBIGUOUS
        compass_question never interpolates a raw request_ref payload.
        """
        request = ProjectBoundsRequest(
            project_id="meridian-v2",
            request_kind="ambiguous",
            request_ref="raw_prompt:secret-request-via-ambiguous-path",
            candidates=(self._safe_candidate(),),
            evidence_refs=("proof:safe",),
            ambiguity_reason="safe reason",
        )
        result = evaluate_project_bounds(self._project(), request)
        assert result.decision is ProjectBoundsDecision.BLOCKED
        assert "raw_context_request_field_blocked" in result.blockers
        encoded = json.dumps(result.to_dict(), sort_keys=True)
        assert "secret-request-via-ambiguous-path" not in encoded

    def test_bounds_blocked_request_field_serializes_stably(self):
        request = ProjectBoundsRequest(
            project_id="meridian-v2",
            request_kind="task_addition",
            request_ref="raw_prompt:secret",
            candidates=(self._safe_candidate(),),
            evidence_refs=("proof:safe",),
        )
        result = evaluate_project_bounds(self._project(), request)
        assert tuple(result.to_dict().keys()) == project_bounds_result_dict_keys()


class TestProjectIdentityScalarRawContextRedaction:
    """Codex Review B follow-up — Cadence 4/4 self-review repair.

    Before the repair, _project_identity_blockers() only scanned
    candidate.evidence_refs, and evaluate_project_identity() serialized
    candidate.mission_bearing / title / outcome / project_id verbatim. A
    raw-prompt payload smuggled through any of those scalar identity fields
    therefore (a) failed to add a raw-context blocker and (b) leaked into
    ProjectIdentityEvaluation.to_dict() output.

    Reproducer (mission_bearing leak):
      candidate = ProjectIdentityCandidate(
          ...,
          mission_bearing='raw_prompt:secret mission payload',
      )
      evaluate_project_identity(candidate).decision is DEFINED  # not blocked
      json.dumps(...to_dict()) contained 'secret mission payload'.
    """

    @pytest.mark.parametrize(
        ("field", "raw_value"),
        (
            ("mission_bearing", "raw_prompt:secret mission payload"),
            ("project_id", "raw_prompt:secret-project-id-payload"),
            ("title", "raw_transcript:secret title transcript"),
            ("outcome", "free_form_context:secret outcome body"),
        ),
    )
    def test_raw_context_in_scalar_identity_field_blocks_and_redacts(
        self, field, raw_value
    ):
        candidate = _identity_candidate(**{field: raw_value})
        result = evaluate_project_identity(candidate)
        assert result.decision is ProjectIdentityDecision.BLOCKED
        assert f"raw_context_{field}_blocked" in result.blockers
        assert getattr(result, field) == "<redacted_raw_context>"
        payload = result.to_dict()
        encoded = json.dumps(payload, sort_keys=True)
        assert raw_value not in encoded
        assert "secret" not in encoded or "<redacted_raw_context>" in encoded
        assert payload[field] == "<redacted_raw_context>"
        assert payload["execution_authorized"] is False

    def test_safe_mission_bearing_preserved_unchanged(self):
        candidate = _identity_candidate(
            mission_bearing="Ship Meridian V2 project-boundary runtime.",
        )
        result = evaluate_project_identity(candidate)
        assert result.decision is ProjectIdentityDecision.DEFINED
        assert result.mission_bearing == (
            "Ship Meridian V2 project-boundary runtime."
        )
        assert "<redacted_raw_context>" not in result.mission_bearing

    def test_safe_scalar_identity_fields_preserved_unchanged(self):
        candidate = _identity_candidate(
            project_id="meridian-v2",
            title="Meridian V2",
            outcome=(
                "Prime can coordinate V2 harness runtime without project drift."
            ),
            mission_bearing="Ship Meridian V2 project-boundary runtime.",
        )
        result = evaluate_project_identity(candidate)
        payload = result.to_dict()
        assert payload["project_id"] == "meridian-v2"
        assert payload["title"] == "Meridian V2"
        assert payload["outcome"] == (
            "Prime can coordinate V2 harness runtime without project drift."
        )
        assert payload["mission_bearing"] == (
            "Ship Meridian V2 project-boundary runtime."
        )
        assert "<redacted_raw_context>" not in json.dumps(payload, sort_keys=True)


class TestProjectIdentitySharedRefRawContextRedaction:
    """Codex Review B follow-up — raw-context payload smuggled through
    relationship-ref tuples (repo_refs / venture_refs / session_refs) leaked
    via ProjectIdentityEvaluation.shared_repo_refs / shared_venture_refs /
    shared_session_refs when the candidate and a neighbor both carried the
    same raw payload.

    Reproducer (shared_repo_refs leak):
      candidate.repo_refs = ('raw_prompt:shared-repo-secret',)
      neighbor.repo_refs  = ('raw_prompt:shared-repo-secret',)
      evaluate_project_identity(candidate).shared_repo_refs
        -> ('raw_prompt:shared-repo-secret',)  # raw payload preserved
    """

    @pytest.mark.parametrize(
        ("ref_field", "raw_value"),
        (
            ("repo_refs", "raw_prompt:shared-repo-secret"),
            ("venture_refs", "raw_prompt:shared-venture-secret"),
            ("session_refs", "raw_prompt:shared-session-secret"),
        ),
    )
    def test_raw_context_in_relationship_ref_blocks_before_overlap(
        self, ref_field, raw_value
    ):
        """The raw-context guard fires BEFORE neighbor overlap evaluation, so
        no shared-refs leak path can be reached. The result is BLOCKED with a
        per-field raw-context blocker and the serialized output redacts the
        payload.
        """
        candidate = _identity_candidate(
            **{ref_field: (raw_value,)},
        )
        result = evaluate_project_identity(candidate)
        assert result.decision is ProjectIdentityDecision.BLOCKED
        assert f"raw_context_{ref_field}_blocked" in result.blockers
        encoded = json.dumps(result.to_dict(), sort_keys=True)
        assert raw_value not in encoded
        assert result.to_dict()["execution_authorized"] is False

    def test_safe_shared_refs_still_surfaced(self):
        """Regression: a safe shared repo ref with a distinguishing bearing
        still appears in shared_repo_refs (DEFINED path) unchanged.
        """
        neighbor = ProjectIdentityNeighbor(
            project_id="meridian-shadow",
            mission_bearing="A truly different bearing for the shadow project.",
            repo_refs=(
                "repo:C:/Users/scott/Code/Meridian-Worktrees/build-4-aegis",
            ),
            venture_refs=("venture:Meridian",),
        )
        candidate = _identity_candidate(neighbors=(neighbor,))
        result = evaluate_project_identity(candidate)
        assert result.decision is ProjectIdentityDecision.DEFINED
        assert "repo:C:/Users/scott/Code/Meridian-Worktrees/build-4-aegis" in (
            result.shared_repo_refs
        )
        assert "<redacted_raw_context>" not in result.shared_repo_refs


class TestProjectDifferenceProjectIdRedaction:
    """Codex Review B follow-up — left/right project_id raw-context leak.

    Before the repair, _project_difference_raw_context_blockers() only
    scanned tuple-shaped fields, not the scalar project_id. A raw payload
    smuggled through left.project_id therefore reached the DISTINCT branch
    and was copied verbatim into ProjectDifferenceEvaluation.left_project_id,
    leaking through to_dict()['left_project_id'].

    Reproducer (before fix):
      left  = ProjectDifferenceProfile(project_id='raw_prompt:left-secret', ...)
      right = ProjectDifferenceProfile(project_id='right-id', ...)
      result = evaluate_project_difference(left, right, evidence_refs=('proof:cmp',))
      result.decision is DISTINCT
      result.to_dict()['left_project_id'] == 'raw_prompt:left-secret'
    """

    @pytest.mark.parametrize(
        ("side", "raw_value"),
        (
            ("left", "raw_prompt:left-secret"),
            ("right", "raw_prompt:right-secret"),
            ("left", "raw_transcript:left-session"),
            ("right", "free_form_context:right-scratch"),
        ),
    )
    def test_raw_context_in_project_id_blocks_and_redacts(self, side, raw_value):
        if side == "left":
            left = _difference_profile(project_id=raw_value)
            right = _other_difference_profile()
        else:
            left = _difference_profile()
            right = _other_difference_profile(project_id=raw_value)
        result = evaluate_project_difference(
            left, right, evidence_refs=("proof:cmp",),
        )
        assert result.decision is ProjectDifferenceDecision.BLOCKED
        assert f"raw_context_in_{side}_project_id_blocked" in result.blockers
        payload = result.to_dict()
        encoded = json.dumps(payload, sort_keys=True)
        assert raw_value not in encoded
        assert payload[f"{side}_project_id"] == "<redacted_raw_context>"
        assert payload["execution_authorized"] is False
        assert payload["merge_authorized"] is False

    def test_safe_project_ids_preserved_distinct(self):
        result = evaluate_project_difference(
            _difference_profile(project_id="meridian-v2-a"),
            _other_difference_profile(project_id="meridian-v2-b"),
            evidence_refs=("proof:cmp",),
        )
        assert result.decision is ProjectDifferenceDecision.DISTINCT
        payload = result.to_dict()
        assert payload["left_project_id"] == "meridian-v2-a"
        assert payload["right_project_id"] == "meridian-v2-b"
        assert "<redacted_raw_context>" not in json.dumps(
            payload, sort_keys=True
        )

    def test_safe_project_ids_preserved_same_project(self):
        result = evaluate_project_difference(
            _difference_profile(),
            _difference_profile(),
            evidence_refs=("proof:cmp",),
        )
        assert result.decision is ProjectDifferenceDecision.SAME_PROJECT
        payload = result.to_dict()
        assert payload["left_project_id"] == "meridian-v2"
        assert payload["right_project_id"] == "meridian-v2"

    def test_raw_context_in_both_project_ids_aggregates_blockers(self):
        result = evaluate_project_difference(
            _difference_profile(project_id="raw_prompt:left-secret"),
            _other_difference_profile(project_id="raw_prompt:right-secret"),
            evidence_refs=("proof:cmp",),
        )
        assert result.decision is ProjectDifferenceDecision.BLOCKED
        assert "raw_context_in_left_project_id_blocked" in result.blockers
        assert "raw_context_in_right_project_id_blocked" in result.blockers
        encoded = json.dumps(result.to_dict(), sort_keys=True)
        assert "left-secret" not in encoded
        assert "right-secret" not in encoded


class TestHandoffScalarMetadataRedaction:
    """Codex Review B follow-up — handoff scalar metadata raw-context leak.

    Before the repair, _handoff_request_blockers() checked tuple refs and
    enum membership, but did not scan the scalar reason_category /
    payload_type / source_project_id / target_project_id fields for the
    raw-context prefix (only exact-match enum membership). When any of those
    scalar fields carried a raw payload, _handoff_result() copied them
    verbatim and ProjectHandoffEvaluation.to_dict() leaked the payload.

    Reproducer (before fix):
      request = _handoff_request(reason_category='raw_prompt:secret reason')
      result  = evaluate_cross_project_handoff(src, tgt, request)
      result.decision is BLOCKED   # via unknown_handoff_reason_category
      result.to_dict()['reason_category'] == 'raw_prompt:secret reason'
    """

    @pytest.mark.parametrize(
        ("field", "raw_value", "expected_blocker"),
        (
            (
                "reason_category",
                "raw_prompt:secret reason",
                "raw_context_reason_category_blocked",
            ),
            (
                "reason_category",
                "raw_transcript:reason transcript",
                "raw_context_reason_category_blocked",
            ),
            (
                "payload_type",
                "raw_prompt:secret payload type",
                "raw_context_payload_type_blocked",
            ),
            (
                "payload_type",
                "free_form_context:payload notes",
                "raw_context_payload_type_blocked",
            ),
            (
                "source_project_id",
                "raw_prompt:secret-source-id",
                "raw_context_source_project_id_blocked",
            ),
            (
                "target_project_id",
                "raw_prompt:secret-target-id",
                "raw_context_target_project_id_blocked",
            ),
        ),
    )
    def test_raw_context_in_scalar_metadata_blocks_and_redacts(
        self, field, raw_value, expected_blocker
    ):
        result = evaluate_cross_project_handoff(
            _difference_profile(),
            _other_difference_profile(),
            _handoff_request(**{field: raw_value}),
        )
        assert result.decision is ProjectHandoffDecision.BLOCKED
        assert expected_blocker in result.blockers
        assert getattr(result, field) == "<redacted_raw_context>"
        payload = result.to_dict()
        encoded = json.dumps(payload, sort_keys=True)
        assert raw_value not in encoded
        assert payload[field] == "<redacted_raw_context>"
        assert payload["execution_authorized"] is False
        assert payload["review_ready"] is False

    def test_safe_scalar_metadata_preserved_unchanged(self):
        result = evaluate_cross_project_handoff(
            _difference_profile(),
            _other_difference_profile(),
            _handoff_request(
                reason_category="proof_packet",
                payload_type="proof_refs",
                source_project_id="meridian-v2",
                target_project_id="meridian-ui-review",
            ),
        )
        assert result.decision is ProjectHandoffDecision.REVIEW_READY
        payload = result.to_dict()
        assert payload["reason_category"] == "proof_packet"
        assert payload["payload_type"] == "proof_refs"
        assert payload["source_project_id"] == "meridian-v2"
        assert payload["target_project_id"] == "meridian-ui-review"
        assert "<redacted_raw_context>" not in json.dumps(payload, sort_keys=True)

    def test_raw_context_in_multiple_scalars_aggregates_blockers(self):
        result = evaluate_cross_project_handoff(
            _difference_profile(),
            _other_difference_profile(),
            _handoff_request(
                reason_category="raw_prompt:secret reason",
                payload_type="raw_prompt:secret payload type",
                source_project_id="raw_prompt:secret-source",
                target_project_id="raw_prompt:secret-target",
            ),
        )
        assert result.decision is ProjectHandoffDecision.BLOCKED
        assert "raw_context_reason_category_blocked" in result.blockers
        assert "raw_context_payload_type_blocked" in result.blockers
        assert "raw_context_source_project_id_blocked" in result.blockers
        assert "raw_context_target_project_id_blocked" in result.blockers
        encoded = json.dumps(result.to_dict(), sort_keys=True)
        assert "secret reason" not in encoded
        assert "secret payload type" not in encoded
        assert "secret-source" not in encoded
        assert "secret-target" not in encoded

    def test_handoff_redacted_result_serializes_stably(self):
        result = evaluate_cross_project_handoff(
            _difference_profile(),
            _other_difference_profile(),
            _handoff_request(reason_category="raw_prompt:secret reason"),
        )
        assert tuple(result.to_dict().keys()) == project_handoff_result_dict_keys()

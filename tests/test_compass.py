"""Tests for Compass project definition runtime."""

from __future__ import annotations

import json
from dataclasses import FrozenInstanceError

import pytest

from meridian_core.compass import (
    ProjectDefinition,
    ProjectDifferenceDecision,
    ProjectDifferenceEvaluation,
    ProjectDifferenceEvidence,
    ProjectDifferenceProfile,
    ProjectHandoffDecision,
    ProjectHandoffEvaluation,
    ProjectHandoffRequest,
    ProjectRelationshipRefs,
    ProjectScopeCandidate,
    ProjectScopeDecision,
    ProjectScopeEvaluation,
    define_project,
    evaluate_cross_project_handoff,
    evaluate_project_difference,
    evaluate_project_scope,
    project_difference_evidence_dict_keys,
    project_difference_profile_dict_keys,
    project_difference_profile_from_definition,
    project_difference_result_dict_keys,
    project_definition_dict_keys,
    project_definition_fingerprint,
    project_handoff_request_dict_keys,
    project_handoff_result_dict_keys,
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

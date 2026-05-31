# Public Exports Readiness Checklist

**Status:** V2 policy defining when Meridian harness objects are ready to become package-root public exports.

**Audience:** Build 2 (package/API), Build lanes implementing harnesses, Codex Reviews, Scott.

**Purpose:** Provide a clear, repeatable checklist that gates progression from internal module imports to `meridian_core.__all__` public exports. This checklist prevents premature or unsafe exports and documents the decision trail for each name.

---

## When to Use This Checklist

**Before** adding any new name to `meridian_core.__all__`, fill out the checklist for that name:

1. When a harness implementation is complete and tested.
2. When a harness contract is finalized and proven stable.
3. When a Codex review clears the implementation or contract.
4. When the Build 2 lane decides the name should be public.

The checklist is not a pass-fail quiz. It documents what has been verified and flags what is still pending.

---

## Readiness Dimensions

Each dimension is evaluated independently. All dimensions should be at least green (verified) before export approval. Yellow (partial) dimensions require explicit Codex or Build 2 sign-off.

### 1. Runtime Stability

Does the code exist, compile, and pass tests in isolation?

- Green: Code is stable and tested. Implementation exists in main; tests pass; no crashes or logic errors.
- Yellow: Code exists but is maturing. Implementation merged; some tests pass; known limitations documented.
- Red: Code is incomplete or broken. Not yet merged, test failures, or architectural changes pending.

For package exports: Green required. Yellow requires explicit sign-off.

### 2. Test Coverage & Correctness

Does the test suite prove the name behaves as documented?

- Green: Tests exist and passing. >= 80% code coverage; public API contract tested; edge cases documented.
- Yellow: Tests exist but partial. 50-79% coverage; happy path tested; edge cases flagged TODO.
- Red: Tests missing or failing. < 50% coverage or active test failures.

For package exports: Green required.

### 3. Documentation

Is the name's purpose, parameters, return type, and failure modes clear?

- Green: Public API documented. Docstring complete; return types/exceptions documented; examples provided.
- Yellow: Documentation exists but minimal. Docstring present; missing examples or edge-case notes.
- Red: Documentation missing or stale. No docstring or docstring contradicts code.

For package exports: Green required.

### 4. Contract Baseline (for harnesses)

Is the name part of a finalized, published contract?

- Green: Contract published. Named in docs/<harness>-contract.md; Codex cleared; domain frozen.
- Yellow: Contract draft exists. Draft docs/<harness>-contract.md with name; awaiting final Codex review.
- Red: No contract or stale. Name not in contract, or contract predates code by > 1 build cycle.

For package exports: Green required.

### 5. FileMap Registration (cross-harness names only)

If the name is used by other harnesses, is it registered in FileMap?

- Green: FileMap entry exists. Name/module path in FileMap; area/purpose current; reviewed by FileMap lane.
- Yellow: FileMap entry pending. Name used by other harnesses; entry requested but not merged.
- Red: FileMap entry missing. Name used by 2+ harnesses but FileMap unaware.

For package exports: Green required if used by non-root modules. Yellow if Build 3 request active.

### 6. Backward-Compatibility Risk

Does exporting this name limit future refactoring or create breaking-change risk?

- Green: Low risk. Name unlikely to change; no known refactoring; class/function is final/immutable.
- Yellow: Moderate risk. Name will change; export gated on contract finalization (documented).
- Red: High risk. Name in flux; planned refactoring would break callers; no contract freeze date.

For package exports: Green required. Yellow requires notation in __all__ or comment.

### 7. Naming Convention

Is the public name consistent with Meridian's naming conventions?

- Green: Follows conventions. Enum/class: PascalCase; function/constant: snake_case; no private prefix; <= 50 chars.
- Yellow: Unusual but justifiable. Non-standard casing approved by Build 2.
- Red: Violates conventions. Private prefix exposed; inconsistent; misleading.

For package exports: Green required unless Build 2 approves Yellow.

---

## Checklist Template

Use for each export candidate:

Candidate: <FullyQualifiedName>
- Module: meridian_core.<module>
- Kind: enum / dataclass / function / constant
- Proposed addition to __all__: Yes / No
- Rationale: One-line reason for export

Readiness Dimensions:
- Runtime Stability: Green / Yellow / Red
- Test Coverage: Green / Yellow / Red
- Documentation: Green / Yellow / Red
- Contract Baseline: Green / Yellow / Red
- FileMap Registration: Green / Yellow / Red / N/A
- Backward-Compatibility: Green / Yellow / Red
- Naming Convention: Green / Yellow / Red

Decision: Export / Do Not Export / Defer Until <milestone>

---

## Current Exports Status

V0/V1 Stable, Production-Ready:
All core names: ProgressIntention, Mission*, RiskTier, RelayRoute, AegisEvidence, ReviewConsoleItem, HarnessBuild, FileMap, FileArea, CouncilPlan, PromptBudgetPlan, PromptMetricSample, PromptPacket, and others documented in docs/package-api-surface-note.md

V2 Recently Exported (Green):
- CognitionActionType, CognitionLane, CognitionDecision, CognitionPolicy, CognitionPolicyResult, cognition_policy_for_tier, evaluate_cognition_policy (Build 2, commit b04c465; all dimensions green)

V2 Pending Exports (Contract-Complete, Runtime Pending):
- MemoryRecord, MemoryQuery, MemoryHit, MemoryKind, MemorySource (Echo harness)
- AtlasHit, AtlasQuery, AtlasResult, AtlasSource (Atlas harness)
- PrimeNextAction (Prime Autonomy)
- SessionLifecycleState (Session Lifecycle)
- WorkflowWorkOrder, WorkflowInputPacket, etc. (Workflow dispatch)

---

## Export Approval Gates

1. Build 2 completes readiness checklist; all dimensions green or approved yellow.
2. If dimension is red, defer until gap closed.
3. If any dimension yellow, Codex review must explicitly approve (documented in PR).
4. Build 2 merges export and updates this checklist with commit hash/date.

---

## Maintenance

This checklist is reviewed by Build 2 when new exports are added or Codex review surfaces concerns. Last updated: Build 2, 2026-06-05.

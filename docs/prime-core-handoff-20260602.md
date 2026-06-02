# Prime Core / Harness Stage Handoff - 2026-06-02

## Read This First

This handoff is for a new Codex session continuing current Meridian work.

Work only in Meridian. Do not touch Polaris.

Current implementation lane:

- Worktree: `C:\Users\scott\Code\Meridian-Worktrees\project-context-integrity`
- Branch: `codex/project-context-integrity`
- Shared main: do not assume it is safe to edit unless Scott explicitly asks.
- Live UI server: Scott runs it separately at `http://127.0.0.1:5500/index.html`; do not start another server.

Current operating rule from Scott:

- Before work, state intent and presumed alignment, then proceed unless corrected.
- Permission requirement applies to writes. Reads/checks can proceed.
- Keep outputs short.
- Commit meaningful checkpoints.
- Update Git and Obsidian around every three prompt-level changes.
- Work must be scoped to one harness or Spark setting/control.
- Frontend and backend must not drift. Visible harness UI must represent backend truth.
- Harness right-panel titles use `[Harness] Runtime Logic`.

## Current Commit Stack In This Lane

Recent commits:

- `44903eb4` Add harness stage HTML dashboard
- `3ced8fc6` Add harness stage checklist
- `c9256622` Record Prime core runtime depth
- `723a5898` Add Prime no drift audit
- `aa16e5e5` Add Prime interaction request contract
- `f5b67f66` Bind Aegis risk into Prime runtime
- `bf709340` Normalize wired harness runtime titles
- `5377fd75` Record Prime runtime tracker status
- `13c8b7af` Expose Prime runtime logic in harness
- `7c7b3103` Add Prime ownership and executability gates
- `9fac6846` Add Prime runtime decision contract
- `70027afa` Move Compass Vulcan depth to backend V2 checklist
- `8d23cb30` Deepen Compass and Vulcan checklist definitions
- `412a72e3` Split Compass project context and Vulcan sessions

The worktree was clean after `44903eb4`.

## Most Important Files

Prime runtime:

- `meridian_core/prime_runtime.py`
- `tests/test_prime_runtime.py`

Visible UI and bridge:

- `index.html`
- `scripts/meridian-model-bridge.js`
- `tests/test_bifrost_cockpit.py`

Harness stage tracking:

- `docs/harness-stage-checklist.md`
- `docs/harness-stage-checklist.html`

Build planning:

- `docs/v2-progress-tracker.md`
- `docs/v2-detailed-build-plan.md`
- `docs/ui-integration-checklist.md`

FileMap:

- `meridian_core/filemap.py`
- `docs/FileMap.md`
- `tests/test_filemap.py`

Obsidian log updated during this work:

- `G:\My Drive\Aesop Academy\Obsidian\Meridian_Build\8-Logs.md`

## What Was Built

### Compass / Vulcan Split

Compass owns project context, project definition, bounds, scope, project difference, and cross-project communication.

Vulcan owns live session lifecycle, User Session targets, stale target guards, command plans, lifecycle state, and session grouping.

Built files/surfaces:

- `meridian_core/compass_logic_snapshot.py`
- `meridian_core/vulcan_logic_snapshot.py`
- `/bridge/compass-logic`
- `/bridge/vulcan-logic`
- Compass Runtime Logic panel
- Vulcan Runtime Logic panel

Important correction:

The deep Compass/Vulcan analysis was moved out of the UI checklist and into backend V2 planning. UI may render backend-sourced snapshots, but deeper controls wait for backend runtime.

### Prime Runtime Core

Prime now has a backend runtime packet in `meridian_core/prime_runtime.py`.

Core objects:

- `PrimeDecisionStatus`
- `PrimeIntentKind`
- `PrimeSourceRef`
- `PrimeProof`
- `PrimeExecutability`
- `PrimeAegisRiskInput`
- `PrimeInteractionRequest`
- `PrimeRuntimeContext`
- `PrimeDecision`
- `PrimeDriftAudit`

Core functions:

- `assemble_prime_runtime_context`
- `aegis_risk_from_aggregate`
- `resolve_prime_owner`
- `evaluate_prime_executability`
- `build_prime_proof_packet`
- `make_prime_decision`
- `resolve_prime_decision`
- `resolve_prime_interaction`
- `audit_prime_decision`
- `prime_runtime_snapshot`

Prime runtime currently assembles backend state from:

- Compass source refs and project summary
- Vulcan source refs and session-state summary
- Relay source refs and model-route summary
- Aegis aggregate gate/risk input

Prime runtime emits:

- typed request
- runtime decision
- owner harness
- status
- action
- why
- risk
- context
- Aegis risk logic
- no-drift audit
- proof packet
- blockers
- visible-to-Scott declarations

Prime runtime does not yet execute live actions.

### Aegis Risk Binding

Prime no longer treats Aegis as only a placeholder.

Prime consumes Aegis aggregate gate summary through `PrimeAegisRiskInput`.

Source path:

- `meridian_core.aegis.summarize_aggregate_route_gates`

Prime Aegis fields:

- `highestSeverity`
- `aggregateAction`
- `evidenceRequired`
- `blockedGates`
- `demotedGates`
- `approvalsPresent`
- `waiversPresent`
- `blocking`
- `requiresApproval`

If Aegis blocks, Prime executability becomes `needs_approval`.

Bug fixed:

`make_prime_decision` no longer flattens approval-needed decisions into generic `blocked` just because blockers exist. It preserves `needs_approval`.

### Prime Interaction Request

Prime now carries an explicit typed request in each decision.

`PrimeInteractionRequest` fields:

- `request_id`
- `intent`
- `action`
- `why`
- `project_id`
- `risk`
- `requires_approval`
- `requires_clarification`
- `visible_prompt_ref`

This prevents the UI from inventing why Prime made a decision.

### Prime No-Drift Audit

Prime emits `PrimeDriftAudit`.

Audit checks:

- request project matches context project
- owner source is available unless owner is Prime
- proof packet includes owner source or Prime
- Aegis risk is visible when Aegis source is available
- visible field declaration is complete

Audit output:

- `status`
- `checks`
- `failures`
- `clean`

Prime Runtime Logic UI renders this as `No drift audit logic`.

### Prime Runtime Logic UI

Clicking Prime opens `Prime Runtime Logic`.

The panel renders backend data from:

- `/bridge/prime-logic`
- `meridian_core.prime_runtime`

Current status:

- Prime Runtime Logic UI is built-awaiting-review.
- It is not review-cleared.
- Do not bind live execution or live Compass/Vulcan/Relay inputs until review acceptance.

Visible sections currently include:

- Prime backend source
- Runtime truth map
- Typed interaction request
- Decision and owner logic
- No drift audit logic
- Backend context logic
- Aegis risk logic
- Backend source refs
- Proof and invalidation logic
- Visible-to-Scott declaration
- Execution blockers
- Backend capability sections

### Harness Runtime Logic Naming

Wired harness panel titles now follow:

- `Prime Runtime Logic`
- `Relay Runtime Logic`
- `Compass Runtime Logic`
- `Vulcan Runtime Logic`

Old names removed:

- `Relay Model Logic`
- `Compass Project Logic`
- `Vulcan Session Logic`

Tests guard this naming.

### Harness Stage Checklist

Built:

- `docs/harness-stage-checklist.md`
- `docs/harness-stage-checklist.html`

Purpose:

Track every harness by stage so Scott can ask for current state or build a specific harness/stage later.

Stages:

- Contract / Baseline
- V2 Backend
- Core Implementation
- Prime Integration
- Runtime Logic UI
- Proofs / Review
- Operations

Extra no-drift checks documented:

- FileMap / Discoverability
- Obsidian / Build Log
- Review State

Update rule:

When `docs/harness-stage-checklist.md` changes, update `docs/harness-stage-checklist.html` in the same checkpoint.

## Current Harness State

| Harness | Contract / Baseline | V2 Backend | Core Implementation | Prime Integration | Runtime Logic UI | Proofs / Review | Operations | Next Build |
|---|---|---|---|---|---|---|---|---|
| Prime | built | built-awaiting-review | built-awaiting-review | built-awaiting-review | built-awaiting-review | awaiting review | not live execution | Review Prime Runtime Logic UI and runtime contract before binding live Compass/Vulcan/Relay inputs. |
| Relay / Model | built | needs build | partial | partial via Prime source refs | wired | partial | Auto disabled | Provider metadata, DeepSeek route, prompt payload visibility, dispatch hardening. |
| Compass | baseline | needs build | snapshot only | partial via Prime source refs | wired | not reviewed as runtime | no writes | Project definition, bounds/scope, difference, cross-project handoff runtime. |
| Vulcan / Session Lifecycle | baseline | needs build | partial | partial via Prime source refs | wired | partial | no live command execution | Live session state evidence, command-plan proof, permissions, close/archive write-through. |
| Aegis | built | built | built | wired into Prime risk input | partial | review-cleared core; Prime binding awaiting review | proof gates only | Runtime Logic UI for Aegis and live proof packet surfaces. |
| Bifrost | built | needs build | partial | renders Prime/Relay/Compass/Vulcan snapshots | owns UI shell | partial | UI only | V2 cockpit extensions, balance, prompt payload, voice surface. |
| Echo | built | built | built | not wired into Prime runtime | not wired | review-cleared core | query only | Feed live memory hits into Prime runtime packet. |
| Atlas | built | built | built | not wired into Prime runtime | not wired | review-cleared core | retrieval only | Feed live retrieval hits into Prime runtime packet. |
| Beacon | baseline/partial | not queued here | partial | not wired into Prime runtime | not wired | partial | observes only | Define heartbeat/liveness Runtime Logic UI and Prime heartbeat input boundary. |
| Charon / FileMap | built | built | built | indirect via docs/context | partial | tests passing | lookup only | Runtime Logic UI reading FileMap state. |
| Arbiter / Reviews | partial | partial | partial | not wired into Prime runtime | not wired | partial | review queue only | Runtime Logic UI for review state and Prime acceptance gates. |
| Workflow | baseline | baseline | not implemented | not wired | not wired | contract only | no dispatch | Workflow/sub-agent runtime and Prime work-order binding. |
| Federation | horizon | horizon | planning only | not wired | not wired | review-cleared planning | no runtime | Keep out of V2 runtime until Prime core is stable. |
| Security / Guardrails | reserved | not queued | not implemented | not wired | not wired | none | none | Define Security harness scope separate from Aegis proof gates. |
| Ratchet / Tool | planned | not queued | not implemented | not wired | not wired | none | none | Define tool execution contract and permission boundaries. |
| Source / Git | planned | not queued | not implemented | not wired | not wired | none | none | Define branch/worktree mutation gates before any UI action. |
| Vision / Browser | planned | not queued | not implemented | not wired | not wired | none | none | Define browser/vision harness contract and proof surface. |
| Autonomy / Release | planned | not queued | not implemented | not wired | not wired | none | none | Define release/autonomy gates after Prime/Vulcan/Aegis mature. |

## V2 Progress Snapshot

From `docs/v2-progress-tracker.md`:

- Prime Autonomy: 2 clear, 1 awaiting review, total 3.
- Echo Harness: 2 clear, 2 contract baseline, total 4.
- Atlas Harness: 2 clear, 1 contract baseline, total 3.
- Relay/Model Harness: 2 clear, 2 baseline, 6 needs build, total 10.
- Aegis Harness: 2 clear, total 2.
- Compass Harness: 1 baseline, 4 needs build, total 5.
- Session Lifecycle Harness: 1 clear, 1 baseline, 5 needs build, total 7.
- Bifrost Harness: 1 clear, 2 baseline, 6 needs build, total 9.
- Federation Harness: 1 clear, total 1.
- Total V2: 13 clear, 1 awaiting review, 9 baseline, 21 needs build, total 44.

Important correction:

- Prime Runtime Logic UI was previously overstated as wired before its frontend surface was complete. It now has a fuller frontend runtime logic renderer and is built-awaiting-review, not review-cleared.

## Current Priority

1. Prime review acceptance.
2. Compass backend runtime.
3. Vulcan live session state and command-plan proof.
4. Relay model/provider metadata and prompt payload visibility.
5. Echo/Atlas live inputs into Prime runtime.

## Verification Already Run

Prime/Aegis/Bifrost/FileMap verification after Aegis risk binding:

- `471 passed`
- Prime snapshot JSON passed
- Bridge self-test passed

Prime/docs verification after interaction/no-drift work:

- `285 passed`
- Prime snapshot JSON passed
- Bridge self-test passed

Harness stage checklist verification:

- `46 passed`

Harness stage HTML dashboard verification:

- `47 passed`

Useful commands:

```powershell
python -m pytest tests\test_prime_runtime.py tests\test_bifrost_cockpit.py tests\test_filemap.py -q
python -m pytest tests\test_prime_runtime.py tests\test_aegis.py tests\test_bifrost_cockpit.py tests\test_filemap.py -q
python -m meridian_core.prime_runtime | python -m json.tool
node scripts\meridian-model-bridge.js --self-test
```

Do not start a new server for UI checks. Scott already has Live Server running.

## Bridge / UI Details

Bridge routes added/used:

- `/bridge/prime-logic`
- `/bridge/relay-logic`
- `/bridge/compass-logic`
- `/bridge/vulcan-logic`

Bridge capability added:

- `primeRuntimeSnapshot`

Prime bridge command:

- spawns `python -m meridian_core.prime_runtime`

Relay bridge command:

- spawns `python -m meridian_core.relay_logic_snapshot`

Compass/Vulcan bridge commands:

- spawn `python -m meridian_core.compass_logic_snapshot`
- spawn `python -m meridian_core.vulcan_logic_snapshot`

`index.html` contains render/load functions for:

- `renderPrimeDecisionSnapshot`
- `loadPrimeLogic`
- `renderPrimeLogic`
- `renderRelayLogicSnapshot`
- `loadRelayLogic`
- `renderCompassLogicSnapshot`
- `loadCompassLogic`
- `renderVulcanLogicSnapshot`
- `loadVulcanLogic`

## No-Drift Rules To Preserve

- Frontend must render backend packets, not duplicate backend logic.
- If a harness stage changes in Markdown, update the HTML dashboard in the same checkpoint.
- If a new module/doc matters, register it in:
  - `meridian_core/filemap.py`
  - `docs/FileMap.md`
  - `tests/test_filemap.py` required paths if important.
- Do not mark built-awaiting-review as review-cleared without explicit review acceptance.
- Do not wire live execution until Operations stage is explicitly built and gated.
- Auto model routing remains disabled until Prime and Relay are fully bound.
- Heartbeat belongs to Beacon/heartbeat harness, not Relay.
- Session lifecycle belongs to Vulcan, not Compass or Relay.
- Model routing belongs to Relay/Model, not Beacon or Vulcan.
- Project context belongs to Compass, not Vulcan.
- Proof/risk gates belong to Aegis, but Prime consumes Aegis results for orchestration.

## User Preferences / Recent Corrections

Scott was explicit:

- Do not do unasked work.
- Permission is required for writes, not reads.
- The visible harness must say logic and explain logic.
- Prime Directive #1 is logic. Rules are Prime Directive #3: No Drift.
- Front-end interface and back-end interface should not be different.
- Nothing should occur in backend that is not visibly represented in harness once harness is wired.
- Harness right panel should use `[Harness] Runtime Logic`.
- Continue building when explicitly told, but keep work scoped and committed.

## What Not To Do

- Do not touch `C:\Users\scott\Code\Polaris`.
- Do not start another dev server.
- Do not make shared main implementation changes unless Scott explicitly approves.
- Do not move/cherry-pick/merge/rebase/reset unless explicitly requested.
- Do not introduce hidden backend mutation from harness UI.
- Do not treat placeholder UI as completion.
- Do not push to main/origin unless Scott explicitly asks.

## Recommended Next Session Start

1. Check worktree status:

```powershell
git status --short --branch
```

2. Read these files:

```text
docs/prime-core-handoff-20260602.md
docs/harness-stage-checklist.md
docs/harness-stage-checklist.html
docs/v2-progress-tracker.md
meridian_core/prime_runtime.py
tests/test_prime_runtime.py
```

3. If Scott asks to continue Prime:

Recommended next step is **Prime Runtime Logic UI review acceptance** before live Compass/Vulcan/Relay inputs are bound.

4. If Scott asks to build next harness:

Recommended next backend build is **Compass backend runtime** because Prime currently only has Compass snapshot/source refs, not real project identity/bounds/scope objects.

## Open Questions / Known Gaps

- Prime backend runtime packet and Prime Runtime Logic UI are built-awaiting-review, not review-cleared.
- Compass Runtime Logic UI is wired, but Compass core runtime is not built.
- Vulcan Runtime Logic UI is wired, but live session lifecycle state/command execution is not fully built.
- Relay Runtime Logic UI is wired, but provider metadata, DeepSeek primary route, prompt payload visibility, and Auto routing are not complete.
- Echo and Atlas are review-cleared core capabilities, but not wired into `PrimeRuntimeContext`.
- Aegis core is review-cleared and Prime consumes risk input, but Aegis itself lacks a full `Aegis Runtime Logic` UI.
- Bifrost owns the UI shell, but V2 cockpit extensions, balance, prompt payload, and voice surface remain needs-build.
- Beacon heartbeat Runtime Logic UI and Prime heartbeat input boundary remain undefined.
- Operations stage is not complete for any live mutation harness.

## If You Update This Handoff

Update this handoff when:

- a new harness stage changes,
- Prime runtime adds a new backend field,
- Runtime Logic UI gains a new section,
- a built-awaiting-review item becomes review-cleared,
- live Operations are enabled,
- main/origin movement changes the branch status.

Also update:

- `docs/harness-stage-checklist.md`
- `docs/harness-stage-checklist.html`
- `docs/v2-progress-tracker.md`
- `docs/FileMap.md`
- `meridian_core/filemap.py`
- Obsidian build log if this is a meaningful checkpoint.

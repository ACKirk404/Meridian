# Harness Stage Checklist

**Purpose:** Track each Meridian harness by build stage so Scott can ask for a harness by name and stage later.

**Rule:** A harness is not complete because its button exists. Completion means backend capability, Prime integration, visible Runtime Logic UI, and proof/review are all aligned.

**HTML view:** `docs/harness-stage-checklist.html`

**Update rule:** When this checklist changes, update the HTML view in the same checkpoint.

## Stage Definitions

| Stage | Meaning | Done When |
|---|---|---|
| Contract / Baseline | The harness has a written contract, checklist, or architecture boundary. | Scope, owner, non-owner boundaries, and acceptance criteria are documented. |
| V2 Backend | The backend requirement is represented in the V2 build plan/tracker. | `docs/v2-progress-tracker.md` has the build item and dependency status. |
| Core Implementation | The harness has typed runtime/domain code. | Runtime module exists with unit tests and no UI-only logic. |
| Prime Integration | Prime can consume the harness state or decision. | Prime packet/source refs/proof path include the harness without hidden interpretation. |
| Runtime Logic UI | Clicking the harness shows `[Harness] Runtime Logic`. | Right-panel UI renders complete backend-sourced logic through a bridge/snapshot path; a titled shell or partial snapshot is not complete. |
| Proofs / Review | The harness has proof gates, tests, and review status. | Tests pass; review state is explicit as cleared, awaiting review, or not started. |
| Operations | The harness can safely execute or mutate live state. | Live actions are gated, auditable, and recoverable. |

## Current Harness Matrix

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

## Missing Stage Checks

These are the extra stages beyond the initial list that matter for no drift:

| Stage | Why It Matters |
|---|---|
| Contract / Baseline | Prevents building UI or runtime code before ownership is clear. |
| Operations | Separates visible logic from live state mutation. A harness can be visible before it can execute. |
| FileMap / Discoverability | Prime and future sessions must be able to find the harness files without rediscovery. |
| Obsidian / Build Log | Keeps Scott-facing continuity outside Git diffs and short chat memory. |
| Review State | Separates built from accepted. Built-but-awaiting-review is not done. |

## Ask-For-It Format

Use:

```text
Show me <Harness> by stage.
Build <Harness> <Stage>.
What is blocking <Harness> from <Stage>?
Update the Harness Stage Checklist.
```

## Current Priority

1. Prime review acceptance.
2. Compass backend runtime.
3. Vulcan live session state and command-plan proof.
4. Relay model/provider metadata and prompt payload visibility.
5. Echo/Atlas live inputs into Prime runtime.

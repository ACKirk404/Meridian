# Workflow Sub-Agent Harness Contract

**Status:** V2 cross-track contract — domain slice not yet implemented; runtime in `meridian_core/workflow_dispatch.py` (or equivalent) to be built by Build 1 (or other runtime lane) after this contract lands.
**Owner harness:** Workflow Sub-Agent (cross-track; consumed by Echo, Atlas, Aegis, Relay, Bifrost, Beacon, Session Lifecycle).
**Owner lane (doc):** Build 4 (Opus high-level thinking).
**Audience:** Prime, every harness, Scott, future contributors.
**Purpose:** Define how Prime delegates bounded work to workflow / sub-agent contexts; pin the work order, input packet, heartbeat, proof/result, and error/restart/resteer summaries; specify what must never return to Prime as raw context; explain how this differs from a normal Model Harness call.

The Workflow Sub-Agent Harness exists because Prime's effective intelligence depends on a lean orchestrator context. If every harness's working memory — searches, drafts, retries, full transcripts, raw logs — accumulates in Prime, Prime stops being able to judge, prioritize, and coordinate. Workflow sub-agents move bounded harness work into separate contexts and return **typed summaries** instead of raw chat history.

This document is implementation-facing. It pins the contract shape, the prompt-drag guardrails on what comes back, the per-harness usage rules, and the first runtime tests.

Architectural principle (from `context.md` "Workflow Sub-Agents"):

> Prime owns intent, policy, priority, and final coordination.
> Workflow sub-agents own bounded harness work and return structured results.

---

## What a Workflow Sub-Agent Is — and Is Not

A **workflow sub-agent** is a separate-context execution surface that runs a single, bounded harness task end-to-end and returns a typed summary. It may be backed by a host-model workflow primitive (e.g., a Claude workflow / sub-agent capability), by a long-lived script, by a worker session, or by an in-process sandbox — the contract is the same regardless of backing.

A workflow sub-agent is **not**:

- A normal model call. A model call returns a token stream that Relay budgets and Prime renders. A workflow sub-agent returns a *result document*, not a transcript.
- A new Prime. It does not deliberate across the whole project. It executes a bounded work order.
- A long-running chat. Prime does not "talk to" a workflow sub-agent. Prime issues a work order and receives heartbeats and a final summary.
- A backdoor for prompt drag. Raw transcripts, raw search results, raw logs, and raw model intermediate output never flow back into Prime's context (see Prompt-Drag Guardrails).
- A privileged actor. A workflow sub-agent has no more authority than the work order grants. It cannot escalate, change risk tier, bypass Aegis, or open new gates on its own.

---

## Harness Ownership and Boundaries

| Concern | Owner |
|---|---|
| Issue work orders, accept results | Prime |
| Run bounded harness work in a separate context | Workflow Sub-Agent Harness |
| Maintain context budget and quote summaries | Workflow Sub-Agent Harness + Relay |
| Authorize what may flow back into Prime | Aegis (via `CognitionPolicy`) |
| Render workflow status to Scott | Bifrost |
| Persist final results | the calling harness (Echo, Atlas, Aegis, etc.) — never Prime directly |
| Spawn/recover/stop workflow sessions | Session Lifecycle Harness |
| Provide proof/test evidence on workflow outputs | Aegis + the calling harness |

A workflow sub-agent never edits FileMap, never writes to Echo directly (it returns a result; Prime decides whether to record it), and never calls another workflow sub-agent without an explicit nested work order.

---

## Domain Shape

The runtime slice introduces a small set of frozen dataclasses (suggested module `meridian_core/workflow_dispatch.py`). Names and field semantics are normative; field types follow existing `meridian_core` conventions (frozen dataclasses, enums, tuples).

### `WorkflowWorkOrder`

The complete, self-contained instruction to a workflow sub-agent.

- `work_order_id` — stable identifier, deterministic where possible.
- `harness` — `WorkflowHarness` enum: `ECHO`, `ATLAS`, `AEGIS`, `RELAY`, `BIFROST`, `BEACON`, `SESSION_LIFECYCLE`. Identifies which harness owns the work.
- `action` — short string naming the harness action (e.g., `"atlas.search"`, `"aegis.review_proof"`, `"bifrost.verify_render"`). Each harness publishes its own allowed action vocabulary.
- `intent` — one-sentence human-readable statement of what success looks like. Must be present.
- `risk_tier` — integer 1–4, set by Prime via Aegis's tier engine. Determines proof, review, and human-gate requirements on the result.
- `input` — a `WorkflowInputPacket` (see below).
- `expected_result_shape` — short string naming the expected result schema (e.g., `"AtlasResult"`, `"ProofReview"`, `"BifrostRenderCheck"`). The workflow sub-agent must conform to this shape or return a structured error.
- `time_budget_seconds` — soft cap. Beyond this, the sub-agent must heartbeat with `WARNING` and consider early-return.
- `hard_timeout_seconds` — hard cap. Beyond this, Session Lifecycle stops the sub-agent and Prime receives an error summary.
- `created_at` — UTC timestamp.
- `parent_work_order_id` — optional. Used only when one workflow sub-agent legitimately delegates a nested bounded task. Nesting depth is hard-capped (recommended ≤ 2 in first slice).

`WorkflowWorkOrder` is immutable. A reissue is a new order with a new id.

### `WorkflowInputPacket`

The context the workflow sub-agent is given. This is the **only** input — the sub-agent does not have implicit access to Prime's memory, conversation, or Scott's chat.

- `project` — project key (e.g., `meridian`).
- `goal_summary` — short prose, ≤ ~500 chars. The "why" framed for the sub-agent.
- `inputs` — tuple of typed inputs: `MemoryHit` summaries, `AtlasHit` excerpts, file paths to read, structured config. Each entry carries a `source` tag.
- `allowed_tools` — tuple of tool names the sub-agent may invoke (e.g., `"read_file"`, `"run_tests"`). Tools not listed are not callable. Empty tuple means "summarize-only."
- `allowed_paths` — tuple of repository-relative path prefixes the sub-agent may read. Anything outside is denied.
- `forbidden_paths` — tuple of path prefixes the sub-agent must not touch even if `allowed_paths` would otherwise permit (e.g., `.env*`, secrets, other lanes' live queues).
- `prompt_budget` — `PromptBudgetPlan` carried over from Relay; sets the cap on injected context inside the sub-agent's own model calls.
- `gate_context` — optional. Tier-3+ orders include the `CognitionPolicy` decision and any required-proof handles so the sub-agent knows what evidence it must produce.

`WorkflowInputPacket` is immutable.

### `WorkflowHeartbeat`

Periodic, lightweight status updates the sub-agent emits while running.

- `work_order_id` — the order this heartbeat is for.
- `sequence` — monotonically increasing integer.
- `emitted_at` — UTC timestamp.
- `phase` — `WorkflowPhase` enum: `STARTED`, `WORKING`, `WAITING_FOR_TOOL`, `WAITING_FOR_GATE`, `WARNING`, `FINALIZING`.
- `summary` — short prose, ≤ ~200 chars. Headline only (e.g., `"3 files read, 1 candidate found"`).
- `progress_estimate` — optional float in `[0.0, 1.0]`; omitted if not estimable.
- `next_action` — optional short string (e.g., `"will run tests"`).

Heartbeats are **not** stored in Echo, never injected into Prime's prompt, and never aggregated into the result. Bifrost may render them live; Beacon may use them for liveness.

### `WorkflowResultSummary`

The final, typed result a sub-agent returns when work completes successfully.

- `work_order_id` — the order this result is for.
- `harness` — mirrors the order.
- `result_shape` — mirrors `expected_result_shape` from the order.
- `summary` — short prose, ≤ ~1000 chars. Human-readable headline of what happened. This is the only free-text field Prime is ever shown by default.
- `outputs` — tuple of typed output records matching `result_shape` (e.g., `tuple[AtlasHit, ...]`, a `ProofReviewVerdict`, a `BifrostRenderCheck`). These are structured, not prose.
- `proof_trail` — `ProofTrail` (existing Aegis type) listing evidence the sub-agent produced or referenced. Required when `risk_tier >= 2`.
- `tokens_used` — integer estimate; used for telemetry and budget enforcement.
- `time_used_seconds` — actual wall time spent.
- `next_action_recommendation` — optional short string describing what Prime might do next (e.g., `"register 1 missing FileMap path"`). Advisory only; Prime decides.
- `requires_human_gate` — bool. True when the sub-agent surfaces a finding that needs Scott (e.g., tier-4 disposition, ambiguous proof). Prime routes to Review Console.

The sub-agent must produce a `WorkflowResultSummary` or a `WorkflowErrorSummary`. There is no third return shape.

### `WorkflowErrorSummary`

The final, typed result a sub-agent returns when work cannot complete.

- `work_order_id` — the order this error is for.
- `harness` — mirrors the order.
- `failure_kind` — `WorkflowFailureKind` enum: `TIMEOUT`, `TOOL_DENIED`, `INPUT_INVALID`, `PROOF_UNAVAILABLE`, `GATE_REQUIRED`, `INTERNAL_ERROR`, `RESTEER_REQUESTED`.
- `summary` — short prose, ≤ ~500 chars. What failed and why, in human terms.
- `partial_outputs` — optional tuple of typed outputs the sub-agent did manage to produce.
- `proof_trail` — `ProofTrail` for whatever was produced; may be empty.
- `resteer_request` — optional `WorkflowResteerRequest` (see below). Present only when `failure_kind == RESTEER_REQUESTED` or when the sub-agent recommends a specific resteer to Prime.
- `tokens_used` / `time_used_seconds` — same as success summary.

### `WorkflowResteerRequest`

Used when the sub-agent cannot finish under the original work order but can suggest a tighter or different bounded order Prime could issue.

- `original_work_order_id` — pointer back to the original order.
- `reason` — short prose, ≤ ~300 chars.
- `suggested_changes` — structured suggestion (e.g., narrower `allowed_paths`, additional `inputs`, lower `risk_tier`, different `action`). Not a freeform plan — a delta the runtime can apply to construct a new `WorkflowWorkOrder`.
- `do_not_retry` — bool. True when the sub-agent believes the work cannot be done at all and Prime should escalate to Review Console rather than re-issue.

Restart vs. resteer mirrors `docs/prime-restart-resteer-logic.md`:

- **Restart** = same work order, fresh sub-agent context. Use when failure was contextual (timeout, transient tool error, session went stale). Prime decides; Session Lifecycle executes.
- **Resteer** = new work order derived from `WorkflowResteerRequest`. Use when the original framing was wrong. Prime decides; the new order is a new `WorkflowWorkOrder`.

---

## What Must Never Return to Prime as Raw Context

These rules are normative. Violations are Aegis findings, not workflow findings.

1. **No raw transcripts.** The sub-agent's internal chat, model output, intermediate tool results, and scratch reasoning never reach Prime's context. Only `WorkflowResultSummary` / `WorkflowErrorSummary` and their structured fields do.
2. **No raw file content.** Even when the sub-agent read files, only typed excerpts (e.g., `AtlasHit.excerpt`) or structured derived records may appear in `outputs`. Whole files do not flow back.
3. **No raw search results.** A web search, code grep, or registry lookup must be distilled into structured records or a one-line summary before return.
4. **No raw logs.** Worker logs, build logs, test stdout, browser console dumps must be distilled into a `ProofTrail` entry or a structured finding. The raw text stays in the sub-agent's context.
5. **No heartbeats in the result.** The heartbeat stream is operational, not narrative. Bifrost renders heartbeats; Prime does not absorb them.
6. **No prose plans.** A sub-agent does not return "here is what I think Prime should do next." It returns `next_action_recommendation` as a short structured hint — Prime decides, not the sub-agent.
7. **No Scott-facing voice.** A sub-agent does not speak to Scott. If it has a finding for Scott, it sets `requires_human_gate=True` and Prime routes the summary to the Review Console.
8. **No other-project bleed.** A sub-agent operates on a single `project`. Cross-project content does not enter `outputs`.
9. **Default injection back into Prime is zero.** When Prime receives a result, only `summary`, `result_shape`, and the structured `outputs` are eligible for Prime's working context — and only when Aegis's `CognitionPolicy` allows. Free-text expansion of `outputs` is opt-in per route.

The motivation is the same as Echo and Atlas: workflow sub-agents make Prime more powerful only if they protect Prime from prompt drag. A workflow that returns raw transcripts is worse than no workflow at all.

---

## How Each Harness Uses Workflow Contexts

Each harness publishes its own action vocabulary against this contract. The rules below pin the intent, not the full vocabulary.

### Echo (durable memory)

- **Workflow actions:** memory maintenance (compaction, supersession bookkeeping), bulk import distillation, large query preparation when too many candidates exist for a synchronous call.
- **Inputs:** project key, query parameters, optional candidate set.
- **Outputs:** typed `MemoryRecord` tuples or `MemoryHit` summaries — never raw chat from which a record was extracted.
- **Why workflow:** keeps Prime out of the loop on bulk text distillation; Prime sees the distilled records, not the source noise.

### Atlas (retrieval)

- **Workflow actions:** large or expensive retrieval scans (e.g., wide FileMap queries with many candidates), Echo-fold-in passes, broad doc-allowlist reads.
- **Inputs:** `AtlasQuery`, candidate constraints.
- **Outputs:** `AtlasResult` with `hits` and `missing_paths` — never raw file dumps.
- **Why workflow:** Atlas already returns excerpts; workflow execution means the full read+rank work doesn't inflate Prime's context.

### Aegis (gated cognition / proof)

- **Workflow actions:** proof review, cross-finding synthesis, finding triage, waiver preparation.
- **Inputs:** the `ProofTrail` candidates, the action under review, the risk tier, and the policy in force.
- **Outputs:** a typed `ProofReviewVerdict` with `decision`, `blocking_reasons`, and any new `ProofTrail` entries — never raw test output, raw browser screenshots, or raw lane-disagreement chat.
- **Why workflow:** review tasks naturally produce verbose intermediate text that must not become Prime's context.

### Relay (model dispatch)

- **Workflow actions:** model dispatch itself when the host primitive supports running a model call in a separate sub-agent context (so the dispatch transcript stays out of Prime), multi-call aggregation, dual-lane comparison synthesis.
- **Inputs:** `PromptPacket`, `RelayRoute`, dual-lane configuration.
- **Outputs:** a typed dispatch summary (status, tokens used, structured response excerpts, `ProofTrail` references) — never the raw model transcript.
- **Why workflow:** the cleanest way to keep model output discipline is to never let it touch Prime's window in the first place.

### Bifrost (cockpit UI)

- **Workflow actions:** local preview/build verification, render-check screenshots, view-model fixture validation, accessibility/escape audit.
- **Inputs:** the cockpit view-model fixture or a local URL, the expected render checks.
- **Outputs:** a typed `BifrostRenderCheck` summary (pass/fail per check, screenshot file references, diff annotations) — never raw HTML, raw CSS, or raw browser console dumps.
- **Why workflow:** UI verification is verbose and Scott-facing; the verbose part stays in the sub-agent; Prime sees pass/fail and where to look.

### Beacon (liveness)

- **Workflow actions:** liveness sweeps over many files/sessions, staleness audits, harness health pings.
- **Inputs:** target set (paths, sessions, harnesses), staleness thresholds.
- **Outputs:** a typed `BeaconLivenessReport` summary keyed by target with `age`, `status`, and per-target reasons — never raw file scans.
- **Why workflow:** liveness work is naturally bursty; doing it in-context floods Prime; doing it in a sub-agent yields a compact report.

### Session Lifecycle (spawn/watch/steer/recover)

- **Workflow actions:** session watch loops, steer attempts, recovery probes, stale-session diagnosis.
- **Inputs:** `SessionLifecycleState`, the target action (watch/steer/recover/etc.), permission object for branch/worktree moves.
- **Outputs:** a typed `SessionLifecycleResult` summary with new state, transitions taken, evidence, and any human-gate flags — never raw worker chat or raw session log.
- **Why workflow:** this is the case where context bleed is most damaging — worker sessions can be very chatty. The workflow shape is what makes Session Lifecycle safe.

Session Lifecycle is also the harness that *operates* workflow sub-agents (spawn, watch, recover) for the other harnesses. The two roles are distinct: Session Lifecycle's own workflows are about session state; everyone else's workflows are about their own domain work. Both follow this contract.

---

## How This Differs From a Normal Model Harness Call

| Dimension | Normal Model Call (Relay + Model Harness) | Workflow Sub-Agent |
|---|---|---|
| Initiator | Prime, via Relay route | Prime, via a typed `WorkflowWorkOrder` |
| Context flow | Prompt + response live in or near Prime's window | Sub-agent context is separate; only the summary returns |
| Return shape | Token stream / model response field | `WorkflowResultSummary` or `WorkflowErrorSummary` |
| Granularity | Single inference / single tool call | Bounded multi-step harness task |
| Heartbeats | None — synchronous or short async | Periodic `WorkflowHeartbeat` updates |
| Proof | Optional per route | Required for `risk_tier >= 2` |
| Prompt-drag | Bounded by `PromptBudgetPlan` per call | Bounded by both `PromptBudgetPlan` (inside sub-agent) and the prompt-drag guardrails on what comes back |
| Cancellation | Stops the single call | Session Lifecycle stops the whole sub-agent context |
| Restart vs. resteer | N/A — Relay retries the same call | Distinct concepts; see `docs/prime-restart-resteer-logic.md` |
| Who renders to Scott | Bifrost renders Prime's voice | Bifrost renders sub-agent heartbeats live and the result summary on completion |

A normal model call is a unit of *inference*. A workflow sub-agent is a unit of *bounded harness work* that may include many inferences and tool calls — and whose internal context is invisible to Prime by construction.

If a job is one prompt → one response, it is a Model Harness call, not a workflow. If a job is "spend up to N minutes doing this bounded thing and report back," it is a workflow.

---

## Review and Proof Expectations Before Workflow Results Affect Durable State

A workflow result may not silently change durable state. Promotion of results into durable artifacts (Echo records, FileMap entries, branch operations, Review Console gates, Bifrost releases) goes through review/proof gates appropriate to the work order's risk tier.

| Risk tier | Required before durable promotion |
|---|---|
| **Tier 1** | Prime accepts the summary; no extra gate. Result may be cached or used in working context. |
| **Tier 2** | `WorkflowResultSummary.proof_trail` must be non-empty and Aegis's policy must be `ALLOW`. Reviewer lane logs the summary. |
| **Tier 3** | Tier-2 conditions, plus a Review Console entry rendering the summary and `outputs`. Prime does not promote until the lane records `pass` or `no actionable findings`. |
| **Tier 4** | Tier-3 conditions, plus an explicit Scott approval in the Review Console human gate. `requires_human_gate=True` must be set on the result; Prime refuses promotion otherwise. |

Specific rules:

- **No durable write on `WorkflowErrorSummary`.** Errors never promote outputs. Prime may store the error for telemetry but does not record `partial_outputs` as durable Echo records.
- **No branch / worktree movement from a workflow.** Session Lifecycle may *propose* moves via its result; only Prime + Scott permission (per `prime-restart-resteer-logic.md`) authorizes the move.
- **No FileMap edits from a workflow.** Atlas/Beacon may report `missing_paths` or stale entries; Build 3 (FileMap lane) is the only writer.
- **No Echo writes from a workflow.** Echo workflows produce distilled `MemoryRecord` candidates; Prime issues the `add` against Echo's repository.
- **No prompt-budget bypass.** Any model call inside the sub-agent is still subject to `PromptBudgetPlan` and Relay telemetry.

---

## Failure-Soft Behavior

The workflow harness must fail soft from Prime's perspective.

| Condition | Behavior |
|---|---|
| Sub-agent missing / unavailable | Prime receives a `WorkflowErrorSummary` with `failure_kind=INTERNAL_ERROR`. No exception bubbles into the orchestrator. |
| Hard timeout exceeded | Session Lifecycle stops the sub-agent; emits `failure_kind=TIMEOUT` with whatever `partial_outputs` exist. |
| Tool denied (not in `allowed_tools`) | Sub-agent emits `failure_kind=TOOL_DENIED` and exits cleanly. |
| Forbidden path read attempt | Sub-agent emits `failure_kind=TOOL_DENIED` with the offending path; access is refused at the tool layer, not just reported. |
| Result shape does not match `expected_result_shape` | Emit `failure_kind=INPUT_INVALID` rather than coerce silently. |
| Tier-3+ work order missing `gate_context` | Emit `failure_kind=GATE_REQUIRED` before doing real work. |
| Proof required but unavailable | Emit `failure_kind=PROOF_UNAVAILABLE` with whatever proof candidates exist. |
| Sub-agent crashes mid-run | Session Lifecycle reports `failure_kind=INTERNAL_ERROR`; heartbeat absence is detected by Beacon. |

The orchestrator never sees a bare exception from the workflow harness. Every failure produces a typed summary.

---

## First Runtime Tests

Build 1 (or whichever runtime lane picks up `meridian_core/workflow_dispatch.py`) should land at minimum the following tests in `tests/test_workflow_dispatch.py` before the slice is marked built. These are the proof gates the V2 workflow harness must clear.

### Domain shape

- `WorkflowWorkOrder`, `WorkflowInputPacket`, `WorkflowHeartbeat`, `WorkflowResultSummary`, `WorkflowErrorSummary`, `WorkflowResteerRequest` are frozen dataclasses.
- `WorkflowHarness`, `WorkflowPhase`, `WorkflowFailureKind` enums cover the values listed above.
- Mutation attempts on any of the above raise `FrozenInstanceError`.

### Dispatch and result

- Issuing a `WorkflowWorkOrder` with a registered fake harness handler returns a `WorkflowResultSummary` whose `work_order_id` matches.
- The returned `result_shape` equals `expected_result_shape` from the order; mismatch produces `WorkflowErrorSummary(failure_kind=INPUT_INVALID)`.
- `outputs` is a tuple, not a list.
- A successful tier-1 result with empty `proof_trail` is accepted; a successful tier-2 result with empty `proof_trail` is rejected (becomes an error with `failure_kind=PROOF_UNAVAILABLE`).

### Input packet hygiene

- A work order whose `input.inputs` references a path outside `allowed_paths` is rejected before dispatch (test the validator).
- A work order whose `input.allowed_tools` is empty produces results with `outputs` populated only via summarize-only paths (test with a stub harness).
- A work order whose `input.forbidden_paths` overlaps `allowed_paths` always denies the forbidden subset.

### Heartbeats

- A long-running fake harness emits heartbeats with monotonically increasing `sequence`.
- Heartbeats do not appear in the final `WorkflowResultSummary.outputs` or `summary`.
- Heartbeats are not silently retained in Prime-visible state (test by asserting the dispatch return type contains no heartbeat list).

### Errors and restart/resteer

- A handler that raises produces `failure_kind=INTERNAL_ERROR` and no exception bubbles up.
- A handler that exceeds `hard_timeout_seconds` produces `failure_kind=TIMEOUT` and any `partial_outputs` recorded so far.
- A handler that returns a `WorkflowResteerRequest` produces a `WorkflowErrorSummary(failure_kind=RESTEER_REQUESTED, resteer_request=...)`.
- `WorkflowResteerRequest.suggested_changes` is structured (test that it can be applied to construct a new valid `WorkflowWorkOrder`).
- `WorkflowResteerRequest.do_not_retry=True` is honored — the dispatch helper exposes it as a flag Prime can check.

### Risk-tier gating

- Tier-3 order missing `gate_context` returns `failure_kind=GATE_REQUIRED` before invoking the handler.
- Tier-4 result without `requires_human_gate=True` is rejected by the promotion helper (test the promotion helper, not the dispatch helper).

### Nesting cap

- A nested work order beyond the depth cap (recommended 2) is rejected with `failure_kind=INPUT_INVALID`.

### Prompt-drag guardrails (cross-with Aegis tests)

- `WorkflowResultSummary.summary` is bounded in length (assert hard cap).
- `WorkflowResultSummary` does not expose any field carrying raw transcripts (assert by field names and by handler contract test).
- A test handler that *tries* to attach a raw transcript field is rejected by the dispatch layer.

These tests are domain-only and use fake/stub harness handlers — they do not require live Echo, Atlas, Aegis, Relay, Bifrost, or Session Lifecycle implementations. Per-harness workflow handler tests belong with those harnesses.

---

## Cross-References

- `context.md` "Workflow Sub-Agents" — the architectural principle this contract operationalizes.
- `docs/v2-detailed-build-plan.md` Track 6 — Session Lifecycle Harness, which both owns workflow execution mechanics and is itself a workflow consumer.
- `docs/echo-memory-contract.md` — Echo's prompt-drag guardrails parallel this contract's.
- `docs/atlas-retrieval-contract.md` — Atlas's prompt-drag guardrails parallel this contract's.
- `docs/prime-restart-resteer-logic.md` — restart vs. resteer semantics this contract inherits.
- `docs/review-console-surface-contract.md` — where tier-3+ workflow results are routed when human inspection is required.

---

## Out of Scope for V2 First Wave

- Cross-Meridian workflow dispatch (federation).
- Workflow sub-agents that call external services beyond the existing model and tool adapters.
- Public/account-level workflow distribution.
- Automatic workflow re-issuance without Prime decision.
- Workflow sub-agents that mutate FileMap, Echo, or branch/worktree state directly.
- Long-lived "background" workflow sub-agents without an explicit work order and bounded budget.
- Free-text return paths that bypass `WorkflowResultSummary` / `WorkflowErrorSummary`.

These belong to later V2 waves or to the federation horizon when it is written.

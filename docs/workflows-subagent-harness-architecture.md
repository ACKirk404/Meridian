# Claude Workflows / Sub-Agent Harness Architecture Note

**Status:** V2 architecture narrative — companion to the implementation-facing `docs/workflow-subagent-harness-contract.md`.
**Owner harness:** Workflow Sub-Agent (cross-cutting).
**Owner lane (doc):** Build 4 (Opus high-level thinking).
**Audience:** Prime, every harness owner, Scott, future contributors.
**Purpose:** Explain *why* Meridian moves bounded harness work into Claude Workflow / sub-agent contexts, *which* harnesses should adopt that pattern, *what* state Prime keeps locally vs. delegates, *what* each workflow returns, *how* this protects Prime's context window, and *how* the pattern maps to Meridian's long-term harness design.

This is the narrative companion to `docs/workflow-subagent-harness-contract.md`. The contract pins the domain shapes, error/result/heartbeat schemas, prompt-drag rules, per-harness usage rules, and first runtime tests. This note explains the architectural intent the contract serves so anyone touching the workflow seam — Prime authors, harness implementers, Bifrost integrators, Scott — works from the same picture.

If you are about to implement a workflow handler, read this note first, then read the contract.

---

## The Problem We Are Solving

Prime is the orchestrator. Its job is intent, policy, priority, and final coordination. Prime's intelligence is bounded by its model's context window. Every token of working memory Prime spends absorbing harness logs, search results, raw transcripts, intermediate drafts, retries, or proof artifacts is a token it cannot spend on judgment.

Without discipline, the orchestrator window fills predictably:

- Echo wants to surface the raw memory text it found.
- Atlas wants to dump file contents that *might* be relevant.
- Aegis wants to attach full proof logs.
- Relay wants to leave model transcripts in the loop in case Prime needs them.
- Bifrost wants to ship full HTML/CSS so Prime can verify a render.
- Beacon wants to attach every health probe response.
- Session Lifecycle wants to mirror every worker session's chat into Prime.

Each of those is locally rational. Together they make Prime stupider — not because the model degrades, but because Prime's window stops being a coordination surface and starts being a noisy log aggregator. The orchestrator that should be deciding *what matters* becomes the place where *everything ends up*.

Claude Workflows / sub-agents give us a way out: a separate context where bounded harness work runs end-to-end, returns a typed summary, and leaves the working noise behind.

---

## The Core Principle

From `context.md` "Workflow Sub-Agents":

> Prime owns intent, policy, priority, and final coordination.
> Workflow sub-agents own bounded harness work and return structured results.

Practical restatement:

- **If a job is one prompt → one response, it is a Model Harness call** (Relay handles the budget, transcript stays close to Prime).
- **If a job is "spend up to N minutes doing this bounded thing and report back," it is a workflow** (Workflow Sub-Agent Harness handles dispatch, transcript stays inside the sub-agent, only a typed summary returns to Prime).

A workflow sub-agent is not a smaller Prime. It does not deliberate across the whole project. It executes a bounded work order against a typed input packet and produces a typed result summary — or a typed error summary. Nothing else returns.

---

## Which Harnesses Should Run as Workflows

These harnesses should default to workflow execution for any bounded, multi-step task. The contract pins the action vocabulary; this note states the architectural intent.

| Harness | Why workflow | Typical workflow actions |
|---|---|---|
| **Echo** (durable memory) | Memory maintenance distills noisy source text into typed records; that distillation should never touch Prime's window. | Memory compaction, bulk-import distillation, large-query preparation. |
| **Atlas** (retrieval) | Wide FileMap/doc scans and Echo fold-in passes can be expensive; keeping them in a sub-agent means only the ranked hits return. | Wide retrieval scans, Echo fold-in passes, broad doc-allowlist reads. |
| **Aegis** (gated cognition / proof) | Proof review is naturally verbose; only a verdict and `ProofTrail` should reach Prime. | Proof review, finding synthesis, waiver preparation, cross-lane disagreement summary. |
| **Relay** (model dispatch) | When the host primitive supports it, dispatching a model call inside a sub-agent is the cleanest way to prevent the transcript from polluting Prime's window. | Dispatch itself, multi-call aggregation, dual-lane comparison synthesis. |
| **Bifrost** (cockpit UI) | UI verification produces a lot of HTML/CSS/console text; Prime should see pass/fail and where to look, not the raw render. | Local preview/build verification, render checks, view-model fixture validation, escape/accessibility audit. |
| **Beacon** (liveness) | Liveness sweeps are bursty; aggregating them in a sub-agent yields a compact report. | Liveness sweeps over files/sessions, staleness audits, harness health pings. |
| **Session Lifecycle** (spawn/watch/steer/recover) | The case where Prime context bleed is most damaging — worker sessions can be very chatty. Workflows are what make Session Lifecycle safe at scale. Session Lifecycle also *operates* workflow sub-agents for other harnesses. | Session watch loops, steer attempts, recovery probes, stale-session diagnosis. |

This list is closed for the first slice. Adding a new workflow-backed harness is an architecture change, not an implementation detail — it goes through this note and the contract.

What should *not* be a workflow:

- Single inferences. Use the Model Harness.
- Prime's own deliberation. Prime does not delegate "what should we do next?" to a sub-agent.
- Anything that needs to mutate global state directly. Workflows return summaries; durable promotion happens in the calling harness or in Prime per the contract's tier-keyed gates.
- Long-lived watch loops without a bounded work order. If you cannot say "the job ends when X is true," it is not a workflow — it is a background process, and Meridian should not run those in V2.

---

## What State Prime Keeps Locally

Even with workflows, Prime keeps a small, durable set of state in its own context. The split is intentional.

**Prime keeps:**

- The current `PrimeNextAction` (or recent ones) — what Prime proposes to do.
- The current `CognitionPolicy` decisions in flight for tier-2+ actions.
- Active gate references from Review Console — what is waiting on Scott.
- The list of active workflow `work_order_id`s and their last `WorkflowHeartbeat` summary line — Prime sees liveness, not contents.
- A short rolling summary of recent Scott directions and Prime's current intention (from `docs/prime-restart-resteer-logic.md`).
- Standing instructions and Charter constraints relevant to current work.

**Prime delegates (does NOT keep in context):**

- Raw `MemoryRecord.body` text — only summaries via `MemoryHit`.
- Raw file content — only `AtlasHit.excerpt`.
- Workflow sub-agent transcripts — never.
- Raw proof logs, test stdout, browser console dumps — Aegis returns a `ProofTrail` reference.
- Raw worker session chat — Session Lifecycle returns a typed `SessionLifecycleResult` summary.
- Tool intermediate results inside a sub-agent — they live and die in the sub-agent.
- Heartbeat history — Bifrost renders heartbeats live; Prime keeps only the latest line per active work order.

If Prime needs to "see more" about a workflow result, the correct path is to issue a follow-up work order (narrower or different) — not to widen the result schema.

---

## What Each Workflow Returns

Every workflow returns exactly one of two things. There is no third return shape.

**`WorkflowResultSummary`** — success. Carries:

- A short prose `summary` (≤ ~1000 chars, the headline Prime sees).
- Typed `outputs` matching the work order's `expected_result_shape` (e.g., `tuple[MemoryHit, ...]`, an `AtlasResult`, a `ProofReviewVerdict`, a `BifrostRenderCheck`, a `SessionLifecycleResult`).
- A `ProofTrail` reference (required for `risk_tier >= 2`).
- Tokens used, time used, optional `next_action_recommendation`, and a `requires_human_gate` flag.

**`WorkflowErrorSummary`** — failure. Carries:

- A typed `failure_kind` (`TIMEOUT`, `TOOL_DENIED`, `INPUT_INVALID`, `PROOF_UNAVAILABLE`, `GATE_REQUIRED`, `INTERNAL_ERROR`, `RESTEER_REQUESTED`).
- A short prose `summary` of what failed.
- Optional `partial_outputs` (typed, same shape rules as success).
- Optional `WorkflowResteerRequest` carrying a structured suggested delta for a new work order (not a freeform plan).

Anything else a sub-agent produced — intermediate text, tool dumps, raw search results, full transcripts, scratch reasoning — stays inside the sub-agent context and is discarded when the sub-agent terminates. The contract enforces this as a normative prompt-drag rule and as a runtime test (handler attempting to attach a raw transcript field is rejected at dispatch).

---

## How This Protects Prime's Context Window

The protection is structural, not aspirational.

1. **Separate context.** The sub-agent runs in its own window. No quoting from Prime's window into the sub-agent except what the typed `WorkflowInputPacket` carries. No reflection from the sub-agent into Prime's window except the typed summary.
2. **Typed boundary at both ends.** Inputs and outputs are frozen dataclasses with bounded fields. There is no free-text passthrough that grows under pressure.
3. **Hard caps on the rendered surface.** `WorkflowResultSummary.summary` has a length cap. `PrimeNextAction.echo_inputs` and `.atlas_inputs` have rendered caps. The "more context" pressure that normally inflates prompts is structurally absorbed instead — by issuing more work orders, not by widening one.
4. **Default injection is zero.** When a result comes back, only `summary`, `result_shape`, and structured `outputs` are eligible for Prime's working context — and only when Aegis's `CognitionPolicy` allows. Free-text expansion is opt-in per route.
5. **Heartbeats stay operational.** Bifrost renders them live for Scott; Prime keeps the last line. They never enter the result.
6. **Errors are typed, not raised.** A workflow that crashes returns `WorkflowErrorSummary(failure_kind=INTERNAL_ERROR)`. Prime sees a typed error and decides; it does not catch an exception trace.
7. **Promotion is gated.** Workflow results don't silently mutate durable state. Tier-1 accepts the summary; tier-2+ requires `ProofTrail` and Aegis policy `ALLOW`; tier-3 adds Review Console; tier-4 requires Scott. The gating itself is structural — there is no codepath that promotes a result without going through the gates.

Without these properties, "use Claude Workflows" would just be a way to move the same prompt-drag problem one layer down. With them, the workflow seam is a real budget — text spent inside a sub-agent is text not spent in Prime.

---

## How This Maps to Meridian's Long-Term Harness Design

Meridian's harness model treats every cross-cutting concern (memory, retrieval, proof, dispatch, UI, liveness, lifecycle) as its own harness owned by a single lane. Workflows are the **execution shape** that lets harnesses do bounded multi-step work without owning a piece of Prime's window.

The mapping has three levels.

### Level 1 — Today (V2 first wave)

- Echo, Atlas, Aegis, Relay, Bifrost, Beacon, Session Lifecycle each expose an action vocabulary against the workflow contract.
- Workflows are dispatched and supervised by the Session Lifecycle harness (the "operator" role).
- Prime issues work orders, watches heartbeat liveness, and reads result/error summaries.
- All durable state changes go through the calling harness or Prime, gated by Aegis tier.

### Level 2 — V2 mature

- The workflow-backed action vocabularies stabilize and the contract's runtime tests (per `docs/workflow-subagent-harness-contract.md`) are landed in `meridian_core/workflow_dispatch.py` and per-harness modules.
- Bifrost's cockpit shows the active workflow list with status, age, and tier.
- Council deliberation at tier-3 can itself be a workflow (multiple lanes voting in sub-agent contexts; only the Chairman's verdict and `ProofTrail` return to Prime).
- Restart vs. resteer (per `docs/prime-restart-resteer-logic.md`) is plumbed into workflow lifecycle: a restart reissues the same work order in a fresh sub-agent; a resteer applies a typed `WorkflowResteerRequest` to construct a new order.

### Level 3 — Long-term (federation, multi-Meridian)

- Workflow contexts become the **federation boundary**: cross-Meridian work is dispatched as work orders with the same typed shape, supervised by the remote Session Lifecycle, returning typed summaries. The federation horizon (`docs/federation-harness-horizon.md` when written) inherits the workflow contract without adding new context-leak surfaces.
- Public/account distribution can reuse workflows as the "do bounded work for this customer" primitive without re-architecting harnesses.
- The "agent factory" thesis becomes operational: Meridian's value is not that Prime is brilliant, but that bounded harness work is composable, typed, and budget-disciplined across many sub-agent contexts in parallel — with Prime coordinating, not absorbing.

The throughline is the same at every level: bounded harness work runs elsewhere; typed summaries return; Prime coordinates.

---

## What This Note Does Not Decide

This note is narrative architecture. It does not pin:

- The domain shapes, schemas, prompt-drag rules, or runtime tests — those are in `docs/workflow-subagent-harness-contract.md`.
- The Prime autonomy selector rules — those are in `docs/prime-autonomy-v2-contract.md`.
- The Echo/Atlas data contracts — those are in `docs/echo-memory-contract.md` and `docs/atlas-retrieval-contract.md`.
- The Session Lifecycle action vocabulary — that belongs to `docs/session-lifecycle-v2-contract.md` when it is written.
- The Aegis policy engine — that belongs to `docs/cognition-policy-v2-contract.md` when it is written.
- The Bifrost rendering of workflow status — that belongs to a Bifrost V2 extensions doc when it is written.

When those documents and this note disagree on a detail, the dedicated contract wins. This note's job is to keep the *intent* coherent across them.

---

## Cross-References

- `context.md` "Workflow Sub-Agents" — the architectural principle this note expands.
- `docs/workflow-subagent-harness-contract.md` — implementation-facing companion (domain shapes, prompt-drag rules, runtime tests).
- `docs/prime-autonomy-v2-contract.md` — Prime autonomy that decides *which* workflow to spawn next.
- `docs/echo-memory-contract.md` and `docs/atlas-retrieval-contract.md` — parallel prompt-drag postures workflows must honor.
- `docs/prime-restart-resteer-logic.md` — restart/resteer semantics workflow lifecycle inherits.
- `docs/review-console-surface-contract.md` — where tier-3+ workflow results route for Scott's disposition.
- `docs/v2-detailed-build-plan.md` Track 6 — Session Lifecycle, the harness that operates workflows for others.
- `docs/federation-harness-horizon.md` (when written) — the long-term boundary workflows naturally support.

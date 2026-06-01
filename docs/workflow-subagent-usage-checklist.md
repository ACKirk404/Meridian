# Workflow Sub-Agent Usage Checklist

**Owner:** Workflow Sub-Agent Harness
**Status:** V2 operational checklist
**Source contracts:** `docs/workflows-subagent-harness-architecture.md`, `docs/workflow-subagent-harness-contract.md`

## Purpose

This checklist tells Prime when bounded harness work should run in a workflow/sub-agent context instead of inside Prime's orchestrator window or as a single Relay model call.

The rule is simple:

- Use a normal Relay/Model Harness call for one prompt to one response.
- Use a workflow/sub-agent for bounded multi-step harness work that would otherwise drag raw working context into Prime.

Prime owns intent, policy, priority, acceptance, and next action. Workflow sub-agents own bounded harness work and return typed summaries.

## Required Decision Checklist

Prime should route a task through a workflow/sub-agent when all required checks pass:

- [ ] **Bounded work:** The task has a clear end condition, expected result shape, and time budget.
- [ ] **Harness-owned:** The work belongs to Echo, Atlas, Aegis, Relay, Bifrost, Beacon, or Session Lifecycle.
- [ ] **Multi-step:** The task needs more than one read, tool call, verification pass, model call, or retry.
- [ ] **Context-risky:** The working material includes raw logs, raw transcripts, broad search results, file bodies, render output, proof artifacts, or worker-session chatter.
- [ ] **Typed output possible:** The result can be returned as `WorkflowResultSummary` or `WorkflowErrorSummary`, not as a raw transcript.
- [ ] **Aegis-gated:** The task has a risk tier and a clear proof/human-gate requirement.
- [ ] **Permission-bounded:** Allowed tools, allowed paths, forbidden paths, and branch/worktree permissions are explicit.
- [ ] **Prime-safe return:** The result summary is small enough for Prime and does not require raw context injection.

If any required check fails, Prime should use a narrower work order, a direct Relay call, or a human-gated Review Console item.

## Immediate Disqualifiers

Do not use a workflow/sub-agent when:

- The job is Prime's own deliberation about what matters next.
- The job has no bounded stopping condition.
- The job requires silent branch movement, shared worktrees, or destructive filesystem/session actions.
- The expected output is a raw chat transcript, raw test log, raw browser console dump, raw HTML/CSS, raw search result page, or raw file body.
- The work crosses project boundaries without explicit project/user permission.
- The work needs durable promotion before Aegis and Prime accept the result.
- The task is a single short model response that Relay can dispatch with a bounded prompt.

## Harness Routing Matrix

| Harness | Use Workflow When | Expected Return |
|---|---|---|
| Echo | Memory maintenance, bulk distillation, supersession bookkeeping, or large candidate preparation would expose raw memory text. | `WorkflowResultSummary` with typed `MemoryRecord` or `MemoryHit` summaries. |
| Atlas | Retrieval needs broad FileMap/doc scans, many candidate reads, or Echo fold-in ranking. | `WorkflowResultSummary` with `AtlasResult`, ranked hits, missing paths, and proof refs. |
| Aegis | Proof review, finding synthesis, waiver preparation, or disagreement triage would produce verbose evidence chatter. | `WorkflowResultSummary` with proof verdict, blocking reasons, and `ProofTrail` refs. |
| Relay | Multi-call aggregation, route comparison, or dispatch transcript handling would pollute Prime's context. | Typed dispatch summary with status, route, token use, structured excerpts, and proof refs. |
| Bifrost | Preview verification, render screenshot checks, escape/a11y checks, or view-model validation would create noisy UI output. | `BifrostRenderCheck` summary with pass/fail checks and artifact refs. |
| Beacon | Liveness/staleness sweeps cover many sessions, paths, harnesses, or heartbeat sources. | `BeaconLivenessReport` keyed by target with age, status, and reason. |
| Session Lifecycle | Watch, steer, restart, resteer, recover, transfer, or archive diagnosis would mirror worker-session chatter into Prime. | `SessionLifecycleResult` or `WorkflowErrorSummary` with state transition, evidence, and gate flags. |

## Work Order Checklist

Before dispatching a workflow, Prime must build a `WorkflowWorkOrder` with:

- [ ] `work_order_id`
- [ ] owning `harness`
- [ ] bounded `action`
- [ ] one-sentence `intent`
- [ ] `risk_tier`
- [ ] `WorkflowInputPacket`
- [ ] `expected_result_shape`
- [ ] `time_budget_seconds`
- [ ] `hard_timeout_seconds`
- [ ] `created_at`
- [ ] optional `parent_work_order_id` only when nested delegation is explicitly allowed

The `WorkflowInputPacket` must include:

- [ ] `project`
- [ ] short `goal_summary`
- [ ] typed `inputs` with source tags
- [ ] explicit `allowed_tools`
- [ ] explicit `allowed_paths`
- [ ] explicit `forbidden_paths`
- [ ] `prompt_budget`
- [ ] `gate_context` for tier-2+ or proof-sensitive work

## Result Acceptance Checklist

Prime may accept a workflow result only when:

- [ ] The return shape is exactly `WorkflowResultSummary` or `WorkflowErrorSummary`.
- [ ] The result `work_order_id` matches the active order.
- [ ] The result `harness` matches the active order.
- [ ] The result shape matches `expected_result_shape`, or the error shape explains why it cannot.
- [ ] Tier-2+ results include a usable `ProofTrail`.
- [ ] The summary is bounded and does not include raw transcript/log/file/search content.
- [ ] Any `requires_human_gate=True` result is routed to Review Console before durable action.
- [ ] Any `WorkflowResteerRequest` is treated as a recommendation; Prime must issue a new work order to act on it.

## Prompt-Drag Guardrail Checklist

Workflow return payloads must never include:

- [ ] raw worker transcripts
- [ ] raw model scratch output
- [ ] raw test stdout
- [ ] raw browser console logs
- [ ] raw screenshots embedded as prose
- [ ] raw HTML/CSS dumps
- [ ] full file bodies
- [ ] broad search result dumps
- [ ] heartbeat history
- [ ] cross-project context

Allowed return payloads:

- [ ] short summary
- [ ] typed output records
- [ ] proof references
- [ ] artifact paths
- [ ] next-action recommendation as a short advisory field
- [ ] human-gate flag

## Restart vs. Resteer Checklist

Use **restart** when:

- [ ] The work order is still correct.
- [ ] Failure was transient, stale, timed out, or caused by a lost session.
- [ ] The same inputs, allowed tools, and expected result shape still apply.

Use **resteer** when:

- [ ] The work order was too broad, underspecified, or framed incorrectly.
- [ ] The workflow returns `WorkflowResteerRequest`.
- [ ] New allowed paths, inputs, risk tier, or result shape are needed.

Never let a workflow restart or resteer itself. Prime decides; Session Lifecycle executes.

## Bifrost Visibility Checklist

Bifrost should render workflow status without turning into a log wall:

- [ ] active workflow id
- [ ] harness
- [ ] phase
- [ ] last heartbeat summary
- [ ] age / timeout pressure
- [ ] risk tier
- [ ] proof status
- [ ] human-gate flag
- [ ] final result or error summary

Bifrost should not render raw sub-agent transcripts or permanent top-navigation noise for workflow internals.

## First Runtime Slice Expectations

The first runtime implementation should prove:

- [ ] frozen domain objects for work orders, input packets, heartbeats, results, errors, and resteer requests
- [ ] validation rejects missing intent, missing expected result shape, unbounded timeouts, raw transcript fields, and forbidden return payloads
- [ ] tier-2+ result acceptance requires proof
- [ ] restart and resteer are distinct typed outcomes
- [ ] Session Lifecycle can represent a workflow as watched state without executing real process control
- [ ] no filesystem, network, branch movement, session mutation, or model calls in the first pure domain slice

## Prime Operating Rule

When Prime is unsure whether to use a workflow, choose the path that keeps Prime's context smallest while preserving proof and gates.

If that still leaves ambiguity, Prime should issue a smaller work order, not a larger prompt.

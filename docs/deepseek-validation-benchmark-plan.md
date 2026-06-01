# DeepSeek Validation Benchmark Plan

**Owner:** Relay / Model Harness
**Status:** V2 benchmark plan
**Source gate:** `docs/deepseek-provider-validation-gate.md`

## Purpose

This plan defines the proof Meridian requires before DeepSeek can move beyond candidate provider status.

DeepSeek is a primary provider candidate beside Claude and OpenAI, but it must earn authority through direct API proof, prompt-payload flatness, bounded Q-mode behavior, coding benchmark results, and independent Codex review. Until that proof exists, DeepSeek is useful for planning and bounded drafting, not autonomous implementation, review clearing, branch movement, or worktree authority.

## Validation Levels

| Level | Name | Allowed Use | Required Gate |
|---|---|---|---|
| 0 | Candidate | bounded planning, summaries, checklist/contract drafts, low-risk docs with review | direct API metadata + payload visibility |
| 1 | Assisted Coding | small patch drafts under trusted review | coding benchmark pass + tests + Codex review |
| 2 | Gated Build Lane | selected build queue tasks under Aegis/review cadence | repeated representative slices with demotion policy |
| 3 | Primary Coding Provider | normal selected-risk build provider | sustained pass rate, prompt discipline, cost/latency evidence |

No level grants review-clearing authority, branch movement, or worktree mutation unless a later Prime/Aegis permission object explicitly permits it.

## Benchmark Round Structure

Each benchmark round must record:

- provider id: `deepseek`
- API mode: `direct`
- model id used
- route owner: Relay / Model Harness
- trust level before round
- task id and task type
- allowed files or docs
- prompt payload token estimate
- payload budget percent
- payload delta from prior Q-mode poll or dispatch
- whether the task packet changed
- latency and error state
- output artifact
- tests or proof commands
- Codex review result
- promotion/demotion decision

Aggregator or OpenRouter traffic does not count as direct API proof. If a benchmark expects direct DeepSeek and telemetry shows an aggregator route, the round fails as a route mismatch.

## Round 0: Direct API And Metadata Proof

Goal: prove the Model Harness can describe and dispatch DeepSeek as a direct provider candidate without bypassing Relay or Aegis.

Required checks:

- [ ] Provider metadata uses `provider=deepseek`.
- [ ] API mode is `direct`.
- [ ] Model id is structured, not embedded in prompt prose.
- [ ] Context budget and prompt budget are structured.
- [ ] Trust state starts at `candidate`.
- [ ] Allowed task types and blocked task types are explicit.
- [ ] Aegis risk tier is attached before dispatch.
- [ ] Prompt payload snapshot exists before dispatch.
- [ ] Bifrost/Balance can show direct-vs-aggregator route state.

Pass condition: DeepSeek can be selected as a candidate route through Relay/Model Harness, but blocked from autonomous coding and review-clearing authority.

## Round 1: Q-Mode Prompt Flatness

Goal: prove DeepSeek Q-mode does not replay the whole prior conversation or grow prompts additively across idle queue checks.

Protocol:

1. Send a bounded queue task packet to DeepSeek Q-mode.
2. Repeat three idle queue polls with no task-changing content.
3. Record prompt payload snapshot for every dispatch.
4. Compare token estimate, payload label, budget percent, and growth delta.

Pass condition:

- Prompt payload remains flat or changes only within a tiny expected metadata delta.
- No prior model response is replayed unless explicitly included in the task packet.
- No hidden transcript accumulation appears in the payload.

Fail condition:

- Payload grows meaningfully on idle checks.
- Prompt includes prior assistant/model responses by default.
- Prompt payload evidence is missing.

Failure result: mark DeepSeek Q-mode as degraded and block DeepSeek from build-lane queue polling until Relay/Model Harness proves flat prompts.

## Round 2: Low-Risk Docs Task

Goal: test useful docs output without granting code authority.

Task examples:

- write a bounded checklist from an existing contract
- summarize a narrow architecture note
- draft a docs-only comparison table

Required constraints:

- Single allowed docs file or generated artifact.
- No runtime code edits.
- No FileMap edits unless explicitly assigned.
- Codex Reviews B or A must review before the result is accepted.

Pass condition:

- Output stays in scope.
- No invented architecture or provider claims.
- No raw unrelated context.
- Codex review finds no blocking issue.

## Round 3: Small Coding Patch Draft

Goal: determine whether DeepSeek can draft a small code change under trusted review.

Task shape:

- one small pure function or dataclass helper
- one focused test file
- no filesystem/network/session mutation
- no branch/worktree operations
- no package/API expansion unless explicitly allowed

Required proof:

- Tests pass locally.
- Diff only touches allowed files.
- Codex review inspects the patch before merge.
- Aegis risk tier remains 1 or 2.

Pass condition:

- Patch is correct, scoped, deterministic, and review-clean.

Failure examples:

- hallucinated APIs
- modifies extra files
- weak or missing tests
- ignores existing code style
- changes behavior outside scope
- prompt payload grows unexpectedly

## Round 4: Representative Meridian Build Slice

Goal: test whether DeepSeek can handle a real Meridian build slice while still gated.

Eligible tasks:

- small docs-to-runtime mapping
- small FileMap registration
- small metadata helper
- focused UI view-model fixture update

Ineligible tasks:

- Codex review clearing
- branch/worktree movement
- session orchestration authority
- high-risk Aegis/cognition changes
- broad refactors
- vendor billing/account automation

Pass condition:

- Multiple representative slices pass tests and Codex review with no MEDIUM+ findings.
- Failures are understandable and recoverable.
- Prompt payload remains flat under Q-mode.

## Required Codex Review Proof

Every DeepSeek-produced coding or build artifact must be reviewed by Codex until DeepSeek reaches an explicitly recorded higher trust state.

Codex review must record:

- DeepSeek model id and direct API evidence.
- Prompt payload snapshot evidence.
- Allowed files.
- Tests run.
- Findings by severity.
- Whether the result counts toward promotion, neutral evidence, or demotion.

DeepSeek must never review or clear its own output.

## Promotion Rules

Promotion is evidence-based and reversible.

To promote from Candidate to Assisted Coding:

- Direct API proof passes.
- Q-mode flatness passes.
- At least two low-risk docs tasks pass Codex review.
- At least two small coding patch drafts pass tests and Codex review.

To promote from Assisted Coding to Gated Build Lane:

- At least five representative Meridian build slices pass.
- No HIGH or CRITICAL findings.
- MEDIUM findings are rare, repaired, and pattern-analyzed.
- Prompt payload flatness remains stable.
- DeepSeek failures are documented with known demotion triggers.

To promote to Primary Coding Provider:

- Sustained pass rate over a longer sample of implementation, docs, and repair tasks.
- Cost/latency advantage is visible in Balance telemetry.
- Aegis can still require second-lane cognition for higher-risk work.
- Scott or Prime explicitly accepts the trust-state change.

## Demotion Triggers

DeepSeek is demoted or blocked when:

- Direct API route is missing or silently replaced by aggregator routing.
- Prompt payload grows additively across Q-mode checks.
- Output modifies files outside allowlist.
- Output invents APIs, test commands, provider behavior, or architecture commitments.
- Tests fail in a way the model did not predict or repair.
- Codex review finds HIGH/CRITICAL issue.
- Repeated MEDIUM findings show the same failure pattern.
- DeepSeek attempts or recommends review-clearing, branch movement, worktree mutation, or gate bypass.
- Provider quota/cost/latency makes the route unsafe for the current task.

## Evidence Storage

Benchmark evidence should be stored as structured records, not raw transcripts.

Minimum evidence fields:

- benchmark round id
- provider metadata
- trust state before and after
- task packet summary
- prompt payload snapshot refs
- proof command refs
- Codex review refs
- promotion/demotion decision
- follow-up recommendation

Raw prompts, raw completions, and raw logs should not be injected into Prime. If they must be retained, store them as artifacts referenced by a proof packet, not as Prime context.

## Bifrost And Balance Requirements

Bifrost should show:

- DeepSeek direct vs aggregator route
- current trust state
- prompt payload label
- growth/flat status for Q-mode
- budget percent
- cost/quota pressure when available
- whether external Codex review is required
- latest benchmark result

Bifrost displays the state. Prime/Relay/Aegis decide the route.

## Acceptance Criteria

This benchmark plan is ready when:

- It gives Prime a repeatable ladder for DeepSeek trust.
- It prevents DeepSeek from becoming a silent autonomous coding lane.
- It makes direct API proof distinct from OpenRouter/aggregator behavior.
- It requires Q-mode prompt flatness proof before queue usage.
- It requires Codex review before any DeepSeek coding output is trusted.
- It defines clear promotion and demotion triggers.

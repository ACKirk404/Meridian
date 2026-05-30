# Meridian Capabilities Architecture Map

**Status:** Strategic/architectural — no runtime code
**Owner lane:** Build 4 (Opus high-level thinking)
**Audience:** Prime, Codex, Scott, future contributors
**Purpose:** Single high-level map of the capabilities that make Meridian distinct and marketable. Not a feature list; a positioning and maturity map.

This document orients anyone — Scott, a reviewer, a future contributor, or Prime itself — to what Meridian *is*, what makes it different from a wrapper around a model API, and what state each capability is in today. It is deliberately strategic and does not enumerate file paths, class names, or build steps. For those, see `docs/meridian-capabilities.md`, `docs/meridian-pillars.md`, `docs/relay-prompt-budget-integration-brief.md`, `docs/prompt-packet-design-brief.md`, `docs/prompt-packet-implementation-checklist.md`, and the live FileMap.

---

## Reading Key

Every capability below uses the same shape.

- **Definition** — one sentence anyone can repeat.
- **Why it matters** — what would be missing if Meridian did not have this.
- **Maturity** — one of:
  - `planned` — named and described, not yet built.
  - `domain slice` — a typed domain model or contract exists; no runtime integration yet.
  - `integrated` — wired into the running system and exercised by tests or live workflow.
  - `needs hardening` — integrated but not yet trustworthy, observable, or recoverable enough for production load.
- **Likely harness owner** — which harness Prime will route to in order to use the capability.
- **Risks / open questions** — what could derail it, ambiguity that still needs resolution, or load-bearing decisions still owed.

Maturity reflects the architecture map's view from Build 4 today. It is not a release-readiness scorecard.

---

## What Makes Meridian Different

Most AI tools today are either:

1. A chat interface around a single model.
2. A workflow runner that hard-codes prompts and tools into procedures.
3. An autonomous agent loop that the user supervises message-by-message.

Meridian is a fourth shape: a **Prime-centered command system** where a persistent local brain reasons over a portfolio, dispatches worker sessions through a harness mesh, gates completion claims with proof, and treats every meaningful decision as a risk-tier choice rather than a model choice. The vendor model is a cognitive resource. The harness is the hands, senses, and memory. The user is the bottleneck for judgment, not coordination.

The capabilities below are the load-bearing pieces of that shape.

---

## 1. Prime as Persistent Orchestrator

- **Definition:** Prime is Meridian's local brain and orchestrator — the central reference line that interprets intent, reads portfolio and harness state, selects next moves, and dispatches worker sessions.
- **Why it matters:** Without Prime there is no "local owner of reality." Every other capability — memory, proof, dual-lane cognition, review automation — only earns its keep because Prime can call it deterministically and explain why. Prime is what makes Meridian a coordinated system rather than a pile of agents.
- **Maturity:** `domain slice`. The Prime identity, mission-first boot, progress intention, and risk-tier engine are defined in `context.md` and `docs/meridian-pillars.md`. Domain modules (intention, objectives, risk assessment, council, relay route) exist as typed slices. Prime as a long-lived runtime process with continuous heartbeat and steering is still planned.
- **Likely harness owner:** Prime itself (the kernel). Bifrost surfaces it; Compass, Echo, Atlas, Beacon, Aegis, Relay are the capabilities Prime reasons over.
- **Risks / open questions:**
  - Prime must not collapse back into "one giant runtime file" — the Polaris `server.js` failure mode. Hard ceiling on what Prime owns vs. delegates.
  - Persistent state substrate is not yet chosen (typed store vs. JSON event log vs. SQLite). The choice shapes everything downstream.
  - The boundary between "Prime decides" and "Prime asks Scott" must remain inspectable, not hidden in heuristics.
  - Risk tier visibility must be a first-class UI control, not a debug field.

---

## 2. Worker Sessions as Harness-Driven Execution Lanes

- **Definition:** Worker sessions are bounded, inspectable execution lanes that Prime dispatches through Relay; they are labor Meridian recruits, not the place Scott works.
- **Why it matters:** Polaris taught that a wall of session cards is a *diagnostic* surface, not a *primary* surface. By treating workers as managed lanes behind Prime, Meridian inverts the orientation: Scott talks to one brain, that brain runs many hands. This is also what lets dual-lane cognition exist at all — two lanes are routine if lanes are first-class harness objects.
- **Maturity:** `domain slice`. RelayRoute, lanes, cost posture, context strategy, and Council plan are typed. Real worker dispatch through a managed runtime (the equivalent of Polaris's session lifecycle, but properly bounded) is still planned. The current Build 1–4 live-queue workers are the closest live analogue: harness-driven lanes that pull, poll, commit, and report.
- **Likely harness owner:** Relay (dispatch, lifecycle, steering capability). Beacon (liveness). Bifrost (inspect panel when Scott explicitly opens one).
- **Risks / open questions:**
  - Each backend (Claude CLI, Codex CLI, OpenRouter, hosted GPT) has a different steering capability. The harness must report this honestly per-backend, not pretend they are uniform.
  - Lane independence must be real, not nominal — two lanes that silently share context cease to be two lanes for the purpose of disagreement detection.
  - The single inspect-on-demand session panel must replace the wall, not coexist with it, or the inversion fails.

---

## 3. Live Queue / Pull / Poll / Review Loop

- **Definition:** A durable, file-based queue (e.g. `docs/live-build-N.md`) that worker sessions pull from, poll on an interval, write completion logs to, and feed back into for cross-check and Codex review.
- **Why it matters:** This is the lightest possible substrate for Prime-style coordination *before* Prime exists as a runtime. It proves the directive-based coordination pattern (Polaris Lesson 5) works in Meridian today: one coordinator (currently Codex / Scott / Build 4 itself) assigns work, multiple lanes execute concurrently without trampling each other, and a review cadence is built into the loop. The queue file is also the audit trail.
- **Maturity:** `integrated`. Build 1–4 live queues are actively in use as of Build 4. Read Checks, Write/Completion Log, Cross-Check Activity, and Codex Review Cadence sections exist and are honored. This is the only capability on this map that is operationally exercising the Meridian build process right now.
- **Likely harness owner:** Eventually Loom (workflow) for queue lifecycle, Relay for dispatch, Beacon for poll heartbeat, Compass for queue→objective mapping. Today it is a flat-file convention that a future harness should subsume rather than replace.
- **Risks / open questions:**
  - Flat-file queues are excellent boundary/debug formats but should not become the primary state substrate (Polaris Lesson 14 / "what not to repeat").
  - The 30-second poll cadence and three-commit Codex review cadence are conventions, not enforced contracts. They need a home in a harness when one exists.
  - Same-file edit conflicts between lanes are currently prevented by per-task file allowlists; a programmatic boundary check would be more durable.
  - The queue currently mixes assignment, log, and audit in one file. Eventually these may want to be separable views over the same underlying event log.

---

## 4. Prompt Budget / Prompt Packet / Prompt Metrics

- **Definition:** A three-part discipline that makes "Relay must not become prompt drag" measurable: **Prompt Budget** sets tier-locked rules (max tokens, allowed sources), **Prompt Packet** is the validated immutable bundle built under those rules, and **Prompt Metrics** measure construction time, token count, and overhead against a vendor baseline.
- **Why it matters:** This is one of Meridian's most distinctive architectural claims. The Polaris postmortem identified prompt overhead inside the agent harness — not orchestration itself — as the dominant tax. Meridian answers by making prompt weight a deterministic function of risk tier and by sealing the prompt as a validated artifact *before* dispatch. Worker dispatch stays lean; Prime stays rich. The split between the two is enforced by data, not by prompt convention.
- **Maturity:** `domain slice` for Prompt Budget (typed, mapped to risk tier, deterministic). Prompt Packet has a design brief and implementation checklist but no runtime code. Prompt Metrics is sketched in the budget integration brief but not built. RelayRoute does not yet carry the budget field in runtime.
- **Likely harness owner:** Relay (carries the budget on every route, builds and seals the packet, emits metrics).
- **Risks / open questions:**
  - Token counting is provider-specific; the budget abstraction must not pretend tokens are universal across model families.
  - The vendor baseline measurement requires sending the same task minimally to the vendor — that itself costs money and may be rate-limited.
  - The packet's `is_valid` flag versus exception-on-invalid is still an open design question (see `docs/prompt-packet-implementation-checklist.md` open questions).
  - The lineage dict is internal accounting; under no circumstance should it leak into the serialized prompt. This needs a test, not just a convention.
  - Tier 3/4 budgets allow proof and explanation context to grow — the ceiling values (5,000 / 8,000) are placeholders and will need empirical tuning.

---

## 5. Review Console and Non-Orchestrator Surface

- **Definition:** A second prompt surface, paired with the Orchestrator Queue, where Prime places artifacts, plans, comparisons, proof, worker outputs, and gate items it wants Scott to see or respond to — separate from the conversational stream.
- **Why it matters:** Polaris collapsed conversation and gating into one stream, which made every review feel like an interruption. Meridian's split lets Prime own routine review loops in the background while still surfacing the small set of items that genuinely need Scott's eyes. It is also where automatic cross-check messages, Aegis proof results, and Council comparisons land without crowding the orchestrator queue.
- **Maturity:** `planned`. The surface is described in `context.md` (Non-Orchestrator Queue) and `docs/meridian-pillars.md` (Pillar 10) but is not yet built. The name itself ("non-orchestrator") is acknowledged as awkward and needs a real product name.
- **Likely harness owner:** Bifrost (UI surface). Aegis (feeds proof outputs). Relay (feeds Council comparisons and lane disagreements). Loom (feeds workflow gates).
- **Risks / open questions:**
  - Naming. "Non-orchestrator" is descriptive but not a product noun. Candidates worth exploring: Review Console, Gates, Watch, Console, Findings, Brief.
  - The boundary between "Prime decides and tells Scott" and "Prime places in the gate window" must be inspectable — otherwise Scott cannot trust the routine-vs-gate split.
  - The surface needs an interaction model: scroll-and-acknowledge, swipeable cards, threaded responses, or a queue with disposition actions. This is a design question, not just an architecture one.
  - Audio/voice integration (NASA-style "Go" calls) is named as a possibility; it crosses into Bifrost surface scope and should not be conflated with the gate surface itself.

---

## 6. Aegis Proof and Gated Cognition

- **Definition:** Aegis is the proof harness; gated cognition is the Pillar 2 / Pillar 6 principle that completion claims, irreversible actions, and high-risk decisions must pass an Aegis gate before Prime commits.
- **Why it matters:** This is the structural answer to "the model said it's done." Polaris proved that proof units (expected behavior, command, expected initial failure, expected passing evidence) move work from belief to evidence. Meridian elevates proof from a workflow add-on to a harness — meaning Prime cannot bypass it for tier-3 or tier-4 actions without making the bypass visible. Combined with risk tiering, this is what makes the system trustworthy at high stakes without making it heavy at low stakes.
- **Maturity:** `domain slice`. Aegis has a typed domain in the core modules; its role in the risk tier engine is defined. Live proof execution (running tests, capturing screenshots, validating browser checks, recording waivers) and end-to-end gate enforcement are planned.
- **Likely harness owner:** Aegis. Hooks into Relay (cannot dispatch tier-3/4 completion without Aegis OK), Compass (objective completion gated), Launch (release gated).
- **Risks / open questions:**
  - The proof catalog is open-ended (test, browser check, screenshot, log, manual waiver). The harness must expose a typed enumeration, not a free-form string field, or the gate becomes prose.
  - Waivers must be auditable and dated. An unaudited waiver path is a backdoor.
  - Tier-4 (human gate) must not silently degrade to tier-3 if Scott is unavailable — the action queues, it does not auto-approve.
  - The relationship between Aegis and the Review Console is close but not identical: Aegis decides whether proof passes; the Review Console is where proof results may be surfaced for Scott. Both are needed.

---

## 7. Council Reasoning

- **Definition:** The Council is Prime's structured internal deliberation system, with named voices (Analyst, Devil's Advocate, Pragmatist, Contrarian, Expansionist, Chairman) whose composition is fixed per risk tier and carried on every RelayRoute as a CouncilPlan.
- **Why it matters:** Probabilistic model output is not deliberation. The Council gives Prime an explicit, inspectable cognitive structure — not a "think harder" prompt — so that disagreement is detectable, escalation is principled, and the Chairman explicitly decides which voice carries the moment. It is also what lets risk tiers shape *process*, not just lane count: a tier-3 decision invokes a fuller Council than a tier-1 decision, deterministically.
- **Maturity:** `domain slice`. CouncilPlan exists as a typed slice carried on RelayRoute. The mapping from risk tier to council composition is defined. Live Council execution — voices actually generating positions, the Chairman synthesizing — is planned and will likely sit inside Prime's reasoning loop, not inside Relay.
- **Likely harness owner:** Prime (Council is internal to the kernel). Relay carries the plan as a contract; Aegis may gate the Chairman's conclusion on high tiers.
- **Risks / open questions:**
  - The Council must not become role-play prompting that inflates worker prompts — Council deliberation belongs in Prime, not in the worker dispatch (this is also a Pillar 13 constraint).
  - "Voices" can be different prompt frames inside one model, different lanes in Relay, or both. The right binding per tier is not yet decided.
  - The Chairman is the load-bearing role — without a strong synthesis policy, the Council degrades into a panel of opinions.
  - Council output should be inspectable in the Review Console (a Council transcript Scott can read), but the transcript must not be silently re-injected into the next dispatch.

---

## 8. Memory and Effective Unbounded Context

- **Definition:** Persistent, ranked, queryable memory (Echo) plus long-term knowledge retrieval (Atlas) and eventual deep search, used to give Prime a working memory that is not bounded by any one model session's context window.
- **Why it matters:** This is Meridian's answer to "the session ran out of tokens and forgot what we decided." A large-context model is helpful but not the core solution. The core solution is that Prime can summarize important state into Echo/Atlas, reset polluted sessions without losing continuity, and inject focused memory into a worker prompt — selectively, ranked, capped — instead of replaying chat history. The effect is a Prime whose memory grows with experience rather than degrading with token pressure.
- **Maturity:** `domain slice`. Echo and Atlas are named, scoped, and described. The Polaris memory injection pattern (ranked, capped, reinforced on access, fail-soft, dependency-injected) is documented as the inheritance. Live memory storage, retrieval, ranking, and decay are still planned. Cross-session memory hand-off (Polaris memory → Meridian Echo) is unscoped.
- **Likely harness owner:** Echo (memory). Atlas (knowledge / RAG). Prime (decides what to remember and when to summarize). Relay (consumes ranked injections per Prompt Budget).
- **Risks / open questions:**
  - Memory injection must respect Prompt Budget — a "richer memory" capability that bloats prompts violates Pillar 13.
  - Correctability and contradiction (a new memory contradicts an older one) needs a real model, not just "newest wins."
  - Source linking is mandatory — an unsourced memory is rumor.
  - The decay policy must be inspectable; Scott should be able to see why a memory was demoted.
  - Multi-Meridian memory sharing (see capability 10) raises permission and compartmentalization questions early; the schema should not assume a single owner.

---

## 9. Cross-Check Review Automation

- **Definition:** Automatic, harness-driven review of completed work — including peer review (another model lane), Codex-style independent review, Aegis proof verification, and registry/boundary checks — without requiring Scott to dispatch the review manually.
- **Why it matters:** In Polaris this pattern emerged organically (`/review-pr`, `/codex-review`, orchestrator approval handler). Meridian elevates it to a Pillar 11 expectation: Prime owns routine builder/reviewer/verifier loops, including the routing of rejections back to the builder, the rerun of tests, and the re-dispatch for verification. Scott only enters for taste, strategy, irreversibility, or explicit takeover. The cross-check cadence currently expressed in the Build 4 queue (request a Codex review after every three commits) is a manual proxy for what this capability will eventually do automatically.
- **Maturity:** `integrated` as a manual cadence in the live queues; `planned` as a harness-driven automatic flow. Independent review paths exist as concepts and have real Polaris precedent. Automated dispatch, finding ingestion, repair routing, and result reporting are not yet built into Meridian's runtime.
- **Likely harness owner:** Relay (dispatches the review lane). Aegis (validates findings as proof). Loom (orchestrates review→repair→re-review workflow). Bifrost / Review Console (surfaces actionable findings).
- **Risks / open questions:**
  - "Cross-check is automatic" must not silently degrade into "cross-check is whatever the writer model agreed with itself about." Lane independence is a hard requirement, not a nice-to-have.
  - The repair loop is where most autonomy risk lives — a repair lane that auto-commits its own fixes needs the same tier discipline as any other build action.
  - The Codex review cadence (every three commits) is a useful heuristic; making it a contract requires a way for the harness to know what counts as a "commit by this lane."
  - Repeated cross-check on unchanged artifacts wastes tokens; the harness needs a "nothing changed since last review" cheap path.

---

## 10. Future Multi-User / Connected Meridian (Federation)

- **Definition:** The longer-road capability for one Meridian instance to coordinate with another Meridian instance — Prime-to-Prime collaboration, with shared project state, plans, artifacts, and progress intentions, while each user's Echo memory, harness state, permissions, and authority chain remain compartmentalized.
- **Why it matters:** This is the strategic differentiator that lets Meridian outgrow being "Scott's personal command system." It is not multi-user chat. It is a model where teams collaborate on portfolios without merging brains: each Prime stays local, each authority chain stays sovereign, and Meridian-to-Meridian links route shared work through explicit permissions and gates. The architectural cost of allowing for this is small if it shapes the schemas early — and very large if it has to be retrofitted later.
- **Maturity:** `planned`. Described in `context.md` (Meridian Federation) and `docs/meridian-capabilities.md`. Explicitly out of V0 scope. The constraint Build 4 should preserve is negative: no schema, identity model, or harness contract should silently assume a single user, a single Prime, or a single local Meridian.
- **Likely harness owner:** Eventually a Federation harness (unnamed) plus participation from Echo (private memory boundary), Charter (policy boundary), Aegis (proof exchange), Relay (cross-Meridian dispatch), Bifrost (visibility of remote state).
- **Risks / open questions:**
  - Identity. There is no model yet for "who is this remote Prime" — accounts, keys, trust levels, revocation are all open.
  - Memory compartmentalization. Echo must distinguish "facts I learned" from "facts I am willing to share with another Meridian."
  - Conflict between remote and local progress intentions — whose Prime decides what moves next on a shared project.
  - Public-repo positioning (the longer-road `context.md` claim that Meridian becomes a marketed tool) is downstream of federation, and the two should not be conflated. Public-repo readiness is a packaging and licensing problem; federation is an architectural one.
  - The temptation to build federation primitives early (RPC layer, sync engine, conflict resolution) before there is any single-user value to share is a known trap — V0 must resist it.

---

## Maturity Snapshot

| # | Capability                                  | Maturity                           | Lead harness owner(s)        |
|---|---------------------------------------------|------------------------------------|------------------------------|
| 1 | Prime as persistent orchestrator            | domain slice                       | Prime (kernel)               |
| 2 | Worker sessions as harness-driven lanes     | domain slice                       | Relay, Beacon, Bifrost       |
| 3 | Live queue / pull / poll / review loop      | integrated                         | (Loom future) — flat-file today |
| 4 | Prompt Budget / Packet / Metrics            | domain slice (Budget); planned (Packet, Metrics) | Relay        |
| 5 | Review Console / non-orchestrator surface   | planned                            | Bifrost, Aegis, Relay        |
| 6 | Aegis proof and gated cognition             | domain slice                       | Aegis                        |
| 7 | Council reasoning                           | domain slice                       | Prime (CouncilPlan via Relay) |
| 8 | Memory and effective unbounded context      | domain slice                       | Echo, Atlas                  |
| 9 | Cross-check review automation               | integrated (manual cadence); planned (automatic) | Relay, Aegis, Loom |
| 10 | Future federation                          | planned (deferred, schema-shaping only) | (Federation harness, TBD) |

Read this table as a snapshot from Build 4, not a release scorecard. "Domain slice" means a typed contract exists; it does not mean the capability is exercised end-to-end at runtime.

---

## What This Map Is Not

- It is not a feature list. Features live under each capability and belong in build plans, not here.
- It is not a release scorecard. Maturity here describes architectural state, not user-facing readiness.
- It is not a naming decision. Provisional names (Bifrost, Echo, Atlas, Aegis, Relay, Loom, Beacon, Compass, Charter, Forge/Vulcan, Lens, Launch, Grove) may change. The capability shape is what is load-bearing; the harness label is not.
- It is not a FileMap. File paths, class names, exports, and public APIs belong in `docs/FileMap.md` (Build 1 territory) and in the per-capability briefs.
- It is not a substitute for the Prime Directives. `docs/meridian-pillars.md` remains the canonical list of load-bearing claims; this map is the capability surface those claims project onto.

---

## How to Use This Map

- **For Prime (when Prime exists):** consult before producing a progress intention; use the maturity column to decide whether a capability is dispatchable or still a planning artifact.
- **For Scott:** read top-to-bottom when re-orienting on what Meridian is for, or jump to a single capability when deciding whether to invest a build slice there.
- **For Codex / reviewers:** read the risks/open questions per capability; those are the items most likely to need adjudication before runtime code lands.
- **For future contributors / public repo readers:** start here, then read `docs/meridian-pillars.md`, then `context.md`, in that order. This map gives the shape; the pillars give the principles; the context file gives the working vocabulary.

---

## Cross-References

- Working vocabulary and canonical definitions: `context.md`
- Load-bearing claims (Prime Directives / Meridian Pillars): `docs/meridian-pillars.md`
- Quick recall sheet for capabilities (plain-language): `docs/meridian-capabilities.md`
- Polaris lessons informing each capability: `docs/polaris-lessons-for-meridian.md`
- Prompt Budget design: `docs/relay-prompt-budget-integration-brief.md`
- Prompt Packet design: `docs/prompt-packet-design-brief.md`
- Prompt Packet implementation: `docs/prompt-packet-implementation-checklist.md`

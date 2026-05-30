# Meridian Context

This document defines the working language for Meridian. It is not a glossary for marketing. It is a build contract: when we use these words in code, docs, prompts, memory, UI, and tests, they should mean the same thing.

Meridian's purpose:

> Meridian is a proactive portfolio orchestrator and builder. It advances projects, businesses, websites, tools, and experiments until Scott's judgment is the bottleneck.

Public intent:

> Meridian should eventually become a publicly available repo and marketed tool for people following Scott's AI work. This is a later-road constraint, not a V0 requirement.

Public positioning:

> You talk to the orchestrator. The orchestrator drives the worker sessions.

## Canonical Project Anchors

Meridian already has its own repo and Obsidian workspace.

Local repository:

```text
C:\Users\scott\Code\Meridian
```

Remote repository:

```text
https://github.com/AesopScott/Meridian.git
```

Obsidian build folder:

```text
G:\My Drive\Aesop Academy\Obsidian\Meridian_Build
```

Obsidian sessions folder:

```text
G:\My Drive\Aesop Academy\Obsidian\Meridian_Sessions
```

Current build files:

- `1-Soul.md`
- `2-Architecture.md`
- `3-Build-Plan.md`
- `4-Changelog.md`
- `5-Permissions.md`
- `6-Obsidian.md`
- `7-Integrations.md`
- `8-Logs.md`
- `FileMap.md`

When building Meridian, use these anchors instead of the Polaris repo/docs unless explicitly harvesting Polaris lessons.

## Core Principle

Meridian is not an app home. Meridian is a builder and operator.

It does not exist primarily to host agents or applications. It exists to turn intent into useful progress across a portfolio of work.

The local orchestrator is the local brain. Remote models are cognitive resources. Harnesses are the hands, senses, memory, and shipping paths.

## Portfolio

A portfolio is the full set of ventures Meridian is aware of and may help advance.

A portfolio can include:

- Businesses
- Software products
- Websites
- Internal tools
- Automation systems
- Communities
- Experiments
- Client projects
- Research directions

The portfolio is not just a list of repos. It is a map of active and potential value creation.

Example:

```text
Scott's portfolio
  - Meridian
  - Polaris
  - Aesop Academy
  - Advanced AI Concepts
  - CareGuide
  - future SaaS experiments
  - event automation
  - websites and landing pages
```

## Venture

A venture is a value-seeking container inside the portfolio.

Use venture when the work has business, audience, revenue, market, community, or strategic identity beyond a single codebase.

Examples:

- Aesop Academy
- Advanced AI Concepts
- CareGuide
- A future productized AI tool

A venture may contain many projects.

## Project

A project is an organized body of work with a concrete outcome.

A project may be software, content, operations, research, design, or launch work. It may or may not have a Git repository.

Examples:

- Build the Meridian local orchestrator
- Launch a website for a venture
- Create a lead capture funnel
- Automate Meetup event copying
- Build a Chrome extension

Do not use project as a synonym for repository. A repo is an implementation container. A project is an outcome container.

## Repository

A repository is a version-controlled codebase.

Repos are important to the harness, but they are not the top-level planning unit. A single project may use multiple repos, and a single repo may support multiple projects.

## Initiative

An initiative is a directional push inside a venture or project.

Use initiative for proactive portfolio motion: something Meridian can monitor, advance, pause, or escalate.

Examples:

- Improve Advanced AI Concepts event operations
- Build Meridian V0
- Prepare CareGuide for production promotion
- Explore a new SaaS idea
- Refresh a website

An initiative usually has objectives.

## Objective

An objective is a concrete desired outcome.

It should answer:

- What should be true when this is done?
- Why does it matter?
- How will we know?

Examples:

- Meridian can inspect harness heartbeat and inject decisions into blocked sessions.
- A landing page exists and captures leads.
- The memory panel allows Scott to edit or archive memories.
- The event copy automation avoids duplicate Meetup events.

Objectives can be short-lived or durable.

## Goal

A goal is a durable objective with persistence and follow-through.

Use goal when Meridian should keep pursuing the outcome across time, sessions, heartbeats, or restarts.

All goals are objectives. Not all objectives need to become goals.

## Task

A task is a bounded unit of work.

Tasks are execution units, not strategy units. They should be small enough to plan, perform, verify, and close.

Examples:

- Add a read-only builder kernel module.
- Wire a heartbeat endpoint.
- Fix a failing browser verification.
- Draft homepage copy variants.

Tasks may belong to objectives, initiatives, projects, or ventures.

## Next Move

A next move is the smallest useful action Meridian can take to advance an objective.

Next moves are the core of proactive operation.

Examples:

- Inspect the repo for existing scaffold patterns.
- Ask Scott to choose between two customer segments.
- Spawn a reviewer for a PR.
- Run browser verification.
- Draft an app blueprint.
- Create a sandbox prototype.

Meridian should constantly ask: what is the next move that advances the portfolio without unnecessary risk?

## Scott Bottleneck

A Scott bottleneck is a decision or judgment only Scott should make.

Meridian should work to make Scott the bottleneck for judgment, not execution.

Good Scott bottlenecks:

- Choose priority between ventures.
- Approve brand direction.
- Decide whether to spend money.
- Accept a strategic tradeoff.
- Publish externally.
- Choose target customer.

Bad Scott bottlenecks:

- Remember to run the next command.
- Notice a session stalled.
- Copy context between agents.
- Check whether tests ran.
- Manually summarize every project state.

## Harness

A harness is a capability surface Meridian can use to sense or act.

Harnesses are distributed. Each harness should report state, expose capabilities, and accept commands through a controlled interface.

Examples:

- Agent harness
- Tool harness
- Git/worktree harness
- Memory harness
- Proof harness
- Browser harness
- Release harness
- UI harness
- Backlog/task harness

## Heartbeat

A heartbeat is a live state report from a harness, session, objective, or workflow.

It tells Meridian what is alive, busy, blocked, stale, failed, or ready.

Minimum heartbeat shape:

```text
id
kind
status
current_work
last_event
blockers
capabilities
updated_at
```

Heartbeat gives Meridian liveness. Without heartbeat, Meridian becomes a static planner.

## Workflow

A workflow is coordinated motion over time.

Workflows may be fixed, generated, or adaptive. A workflow is not the mind. It is a path the orchestrator can choose, revise, pause, or abandon.

Examples:

- Plan -> build -> verify -> review -> ship
- Research -> compare -> ask Scott -> prototype
- Detect blocker -> diagnose -> inject instruction -> verify recovery

## Kernel

The kernel is Meridian's local reasoning core.

It builds the local state model, interprets intent, reads heartbeat, checks policy, selects next moves, calls remote models when useful, and injects decisions into harnesses or sessions.

The kernel should not become a giant monolith. It should reason over domain objects and delegate execution to harnesses.

## Local Brain

The local brain is Meridian's persistent, local understanding of reality.

It includes:

- Kernel state
- Portfolio state
- Harness heartbeats
- Memory
- Event log
- Policies
- Current objectives
- Known blockers

The local brain maintains continuity. Remote models help with bounded reasoning, generation, review, and synthesis.

## Remote Brain

A remote brain is a model or agent session used for cognitive work.

Examples:

- Claude
- Codex
- GPT
- DeepSeek
- Future local or hosted models

Remote brains do not own Meridian's truth. They propose, generate, review, and reason. The local brain decides what to trust, verify, store, or act on.

## Memory

Memory is durable experience that should shape future behavior.

Memory should include:

- User preferences
- Project decisions
- Venture facts
- Failure modes
- Proof patterns
- Tooling workarounds
- Strategic context

Memory is not gospel. It should be source-linked, correctable, reinforced, contradicted, and decayed.

## Proof

Proof is evidence that a claim or result is trustworthy enough to proceed.

Proof can be:

- Automated test
- Browser verification
- Screenshot
- Build output
- API check
- Review verdict
- Diff inspection
- Manual waiver

No important work should be marked done without proof or an explicit waiver.

## Artifact

An artifact is a durable output Meridian creates, modifies, verifies, or ships.

Examples:

- Code files
- Generated app folder
- Screenshot
- Test report
- PR
- Build package
- Document
- Website
- Design asset
- Decision brief

Artifacts should be indexed so Meridian can refer to them later.

## Decision

A decision is a committed choice with a reason.

Meridian should record important decisions in a decision journal:

```text
decision
reason
context
alternatives_considered
evidence_required
actor
timestamp
outcome
```

## Policy

A policy is a constraint or preference that shapes Meridian's actions.

Hard policies cannot be bypassed without Scott approval.

Soft policies are heuristics that Meridian may adapt with explanation.

## Agent

An agent is a bounded worker with a role, context, tools, and expected output.

Agents are not the center of Meridian. They are labor Meridian can recruit.

Roles may include:

- Planner
- Builder
- Reviewer
- Verifier
- Researcher
- Designer
- Release operator
- Memory distiller

The orchestrator assigns roles, not fixed providers. The selected model/interface determines which backend fills a role.

Default build lane:

```text
Builder: selected interface model, currently Claude Sonnet via Max by default
Session review: Claude Opus
Independent session review: Codex
Per-file review: third-party/OpenRouter reviewer
```

This default can change by project, risk, availability, or Scott's explicit selection.

## Builder

A builder is the part of Meridian that turns intent into working artifacts.

Builder does not mean "code generator only." It includes product interpretation, app blueprinting, implementation, verification, and shipping.

## Operator

An operator is the part of Meridian that keeps the portfolio moving.

It scans initiatives, detects stalled work, starts safe next moves, and escalates Scott bottlenecks.

## Orchestrator Session

The orchestrator session is Scott's primary conversational surface.

Scott should mostly talk to the orchestrator, not individual worker sessions. The orchestrator interprets intent, checks portfolio and harness state, then injects instructions into workers.

Worker sessions are managed execution surfaces. They should be visible and inspectable, but manual prompting inside them should be exceptional.

## Prime

Prime is the current provisional name for Meridian's orchestrator/local brain.

Prime reads portfolio state, listens to harness heartbeat, consults memory and knowledge, coordinates worker sessions, and asks Scott for judgment only where judgment matters.

The name comes from the Prime Meridian: the reference line that gives every other position meaning. In Meridian, Prime is the central reference point for orientation, priority, coordination, and decision-making.

Prime is currently preferred over Oracle and Daemon for the user-facing orchestrator identity. Oracle may remain useful as the name for a brief/recommendation mode. Daemon may still describe the internal always-on runtime/process nature of Meridian.

## Dynamic Risk-Tiered Dual-Structured Gated Cognition

Meridian's decision engine is Dynamic Risk-Tiered Dual-Structured Gated Cognition: Prime, Meridian's orchestrator, dynamically adjusts reasoning depth by risk tier, can use independent dual lanes, applies structured Council deliberation, and gates completion claims through Aegis proof when consequences require it.

This is Prime Directive Two.

Dynamic means Prime can change process midstream as consequence, uncertainty, reversibility, or proof requirements change.

Risk-tiered means Prime selects the amount of scrutiny required for the action.

Dual means meaningful work can use independent model lanes or reasoning paths when the tier requires it.

Structured means Prime does not merely ask a model to think harder. It can use named cognition structures, including The Council.

Gated means Aegis controls proof, completion claims, escalation, and human gates when consequences require it.

## The Council

The Council is Prime's internal reasoning chamber.

It is a structured cognition mode, not necessarily six separate models or six worker sessions. Prime may invoke all or part of the Council depending on risk tier.

Council voices:

- Analyst: evidence-based, skeptical, cites reasoning, asks what is actually known.
- Devil's Advocate: challenges assumptions and finds flaws in the prevalent view.
- Pragmatist: focuses on what is realistic, actionable, timely, and cost-aware.
- Contrarian: pushes against the answer that seems most obvious or agreeable.
- Expansionist: finds possibilities, upside, and paths the current frame is missing.
- Chairman: collects the voices, weighs their value for the moment, and determines what Prime presents or does next.

The Chairman does not average the voices. The Chairman decides which voice matters most for the conversation, action, risk tier, and gate.

## Dual-Lane Cognition

Risk-tiered dual-lane cognition is Meridian's decision engine.

It is Meridian's answer to weak or probabilistic model judgment inside the orchestrator itself.

The system is dynamic. Prime may switch risk tiers on the fly as context changes.

Changing risk tier may matter more than changing models because it changes the decision process: deterministic logic, single-lane cognition, dual-lane cognition, proof requirements, and human gates.

Prime should not depend on a single model pass for meaningful decisions. For high-impact decisions, Prime should ask Relay for two independent cognition lanes, compare the candidate actions, detect disagreement, and then choose, merge, validate, retry, or escalate to Scott.

The value is not merely "two answers." The value is disagreement detection, risk classification, and adjudication by Prime.

Example flow:

```text
Prime intent
  -> Relay
    -> Candidate A from model/lane A
    -> Candidate B from model/lane B
  -> Prime compares candidates
  -> Aegis checks proof/risk where needed
  -> Prime chooses, merges, retries, or escalates
```

Risk-tier rule of thumb:

- Tier 0: deterministic local logic only.
- Tier 1: one model lane allowed for low-risk reversible actions.
- Tier 2: two independent lanes required for meaningful Prime decisions.
- Tier 3: two lanes plus Aegis proof required for high-risk or completion claims.
- Tier 4: Scott approval required for irreversible, financial, public, policy, account-based automation, or strategic actions.

This principle should influence future Relay, Aegis, Charter, and Prime design, but it should not expand the current wake-sequence build slice unless explicitly requested.

The UI should make the active risk tier visible.

Users should be able to see why Prime selected a tier, what that tier requires, and whether Prime escalated or de-escalated the tier during work.

The interface should treat risk tier as a major control/state, at least as important as model selection.

## Relay Prompt Efficiency

**Relay Must Not Become Prompt Drag.**

Relay should make model sessions steerable, observable, and coordinated without bloating prompts, slowing response time, or making the worker experience worse than using the vendor app directly.

This is a first-class Relay design constraint derived from the Polaris lesson that the major orchestration performance tax was prompt overhead in the agent harness — not orchestration itself.

Practical rules:

- Prime orchestration can be rich, but Relay dispatch must be lean.
- Default worker prompts should be minimal.
- Memory and context injection should be selective, ranked, and task-specific.
- Diagnostic metadata should not ride inside every model prompt.
- Session state should live outside the prompt when possible.
- Use references, file paths, and retrieval hooks instead of dumping context inline.
- Risk tier determines prompt weight. Tier 0–1 prompts should be near-minimal. Tier 3–4 may carry richer Council and proof context, but must still have a budget.
- The worker prompt should have an explicit token/context budget.
- Relay should eventually measure: prompt construction time, prompt token count, time to first token, total response time, and vendor/native delta where possible.
- Heavy process belongs in Prime, Aegis, Echo, Atlas, or Review Console — not automatically in every worker message.

See `docs/polaris-lessons-for-meridian.md` Lesson 16 for full context.

## Wake Experience

The wake experience is the moment Meridian comes online and the orchestrator session becomes active.

Prime's first wake responsibility is to locate, read, and obey the controlling boot instruction file.

Before Prime summarizes portfolio state, checks harnesses, proposes work, or talks confidently, it must know the first file it is supposed to read and follow without exception.

This file is the root of Prime's authority chain for the current run. Everything else in the wake sequence comes after it.

This file replaces the old "server.js is the heart of the harness" mental model from Polaris. In Meridian, the first center of gravity is a readable mission file that Prime loads before it acts.

The provisional filename is `MISSION.md`.

`MISSION.md` is not the wake sequence copy and not the whole orchestrator personality. It is the launch protocol and authority chain for Prime. Its job is to tell Prime which harnesses to call, in what order, and which immutable operating rules must be followed.

Prime is the actor. `MISSION.md` is the mission control protocol Prime follows.

The mission file may include a small number of immutable rules, but those rules should be rare, plain, and foundational.

Provisional user-facing wake language:

```text
Good morning, Scott.
Allow me to check today's mission file.
```

Target feeling:

```text
Prime online.
Meridian has established position.
Beacon Go.
Echo Go.
Relay Go.
Good morning, Scott.
```

The wake sequence should feel like a command system coming alive: cinematic enough to be memorable, but functional enough that every "go" maps to a real subsystem check.

The short NASA-style "Go" calls are allowed as the cinematic wake layer:

```text
Bifrost Go.
Beacon Go.
Echo Go.
Relay Go.
Aegis Go.
```

These calls should be brief and status-backed.

The NASA-style wake sentence sequence belongs in the non-orchestrator window as system-level information. It should not crowd the orchestrator conversation queue.

The orchestrator queue should contain Prime's conversational messages, progress intentions, judgment requests, and outcomes. The non-orchestrator window should show system messages, readiness calls, harness health, proof status, worker/session state, and other instrumentation Prime wants visible.

Go calls may happen before the progress intention in time, but they should be displayed as system instrumentation rather than conversational content.

The sequence may support modes such as:

- Full wake sequence: first run of the day, cinematic and complete.
- Fast wake: short version after the first daily startup.
- Skip: straight to the command center.

## Progress Intention

Prime should express meaningful work as a progress intention before execution.

The wake brief has two layers:

- Go calls: short, NASA-style subsystem readiness signals.
- Progress intention: Prime saying, "Here is what I intend to work on next," with clear opportunities for Scott to modify, approve, redirect, or stop it.

The progress intention is not a loading transcript and not a final plan.

Progress intention should focus on valuable work, not internal boot mechanics.

It should describe:

- Which project or projects Prime intends to advance.
- Which stage of each process the work is in.
- Why that work is prioritized, especially from backlog priority.
- How many sessions or worker lanes Prime expects to open.
- Any valuable health or risk information that affects the work.
- What Prime will ask Scott to decide before it proceeds.
- The next stage Prime intends to boot or enter.

It should not normally describe routine loading steps such as reading memory, checking tool availability, or contacting harnesses unless that information affects a user-facing decision.

This applies beyond wake. Prime should prefer progress-intention behavior for meaningful actions:

```text
Stage: Mission Boot > Compass Initiating

Mission Objectives:
<Open Project 1 - Stage Build - Risk Tier 2>
<Open Project 2 - Stage Review - Risk Tier 3>
<Open Project 3 - Stage Plan - Risk Tier 4>

Next Stage: Intention Engine Bootup
```

Scott can then approve, modify, or override the intention.

Low-risk observation and formatting actions may happen without explicit intent prompts. Meaningful actions should expose intention before execution, especially when they affect files, sessions, memory, policy, release, accounts, money, or public output.

## Persistent Prime Context

Worker and model sessions have fragile context. They fill up, drift, summarize poorly, or end.

Prime should not lose context just because a model session runs out of tokens.

Meridian's architecture should make Prime durable by backstopping session context with persistent memory and knowledge retrieval:

- Echo stores decisions, preferences, lessons, open loops, and project continuity.
- Atlas provides long-term RAG/knowledge retrieval.
- Future deep search can expand Prime's recall beyond local memory and indexed knowledge.
- Session prompts should receive focused memory injections instead of giant chat-history replays.
- When a session becomes bloated or polluted, Prime can summarize important state into Echo/Atlas and start a cleaner session.

A very large-context model may be useful for the orchestrator, but it is not the core solution.

The core solution is that Prime has persistent, queryable, ranked access to memory and knowledge. Prime's effective memory should not be bounded by any one model session's context window.

## Meridian File Map

Meridian needs a living knowledge tracker for important files and what they do.

This should be more than a static README. It should be an architecture-aware file map that sessions can consult, visualize, and eventually receive through memory injection automatically.

Purpose:

- Help any session quickly find the important Meridian files.
- Explain what each file owns.
- Reduce repeated repository rediscovery.
- Support future visual knowledge views.
- Feed Echo/Atlas memory injection so Prime and worker sessions start with the right file context.

The file map should include:

- file path
- owner harness or architecture area
- purpose
- public API or key objects
- related tests
- maturity/build metadata if known
- common reasons to edit it
- risks/cautions

The file map should be updated when new important files are added or ownership changes.

## Meridian Federation

Meridian should eventually support collaboration between multiple Meridian instances.

This is not merely multi-user chat. The stronger model is Meridian-to-Meridian coordination, where each user may have their own Prime, memory, harness state, projects, permissions, and local operating context.

Possible future capabilities:

- Connect one Meridian to another Meridian.
- Share selected project state, plans, artifacts, and proof.
- Exchange progress intentions between Primes.
- Coordinate builder/reviewer/verifier work across users.
- Keep each user's private Echo memory and local harness state compartmentalized.
- Route shared work through explicit permissions and gates.
- Let teams collaborate while preserving each Meridian's local authority chain.

This should not expand V0, but the architecture should avoid assumptions that only one user, one Prime, or one local Meridian can ever exist.

## Build And Harness Maturity

Meridian should track both overall build identity and per-harness maturity.

The overall Meridian build needs a build number starting now. This is separate from package versioning. Package version may describe software release semantics, while build number identifies the evolving Meridian system state.

Each harness should also have its own build number and maturity state.

Harness build number answers:

```text
Which implementation generation of this harness is currently present?
```

Harness maturity answers:

```text
How trustworthy, complete, proven, and operational is this harness?
```

These are related but not identical. A harness can have a high build number and low maturity if it has churned without becoming reliable. A harness can have a low build number and high maturity if it is small, stable, and well proven.

Suggested maturity states:

- Concept: named and defined, not implemented.
- Skeleton: domain shape exists, limited behavior.
- Prototype: works in controlled demo/sample state.
- Operational: useful in real workflow with tests/proof.
- Hardened: resilient, observable, recoverable, and trusted.
- Deprecated: retained for compatibility but no longer preferred.

Prime should be able to report Meridian build number, harness build numbers, and harness maturity in system views. This should eventually influence progress intention, risk tiering, and release gates.

## Prime-Centric Workspace

Meridian's UI should invert the Polaris worker-card model.

Polaris was primarily a wall of worker session cards with orchestration controls around them. Meridian should be Prime-centric: the Prime interface is the deep command surface, and worker sessions become compact controlled instruments.

Earlier default layout concept:

```text
Row 1:
  Prime Interface
  progress intention, bottlenecks, backlog priority, approvals,
  model lanes, proof status, recent decisions, next moves

Row 2:
  Builder Session | Reviewer Session | Verifier Session
  compact status, current assignment, health, last event,
  transfer/open, stop/retry/archive
```

This may be useful as a diagnostic or expanded lane view, but it should not be assumed to be the primary Meridian interface.

The stronger current direction is that the whole interface becomes the orchestrator interface, apart from top-level navigation.

Primary layout concept:

```text
Top:
  Meridian navigation and project/portfolio controls

Main:
  Prime Interface
  progress intention, final plan reviews, unresolved judgment,
  backlog priority, approvals, proof status, next moves

Secondary:
  Tabbed main screen
  Orchestrator Queue tab for Scott/Prime communication
  Non-Orchestrator Queue tab for review/gating/system visibility
```

Builder, Reviewer, and Verifier remain important roles:

- Builder: turns intent into artifacts.
- Reviewer: critiques, improves, and catches issues.
- Verifier: checks proof, tests, completion, and evidence.

But they do not necessarily need permanent primary session panels. A single session/detail panel may be enough, opened only when Scott wants to inspect a specific worker, review, verification run, log, or transfer target.

Additional lanes such as Researcher or Operator may exist, but the main screen should avoid becoming a wall of sessions. Extra sessions can live behind queues, tabs, drawers, filters, or harness-specific views.

Prime should remain the primary place Scott works. Manual prompting inside worker sessions should be exceptional.

The interface should include a persistent control to call up mission objectives at any time. This should show the current Compass-derived objective list with project, stage, risk tier, and next stage.

Working rule for Codex/Prime collaboration: after providing useful information or giving Scott something to copy into Claude, do not simply wait. Start the next reasonable step immediately unless Scott explicitly asks to pause, stop, or only discuss. Scott may copy/read while Codex continues preparing, reviewing, or drafting the next slice.

Claude handoff rule: every build handoff should include a completion protocol for testing, committing to git, pushing to origin, and updating the Meridian Obsidian build notes unless Scott explicitly says the slice is local-only or no-commit.

Default Obsidian locations:

- `G:\My Drive\Aesop Academy\Obsidian\Meridian_Build`
- `G:\My Drive\Aesop Academy\Obsidian\Meridian_Sessions`

When Codex gives Scott a handoff to paste into Claude, it should be presented in a fenced text block so the UI provides a copy button.

When Scott is running two Claude builder sessions simultaneously, Codex handoffs should be addressed explicitly as `Build 1` and `Build 2`.

Build 1 and Build 2 handoffs should avoid editing the same files whenever possible. Each handoff should name its allowed file scope and should remind Claude to commit only its own slice files.

Prime should also own routine review, rejection, retry, and verification loops.

Scott should not be pulled into normal builder/reviewer/verifier coordination. If a review rejects work, Prime should route the correction back to the builder. If tests fail, Prime should retry or assign repair, then rerun review and verification. Dual-lane cognition and multimodal review should reduce the number of issues that require Scott at all.

Human involvement should be reserved for:

- Final plan review and approval.
- Strategic or taste judgments.
- Irreversible, public, financial, account-risking, or policy-sensitive actions.
- Ambiguity that Prime cannot resolve with available memory, knowledge, proof, and model lanes.
- Explicit user preference to inspect or take over.

The main workspace should show routine worker loops as state, not as requests for Scott to manage them.

The orchestrator queue and non-orchestrator queue are not divided by whether Prime can make a decision.

- Orchestrator Queue: the main conversational queue where Scott and Prime communicate.
- Non-Orchestrator Queue: a review/gating prompt window for artifacts, plans, decisions, comparisons, proof, worker outputs, or other items Prime chooses to show Scott.

Prime may place an item in the non-orchestrator queue because the human is the explicit gate, because user visibility is valuable, or because Prime has decided human review is the correct next step. It does not necessarily mean Prime is incapable of deciding.

The orchestrator queue and non-orchestrator queue may be tabs of the same main cockpit screen rather than separate simultaneous panels. This saves space while preserving the distinction.

The non-orchestrator window is still a prompt window. It should allow Scott to respond directly to the artifact, plan, proof, comparison, or gate Prime has placed there, without turning worker-session management back into the primary interface.

Cross-check should be automatic in Meridian, as it became in Polaris.

Automatic cross-check messages and findings should appear in the non-orchestrator prompt window/surface. They are not primary conversational messages from Prime, but they are review/gating material Scott may need to see or respond to.

The name "non-orchestrator" is descriptive but awkward. This surface needs an honest product name that says what it does: review, proof, gates, system findings, and promptable artifacts outside the main Prime conversation.

System-level wake messages such as `Bifrost Go`, `Beacon Go`, and `Relay Go` belong in the non-orchestrator queue/window if displayed as text. Prime's conversational wake message and progress intention belong in the orchestrator queue.

The NASA-style boot sequence may also be audio-first: a spoken readiness sequence such as "Relay Go. Bifrost Go. Beacon Go." As each harness is spoken, corresponding lights or indicators on the cockpit panel should illuminate. This creates the launch-room feeling without requiring all boot messages to occupy persistent conversational space.

## Provisional Harness Names

These names are a holding place for later discussion. They are not final API names or required UI labels.

Preferred current direction is mythic-but-not-mostly-gods: named objects, forces, bridges, records, and roles with strong voice-dictation survivability.

Current favorites:

- Prime: Orchestrator / Local Brain
- Bifrost: UI Harness
- Beacon: Heartbeat / Health Harness
- Echo: Memory Harness
- Atlas: Knowledge / RAG Harness
- Vault: Archive / Records Harness
- Forge or Vulcan: Tool Harness
- Aegis: Proof Harness
- Charter: Policy Harness
- Loom: Workflow Harness
- Compass: Portfolio / Objective Harness
- Relay: Agent / Model Harness
- Groot: Git / Worktree Harness, private/internal favorite
- Grove, Root, or Branch: public-safe Git / Worktree alternatives
- Lens: Browser Harness
- Launch: Release Harness

Earlier pantheon candidates worth keeping:

- Oracle: Orchestrator candidate or brief/recommendation mode
- Athena: Memory Harness
- Thoth: Knowledge / RAG Harness
- Horus: Archive / Records Harness
- Hestia: Heartbeat / Health Harness
- Themis: Policy Harness
- Heimdall: UI Harness
- Odin or Zeus: Orchestrator candidates

Naming rule:

```text
If Scott has to speak it, it must survive dictation.
```

## Open Terms

These terms need more discussion before they become stable:

- Program
- Campaign
- Product
- Business
- Experiment
- Workstream
- Run
- Session
- Thread
- Workspace
- App
- Tool
- System

When a term becomes ambiguous during the build, add it here before encoding it into code.

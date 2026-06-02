# Agentic AI Framework Checklist

**Source:** User-provided "Agentic AI: A Complete Framework" image.
**Purpose:** Convert the framework into a Meridian checklist so Prime can verify that every major agentic-AI concern has an answer, owner, or explicit gap.
**Roadmap role:** This is the entry point into V3. V3 planning starts by resolving this checklist.
**Rule:** Every Meridian answer should map to Prime or a harness. Avoid loose capability names.

Legend:

- `[x]` Answer exists in Meridian architecture or code.
- `[~]` Partial answer exists; needs V2/V3 buildout.
- `[ ]` Gap or later horizon.

## V3 Intake Rule

When V2 closes, Prime must use this checklist as the first V3 intake gate.

Every `[~]` and `[ ]` item must be resolved into one of these outcomes before V3 implementation specs are written:

- **Promote to V3** as a Prime-owned or harness-owned roadmap item.
- **Move earlier** if the item is actually required for V2 autonomy.
- **Park for later** as V4+ or public/product horizon.
- **Reject** as intentionally out of scope for Meridian.

No item leaves this checklist unless it has a named owner: Prime or a harness.

## Key Technologies

- [x] **LLMs** — **Model Harness / Relay Harness:** Provider-neutral model adapter contract exists; primary provider set is Claude + OpenAI + DeepSeek, with DeepSeek direct API now a V2 build requirement.
- [x] **Transformers** — **Model Harness:** Treated as underlying model architecture, not something Meridian builds directly.
- [x] **Attention mechanisms** — **Model Harness / Council:** Treated as underlying model capability; Meridian's equivalent control surface is selective attention through Atlas/Echo retrieval and prompt-budgeted context.
- [x] **Transfer learning** — **Model Harness:** Vendor/model capability, not Meridian-owned runtime behavior.
- [x] **CNNs** — **Model Harness:** Relevant for multimodal/image models later; not a Meridian core build target.
- [x] **LSTMs / recurrent networks** — **Model Harness:** Historical/underlying model capability; no direct Meridian build target.

## AI & ML Foundation

- [x] **Natural language processing** — **Model Harness / Prime:** Primary user/orchestrator interaction surface.
- [x] **Reasoning and problem solving** — **Prime / Council / Aegis:** Council roles, risk-tiered cognition, and proof gates define Meridian's reasoning structure.
- [x] **Supervised learning** — **Model Harness:** Underlying vendor/model training concern; not Meridian-owned.
- [x] **Unsupervised learning** — **Model Harness:** Underlying vendor/model training concern; not Meridian-owned.
- [x] **Reinforcement learning** — **Model Harness:** Underlying vendor/model training concern; Meridian uses feedback loops rather than training models directly.

## Deep Learning Layer

- [x] **Large Language Models** — **Model Harness:** Accessed through adapters and Relay dispatch; DeepSeek is treated as a primary high-volume provider beside Claude and OpenAI.
- [x] **Attention mechanisms** — **Atlas / Echo / Relay:** Meridian's operational answer is ranked retrieval and prompt-budget control.
- [x] **Transfer learning** — **Model Harness:** External model capability.
- [x] **Transformers** — **Model Harness:** External model architecture.
- [x] **CNNs** — **Model Harness:** Future multimodal model support.
- [x] **Recurrent networks / LSTMs** — **Model Harness:** External model architecture.
- [ ] **Deep belief networks** — **No Meridian need identified:** Not relevant to V0-V2 unless a future ML-specific project requires it.

## Gen AI Capabilities

- [x] **Prompt engineering** — **Relay Harness:** Prompt Packet, prompt budget, prompt metrics, and "Relay must not become prompt drag."
- [x] **Tool use and function calling** — **Tool Harness / Relay Harness:** Conceptual harness exists; native tool routing still needs deeper runtime buildout.
- [x] **Hallucination mitigation** — **Aegis / Atlas / Echo:** Proof gates, retrieval, memory, and review lanes are the Meridian answer.
- [~] **Retrieval-Augmented Generation (RAG)** — **Atlas Harness:** Contract exists; runtime retrieval engine is V2 work.
- [~] **Multimodal generation** — **Model Harness / Bifrost:** Not a V2 core item; relevant later for images/audio/video and UI preview artifacts.
- [~] **Personalization** — **Echo Harness:** User/project memory will provide personalization; runtime memory is V2.
- [~] **Speech interfaces (TTS/ASR)** — **Bifrost / Model Harness:** Wake-sequence audio is desired; not built yet.
- [ ] **Audio/music generation** — **Model Harness:** Later horizon only.
- [~] **Code generation** — **Relay / Session Lifecycle Harness:** Current live build lanes prove code-generation orchestration; native session lifecycle is V2.
- [~] **Image generation** — **Model Harness / Bifrost:** Used for diagrams/mockups when useful; not core Meridian runtime yet.
- [ ] **Video generation** — **Model Harness:** Later horizon only.
- [x] **Frameworks and runtimes** — **Bifrost / Meridian Core:** Python core, Bifrost renderer, Electron shell.
- [x] **Output validation** — **Aegis / Codex Reviews:** ProofTrail, review lanes, targeted tests, and Review Console gates.

## Agent Capabilities

- [x] **Agent protocol** — **Prime / Orchestration Harness:** Live queue protocol is the prototype; native domain objects still needed.
- [x] **Agent coordination and communication** — **Prime / Relay / Session Lifecycle:** Live build lanes prove the pattern; V2 makes it native.
- [~] **Multi-agent collaboration** — **Session Lifecycle Harness:** Multiple build and review lanes exist now; native lifecycle/review scaling is V2.
- [x] **State persistence** — **Beacon / FileMap / Obsidian / Git:** Persistent state exists across files, commits, queue logs, and Obsidian.
- [x] **Planning (ReAct, CoT, ToT)** — **Planning Harness / Council:** Council-shaped planning and risk-tiered cognition are Meridian's structured answer.
- [x] **Task scheduling and prioritization** — **Compass / Prime:** Progress intention and queue assignment exist; Prime autonomy selector is V2.
- [x] **Goal decomposition** — **Planning Harness / Compass:** Planning questions, mission objectives, and build slices.
- [x] **Tool orchestration** — **Tool Harness / Relay / Prime:** Conceptual architecture exists; runtime tool catalog needs V2/V3 hardening.
- [x] **Context management** — **Echo / Atlas / Relay:** Prompt budgets now; Echo/Atlas runtime in V2.
- [x] **Human-in-the-loop oversight** — **Review Console / Aegis:** Human gates, plan reviews, approvals, and proof blocking.
- [~] **Memory systems, short-term and long-term** — **Echo / Atlas:** Contracts exist; runtime memory/retrieval is V2.
- [x] **Self-reflection and error recovery** — **Aegis / Codex Reviews / Prime:** Reviews, findings, repairs, restart/resteer docs.
- [~] **Autonomous execution** — **Prime / Session Lifecycle:** Prototype exists through queues; native execution is V2.

## Agent Management

- [x] **Task scheduling** — **Prime / Compass:** Queue scheduling exists; native scheduler is V2.
- [x] **Rollback** — **Git Harness / Aegis:** Git exists as proof/recovery substrate; explicit rollback protocol still needs V2/V3 definition.
- [~] **Self-improvement** — **Prime / Echo / Aegis:** Lessons and review findings feed memory; no self-modifying autonomy without gates.
- [x] **Feedback loops** — **Aegis / Codex Reviews / Review Console:** Review findings and repair routing are active feedback loops.

## Agentic AI Layer

- [~] **Self-improving agents** — **Prime / Echo / Aegis:** Bounded by memory, review, and proof. Not unconstrained self-modification.
- [x] **Rollback mechanisms** — **Git Harness:** Git commits, worktrees, review repair, and explicit no-branch-movement without Prime/Scott.
- [x] **Feedback loops and evaluators** — **Aegis / Codex Reviews:** Current review lanes are evaluators; proof logs become Aegis evidence.
- [~] **Cost and resource management** — **Relay / Model Harness / Bifrost:** Prompt budget and prompt metrics exist; Polaris's Balance button becomes the Meridian provider balance/usage surface for Claude, OpenAI, DeepSeek, and future adapters.
- [~] **Long-term autonomy and goal chaining** — **Prime / Compass / Echo:** Architecture exists; V2 Prime Autonomy builds the first runtime selector. V3 must add a native Goal Runtime / Goal Harness with durable goal objects, objective/status lifecycle, token/time/budget telemetry, continuation/resume policy, proof trail, and completion/blocker/usage-limited semantics.
- [x] **Governance, safety, and guardrails** — **Aegis / Prime Directives / Review Console:** Prime directives, proof gates, human gates, risk tiers.
- [~] **Memory governance and retention policies** — **Echo Harness:** Need explicit retention and memory-edit policy in V2.
- [x] **Observability and tracing** — **Beacon / Bifrost / FileMap / Review Console:** V1 cockpit and proof logs cover the first version.
- [x] **Delegation and handoff protocol** — **Prime / Session Lifecycle / Workflow Sub-Agents:** Live queues prove it; workflow contract is queued.
- [x] **Risk management and constraints** — **Risk Engine / Aegis:** Risk tiers, CognitionPolicy, proof gating.
- [ ] **Agent marketplaces and contracts** — **Federation / Public Product Horizon:** Later V3+ horizon.
- [x] **Failure recovery and replanning** — **Prime Restart/Resteer / Aegis:** Architecture exists; native domain object still needed.
- [~] **Dynamic tooling** — **Tool Harness / Model Harness:** Architecture exists; runtime tool registry/catalog is future work.

## Outputs And Interfaces

- [x] **Code generation** — **Relay / Session Lifecycle:** Live builder lanes are the current proof.
- [x] **Image generation** — **Model Harness / Bifrost:** Available as an external capability; not core runtime.
- [ ] **Video generation** — **Model Harness:** Later horizon.
- [x] **Frameworks and runtimes** — **Meridian Core / Bifrost:** Python package plus Electron cockpit.
- [x] **Output validation** — **Aegis / Codex Reviews:** Tests, proof logs, repair routing, review gates.
- [~] **Speech/audio interfaces** — **Bifrost:** Wake sequence audio desired, not built.

## Governance And Future

- [x] **Governance and safety guardrails** — **Aegis / Prime Directives / Review Console.**
- [~] **Memory governance and retention** — **Echo Harness:** Needs explicit V2 contract/runtime policy.
- [x] **Observability and tracing** — **Beacon / Bifrost / Review Console / FileMap.**
- [x] **Delegation and handoff protocol** — **Prime / Session Lifecycle / Workflow Sub-Agents.**
- [x] **Risk management and constraints** — **Risk Engine / Aegis / CognitionPolicy.**
- [ ] **Agent marketplaces and contracts** — **Federation/public ecosystem horizon.**
- [x] **Failure recovery and replanning** — **Prime Restart/Resteer.**
- [~] **Dynamic tooling** — **Tool Harness:** Needs runtime registry and UI visibility.

## Meridian Coverage Summary

- [x] **Strongly answered now:** Prime, Relay, Aegis, Review Console, Beacon, FileMap, Bifrost V1 cockpit, risk-tiered cognition, review lanes, proof logs, prompt budget, model adapter boundary.
- [~] **V2 core build:** Echo memory runtime, Atlas retrieval runtime, Prime autonomy selector, Session Lifecycle state/commands, workflow sub-agent contract, Bifrost V2 extensions, V2 progress tracker.
- [ ] **Later horizon:** federation/multi-user runtime, marketplace/contracts, video/audio generation, public packaging/account strategy, vector DB, dynamic tool marketplace.

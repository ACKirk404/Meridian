# Meridian Capabilities

This file is a quick recall sheet for the major Meridian capabilities and product claims we are defining.

It is intentionally plain language. Use it when explaining why Meridian is different or when remembering the name of a concept.

## Prime

Prime is Meridian's orchestrator/local brain.

Prime is the central reference line for the system: it establishes position, interprets state, coordinates harnesses, and decides what should move next.

## MISSION.md

`MISSION.md` is Prime's first authority file.

Prime wakes by reading the mission file before it acts. The mission file is the launch protocol: it tells Prime what to follow, which harnesses to call, and what immutable rules apply to the run.

## Progress Intention

Progress intention is how Prime explains meaningful work before doing it.

It should say which project Prime intends to advance, what stage the work is in, why it is prioritized, how many sessions or lanes it expects to use, and what user gate may be needed.

## Risk-Tiered Dual-Lane Cognition

Risk-tiered dual-lane cognition is Meridian's decision engine.

Prime should not depend on a single model pass for meaningful decisions. For higher-risk work, Relay should produce two independent cognition lanes, Prime should compare them, and Aegis should validate proof where needed.

The system should be dynamic. Prime can change risk tiers as the situation changes, which changes the decision process more deeply than simply changing models.

The interface should visualize the active tier, why Prime selected it, and what requirements are active: single lane, dual lane, Aegis proof, or human gate.

## The Council

The Council is Prime's structured internal deliberation system.

When Prime faces a decision, it does not just pass a prompt to a model and accept the output. The Council gives Prime named cognitive positions to consider before acting: Analyst, Devil's Advocate, Pragmatist, Contrarian, Expansionist, and Chairman.

The Council is risk-tier aware. Low-risk tiers engage fewer voices; high-risk tiers invoke the full Council before Prime commits. This is deterministic — the Council composition for a given tier is fixed, not generated.

The Council is consumed by Relay (each RelayRoute carries a CouncilPlan for its tier) and by Compass (ProgressIntention surfaces the active Council plan alongside the risk tier). This means Prime's routing, deliberation, and intention surfaces are all Council-aware out of the box.

## Relay

Relay is the Agent / Model Harness.

Prime does not talk directly to Claude, OpenAI, OpenRouter, or local models. Prime talks to Relay, and Relay manages model roles, adapters, sessions, steering, and dual-lane cognition.

Relay carries a CouncilPlan on every routing decision so Prime knows which Council voices to apply before dispatching.

**Relay Must Not Become Prompt Drag.** Relay should make model sessions steerable, observable, and coordinated without bloating prompts, slowing response time, or making the worker experience worse than using the vendor app directly. Default worker prompts should be minimal. Context injection should be selective and task-specific. Heavy orchestration process belongs in Prime, Aegis, Echo, Atlas, or the Review Console — not automatically inside every worker message.

## Echo

Echo is the Memory Harness.

Echo remembers decisions, preferences, open loops, project context, lessons learned, and how Scott tends to think about recurring situations.

## Persistent Prime Context

Prime should not lose context just because worker/model sessions run out of tokens.

Meridian backstops fragile session context with Echo memory, Atlas knowledge/RAG, and eventually deeper search. Prime can inject focused memory into sessions, summarize important state back into memory, and reset polluted or bloated sessions without losing continuity.

The goal is that Prime's effective memory is persistent and queryable, not bounded by a single model context window.

## Meridian Federation

Meridian should eventually support connecting one Meridian instance to another.

The goal is not just multi-user chat. It is Prime-to-Prime collaboration: shared project state, plans, artifacts, proof, and progress intentions, while each user keeps private memory, local harness state, permissions, and authority chains compartmentalized.

## Beacon

Beacon is the Heartbeat / Health Harness.

Beacon reports liveness, stale sessions, failed harnesses, active monitors, and health signals. Beacon data belongs mostly in system views unless it affects Prime's progress intention.

## Build And Harness Maturity

Meridian should track an overall build number plus per-harness build numbers and maturity states.

Build number tells which implementation generation is present. Maturity tells how trustworthy, complete, proven, and operational that harness is. They are related but not the same.

## Aegis

Aegis is the Proof Harness.

Aegis validates claims with evidence: tests, screenshots, logs, checks, review results, and completion proof.

## Bifrost

Bifrost is the UI Harness.

It is the bridge between Scott and Meridian. Scott enters through Bifrost, but works primarily with Prime.

## Orchestrator Queue

The Orchestrator Queue is the communication lane where Scott and Prime talk.

It is not a worker-session wall. It is the main conversational surface for intention, judgment, decisions, and outcomes.

## Non-Orchestrator Queue

The Non-Orchestrator Queue is the review/gating lane.

Prime places artifacts, plans, comparisons, proof, worker outputs, and approval items here when it wants Scott to see or gate them.

## Prime-Centric Workspace

Meridian should invert the Polaris worker-card model.

The whole interface becomes Prime's working surface. Worker sessions become inspectable machinery behind the orchestrator, not the main place Scott works.

## Builder / Reviewer / Verifier

Builder, Reviewer, and Verifier are core work roles, not necessarily permanent screen panels.

Prime coordinates these roles through Relay and worker sessions. Scott should normally see their results only when Prime decides review, approval, or visibility is valuable.

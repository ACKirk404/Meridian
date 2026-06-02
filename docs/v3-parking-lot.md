# Meridian V3 Parking Lot

**Status:** Not active scope — ideas only
**Owner lane:** Build 4 (Opus high-level thinking)
**Source:** V0/V1/V2 planning sequence; Scott's product direction questions
**Purpose:** Hold V3-horizon ideas without contaminating V0 Prime core, V1 Bifrost cockpit, or V2 Echo/Atlas/Prime autonomy execution.
**V3 entry point:** `docs/agentic-ai-framework-checklist.md`

---

## V3 Is Not Active Scope

V3 planning does not begin until V2 is complete. V2 makes Prime genuinely smarter and more autonomous — persistent memory via Echo, context retrieval via Atlas, autonomous multi-session orchestration, and model harness hardening. V3 assumes that foundation exists and asks what Meridian becomes when it is stable, capable, and ready to face the outside world.

**Do not pull effort toward V3 items during V0, V1, or V2 build.**

---

## When V3 Begins

V3 trigger: V2 closes. Prime can orchestrate work across days without Scott prompting it, retrieves context reliably, and passes proof gates autonomously. At that point, the question shifts from "can Prime do real work?" to "who else can use this, and how?"

---

## V3 Entry Point

V3 starts with the Agentic AI Framework Checklist.

Before V3 receives implementation specs, Prime and the review lanes must walk `docs/agentic-ai-framework-checklist.md` and turn every `[~]` or `[ ]` item into one of four outcomes:

- **Promote to V3:** The item becomes a harness-owned V3 roadmap item.
- **Move earlier:** The item is required for V2 autonomy and moves into `docs/v2-progress-tracker.md` or the relevant V2 contract.
- **Park for later:** The item remains horizon-only and is explicitly tagged V4+ or public/product horizon.
- **Reject:** The item is not a Meridian concern and stays documented as intentionally out of scope.

The checklist is not just a reference image transcription. It is the V3 coverage gate: V3 is the release where Meridian is checked against the broader agentic-AI framework and decides what kind of complete system it intends to become.

Every promoted item must name Prime or a harness owner before it can leave the checklist.

---

## V3 Candidate Themes

| Theme | Description |
|---|---|
| Public repo / release | Clean, documented public face of Meridian — README, contribution model, release process |
| Marketed tool | Positioning, naming, landing page — what is Meridian to someone who has never heard of it? |
| Provider compliance modes | HIPAA, SOC 2, GDPR-aware operation modes behind the Model Harness |
| Hosted / cloud packaging | Meridian as a hosted service: account, billing, multi-tenant isolation |
| Team / business workflows | Multi-user approval flows, team-scoped Prime directives, business lane ownership |
| Native goal runtime | Durable goal objects, status lifecycle, budget telemetry, continuation/resume behavior, proof trail, and completion/blocker semantics owned by Prime/Compass |
| Multi-user polish | V1/V2 federation becomes production-grade: identity, roles, audit trail |
| Distributed Meridian networks | Connect Meridian instances across users/orgs; federated Prime coordination |
| Plugin / extension ecosystem | Third-party harnesses, community Prime skills, external tool adapters |

---

## Parking Lot Items

Every item below must be owned by Prime or a named harness. Items without an owner do not belong here.

### Prime

- [ ] Prime directive versioning — Prime tracks which directive version it is operating under; supports rollback and audit
- [ ] Prime autonomy dial — configurable human-in-loop ratio; V2 Prime can run at full autonomy or stepped autonomy depending on trust level
- [ ] Native Goal Runtime / Goal Harness - Prime and Compass own durable goal objects with objective text, status lifecycle (`active`, `complete`, `blocked`, `usage-limited`), token/time/budget telemetry, continuation/resume policy, proof trail, and completion/blocker semantics so Meridian can coordinate long-running work without relying on external Codex thread goals
- [ ] Multi-Prime coordination — two Prime instances coordinating on a shared project without conflicting
- [ ] Polaris backlog absorption — Prime imports the full Polaris backlog into Meridian's harness-owned backlog model after Meridian is stable enough to become the system of record

### Bifrost Harness

- [ ] Public-facing Bifrost panel — read-only status view for stakeholders who are not Prime operators
- [ ] Bifrost mobile surface — lightweight status and gate-approval on mobile; same domain objects, smaller UI
- [ ] Team Bifrost — shared cockpit for multi-user orgs; role-based panel visibility

### Model Harness

- [ ] Provider compliance modes — HIPAA/SOC 2/GDPR-aware prompt routing; sanitization policies behind the Model Harness adapter interface
- [ ] Model harness metering — token accounting, cost attribution, budget alerts per lane and per Prime directive
- [ ] Offline / local model adapter — route to local models (Ollama, llama.cpp) when cloud access is restricted or cost is a constraint

### Federation Harness

- [ ] Cross-instance Relay dispatch — dispatch a session to a remote Meridian instance; receive proof back
- [ ] Federated Review Console — gate items from a remote Meridian instance appear in the local Bifrost
- [ ] Identity and trust model — how Meridian instances identify themselves to each other; what each can request

### Release Harness

- [ ] Public repo hygiene — `.gitignore`, `CONTRIBUTING.md`, `LICENSE`, `SECURITY.md`, sanitized history
- [ ] Release pipeline — semantic versioning, changelog generation, artifact packaging
- [ ] Hosted packaging — Docker, cloud-deploy templates, one-click install
- [ ] Community harness registry — third-party harnesses discoverable and installable by name
- [ ] Polaris migration checklist — audit Polaris backlog, archived sessions, lessons, and docs before final cutover so no valuable work is stranded

### Aegis Harness

- [ ] Compliance proof trail — Aegis records provenance for compliance-sensitive dispatches; exportable for audit
- [ ] Proof trail retention policy — configurable TTL for proof records; purge / archive at end of project

---

## Rules for Adding to This List

1. Every item names an owner harness. No loose feature names.
2. V3 items do not get implementation specs until V2 closes.
3. Items that turn out to be needed for V2 Prime autonomy get moved to `docs/v2-horizon-plan.md`, not implemented from here.
4. `docs/agentic-ai-framework-checklist.md` is the first V3 intake document. Do not start a V3 roadmap without resolving its partial and gap items.
5. This list is reviewed once at the V2 planning kickoff. Items that do not survive that review are removed.

---

## Cross-References

- V0/V1 tracker: `docs/v0-v1-progress-tracker.md`
- V1 capability plan: `docs/v1-capability-plan.md`
- V2 horizon: `docs/v2-horizon-plan.md`
- V3 entry checklist: `docs/agentic-ai-framework-checklist.md`
- Prime orchestration state model: `docs/prime-orchestration-state-model.md`

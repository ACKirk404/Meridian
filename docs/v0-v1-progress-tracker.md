# Meridian V0/V1 Progress Tracker

**Purpose:** Give Prime, Codex, and Scott a countable progress view. This is the canonical tracker for progress reports: totals first, details second.

**Tracker rule:** Every item is tracked as either a Prime build or a harness build. Do not add loose feature names without naming the owning harness.

## V0 Progress Tracker

**Scope source:** `docs/v0-build-readiness-map.md` gate summary.

| Status | Count | Percent |
|---|---:|---:|
| Built core gate items | 6 | 100% |
| Supporting slices in review | 0 | n/a |
| Needs build core gate items | 0 | 0% |
| Total V0 core gate items | 6 | 100% |

### Built

- [x] **Prime + Mission Boot Harness:** `prime_wake()` CLI - built in `e800c03`; Prime can load mission identity and emit wake status.
- [x] **Prime + Review Console Harness:** `route_to_console()` + `prime_console` / `prime_status` CLI - built in `989366f`, repaired in `9c3e1a3`; Prime can place and show console items.
- [x] **Prime + Review Console Harness:** `prime_approve <item-id>` CLI - implemented across `9d38314` / `d687b7f`; targeted CLI tests pass.
- [x] **Relay Harness:** `relay_executor.py` provider-neutral executor skeleton - built in `190e527`; executor accepts an injected model-call function without vendor code.
- [x] **Relay Harness + Model Harness:** real provider-neutral model/API dispatch path - adapter contract built in `653488b`, registry/dispatch bridge built in `0560eb4`, env-gated HTTP JSON transport built in `869faa4`, hardened in `f353c8d`.
- [x] **Beacon Harness:** `beacon.py` file-backed liveness checks - built in `b575677`; queue/sentinel freshness now produces `Heartbeat` objects.
- [x] **Relay Harness + Aegis Harness:** pre-dispatch proof gate enforcement for tier-3/4 lanes - built in `7c75f43`; blocking proof evidence prevents high-risk dispatch before model calls.

### In Progress / Review

- [x] **Planning Harness + Council:** Council-shaped automated planning harness - built in `2c90247`, grill-with-docs anchor `0f0ecbd`; reviewed and cleared by Codex Reviews A addendum.

### Needs Build

- [x] **Relay Harness:** V0 core model/API dispatch path is built at the provider-neutral HTTP transport level. Vendor-specific endpoint presets and richer response parsing remain post-V0 hardening, not a V0 core gate.

## V0 Review Queue

- [ ] Review A Round 3 - Build 1 `190e527` and Build 2 `d821106`.
- [ ] Review B Round B3 - Build 4 `fd9224d`, Build 5 `a412e90`, and Build 3 FileMap follow-up status.

## V1 Planning Tracker

**V1 definition:** V1 is the cockpit UI release. It turns the V0 CLI/domain capabilities into something Scott can see, steer, and operate. V1 is primarily Bifrost cockpit UI plus wiring existing Meridian capabilities into that UI.

**Explicitly out of V1:** Echo memory engine, Atlas/RAG engine, multi-user/multi-Meridian federation, and public/account adapter strategy. Those remain future capability tracks after the cockpit exists.

| Status | Count | Percent |
|---|---:|---:|
| Built | 0 | 0% |
| In Progress | 3 | 33% |
| Planned / designed | 4 | 44% |
| Needs planning | 2 | 22% |
| Total V1 cockpit items | 9 | 100% |

### Planned / Designed

- [ ] **Bifrost Harness:** cockpit shell - design briefs exist; no UI code.
- [ ] **Bifrost Harness + Aegis Harness:** configurable progress/proof surface - brief built in `a412e90`.
- [ ] **Bifrost Harness:** harness dashboard - brief built in `7c34566`.
- [ ] **Prime + Review Console Harness:** status / review console CLI bridge - brief built in `fd9224d`.

### In Progress

- [ ] **Bifrost Harness:** first static cockpit scaffold - assigned to Build 5 on 2026-05-31 00:42 -06:00.
- [ ] **Prime + Bifrost Harness:** cockpit snapshot/event domain shape - assigned to Build 1 on 2026-05-31 00:42 -06:00.
- [ ] **Bifrost Harness + Prime:** live-data integration contract - assigned to Build 4 on 2026-05-31 00:42 -06:00.

### Needs Planning

- [ ] **Bifrost Harness:** live UI implementation - cockpit shell, Prime conversation, queue panel, review console, progress surface.
- [ ] **Bifrost Harness + Prime:** UI integration wiring - plug V0 Mission/Wake, Review Console, Beacon status, Relay session state, and Aegis proof/gate state into the cockpit.

## Reporting Format

Every progress report should begin with:

```text
V0: <built>/<total> built (<percent>), <in_progress> in progress/review, <remaining> left.
V1: <built>/<total> built (<percent>), <planned> planned/designed, <unplanned> still needs planning.
```

Then list:

- Built
- In Progress
- Needs Build
- Review Queue
- Blockers/Risks
- Next Coordinator Action

When listing items, prefix each with the owner:

- **Prime**
- **Bifrost Harness**
- **Relay Harness**
- **Aegis Harness**
- **Beacon Harness**
- **Compass Harness**
- **Review Console Harness**
- **Echo Harness**
- **Atlas Harness**
- **Model Harness**
- **Session Lifecycle Harness**
- **Federation Harness**

## V2 Horizon

**V2 trigger:** Start detailed V2 planning after V1 cockpit scope is locked.

**V2 direction by owner:** Echo Harness memory, Atlas Harness retrieval, Prime autonomy, Model Harness hardening, Session Lifecycle Harness, and eventual Federation Harness.

**Canonical horizon doc:** `docs/v2-horizon-plan.md`

# Meridian V0/V1 Progress Tracker

**Purpose:** Give Prime, Codex, and Scott a countable progress view. This is the canonical tracker for progress reports: totals first, details second.

**Tracker rule:** Every item is tracked as either a Prime build or a harness build. Do not add loose feature names without naming the owning harness.

## V0 Progress Tracker

**Scope source:** `docs/v0-build-readiness-map.md` gate summary.

| Status | Count | Percent |
|---|---:|---:|
| Built core gate items | 3 | 50% |
| Supporting slices in review | 1 | n/a |
| Needs build core gate items | 3 | 50% |
| Total V0 core gate items | 6 | 100% |

### Built

- [x] **Prime + Mission Boot Harness:** `prime_wake()` CLI - built in `e800c03`; Prime can load mission identity and emit wake status.
- [x] **Prime + Review Console Harness:** `route_to_console()` + `prime_console` / `prime_status` CLI - built in `989366f`, repaired in `9c3e1a3`; Prime can place and show console items.
- [x] **Prime + Review Console Harness:** `prime_approve <item-id>` CLI - implemented across `9d38314` / `d687b7f`; targeted CLI tests pass.
- [x] **Relay Harness:** `relay_executor.py` provider-neutral executor skeleton - built in `190e527`; executor accepts an injected model-call function without vendor code.

### In Progress / Review

- [ ] **Relay Harness + Aegis Harness:** Relay execution summary to Aegis proof trail - built in `0e990df`; awaiting Codex Reviews C Round C2.

### Needs Build

- [ ] **Relay Harness:** real model/API dispatch through the existing Relay executor skeleton.
- [ ] **Beacon Harness:** `beacon.py` - `check_harness_liveness()` from flat-file or sentinel.
- [ ] **Relay Harness + Aegis Harness:** pre-dispatch proof gate enforcement for tier-3/4 lanes.

## V0 Review Queue

- [ ] Review A Round 3 - Build 1 `190e527` and Build 2 `d821106`.
- [ ] Review B Round B3 - Build 4 `fd9224d`, Build 5 `a412e90`, and Build 3 FileMap follow-up status.

## V1 Planning Tracker

**V1 definition:** V1 is the cockpit UI release. It turns the V0 CLI/domain capabilities into something Scott can see, steer, and operate. V1 is primarily Bifrost cockpit UI plus wiring existing Meridian capabilities into that UI.

**Explicitly out of V1:** Echo memory engine, Atlas/RAG engine, multi-user/multi-Meridian federation, and public/account adapter strategy. Those remain future capability tracks after the cockpit exists.

| Status | Count | Percent |
|---|---:|---:|
| Built | 0 | 0% |
| Planned / designed | 4 | 67% |
| Needs planning | 2 | 33% |
| Total V1 cockpit items | 6 | 100% |

### Planned / Designed

- [ ] **Bifrost Harness:** cockpit shell - design briefs exist; no UI code.
- [ ] **Bifrost Harness + Aegis Harness:** configurable progress/proof surface - brief built in `a412e90`.
- [ ] **Bifrost Harness:** harness dashboard - brief built in `7c34566`.
- [ ] **Prime + Review Console Harness:** status / review console CLI bridge - brief built in `fd9224d`.

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

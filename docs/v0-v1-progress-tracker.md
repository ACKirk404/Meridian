# Meridian V0/V1 Progress Tracker

**Purpose:** Give Prime, Codex, and Scott a countable progress view. This is the canonical tracker for progress reports: totals first, details second.

## V0 Progress Tracker

**Scope source:** `docs/v0-build-readiness-map.md` gate summary.

| Status | Count | Percent |
|---|---:|---:|
| Built | 1 | 17% |
| In progress / review | 2 | 33% |
| Needs build | 3 | 50% |
| Total V0 gate items | 6 | 100% |

### Built

- [x] `relay_executor.py` provider-neutral executor skeleton - built in `190e527`; Review A pending, but the V0 gate item now exists in code.

### In Progress / Review

- [ ] `route_to_console()` + `prime_console` / `prime_status` CLI - architecture brief built in `fd9224d`; runtime implementation still needed.
- [ ] Relay gate wire in `relay_executor.py` - depends on the built executor plus Aegis `ProofTrail`; implementation still needed.

### Needs Build

- [ ] `prime_wake()` in `cli.py` - reads mission, builds `WakeBrief`, emits Go-call console items.
- [ ] `beacon.py` - `check_harness_liveness()` from flat-file or sentinel.
- [ ] `prime_approve <item-id>` CLI - Scott disposes of Review Console gate items.

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

- [ ] Bifrost cockpit shell - design briefs exist; no UI code.
- [ ] Configurable progress/proof surface - brief built in `a412e90`.
- [ ] Harness dashboard - brief built in `7c34566`.
- [ ] Prime status / review console CLI bridge - brief built in `fd9224d`.

### Needs Planning

- [ ] Bifrost live UI implementation - cockpit shell, Prime conversation, queue panel, review console, progress surface.
- [ ] UI integration wiring - plug V0 Mission/Wake, Review Console, Beacon status, Relay session state, and Aegis proof/gate state into the cockpit.

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

## V2 Horizon

**V2 trigger:** Start detailed V2 planning after V1 cockpit scope is locked.

**V2 direction:** memory, retrieval, stronger Prime autonomy, model harness hardening, session lifecycle, and eventual multi-Meridian/multi-user federation.

**Canonical horizon doc:** `docs/v2-horizon-plan.md`

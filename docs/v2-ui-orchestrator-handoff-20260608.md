# V2 UI Orchestrator Handoff - 2026-06-09

This handoff replaces the stale 2026-06-08 snapshot. The active Meridian UI lane
is much farther along now and should start from the live checklist/test posture
below, not the older `215/305` count.

## Current State

- Branch: `main`
- Remote: `origin/main`
- Working tree: intentionally dirty with active UI-lane edits; do not reset or
  absorb unrelated backend/doc movement by accident.
- Current checklist count: `305/305 wired` (`100.0%`), `0 partial`,
  `0 planned`, `0 blocked`.
- Active goal remains open: continue wiring honest Electron UI behavior to
  reviewed Meridian backend evidence without inventing control authority.

## Product Authority

- The Meridian UI is the Electron app.
- Root `index.html` is the current renderer source loaded by
  `electron/main.js`.
- Edits to `index.html` are edits to the visible Meridian app.
- `bifrost/preview.html` is proof output only, not the operating UI.

Launch the actual app with:

```powershell
npm start
```

## Main/Coordination Notes

- Backend promotions landed after the original handoff. Refresh against
  `origin/main` before any UI promotion.
- Recent backend-only main movement included:
  - `2e680b6f1` - backend aegis snapshot/doc lease closeout
  - `f4f14b201` - backend prime beacon lease closeout
- Shared checkout rule still applies: do not step on backend-owned files or
  fold ledger/doc lease churn into UI commits unless intentional.
- Re-read `docs/main-write-coordination-ledger.md` before any push or main-write
  coordination.

## Verification Baseline

Current focused proof loop:

```powershell
python -m pytest tests\test_bifrost_cockpit.py -q
node -e "const fs=require('fs'),vm=require('vm'); const html=fs.readFileSync('index.html','utf8'); const scripts=[...html.matchAll(/<script[^>]*>([\s\S]*?)<\/script>/gi)].map(m=>m[1]); scripts.forEach((s,i)=>new vm.Script(s,{filename:'index.html#script'+(i+1)})); console.log('checked '+scripts.length+' scripts');"
git diff --check
```

Latest observed results:

- `tests/test_bifrost_cockpit.py`: `534 passed`
- Embedded script parse: `checked 1 scripts`
- `git diff --check`: recurring CRLF warnings only

## Current Tail Shape

Exact remaining counts are guarded by tests in
`tests/test_bifrost_cockpit.py`. The intended live tail is:

- Planned: none
- Partial: none

## What Changed Since The Old Handoff

Rows that were promoted or materially clarified after the old snapshot include:

- `SET9`, `SET12`, `SET13`, `SET18`
- `XCK8`
- `SET17` promoted to a wired local-posture-defaults slice
- `BAK4`, `BAK5`, `BAK6`
- `BAK11`
- `XCK4`, `XCK5`, `XCK10`
- `ROU9`
- `ARC2`, `ARC3`, `ARC8`
- `VOC1`, `VOC5`, `VOC6`
- `VOC10` moved to honest `partial`
- `VOC7` moved to honest `partial`
- `BAK3`, `BAK7`, `BAK9`, `BAK10`
- `BR7` moved to honest `partial`

Recent UI-owned renderer improvements after this handoff was first refreshed:

- Backlog now exposes display-only filter/action summaries for the current
  reviewed candidate set.
- Backlog filter summary now makes active Compass-project inheritance and the
  missing dedicated project/priority controls explicit.
- Backlog now also exposes a dedicated mutation-action posture section so edit /
  approve / defer / convert / archive / owner / priority controls are plainly
  marked unavailable.
- Backlog filter state now persists per active project/user in
  `meridian.backlog-filter.v1`, so query/state/severity/response/owner/blocked
  posture survives surface reloads without implying any durable backlog-query
  backend or mutation authority.
- Crosscheck now exposes display-only repair-routing, approval, recent-ledger,
  review-action, and stop-condition summaries for the current reviewed finding
  set.
- Crosscheck now also exposes a dedicated Crosscheck run posture so current
  reviewed scope, gating, proof blockers, and explicit run-control
  unavailability are visible without implying a run backend.
- Crosscheck review posture now also makes explicit waive/dismiss-control
  unavailability and history-mutation boundaries visible for the filtered
  findings set.
- Crosscheck repair/action posture now also makes explicit rerun-control
  unavailability and current repair/proof-blocking posture visible for the
  filtered findings set.
- Backlog mutation posture now also carries an explicit convert-to-task
  unavailable slice over the filtered reviewed candidate set, without implying
  task creation authority.
- Backlog mutation posture now also carries an explicit archive-action
  unavailable slice over the filtered reviewed candidate set, without implying
  backlog archive authority.
- Routines now also expose a dedicated Routine control posture so create,
  enable/disable, and run-now unavailability are explicit without implying any
  scheduler or automation control backend.
- Backlog mutation posture now also makes create-item unavailability explicit,
  so intake remains visibly deferred without implying a backlog ingest route.
- Backlog candidate source now also makes external-import unavailability
  explicit, so reviewed candidate-source visibility does not imply a Polaris
  import path.
- Backlog candidate source now also surfaces the reviewed queue summary,
  response-authorized posture, and observation timestamp from the Review
  Console snapshot, so the backlog surface exposes more of the backend review
  contract instead of stopping at source/version plus pending-count posture.
- Backlog candidate source now also surfaces reviewed raw-worker-chat visibility
  and execution-controls-visible posture from the same Review Console snapshot,
  so the backlog panel exposes more of the upstream display contract instead of
  implying a narrower queue metadata surface than the backend actually provides.
- Backlog candidate source now also surfaces the shared Review Console harness
  identity and explicit display-only posture, so the backlog panel more clearly
  reads as a filtered projection of the reviewed queue snapshot instead of a
  separate authority-owning backlog backend.
- Backlog mutation posture now also makes project/initiative-link
  unavailability explicit, so active-project framing does not imply scope-link
  authority.
- Routines now expose compact failure summary, Prime routine review posture,
  Prime routine action posture, and routine-history summary ahead of the
  detailed posture grids.
- Archive now exposes compact command-preview, command-gate, reopen/rerun, and
  transcript-access/action summaries ahead of the detailed posture grids.
- Session close/archive proof now also surfaces the reviewed bridge summary
  text as its own source-level summary section, so the archive surface exposes
  the backend's compact display-safe description alongside the more specific
  archive, transcript, reopen/rerun, and proof posture summaries.
- Voice now exposes visible top-icon status copy, backend-sourced disabled
  reasons, compact voice-input/voice-output summaries, and a dedicated Voice
  intent summary for display-only voice controls.
- Voice I/O now also surfaces the reviewed bridge summary text, so the
  renderer exposes the backend's compact display-safe description alongside
  the detailed voice state/posture grids.
- Voice input now also exposes a dedicated input-action posture so push-to-talk,
  dictation draft, spoken-submit, and correction actions are plainly marked
  unavailable.
- Voice now also exposes a dedicated interrupt posture so speaking/output state
  and missing interrupt control are explicit without implying a stop route.
- Voice now also exposes a dedicated Voice selection posture so output-mode
  state and missing voice-list/preference authority are explicit without
  implying a real voice picker.
- Voice input posture is now explicit enough to keep speech-to-text honest as a
  display-only dictation-status slice without implying transcript output.
- Models/Balance now expose a dedicated display-only Prime/Relay Auto-routing
  posture from existing Relay evidence, provider-balance, and Relay-logic
  snapshots, making the current gate and execution boundary explicit without
  enabling Auto dispatch.
- Provider Balance now also exposes its reviewed summary text, explicit
  `mutation_authorized` posture, and per-provider prompt-delta fields, so the
  shared UI matches more of the reviewed provider-balance contract without
  adding any route or account authority.
- Model Harness backend binding now also surfaces Provider Balance
  `display_only` and `mutation_authorized` posture, so the cross-surface
  dispatch summary makes the upstream no-mutation boundary explicit instead of
  only showing selected-provider/routing-state fields.
- Prime Runtime Logic now also exposes Beacon liveness input from the reviewed
  Prime runtime context, so Prime-visible execution/advisory posture includes
  Beacon source, statuses, observed harnesses, blockers, observation mode, and
  advisory-only authorization state instead of stopping at Aegis/Relay.
- The Prime harness/checklist wording now reflects that Beacon advisory posture
  is part of the visible Prime runtime packet, not only a backend-internal
  input.
- Prime Runtime now also surfaces the reviewed bridge summary text as its own
  source-level summary section, keeping that compact backend description
  separate from the larger Runtime truth map block and aligning Prime with the
  other summary-bearing renderer panels.
- Release autonomy now also surfaces the reviewed bridge summary text as its
  own source-level summary section, so the Release harness exposes the backend's
  compact display-only description alongside posture, authority-boundary, and
  blocker sections.
- Release autonomy source now also shows the backend-generated timestamp, so
  the Release harness names when that display-only autonomy snapshot was
  produced instead of presenting the release posture as timeless.
- Vulcan now also surfaces per-session pending approval reasons and recorded-at
  timestamps from the reviewed Prime autonomy input instead of only showing a
  coarser permission-summary shell.
- Crosscheck / Review Console now also surfaces the reviewed snapshot
  observation timestamp, so visible review posture names when the current queue
  metadata was observed instead of presenting timeless findings.
- Checklist wording is now tighter around `SET13`, `XCK8`, `XCK10`, and `VOC5`
  so those rows describe the currently proven UI posture without implying
  direct snapshot ownership, durable repair history, or spoken-response
  execution that the renderer does not actually own.
- Voice proof now includes a section-scoped Voice output assertion covering the
  read-aloud/mute display-only boundary, keeping the `VOC5`/`VOC6` wording tied
  to the exact reviewed renderer block instead of broader whole-surface string
  presence.
- Relay evidence and Aegis logic now also surface their reviewed bridge summary
  text as explicit source-level summary sections, so those panels expose the
  backend's compact advisory/proof description alongside the more detailed
  intent, packet, dispatch, and cognition-policy sections.
- FileMap Registry now also surfaces the backend injection summary, so the UI
  exposes the compact context/memory-injection view the FileMap backend already
  produces instead of only raw counts and focus entries.
- Echo Memory, Atlas Retrieval, and FileMap Registry now also surface their
  reviewed bridge summary text as explicit source-level summary sections, so
  those read-only memory/retrieval/registry panels expose the backend's compact
  display-safe description alongside query, hit, and registry-detail sections.
- Echo Memory, Atlas Retrieval, and FileMap Registry source cards now also show
  the reviewed `mutation_authorized` posture from their backend snapshots so
  those panels state their no-write boundary explicitly.
- Goal Runtime and Workflow Dispatch source cards now also show the reviewed
  `mutation_authorized` posture from their backend snapshots so those status
  surfaces state their no-write boundary as explicitly as the other renderer
  panels.
- Goal Runtime now also surfaces the reviewed bridge summary text as an
  explicit source-level summary section, so the runtime continuity surface
  exposes the backend's compact display-safe description alongside the goal,
  continuation-policy, and checkpoint-discipline sections.
- Workflow Dispatch now also surfaces the reviewed bridge summary text, so the
  routines surface exposes the backend's compact status description alongside
  cadence, failure, and Prime review posture.

The checklist/test pair now also enforces:

- exact remaining row ids and counts
- explicit missing-authority wording for all planned rows
- visible-posture plus missing-authority wording for all partial rows

## Frontend-Owned Near-Term Work

The easy overclaims are mostly gone. Remaining UI-lane work is now mostly:

- harvesting honest display-only/backend-backed slices already present in the UI
- tightening wording so visible posture is truthful
- adding small UI-local defaults/filters only when they do not imply backend
  mutation or execution

`SET17` is a good example of the new standard: the UI really does persist
Prime/User session-window defaults (`hidden`, `collapsed`, `pinned`, `size`)
via `meridian.session-window-defaults.v1`, but archive/transfer/rerun and
close/write-through authority remain backend-owned, so the row stays `partial`.
The Settings surface now also explicitly summarizes which defaults are exposed
versus unavailable.

## Backend-Owned Authority Gaps

No rows are still `planned`. The remaining tail is now a single `partial` row,
and it should stay partial until reviewed backend authority/data arrives for
the missing close/write-through execution behavior.

The remaining backend-bound partial is:

- `SK9`: real session close/write-through/Obsidian capture

## Selected Remaining Backend Asks

This is the smallest reviewed backend addition that would let the final
remaining partial row advance without inventing authority:

- `SK9`:
  reviewed close/write-through authority plus any Obsidian capture action and
  archive/session mutation route needed for real close behavior.

If this backend evidence does not arrive, the row should stay `partial`. The
current UI now makes the missing execution/mutation authority
pretty explicit, and overclaiming from display-only posture would no longer be
honest.

## Useful Current Partial Reality

- `BAK4`, `BAK5`, `BAK6`, `BAK11`: backlog now exposes display-only modify /
  approve / reject visibility plus filter summaries over the current reviewed
  candidate set, including explicit active-project inheritance, missing
  project/priority controls, and a dedicated mutation-action posture, but still
  has no edit/approval/reject/query backend authority.
- `XCK4`, `XCK5`, `XCK10`: Crosscheck now exposes read-only repair-routing,
  approval, recent-ledger, and explicit review-action posture over the current
  reviewed queue, but still has no response/run/reroute authority or durable
  history backend.
- `XCK12`: stop-condition alert is now wired as a display-only summary plus
  alert over the current reviewed review/proof blockers.
- `ROU9`: routines now expose compact Prime review/action posture for the
  latest reviewed results, but still have no accept/reroute/retry/escalate
  authority or scheduler backend.
- `ROU8`, `ROU11`: failure handling and routine-history/archive are already
  wired as display-only workflow status slices.
- `XCK10`: recent review ledger is real for the current pending queue with
  UI-local filters, but there is no completed review history or durable repair
  routing history yet.
- `ARC2`, `ARC3`, `ARC8`: archive surface truthfully shows command-preview,
  command-gate, reopen/rerun, and transcript-access/action summaries/posture
  plus blockers, but exposes no live reopen/rerun/raw transcript controls.
- `VOC1`, `VOC5`, `VOC6`: Voice I/O displays reviewed authorization/capture
  posture, visible status copy, disabled controls, compact voice-input /
  voice-output summaries, and explicit input-action unavailability, but does
  not capture or speak audio.
- `VOC7`: Voice I/O now exposes a dedicated display-only interrupt posture over
  reviewed speaking/output state, but still has no speech-stop route or
  transcript-preserving interrupt action.
- `VOC10`: Voice I/O now exposes a dedicated display-only Voice intent summary
  over reviewed `status_call` / `last_intent_ref` metadata, but still has no
  command recognition runtime, preview, or execution path.
- `BR7`: Models/Balance now expose a dedicated display-only Prime/Relay
  Auto-routing posture over reviewed intent, route owner, policy state, lane
  plan, and gate metadata, but Auto is still disabled and there is no
  executable Relay route decision or provider dispatch path.

## Recommended Next Loop

1. Fetch/reconcile with `origin/main` before any promotion attempt.
2. Keep implementation scoped to UI-owned/display-only slices.
3. Preserve the current proof loop:
   - focused `tests/test_bifrost_cockpit.py`
   - embedded `index.html` script parse
   - bridge self-test only when bridge payloads/routes change
   - `git diff --check`
4. If a row needs new backend fields/routes, stop and name the exact missing
   authority instead of filling it in from UI assumptions.

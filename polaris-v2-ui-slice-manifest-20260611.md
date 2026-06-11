# Polaris V2 UI Slice Manifest

Date: 2026-06-11
Workspace: `C:\Users\scott\Code\Meridian`

This file breaks the dirty shared-checkout `305/305 wired` state into concrete
UI-only slices with code-level anchors. It is intended for Polaris
Claude/Haiku/Opus builders to reconstruct from clean `origin/main`, and for
Codex to use as a review checklist against exact candidate hashes.

Base authority:

- promoted `origin/main`: `bd3147658a09de58b526046d0ba8fc7623407181`
- local dirty proof loop:
  - `python -m pytest tests/test_bifrost_cockpit.py -q` -> `534 passed`
  - `node --check scripts/meridian-model-bridge.js` -> passed
  - `node scripts/meridian-model-bridge.js --self-test` -> passed

Primary UI files:

- `index.html`
- `scripts/meridian-model-bridge.js`
- `tests/test_bifrost_cockpit.py`
- `docs/ui-integration-checklist.md`

## Slice A: Settings / Local posture carry-forward

Rows:

- `SET9`
- `SET12`
- `SET13`
- `SET17`

Code anchors in `index.html`:

- `const progressRetentionWindowKey = 'meridian.progress-retention.v1'`
- `renderProgressRetentionWindowLabel`
- `filterRetainedTimestampedItems`
- `data-progress-retention-surface`
- `.harness-screen[data-session-band-side="left"]`
- `meridian.session-band-side.v1`
- `meridian.instrumentation-band.v1`
- `const sessionWindowDefaultsKey = 'meridian.session-window-defaults.v1'`
- `data-session-window-defaults-surface`

Proof anchors in `tests/test_bifrost_cockpit.py`:

- `test_index_settings_surface_controls_progress_retention_window_locally`
- assertions for `SET12`, `SET13`, `SET17`
- assertions around `progress retention window`
- assertions around session-band side and session-window defaults

Review boundary:

- UI-local persistence only
- no backend settings mutation
- no archive/transfer/rerun default mutation
- no queue/review/proof mutation

## Slice B: Voice posture closeout

Rows:

- `VOC1`
- `VOC3`
- `VOC4`
- `VOC5`
- `VOC6`
- `VOC7`
- `VOC8`
- `VOC9`
- `VOC10`

Backend source:

- `/bridge/voice-io`

Code anchors:

- `voiceControlDisabledReason`
- `relaySection('Voice I/O summary'`
- `relaySection('Voice input summary'`
- `relaySection('Voice input action posture'`
- `relaySection('Voice output summary'`
- `relaySection('Voice selection posture'`
- `relaySection('Voice interrupt posture'`
- `relaySection('Voice intent summary'`
- `data-voice-control="read-aloud-status"`

Bridge anchor in `scripts/meridian-model-bridge.js`:

- reviewed voice controls include `read-aloud-status`

Proof anchors:

- `test_index_voice_io_surface_shows_public_setup_guidance_without_voice_mutati...`
- `test_voice_output_surface_keeps_read_aloud_and_mute_display_only`
- checklist assertions for `VOC1`, `VOC5`, `VOC6`, `VOC10`
- text assertions for read-aloud disabled reason, mute disabled reason,
  correction/dictation posture, and display-only boundaries

Review boundary:

- no microphone capture
- no speech output execution
- no mute mutation
- no prompt send
- no command recognition/preview/execution
- no raw prompt/response/history/chat exposure

## Slice C: Crosscheck posture and review queue closeout

Rows:

- `XCK1`
- `XCK2`
- `XCK4`
- `XCK5`
- `XCK6`
- `XCK7`
- `XCK8`
- `XCK9`
- `XCK10`
- `XCK11`
- `XCK12`

Backend sources:

- `/bridge/review-console`
- `/bridge/aegis-logic`
- `/bridge/relay-logic`
- `/bridge/session-close-archive-proof` for evidence handoff target

Code anchors:

- `renderCrosscheckRunPostureSnapshot`
- `renderCrosscheckLaneComparisonSnapshot`
- `relaySection('Recent review ledger summary'`
- `relaySection('Recent review ledger'`
- `relaySection('Repair routing summary'`
- `relaySection('Stop condition summary'`
- `relaySection('Stop condition alert'`
- `Crosscheck evidence handoff`
- `relaySection('Irreversible action gate'`

Proof anchors:

- assertions for `XCK4`, `XCK10`, `XCK12`
- assertions for `Crosscheck evidence handoff`
- assertions for `Recent review ledger`
- assertions for `Repair routing summary`
- assertions for `Compare model lanes`

Review boundary:

- no rerun
- no approval
- no waiver
- no review-event creation
- no route execution
- no raw finding/evidence body exposure

## Slice D: Backlog advisory / display-only posture closeout

Rows:

- `BAK2`
- `BAK3`
- `BAK4`
- `BAK5`
- `BAK6`
- `BAK7`
- `BAK8`
- `BAK9`
- `BAK10`
- `BAK11`
- `BAK12`

Backend sources:

- `/bridge/review-console`
- `/bridge/goal-runtime`
- `/bridge/prime-logic`

Code anchors:

- `relaySection('Backlog candidate summary'`
- `relaySection('Backlog filter'`
- `relaySection('Backlog filter summary'`
- `relaySection('Backlog action posture'`
- `relaySection('Backlog mutation posture'`
- `relaySection('Backlog candidate list'`
- `renderBacklogRecommendationSnapshot`
- `relaySection('Priority order'`
- `relaySection('Prime recommendation'`

Proof anchors:

- assertions for `Priority order`
- assertions for `Prime recommendation`
- checklist assertions for `BAK2`
- assertions that filters are UI-local and priority remains advisory-only

Review boundary:

- no create/edit/approve/deny/defer/convert/link/archive execution
- no backlog queue mutation
- no fake backlog rows

## Slice E: Routine posture / history / review closeout

Rows:

- `ROU1`
- `ROU2`
- `ROU3`
- `ROU4`
- `ROU5`
- `ROU6`
- `ROU7`
- `ROU8`
- `ROU9`
- `ROU10`
- `ROU11`

Backend source:

- `/bridge/workflow-dispatch-status`
- plus reused runtime continuity / quiet mode context

Code anchors:

- `relaySection('Routine list'`
- `relaySection('Routine control posture'`
- `relaySection('Cadence/trigger view'`
- `relaySection('Next run preview'`
- `relaySection('Last run result'`
- `relaySection('Failure handling'`
- `relaySection('Prime routine review summary'`
- `relaySection('Prime routine review posture'`
- `relaySection('Routine archive/history'`
- `relaySection('Routine history retention'`

Proof anchors:

- assertions for `ROU6`, `ROU7`, `ROU8`, `ROU10`
- assertions for routine review posture and routine history
- assertions that configured routines are not faked

Review boundary:

- no scheduler mutation
- no create-routine execution
- no enable/disable mutation
- no run-now execution
- no accept/reroute/retry/escalate action

## Slice F: Archive / close posture closeout

Rows:

- `SK9`
- `ARC1`
- `ARC2`
- `ARC3`
- `ARC4`
- `ARC5`
- `ARC6`
- `ARC7`
- `ARC8`
- `ARC9`
- `ARC10`
- `ARC11`
- `ARC12`
- `CLS1`
- `CLS2`
- `CLS3`
- `CLS4`
- `CLS5`
- `CLS6`
- `CLS7`
- `CLS9`
- `CLS10`
- `CLS11`
- `CLS12`

Backend sources:

- `/bridge/session-close-archive-proof`
- reviewed lifecycle advisory input

Code anchors:

- `relaySection('Session close archive proof summary'`
- `relaySection('Session archive list'`
- `relaySection('Search archived sessions'`
- `relaySection('Archive summary'`
- `relaySection('Restore proof/artifacts'`
- `relaySection('Archive retention'`
- `relaySection('Safe deletion boundary'`
- `relaySection('Archive to knowledge handoff'`
- `relaySection('Close summary'`
- `relaySection('Close permission gate'`
- `relaySection('Orchestrator-led close proposal'`
- `relaySection('Write-through before close gate'`
- `relaySection('Obsidian capture'`
- `relaySection('Archive-on-close option'`

Proof anchors:

- `test_index_session_archive_surface_uses_backend_proof_snapshot`
- `test_archive_surface_exposes_display_only_close_permission_gate`
- `test_archive_surface_exposes_safe_deletion_boundary_without_delete_controls`
- `test_archive_surface_exposes_retention_posture_without_storage_claims`
- `test_archive_surface_exposes_write_through_before_close_gate`
- checklist assertions for `SK9`, `ARC2`, `ARC3`, `CLS4`

Review boundary:

- no close/archive/reopen/rerun execution
- no transcript body exposure
- no delete control
- no retention mutation
- no POST/message route from this surface

## Slice G: Harness / relay / balance closeout

Rows:

- `BAL10`
- `BR7`
- `HMS5`
- `HMS10`
- `HN1`

Backend sources:

- `/bridge/relay-evidence`
- `/bridge/provider-balance`
- `/bridge/relay-logic`
- `/bridge/workflow-dispatch-status`
- `/bridge/prime-logic`

Code anchors:

- `relaySection('Prime/Relay Auto-routing posture'`
- `relaySection('Relay-mediated dispatch posture'`
- `relaySection('Harness diagnostics'`
- Prime runtime logic / Beacon liveness advisory text

Proof anchors:

- assertions for `BR7`
- assertions for `Relay-mediated dispatch posture`
- assertions for `Harness diagnostics`
- assertion for `HN1` Prime runtime logic surface

Review boundary:

- no provider call
- no route mutation
- no payload construction mutation
- no raw artifact exposure

## Candidate Rules For Polaris

Each clean candidate should:

1. start from clean `origin/main`
2. stay path-limited to the four UI files unless a separate reviewed reason
   exists
3. keep implementation, checklist wording, and tests aligned
4. preserve display-only boundaries where backend authority remains advisory

Each candidate should be handed to Codex with:

- branch/worktree
- exact commit hash
- changed files
- checklist count after the candidate
- proof bundle

Minimum proof:

- `python -m pytest tests/test_bifrost_cockpit.py -q`
- `node --check scripts/meridian-model-bridge.js`
- `node scripts/meridian-model-bridge.js --self-test`
- `git diff --check`

# V2 UI Orchestrator Handoff - 2026-06-08

This is the handoff for the next Meridian UI orchestrator session.

## Current State

- Branch: `main`
- Remote: `origin/main`
- Current pushed head: `973b458cf` - `ui: show project scoped skills`
- Main status at handoff creation: clean and aligned with `origin/main`.
- Current UI checklist count: `215/305 wired` (`70.5%`), `4 partial`, `86 planned`, `0 blocked`.
- Active goal remains open: continue Meridian UI development using Codex-only work until the Electron app UI catches up with reviewed backend capabilities, while keeping main clean/conflict-free and promoting only verified UI slices.

## Product Authority

- The Electron app is the Meridian UI.
- Root `index.html` is the current renderer source loaded by `electron/main.js`.
- Edits to `index.html` are edits to the Electron app's visible UI until the renderer is split into smaller source files.
- Do not describe `index.html` as a separate product, old demo, browser-only replacement, or historical artifact.
- `bifrost/preview.html` is generated backend/view-model proof output only.
- Launch the actual Meridian UI with:

```powershell
npm start
```

## Operating Mode

- User explicitly paused after the last pushed slice, then requested this handoff.
- No new UI implementation should continue until the next orchestrator is intentionally resumed.
- Claude/Opus worker availability was previously constrained. If Opus is unavailable, continue with Codex-only direct slices or Codex-only review. Do not spawn worker sessions that require Opus.
- If Opus becomes available and the user wants scaled workers again, implementation workers should run in Opus and code review sessions in Codex.
- The orchestrator controls promotion. Main must stay clean/conflict-free.

## Main Cleanliness Rule

Before any implementation:

```powershell
git status --short --branch
```

Expected clean state:

```text
## main...origin/main
```

If main is dirty, clean it by committing/pushing verified orchestrator work or by explicitly preserving unrelated/user work without reverting it. Do not reset, checkout, or discard user changes unless the user explicitly asks.

## Recent Promoted UI Slices

Latest promoted commits, newest first:

- `973b458cf` - `ui: show project scoped skills`
- `a60aab31c` - `ui: preserve harness draft notes`
- `ae1f44a67` - `ui: scope harness item actions`
- `42b5b2cf7` - `ui: show skills argument schemas`
- `e207b8efe` - `ui: refresh project scoped surfaces`
- `86aa249cf` - `ui: show relay per-call intent`
- `75c50c0a2` - `ui: add skills pinning`
- `3f33d3654` - `ui: show voice privacy indicator`
- `1db8e87fe` - `ui: clarify skills usage examples`
- `f9ca86ee7` - `ui: add skills registry surface`
- `4b60573fd` - `ui: show backlog candidate list`
- `1189d1b3d` - `ui: add backlog task posture`

## Verification Baseline

The latest full verification before handoff:

```powershell
python -m pytest tests\test_bifrost_cockpit.py -q
node --check scripts\meridian-model-bridge.js
node scripts\meridian-model-bridge.js --self-test
git diff --check
```

Latest observed results:

- `tests\test_bifrost_cockpit.py`: `453 passed`
- Bridge syntax check: passed
- Bridge self-test: passed
- `git diff --check`: only recurring CRLF warnings

Useful embedded script parse check:

```powershell
node -e "const fs=require('fs'),vm=require('vm'); const html=fs.readFileSync('index.html','utf8'); const scripts=[...html.matchAll(/<script[^>]*>([\s\S]*?)<\/script>/gi)].map(m=>m[1]); scripts.forEach((s,i)=>new vm.Script(s,{filename:'index.html#script'+(i+1)})); console.log('checked '+scripts.length+' scripts');"
```

## Progress Count Command

```powershell
@'
from pathlib import Path
from collections import Counter
rows=[]
for line in Path('docs/ui-integration-checklist.md').read_text(encoding='utf-8').splitlines():
    if not line.startswith('| '):
        continue
    parts=[c.strip() for c in line.strip().strip('|').split('|')]
    if len(parts) < 5 or parts[0] in {'ID','---'} or set(parts[0]) <= {'-'}:
        continue
    if parts[3] in {'wired','partial','planned','blocked'}:
        rows.append(parts)
c=Counter(row[3] for row in rows)
print({'wired': c['wired'], 'total': len(rows), 'percent': round(c['wired']/len(rows)*100,1), 'partial': c['partial'], 'planned': c['planned'], 'blocked': c['blocked']})
for row in rows:
    if row[3] in {'partial','planned'}:
        print('|'.join(row[:5]))
'@ | python -
```

## Current Partial Rows

These are intentionally not promoted to wired yet:

- `SK9` - Close. Transient surface close is wired; real session close/write-through remains in `CLS-*`.
- `XCK2` - Review findings. Review Console pending items render id/type/severity/title/suggested actions/status, but owner attribution remains deferred and raw item content stays hidden.
- `VOC5` - Read-aloud response. Status/control is visible and disabled; no speech output.
- `VOC6` - Mute output. Status/control is visible and disabled; no mute mutation.

Do not promote these unless the missing backend authority actually exists.

## Remaining Planned Rows

High-level remaining planned groups:

- Settings: `SET1`, `SET3`-`SET18`
- Models/Balance: `MOD5`, `BAL10`
- Backlog: `BAK2`-`BAK12`
- Crosscheck: `XCK1`, `XCK4`-`XCK12`
- Routines: `ROU1`-`ROU11`
- Archive: `ARC1`-`ARC12`
- Close: `CLS1`-`CLS7`, `CLS9`-`CLS12`
- Voice: `VOC1`, `VOC3`, `VOC4`, `VOC7`-`VOC10`
- Harness: `HMS4`, `HMS5`, `HMS10`, `HMS11`
- Auto routing: `BR7`

## Important Boundaries

### Backlog

Current Backlog UI is display-only and backed by:

- `/bridge/review-console`
- `/bridge/goal-runtime`
- `/bridge/workflow-dispatch-status`

Do not promote Backlog mutation rows (`BAK3`-`BAK10`) until a reviewed backlog backend exists. Do not promote `BAK11` unless real fields for project, state, priority, owner, and blocked status are all available. Current Review Console does not honestly provide all of them.

### Crosscheck

Current Crosscheck reads `/bridge/review-console` and `/bridge/aegis-logic`.

Do not add run/approve/dismiss/re-run controls without reviewed execution backends. `XCK2` remains partial because owner attribution is not available.

### Routines

Current Routines surface is continuity/status only through:

- `/bridge/goal-runtime`
- `/bridge/workflow-dispatch-status`

The tests intentionally say workflow snapshots are not configured routine automation. Do not promote routine list/create/enable/run/history rows from workflow status alone.

### Archive/Close

Current Archive/Close proof uses `/bridge/session-close-archive-proof`, but there is no real archive list/storage/reload/run-again/delete backend. Do not promote `ARC*` or `CLS*` live-control rows from proof posture alone.

### Voice

Current Voice I/O is fail-closed display state from `/bridge/voice-io`.

It explicitly sets:

- `microphone_authorized: False`
- `speech_output_authorized: False`
- `read_aloud_authorized: False`
- `controls_disabled: True`

Do not add `getUserMedia`, `SpeechRecognition`, `MediaRecorder`, `AudioContext`, or `speechSynthesis` until a reviewed voice provider/capture backend exists.

### Model/Relay

Relay/Model Harness owns provider/model identity, prompt payload construction, dispatch/fallback behavior, transport gates, provider balance, and telemetry.

Prime/UI may render backend-owned state, but must not create route tables, assemble prompt payloads, enable Auto routing, or infer model-call intent from transcript text.

`MOD9A` is wired through backend-owned `/bridge/relay-evidence per_call_intent`.

### Harness

Generic harness surfaces are display-only unless a reviewed backend snapshot exists for that harness.

Recently wired:

- `SUR9` / `HMS6`: action metadata names selected harness and logic item, but action remains blocked.
- `HMS14`: generic planned harness surfaces preserve UI-local draft notes under `meridian.harness.draft.v1.<harness>`.

No harness execution, POST, `/bridge/message`, `/bridge/call-result`, User Session retargeting, or cross-harness routing is authorized by these rows.

## Safe Next-Slice Candidates

Prefer small slices that reveal existing backend state or honest UI-local state without inventing control authority.

Possible candidates:

1. `HMS10` - Harness diagnostics, only if implemented as structured display-only diagnostic metadata from existing model harness observability/proof telemetry. Do not claim real per-harness event history unless it exists.
2. `SET18` - Diagnostic log visibility, only if scoped to an existing UI-local preview/diagnostics visibility toggle and not described as per-session event-log backend control unless that backend exists.
3. `SET7` - Progress filter defaults, only if implemented as UI-local defaults for the existing context/filter preview. Be careful: the row says "progress items," so wording/tests must not overclaim.
4. `HMS11` - Harness proof link, only if linking existing proof/check sections already present in model harness surfaces. Do not claim executable verification.

Rows to avoid until backend exists:

- `XCK1`, `XCK5`, `XCK6`, `XCK7`
- `BAK3`-`BAK10`
- `ROU1`-`ROU11`
- `ARC1`-`ARC12`
- `CLS1`-`CLS7`, `CLS9`-`CLS12`
- `VOC1`, `VOC3`, `VOC4`, `VOC7`-`VOC10`
- `BR7`

## Current Important UI Functions

In `index.html`:

- `renderSparkSkillsRegistry(snapshot, query = '')`
- `loadSparkSkills()`
- `renderSparkBacklog()`
- `loadSparkBacklog()`
- `renderSparkCrosscheck()`
- `renderProviderBalance()`
- `renderModelHarnessSurface(button)`
- `renderModelHarnessBackendBindingSnapshot(snapshots = {})`
- `renderHarnessSurface(button)`
- `renderVoiceIoSnapshot(snapshot)`
- `refreshProjectScopedSurfaces()`

Important local storage keys:

- `meridian.session.project`
- `meridian.skills.pinned.v1`
- `meridian.harness.draft.v1.<harness>`
- `meridian.context-filter.v1`
- `meridian.right-panel.mode.v1`
- `meridian.right-panel.selection.v1`

## Current Backend Routes Used By UI

From `scripts/meridian-model-bridge.js`:

- `/bridge/health`
- `/bridge/models`
- `/bridge/recent-calls`
- `/bridge/message`
- `/bridge/restart`
- `/bridge/user-sessions`
- `/bridge/prime-logic`
- `/bridge/compass-logic`
- `/bridge/vulcan-logic`
- `/bridge/relay-logic`
- `/bridge/relay-evidence`
- `/bridge/provider-balance`
- `/bridge/review-console`
- `/bridge/aegis-logic`
- `/bridge/beacon-liveness`
- `/bridge/federation-horizon`
- `/bridge/goal-runtime`
- `/bridge/workflow-dispatch-status`
- `/bridge/echo-memory`
- `/bridge/atlas-retrieval`
- `/bridge/filemap`
- `/bridge/session-close-archive-proof`
- `/bridge/voice-io`
- `/bridge/prime-autonomy`

## Session Coordination Rules

- Use a session for one coherent task thread.
- Start a new session when the next task no longer needs most of the prior working context, unless detailed prior reasoning is needed.
- The orchestrator should not ingest raw worker session history by default.
- Ingest compact, typed session state:
  - worker transcript stored, not replayed;
  - worker summary small and checkpointed;
  - session state packet always available;
  - evidence refs links/ids;
  - raw detail fetched only on demand.

## How To Promote A Slice

1. Verify main is clean.
2. Pick one row or a tightly related pair.
3. Implement narrowly in the Electron renderer / bridge only if backed by current reviewed backend state.
4. Update `docs/ui-integration-checklist.md` only when the behavior is real and test-covered.
5. Add focused tests in `tests/test_bifrost_cockpit.py`.
6. Run focused tests and embedded JS parse.
7. Run full verification:

```powershell
python -m pytest tests\test_bifrost_cockpit.py -q
node --check scripts\meridian-model-bridge.js
node scripts\meridian-model-bridge.js --self-test
git diff --check
```

8. Count checklist progress.
9. Commit and push to `main`.
10. Confirm `git status --short --branch` is clean/aligned.

## Handoff Creation Proof

At creation time:

- `git status --short --branch` showed `## main...origin/main`.
- Progress count showed `215/305 wired`, `4 partial`, `86 planned`, `0 blocked`.
- Latest pushed head was `973b458cf`.


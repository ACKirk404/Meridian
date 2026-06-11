# Meridian Session Replacement Handoff

Date: 2026-06-11

Purpose: replace the current Codex session for the active UI-owned Meridian
work without making the next session reconstruct state from thread history.

## What This Session Was Doing

This session was asked to update the Meridian UI itself, not just docs, for a
display-only harness documentation parity pass.

Scope of the completed pass:

- add V2.5 harness documentation parity in the UI
- add V2 harness capability parity in the same UI pass
- do not add backend wiring
- do not turn display-only rows into controls
- do not imply live execution, mutation, provider dispatch, archive restore,
  transcript retrieval, or voice-command execution unless already proven

The UI was updated to explain reviewed backend capability posture inside the
existing harness panels.

## Files Intentionally Touched By This Session

- [index.html](C:\Users\scott\Code\Meridian\index.html)
- [tests/test_bifrost_cockpit.py](C:\Users\scott\Code\Meridian\tests\test_bifrost_cockpit.py)

No backend files were intentionally edited for this pass.

## What Was Added To The UI

### V2.5 advisory parity

Added display-safe explanatory sections covering:

- V2.5 capability digest in the harness backend-binding surface
- Aegis/Security evidence safety and proof quality posture
- harness diagnostics drift, stale-worker, reliability, escalation posture
- review intelligence posture
- FileMap intelligence posture
- memory/retrieval provenance posture
- release/promotion provenance posture

### V2 capability parity

Added harness-level capability posture sections so the interface explains
existing reviewed V2 surfaces without requiring checklist reading:

- Prime: `Prime autonomy posture`
- Relay/Model Harness: `Relay / Model Harness capability posture`
- Compass: `Compass project-boundary posture`
- Vulcan: `Session lifecycle posture`
- Beacon: `Beacon advisory posture`
- Backlog: `Backlog capability posture`
- Goal Runtime: `Prime / workflow continuity posture`
- Workflow/Routines: `Routine capability posture`
- Archive/Close: `Archive / close capability posture`
- Voice: `Voice capability posture`
- Federation: `Federation capability posture`

All of these are copy-only/documentation-in-UI changes inside existing render
surfaces.

## Proof Already Run

Focused proof for this pass is green:

```powershell
python -m pytest tests/test_bifrost_cockpit.py -q
```

Result:

- `536 passed`

Embedded script syntax check is green:

```powershell
$html = Get-Content index.html -Raw
$scripts = [regex]::Matches($html, '<script>([\s\S]*?)</script>') | ForEach-Object { $_.Groups[1].Value }
$tmp = Join-Path $env:TEMP 'meridian-inline-check.js'
[IO.File]::WriteAllText($tmp, ($scripts -join "`n"))
node --check $tmp
```

Result:

- passed

Scoped diff check:

```powershell
git diff --check -- index.html tests/test_bifrost_cockpit.py
```

Result:

- only recurring LF/CRLF warnings

## Current Repository Reality

The shared checkout is dirty and not a safe promotion source.

Current shared-checkout `git status --short` includes many unrelated modified
and untracked files beyond this UI pass, including backend V2.5 work and repo
coordination artifacts.

Important consequence:

- do not promote from `C:\Users\scott\Code\Meridian` directly
- do not assume the diff in this checkout is only this session's work
- if promotion is needed, reconstruct or cherry-pick this pass into a clean
  worktree based on current `origin/main`

## Recommended Next Session Workflow

1. Read this handoff.
2. Verify current main/head state and main-write coordination rules.
3. Create a clean worktree from current `origin/main`.
4. Bring over only the UI parity changes from:
   - `index.html`
   - `tests/test_bifrost_cockpit.py`
5. Re-run focused proof in the clean worktree:
   - `python -m pytest tests/test_bifrost_cockpit.py -q`
   - embedded `node --check` script extraction
   - `git diff --check`
6. If promotion/review is needed, package exact hash, exact file scope, and
   proof for review.

## Source Truth Used For This Pass

The UI wording was reconciled against these sources:

- [docs/FileMap.md](C:\Users\scott\Code\Meridian\docs\FileMap.md)
- [docs/v2-progress-tracker.md](C:\Users\scott\Code\Meridian\docs\v2-progress-tracker.md)
- [docs/ui-integration-checklist.md](C:\Users\scott\Code\Meridian\docs\ui-integration-checklist.md)
- [scripts/meridian-model-bridge.js](C:\Users\scott\Code\Meridian\scripts\meridian-model-bridge.js)
- existing harness panels in [index.html](C:\Users\scott\Code\Meridian\index.html)

## Guardrails The Next Session Should Preserve

- Keep this a UI-owned pass unless explicitly asked to wire backend behavior.
- Do not add new bridge routes for this task.
- Do not add POST actions or executable controls.
- Do not imply:
  - provider dispatch
  - scheduler mutation
  - session mutation
  - archive restore
  - transcript retrieval
  - voice command execution
  - close/archive execution
  unless current reviewed wiring already proves it
- Prefer wording such as:
  - display-only posture
  - reviewed backend snapshot
  - advisory contract
  - command-plan preview
  - non-executable boundary
  - no live mutation route

## Known Good Summary For Review

If another session needs a short reviewer summary, use this:

This pass is a copy/documentation reconciliation inside existing harness UI
surfaces. It makes the interface explain already reviewed V2 and V2.5 backend
capabilities at the harness level. It does not add new backend wiring, new
controls, or new execution authority. Focused cockpit proof is green at
`536 passed`.

## If Another Session Needs To Continue Editing

Most likely follow-up work:

- tighten wording if product copy needs simplification
- move this same parity language into any remaining harness panel that still
  feels under-explained after visual inspection
- port the exact two-file diff into a clean worktree for review/promotion

Least likely but possible:

- if a reviewer says some new wording overclaims a backend capability, narrow
  the wording rather than adding new backend or UI execution logic

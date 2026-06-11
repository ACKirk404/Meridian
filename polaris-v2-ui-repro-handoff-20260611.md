# Polaris V2 UI Reproduction Handoff

Date: 2026-06-11
Workspace: `C:\Users\scott\Code\Meridian`

## Purpose

This handoff is for Polaris Claude/Haiku/Opus implementation sessions. Codex
reviewed the current Meridian shared checkout and found that V2 UI is not
authoritatively complete on promoted `origin/main`, but a large amount of
additional UI wiring exists only in the dirty shared worktree.

Use this document to reproduce that UI state cleanly from promoted main in
path-limited, reviewable candidates. Do not treat the dirty shared checkout as
safe to promote directly.

## Authority Snapshot

Counts from current repo state:

- `origin/main` (`bd3147658a09de58b526046d0ba8fc7623407181`):
  - `243/305 wired`
  - `4 partial`
  - `58 planned`
- local `HEAD` on shared `main` (`c32bc4ed9d7347fcd5f5ed79cefbf0750170f364`):
  - `247/305 wired`
  - `4 partial`
  - `54 planned`
- current dirty shared worktree:
  - `305/305 wired`
  - `0 partial`
  - `0 planned`

Current promoted partial rows on `origin/main`:

- `SK9`
- `XCK2`
- `VOC5`
- `VOC6`

## Key Review Finding

The local checkout is not a simple clean candidate stack:

1. `origin/main` is the only authoritative promoted V2 UI state.
2. local `HEAD` contains 16 UI-only commits not on `origin/main`, but only some
   of them actually increase the wired row count.
3. the jump to `305/305 wired` lives mostly in uncommitted dirty changes across:
   - `docs/ui-integration-checklist.md`
   - `index.html`
   - `scripts/meridian-model-bridge.js`
   - `tests/test_bifrost_cockpit.py`
4. the shared checkout is also mixed with unrelated backend/V2.5 work and must
   not be used as a direct promotion source.

Result: Polaris should reproduce the current dirty UI behavior from clean
`origin/main`, then Codex should review the exact clean candidate hashes before
any promotion.

## Current Dirty Worktree Proof

Codex ran the focused UI proof loop against the current dirty worktree:

- `python -m pytest tests/test_bifrost_cockpit.py -q` -> `534 passed`
- `node --check scripts/meridian-model-bridge.js` -> passed
- `node scripts/meridian-model-bridge.js --self-test` -> passed
- `git diff --check HEAD -- docs/ui-integration-checklist.md index.html scripts/meridian-model-bridge.js tests/test_bifrost_cockpit.py`
  - only recurring LF/CRLF warnings

Self-test output also still reports the current environment note:

- Codex CLI not installed/on PATH
- Claude CLI installed but not logged in

Those setup notes do not block the UI proof loop.

## Clean Local Commits Already Present

These 16 local commits exist on shared `main` but are not promoted to
`origin/main`:

1. `974a865c6` `ui: add balance routing recommendation`
2. `91d8b49e9` `ui: add crosscheck stop condition alert`
3. `886099ed0` `ui: show relay mediated dispatch posture`
4. `d0e14207a` `ui: add harness diagnostics surface`
5. `88e33509a` `ui: note quiet mode on routines`
6. `2acb2db3a` `ui: add crosscheck evidence handoff`
7. `78cd5d550` `ui: add backlog priority order`
8. `e58d975da` `ui: add archive metadata preview`
9. `fedd65d80` `ui: add close summary preview`
10. `27bb87f1b` `ui: add archive proof refs`
11. `edc46c35e` `ui: add archive summary preview`
12. `a99205168` `ui: add routine last run result`
13. `6a064e694` `ui: add routine failure handling`
14. `6eaf04b92` `ui: add routine next run preview`
15. `8bddd250b` `ui: add archive context reference`
16. `c32bc4ed9` `ui: add crosscheck gate posture`

Do not blindly cherry-pick them as a completion strategy. They are useful as
behavior/reference hints, but the dirty worktree has moved beyond them and the
shared checkout is not clean.

## Rows Touched Only In Dirty Worktree

Relative to local `HEAD`, the dirty worktree changes checklist status/wording on
these rows:

- `SK9`
- `SET9`
- `SET12`
- `SET13`
- `SET17`
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
- `XCK1`
- `XCK2`
- `XCK4`
- `XCK5`
- `XCK6`
- `XCK7`
- `XCK8`
- `XCK10`
- `XCK12`
- `ROU1`
- `ROU2`
- `ROU3`
- `ROU4`
- `ROU5`
- `ROU8`
- `ROU9`
- `ROU11`
- `ARC1`
- `ARC2`
- `ARC3`
- `ARC6`
- `ARC8`
- `ARC9`
- `ARC11`
- `ARC12`
- `CLS1`
- `CLS2`
- `CLS3`
- `CLS5`
- `CLS6`
- `CLS7`
- `CLS9`
- `CLS10`
- `CLS11`
- `CLS12`
- `VOC1`
- `VOC3`
- `VOC4`
- `VOC5`
- `VOC6`
- `VOC7`
- `VOC8`
- `VOC9`
- `VOC10`
- `HN1`
- `FM0`
- `HMS4`
- `BR7`

This is the main Polaris rebuild target.

## Recommended Polaris Reconstruction Plan

Start from clean `origin/main` and rebuild in narrow UI-only slices. Keep file
scope limited to:

- `docs/ui-integration-checklist.md`
- `index.html`
- `scripts/meridian-model-bridge.js`
- `tests/test_bifrost_cockpit.py`

Recommended slice order:

1. Voice and settings closeout:
   - `SET9`, `SET12`, `SET13`, `SET17`
   - `VOC1`, `VOC3`, `VOC4`, `VOC5`, `VOC6`, `VOC7`, `VOC8`, `VOC9`, `VOC10`
2. Crosscheck and backlog posture closeout:
   - `BAK3`-`BAK12`
   - `XCK1`, `XCK2`, `XCK4`-`XCK8`, `XCK10`, `XCK12`
3. Archive/close posture closeout:
   - `SK9`
   - `ARC1`, `ARC2`, `ARC3`, `ARC6`, `ARC8`, `ARC9`, `ARC11`, `ARC12`
   - `CLS1`, `CLS2`, `CLS3`, `CLS5`, `CLS6`, `CLS7`, `CLS9`, `CLS10`, `CLS11`,
     `CLS12`
4. Routine and harness/relay closeout:
   - `ROU1`, `ROU2`, `ROU3`, `ROU4`, `ROU5`, `ROU8`, `ROU9`, `ROU11`
   - `BR7`, `HN1`, `FM0`, `HMS4`

If Polaris finds that some of these rows are wording-only promotions rather than
implementation deltas, that is acceptable, but the implementation, checklist
text, and proof must still agree truthfully.

## Codex Review Expectations

For each Polaris candidate, send Codex:

- branch/worktree
- exact commit hash
- changed files
- proof results
- current checklist count after that candidate

Minimum proof for any candidate touching the bridge/UI checklist tail:

- `python -m pytest tests/test_bifrost_cockpit.py -q`
- `node --check scripts/meridian-model-bridge.js`
- `node scripts/meridian-model-bridge.js --self-test`
- `git diff --check`

If a candidate claims new backend-backed display state, Codex review will also
check that:

- no raw prompt/transcript/provider-response/worker-chat/local-path leaks were
  introduced
- executable mutation or dispatch is not implied where authority is still
  display-only
- checklist wording matches the actually rendered UI and bridge snapshot

## Do Not Do

- Do not promote from dirty shared `C:\Users\scott\Code\Meridian`.
- Do not absorb backend/V2.5 files into UI candidates.
- Do not treat `305/305` in the dirty worktree as authoritative completion.
- Do not claim V2 done until the promoted state proves it.

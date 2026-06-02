# Meridian V2 Orchestrator Handoff - 2026-06-01

## Mission

Continuously coordinate the five Meridian build sessions and two Codex review sessions so each has:

- A unique assigned worktree.
- An executable Active Task.
- A concrete Next Candidate.
- Explicit containment rules.
- No idle/waiting state unless a real blocker is written with evidence.

The orchestrator is responsible for routing, containment, review pressure, and queue updates. Build and review workers do the assigned implementation/review work in their own worktrees.

## Transition Coordination File

Use `docs/v2-orchestrator-transition-ledger.md` as the temporary shared coordination file between the current orchestrator and the replacement orchestrator.

This is not a hard handoff cliff. The replacement coordinator should treat the transition ledger like its own session queue:

- Read the ledger before routing.
- Record intake checks and evidence there.
- Recommend or draft route changes there.
- Run one supervised routing cycle before full takeover.
- Wait for current-orchestrator or user approval before declaring takeover complete.

Until `docs/v2-orchestrator-transition-ledger.md` says `Takeover Status: Complete`, the current orchestrator remains the owner of final route approval, branch/worktree movement approval, and contamination recovery decisions.

## Hard Containment Rules

Shared main checkout:

- `C:\Users\scott\Code\Meridian`
- Must stay on `main`.
- Must stay clean.
- Main is coordinator ledger only.

Coordinator worktree:

- `C:\Users\scott\Code\Meridian-Worktrees\coordinator-20260601-200614`
- Branch: `codex/coordinator-20260601-200614`

Workers and review sessions must be told on every new task:

> You must do all work inside your assigned unique worktree. You are not allowed to write to `C:\Users\scott\Code\Meridian` main or push/write to `main` without explicit coordinator approval. Do not move data between worktrees, branches, or the main checkout. Do not cherry-pick, copy files, stash-pop across worktrees, merge, rebase, reset, or salvage. If you believe work must move, stop and ask the coordinator. The coordinator may permit it only after verifying `C:\Users\scott\Code\Meridian` main is clean.

Before any route, merge, fast-forward, salvage, or movement approval:

1. Fetch `origin/main`.
2. Verify shared main is on `main`.
3. Verify shared main is clean with no staged files, dirty implementation files, or untracked worker artifacts.
4. Verify the affected worker worktree is clean.

If shared main is dirty:

1. Pause normal coordination.
2. Preserve/quarantine the contamination without moving it into a worker branch.
3. Reset shared main clean to `origin/main`.
4. Notify the user and record the containment state.

## Current Verified State

Last coordinator verification in this handoff:

- Shared main `C:\Users\scott\Code\Meridian`: clean, `main...origin/main`.
- Coordinator worktree: clean, `codex/coordinator-20260601-200614...origin/main`.
- `origin/main` HEAD at verification: `0e804261 chore: Escalate stalled FileMap audit and Relay UI review`.
- No `cmd.exe` storm observed in the last process sanity check.

Recent coordinator commits on `origin/main`:

- `0e804261 chore: Escalate stalled FileMap audit and Relay UI review`
- `7efecd9a chore: Nudge FileMap audit and Relay UI review`
- `6ae7e0f6 chore: Record index styling containment patch`
- `05eb26d1 chore: Route Relay UI integration review and FileMap audit`
- `7b50ab8e Update Relay harness Obsidian context`

Important: current main legitimately includes the Relay UI/runtime landing from commits `1b9c43db` through `7b50ab8e`. Do not treat those files as contamination unless they become dirty/uncommitted or locally ahead of origin.

## Active Worktrees

Build lanes:

- Build 1: `C:\Users\scott\Code\Meridian-Worktrees\build-1-v2-relay`
- Build 2: `C:\Users\scott\Code\Meridian-Worktrees\build-2-session-lifecycle`
- Build 3: `C:\Users\scott\Code\Meridian-Worktrees\build-3-filemap`
- Build 4: `C:\Users\scott\Code\Meridian-Worktrees\build-4-aegis`
- Build 5: `C:\Users\scott\Code\Meridian-Worktrees\build-5-bifrost`

Review lanes:

- Reviews A: `C:\Users\scott\Code\Meridian-Worktrees\codex-reviews-a`
- Reviews B: `C:\Users\scott\Code\Meridian-Worktrees\codex-reviews-b`

All seven worktrees were clean at last verification.

## Current Lane Status

### Build 1 - Relay / Model Harness

Queue file: `docs/live-build-1.md`

Active task:

- Add DeepSeek candidate metadata presets to the provider-neutral Model Harness.

Allowed files:

- `meridian_core/model_adapter.py`
- `tests/test_model_adapter.py`
- `docs/live-build-1.md`

Proof:

- `python -m pytest tests/test_model_adapter.py -q`

Current evidence:

- Worktree is clean.
- Branch shows ahead of `origin/main`, but the only no-merge commit ahead is `b8405695 chore: Build 1 read check - 2026-06-12 21:50 UTC (idle, cadence 2/3)`.
- Treat the lane as not having produced the active implementation yet.

Next coordinator action:

- Keep pressure on Build 1 to implement or write a real blocker. Do not accept another read-check-only update as progress.

### Build 2 - Session Lifecycle

Queue file: `docs/live-build-2.md`

Active task:

- Add Session Lifecycle restart/resteer recovery tests after permissions binding cleared review.

Allowed files:

- `meridian_core/session_lifecycle.py`
- `tests/test_session_lifecycle.py`
- `docs/live-build-2.md`

Proof:

- `python -m pytest tests/test_session_lifecycle.py -q`

Current evidence:

- Worktree is clean.
- Branch shows ahead of `origin/main` with older implementation commits:
  - `6c3a024b fix: enforce remaining Session Lifecycle permission-invariant gaps`
  - `d8a05864 fix: repair Session Lifecycle permissions contract completeness issues`
  - `6e2f2a5f feat: implement Session Lifecycle permissions and Prime/Beacon binding`
- Those are historical/visibility-problem commits, not completion of the current restart/resteer recovery test task.

Next coordinator action:

- Keep pressure on Build 2 to implement the current recovery tests or write a real blocker.

### Build 3 - FileMap

Queue file: `docs/live-build-3.md`

Active task:

- Audit FileMap coverage for the current-main Relay UI/runtime integration landing.

Allowed files:

- `meridian_core/filemap.py`
- `docs/FileMap.md`
- `tests/test_filemap.py`
- `docs/live-build-3.md`

Proof:

- `python -m pytest tests/test_filemap.py -q`

Must inspect at minimum:

- `meridian_core/relay_logic_snapshot.py`
- `tests/test_relay_logic_snapshot.py`
- `scripts/meridian-model-bridge.js`
- `index.html`
- `docs/relay-completeness-audit.md`
- `docs/relay-heartbeat-model-routing-logic.md`
- `docs/ui-integration-checklist.md`

Current evidence:

- Worktree is clean and aligned to `origin/main`.
- The queue contains an escalation: complete FileMap registration in the next work cycle or write a concrete blocker with command/output evidence.
- Coordinator previously observed missing FileMap coverage for `meridian_core/relay_logic_snapshot.py` and `tests/test_relay_logic_snapshot.py`.

Next coordinator action:

- This is one of the two pressure lanes. If it still has no completion/blocker on next check, escalate again or manually route a focused repair lane.

### Build 4 - Aegis / Relay Routing Docs

Queue file: `docs/live-build-4.md`

Top active task:

- Convert the deepened Relay harness model-selection logic into an implementation checklist.

Allowed files:

- `docs/relay-heartbeat-model-routing-implementation-checklist.md`
- `docs/live-build-4.md`

Current evidence:

- Worktree is clean and aligned to `origin/main`.
- The top queue block still says Active Now.
- The target checklist file does not exist on `origin/main`:
  - `docs/relay-heartbeat-model-routing-implementation-checklist.md`
- `fe0b0138` is in `origin/main`, but it is the account-first wrong-scope fallback repair, not completion of the implementation-checklist task.

Interpretation:

- The Build 4 checklist task is still executable and should remain active.
- The earlier suspicion that this task was completed by `fe0b0138` was incorrect.

Next coordinator action:

- Keep Build 4 assigned to create `docs/relay-heartbeat-model-routing-implementation-checklist.md`.
- After Build 4 marks the checklist Ready on current main, route Reviews B to review that checklist if no higher-priority review finding is active.

### Build 5 - Bifrost

Queue file: `docs/live-build-5.md`

Active task:

- Add stale-session recovery action sample rendering after stale-target guard cleared review.

Allowed files:

- `bifrost/cockpit.py`
- `bifrost/static/cockpit.css`
- `tests/test_bifrost_cockpit.py`
- `docs/live-build-5.md`

Proof:

- `python -m pytest tests/test_bifrost_cockpit.py -q`

Current evidence:

- Worktree is clean and aligned to `origin/main`.
- No fresh completion observed for the current stale-session recovery action task.

Next coordinator action:

- Keep pressure on Build 5 to implement or write a real blocker after the higher-priority review/FileMap pressure clears.

### Reviews A - Runtime / Code Review

Queue file: `docs/live-codex-reviews.md`

Active task:

- Review Build 1 DeepSeek candidate metadata preset slice when it is marked Ready for Codex Review on current main.

Next candidate:

- Review Build 2 restart/resteer recovery tests when marked Ready.

Current evidence:

- Worktree is clean and aligned to `origin/main`.
- Build 1 has not produced a current-main Ready marker for the active DeepSeek metadata preset task.

Next coordinator action:

- No idle read-check commits. Reviews A should poll only for the Ready marker, then review immediately.

### Reviews B - UI / Harness Review

Queue file: `docs/live-codex-reviews-2.md`

Active task:

- Review the current-main Relay harness UI/runtime integration landing.

Allowed review files:

- `index.html`
- `scripts/meridian-model-bridge.js`
- `meridian_core/relay_logic_snapshot.py`
- `tests/test_relay_logic_snapshot.py`
- `docs/relay-completeness-audit.md`
- `docs/relay-heartbeat-model-routing-logic.md`
- `docs/ui-integration-checklist.md`
- `docs/live-codex-reviews-2.md`

Proof:

- `python -m pytest tests/test_relay_logic_snapshot.py -q`

Current evidence:

- Worktree is clean and aligned to `origin/main`.
- The queue contains an escalation: complete this review in the next work cycle or write a concrete blocker with evidence.
- Coordinator previously ran the proof and saw `11 passed`, but the review lane still needs to record pass/finding/blocker itself.

Next coordinator action:

- This is the other pressure lane. If Reviews B still has no pass/finding/blocker on next check, escalate again or replace the lane with a fresh review session.

## Known Queue Inconsistencies / Risks

- Some queue docs contain future-looking timestamps such as 2026-06-12/13 despite the current run date being 2026-06-01. Treat these as unreliable provenance unless verified by Git ancestry.
- Build 1 and Build 2 can show `ahead` because of local merge/read-check history. Do not confuse that with active-task completion.
- Build 4's top Active Now block is valid: `docs/relay-heartbeat-model-routing-implementation-checklist.md` is still missing from `origin/main`. `fe0b0138` is a separate wrong-scope fallback repair, not checklist completion.
- Reviews B and Build 3 were escalated because they had drifted into passive/waiting behavior.

## Quarantine / Containment History

Prior shared-main contaminations were preserved, not silently mixed into worker branches:

- `codex/quarantine-main-impl-992caa8a-20260601-201629`
- `codex/quarantine-main-impl-00e205ed-20260601-201746`
- `codex/quarantine-main-impl-53f5f205-20260601-201847`
- `C:\Users\scott\Code\Meridian-Worktrees\quarantine-main-dirty-53f5f205-20260601-201847.patch`
- `C:\Users\scott\Code\Meridian-Worktrees\quarantine-main-dirty-index-20260601-202746.patch`

Do not resurrect these into main without explicit user approval and a clean-main, path-limited movement plan.

## First Commands For New Orchestrator

Run these before making decisions:

```powershell
Set-Location C:\Users\scott\Code\Meridian
git fetch origin main
git status --short --branch
git status --porcelain

Set-Location C:\Users\scott\Code\Meridian-Worktrees\coordinator-20260601-200614
git status --short --branch
git log --oneline -10
```

Then check every active lane:

```powershell
foreach ($dir in @(
  'C:\Users\scott\Code\Meridian-Worktrees\build-1-v2-relay',
  'C:\Users\scott\Code\Meridian-Worktrees\build-2-session-lifecycle',
  'C:\Users\scott\Code\Meridian-Worktrees\build-3-filemap',
  'C:\Users\scott\Code\Meridian-Worktrees\build-4-aegis',
  'C:\Users\scott\Code\Meridian-Worktrees\build-5-bifrost',
  'C:\Users\scott\Code\Meridian-Worktrees\codex-reviews-a',
  'C:\Users\scott\Code\Meridian-Worktrees\codex-reviews-b'
)) {
  Set-Location $dir
  git status --short --branch
}
```

## Next Best Actions

1. Have the replacement coordinator write intake findings into `docs/v2-orchestrator-transition-ledger.md`.
2. Check whether Build 3 wrote a FileMap completion or concrete blocker after the escalation.
3. Check whether Reviews B wrote a pass/finding/blocker after the escalation.
4. Keep Build 4 on the implementation-checklist task because the checklist file is not present on `origin/main`.
5. If Build 3 and Reviews B remain unchanged, update their queues with stronger routing or replace those sessions; do not let them idle.
6. Once Reviews B closes the Relay UI/runtime review, route the Build 4 checklist review and then Build 5 stale-session recovery review.
7. Keep Build 1/2/5 moving, but prioritize any Codex review findings ahead of normal work.

## Reporting Format

Keep reports short:

- Containment: main clean or contaminated.
- Lane status: active, completed, review waiting, blocker.
- Actions taken: sync, queue update, route, escalation, commit/push.
- Blockers: exact lane, exact missing evidence.

Do not paste raw command output unless the user asks for it.

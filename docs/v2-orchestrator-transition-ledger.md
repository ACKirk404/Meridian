# Meridian V2 Orchestrator Transition Ledger

## Purpose

This file is the shared coordination surface between the current orchestrator and the replacement orchestrator during handoff.

Treat it like a session queue for the new coordinator. The replacement coordinator should read this file first, write short evidence-backed updates here, and only take full ownership after the current orchestrator or user confirms the transition is stable.

## Transition Rules

- The replacement coordinator must work from `C:\Users\scott\Code\Meridian-Worktrees\coordinator-20260601-200614` unless the user assigns a different unique coordinator worktree.
- The replacement coordinator must not write to shared main `C:\Users\scott\Code\Meridian`.
- The replacement coordinator must not move work between branches/worktrees without verifying shared main is clean and recording the exact scope here.
- The replacement coordinator must not accept read-check-only worker updates as progress.
- The current orchestrator remains responsible for final route approval until this ledger says `Takeover Status: Complete`.

## Takeover Status

Status: In transition.

Owner of final routing decisions: current orchestrator.

Replacement coordinator may:

- Inspect main/coordinator/worktree status.
- Inspect queue docs and recent commits.
- Recommend lane routing or escalation.
- Draft coordinator-only queue updates.
- Record evidence in this ledger.

Replacement coordinator may not yet:

- Approve branch/worktree movement.
- Reset/quarantine shared main contamination.
- Replace active build/review queues without confirmation.
- Mark the V2 coordination goal complete or blocked.

## Required First Check

The replacement coordinator should run these checks and summarize the result in the first open checkpoint below:

```powershell
Set-Location C:\Users\scott\Code\Meridian
git fetch origin main
git status --short --branch
git status --porcelain

Set-Location C:\Users\scott\Code\Meridian-Worktrees\coordinator-20260601-200614
git status --short --branch
git log --oneline -10
```

Then check each active lane:

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

## Open Checkpoint 1 - Replacement Coordinator Intake

Status: intake recorded and reviewed by current orchestrator.

Current orchestrator note before replacement intake:

- Shared main was clean and aligned with `origin/main` after the handoff commit.
- All seven worker/review lanes were synced to include the handoff and transition ledger.
- Build 1 and Build 2 are clean but still show local ahead history from prior merge/read-check work; do not treat that as current task completion without commit/queue proof.
- Build 3 remains a pressure lane: current top task is FileMap coverage for Relay UI/runtime integration, and `meridian_core/relay_logic_snapshot.py` / `tests/test_relay_logic_snapshot.py` were still not found in FileMap coverage during the coordinator spot check.
- Reviews B remains a pressure lane: current top task is the Relay UI/runtime integration review; it must pass, route a finding, or write a concrete blocker.
- Build 4 remains active on the Relay routing implementation checklist. The checklist file `docs/relay-heartbeat-model-routing-implementation-checklist.md` is not present on `origin/main`. Do not treat `fe0b0138` as checklist completion; it is the separate account-first wrong-scope fallback repair.
- Replacement coordinator should now run the required first check and record intake below this note.

Replacement coordinator should record:

- Shared main status.
- Coordinator worktree status.
- Seven lane statuses.
- Any dirty/conflicted/stale worktree.
- Whether Build 3 and Reviews B have produced completion/blocker evidence.
- Whether Build 4 queue still needs reconciliation.
- Recommended next action.

Replacement coordinator intake:

- Shared main `C:\Users\scott\Code\Meridian`: fetched and fast-forward checked to corrected main. HEAD `a20d9e0b`, `origin/main` `a20d9e0b`, branch `main...origin/main`, no staged files, dirty files, or untracked files before this ledger update.
- Coordinator worktree `C:\Users\scott\Code\Meridian-Worktrees\coordinator-20260601-200614`: present on `codex/coordinator-20260601-200614...origin/main` at `a20d9e0b`. It is dirty in `docs/v2-orchestrator-transition-ledger.md`; the diff is a current-orchestrator review/supervised-routing approval draft under Open Checkpoint 2. Replacement coordinator did not treat that uncommitted coordinator-worktree draft as takeover completion or branch/worktree movement approval.
- Build 1 `C:\Users\scott\Code\Meridian-Worktrees\build-1-v2-relay`: present, clean, `worktree-build-1-v2-relay...origin/main [ahead 18, behind 1]`. No dirty/conflicted files. No-merge ahead evidence checked: only `b8405695` is a read-check/idle commit; not accepted as progress on the DeepSeek metadata preset task.
- Build 2 `C:\Users\scott\Code\Meridian-Worktrees\build-2-session-lifecycle`: present, clean, `worktree-build-2-session-lifecycle...origin/main [ahead 21, behind 1]`. No dirty/conflicted files. Ahead no-merge commits are historical permission-binding work (`6c3a024b`, `d8a05864`, `6e2f2a5f`), not completion of the current restart/resteer recovery test task.
- Build 3 `C:\Users\scott\Code\Meridian-Worktrees\build-3-filemap`: present, clean, `worktree-build-3-filemap...origin/main [behind 1]`. No dirty/conflicted files. It has not completed or blocked the current FileMap task; the top queue task is still the Relay UI/runtime FileMap audit with escalation text. Targeted coverage check found `docs/relay-completeness-audit.md`, `docs/relay-heartbeat-model-routing-logic.md`, and `docs/ui-integration-checklist.md` registered, but no FileMap coverage hits for `meridian_core/relay_logic_snapshot.py`, `tests/test_relay_logic_snapshot.py`, `scripts/meridian-model-bridge.js`, or `index.html`.
- Build 4 `C:\Users\scott\Code\Meridian-Worktrees\build-4-aegis`: present, clean, `worktree-build-4-aegis...origin/main [behind 1]`. No dirty/conflicted files. The corrected handoff is valid: Build 4 is still correctly assigned to create `docs/relay-heartbeat-model-routing-implementation-checklist.md`; that file is absent from `origin/main`, and `fe0b0138` is the separate account-first wrong-scope fallback repair, not checklist completion.
- Build 5 `C:\Users\scott\Code\Meridian-Worktrees\build-5-bifrost`: present, clean, `worktree-build-5-bifrost...origin/main [behind 1]`. No dirty/conflicted files. Active task remains stale-session recovery action sample rendering; no fresh completion observed.
- Reviews A `C:\Users\scott\Code\Meridian-Worktrees\codex-reviews-a`: present, clean, `worktree-codex-reviews-a...origin/main [behind 1]`. No dirty/conflicted files. Active task remains waiting to review Build 1 DeepSeek metadata preset after a current-main Ready marker.
- Reviews B `C:\Users\scott\Code\Meridian-Worktrees\codex-reviews-b`: present, clean, `worktree-codex-reviews-b...origin/main [behind 1]`. No dirty/conflicted files. It has not completed or blocked the Relay UI/runtime integration review; the top queue task still requires pass, focused finding, or concrete blocker with evidence.
- Missing worktrees: none observed among the coordinator, five build lanes, and two review lanes.
- Intake-only conclusion: no branch/worktree movement approved, no worker implementation files touched, no read-check-only updates accepted as progress, and takeover remains in transition. Recommended next action is current-orchestrator review of this intake before any supervised routing.

## Open Checkpoint 2 - Current Orchestrator Review

Status: reviewed; supervised routing approved.

Current orchestrator should review the replacement coordinator's intake and record:

- Accepted findings.
- Corrections.
- Approved route/queue updates.
- Whether replacement coordinator can advance to supervised routing.

Current orchestrator review:

- Intake accepted. The replacement coordinator correctly preserved containment, did not write to shared main, did not approve movement, and did not treat read-check-only/ahead history as progress.
- Correction: after the replacement intake, the current orchestrator fast-forwarded shared main `C:\Users\scott\Code\Meridian` to `a20d9e0b`; shared main is now aligned with `origin/main` and clean.
- Accepted pressure-lane findings: Build 3 still owes the Relay UI/runtime FileMap audit or a concrete blocker, and Reviews B still owes the Relay UI/runtime review pass/finding/blocker.
- Accepted Build 4 correction: the checklist task remains valid because `docs/relay-heartbeat-model-routing-implementation-checklist.md` is absent from `origin/main`; `fe0b0138` is only the wrong-scope fallback repair.
- Approved supervised routing cycle: replacement coordinator may draft coordinator-scoped queue updates that add path-specific escalation evidence for Build 3 and Reviews B, keep Build 4 on the checklist task, and keep Build 1/2/5 on implement-or-blocker pressure. The replacement coordinator may not approve branch/worktree movement, reset/quarantine main, mark takeover complete, or replace active queues without current-orchestrator/user review.
- Full takeover is not approved yet. Takeover remains `In transition`.

## Open Checkpoint 3 - Supervised Routing Trial

Status: open; replacement coordinator is approved to perform one supervised routing cycle.

Replacement coordinator should perform one supervised routing cycle:

- Keep shared main clean.
- Sync stale clean worktrees if needed.
- Draft or apply only coordinator-scoped queue updates.
- Preserve every worker's unique-worktree and no-movement rule.
- Record actions and proof here.

## Full Takeover Criteria

The replacement coordinator may take full ownership only when all are true:

- Shared main is clean.
- Coordinator worktree is clean after any handoff commits.
- All seven lanes are clean or have documented blockers.
- Every active build queue has an executable Active Task plus a Next Candidate.
- Every active review queue has an executable Active Task plus a Next Candidate.
- Build 3 and Reviews B pressure points are either completed, routed, or have concrete blockers.
- Build 4 queue inconsistency is reconciled or explicitly routed.
- The user or current orchestrator records takeover approval in this ledger.

## Takeover Approval

Takeover Status: In transition.

Approval record:

- Pending.

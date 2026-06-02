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

Status: open.

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

Status: open.

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

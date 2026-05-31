# Prime Queue Runway Policy

## Overview

The Prime queue runway policy defines the invariant that **every build queue must always maintain at least one executable Active Task and at least one Next Candidate Task**, unless explicitly cadence-paused, review-gated, or human-gated. This ensures continuous forward progress, prevents queue stalls and task re-execution, and enables graceful transitions between work items.

## Core Invariant

**No build queue shall enter a state with zero executable or staged tasks.** At all times:

- **Active Task**: One executable task currently running or ready to run.
- **Next Candidate Task**: At least one staged task waiting for Active promotion.
- **Hard Exceptions Only**: Cadence pause (3-commit review gate), human-gate, or provider/model limit are the only valid reasons for a queue to lack both an Active and a Candidate task.

## Prime Runway Assignment

Prime must assign runway ahead of completion. It does not wait for Scott or for a lane to become visibly idle before preparing the next task:

- **Proactive staging**: When Prime observes an Active Task nearing completion, it writes the next Candidate Task before the lane finishes.
- **No idle-then-assign**: Prime does not wait for read-check-only heartbeats to signal emptiness before assigning work.
- **Cross-lane visibility**: Prime monitors all queue files to detect lanes approaching cadence gates or completion and stages candidates preemptively.
- **Non-conflicting candidates during review gates**: When a lane is review-gated (after every three task-changing commits), Prime still prepares non-conflicting candidate tasks so the lane can resume immediately upon cadence clearance.

## Cadence Gating

Build lanes operate on a three-commit cadence:

1. **Commits 1-3**: Execute tasks, append read checks per polling contract.
2. **After Commit 3**: Pause normal build work and await Codex Reviews cadence confirmation before starting new implementation.
3. **Cadence Clear**: Resume work with fresh Active/Next tasks or continue idle polling.

**During cadence pause**, Prime still prepares non-conflicting candidate tasks. The lane must not execute them until cadence is cleared, but the runway stays populated.

This prevents unbounded work accumulation and ensures review gates are respected before major phase transitions.

## Review Gating

- **Active Task Completion**: Mark slice "Ready for Codex Review" with commit hash, files changed, tests run.
- **Codex Lane Ownership**: Separate Codex Reviews lane owns independent review, findings, and repair routing.
- **Repair Tasks**: If Codex lane writes a repair task into this queue, complete before unrelated work.
- **No Self-Review**: Build lanes do not perform their own Codex review.
- **Cadence review is a real gate**: After every three task-changing commits, Codex review is required before more risky implementation. Prime should still prepare non-conflicting candidate tasks during the gate.

## Stale Task Cleanup

Stale top tasks must be closed, archived, or superseded so Q polling does not re-run old work:

- **Stale Active Tasks**: If an Active Task was completed by a parallel session or coordinator inline, the lane must recognize the completion marker and not re-execute.
- **Archiving Protocol**: Completed tasks move to an Archived section or are cleared entirely. The authoritative completion record is in the Write/Completion Log.
- **Superseded Tasks**: If a Candidate Task is obsoleted by later work, it is marked Superseded rather than left as a stale candidate.
- **Duplicate Detection**: Before executing any Active Task, the lane verifies the task body has not already been completed by another session.

## Read-Check Heartbeats and Commit Discipline

Read-check-only commits are **not valid substitute work** and must not spam `main`:

- **Read Checks in queue files**: Timestamped read-check entries belong in the queue file's Read Checks section as an audit log, not as standalone commits.
- **Heartbeat evidence lives in session state**: Queue heartbeat/read evidence belongs in session state, UI status, or a bounded coordinator note — not as individual commits to `main`.
- **No dummy commits**: A commit that changes only a read-check line without any task progress is not a valid work product. Bundled read-check updates accompanying actual task changes are acceptable.
- **30-second polling, 10-minute logging**: Lanes poll every 30 seconds but only append read-check entries approximately every 10 minutes while truly idle. Excessively frequent heartbeat commits are noise.

## Unique Worktrees (Hard Invariant)

Multi-session build systems use dedicated worktrees per session. These are **hard invariants**:

- **Path Isolation**: Each session operates in a unique worktree (e.g., `polaris-wt/chat_XXXXXXX` or `polaris-wt/s_XXXXXXXXXX`). Sessions must never share a worktree.
- **No Shared Main Worktree**: The `C:\Users\scott\Code\Meridian` main worktree must not be used for automated build/review work. If a session finds itself in the main worktree or sharing with another lane, it must stop and report the worktree violation.
- **Assigned Queues (Hard Invariant)**: Each session reads only its assigned build or review queue file. Cross-queue execution is forbidden.
- **Branch-Movement Permission (Hard Invariant)**: Sessions must not move branches. Branch switching, creation, or deletion requires Scott or Prime explicit permission.
- **Merge Conflicts**: Pull and merge gracefully before pushing; use `ort` strategy for automatic resolution.
- **Lock Files**: Remove stale `.git/index.lock` files before retrying git operations if concurrent sessions interfere.

## Provider/Model Limit Handling

When a provider or model limit blocks a lane, Prime must take one of these actions:

- **Reduce active lanes**: Pause lower-priority lanes to free model capacity for critical work.
- **Switch allowed models/providers**: Route the lane to an alternative model or provider that is within limits.
- **Reassign non-model-bound work**: Route docs-only tasks, review tasks, or FileMap registration tasks to the blocked lane since these do not consume model quota.
- **Signal the block**: Mark the queue as blocked with the specific limit reason so other lanes and Prime can adjust routing.

## Lane Ownership

Each build lane owns a specific subset of files and tasks:

- **Allowed Files**: Only edit files explicitly listed in the active task.
- **No Cross-Lane Edits**: Do not edit other lanes' queue files or owned files.
- **Scope Discipline**: Keep task scope tight; do not expand beyond listed files without coordination.

## Queue Structure

```
## Active Task
Goal: <task title>
Allowed files only: <comma-separated file paths>
Task: <detailed description>

## Next Candidate Task
Goal: <next task title>
Allowed files only: <comma-separated file paths>
Task: <detailed description>

## Read Checks
<timestamped entries>

## Write/Completion Log
<task completion entries>
```

### Read Check Format

```
YYYY-MM-DD HH:MM TZ - Build X checked queue; status: idle/running/blocked; <details>
```

### Task Execution Sequence

1. Pull `origin/main`
2. Read queue file for Active Task
3. Append Read Check entry
4. Execute task exactly as written (code/docs only)
5. Run tests if specified
6. Commit task changes with clear message
7. Push to `origin/main`
8. Update Obsidian build notes
9. Mark slice "Ready for Codex Review" in queue file
10. Append Write/Completion Log entry
11. Return to step 2 (queue polling)

## Non-Invariant Scenarios

These are **not** violations of the runway invariant:

- **Cadence Pause**: Pausing after 3 commits for Codex cadence (valid gating, candidate tasks still staged).
- **Review Gating**: Awaiting Codex review clearance before executing a repair or new task (valid gate).
- **Cross-Check Activity**: Noting Codex findings or Aegis repairs (valid event logging).
- **Provider/Model Block**: Lane blocked by API limits (valid exception, Prime must reassign or reduce lanes).
- **Human Gate**: Task explicitly marked as requiring human approval before execution.

The invariant is maintained as long as **one of these is true at any moment**:

1. Active Task is executing (status: "running").
2. Next Candidate Task exists and is staged (status: "idle" with candidacy noted).
3. Cadence gating is active (status: "idle" and waiting for cadence clearance).
4. Provider/model limit block is active with Prime aware and acting.
5. Human gate is explicitly required with Prime or Scott aware.

---

**Version**: 2.0  
**Effective**: 2026-06-10  
**Coordinator**: Scott  
**Authority**: Prime queue runway policy coordination — revised per live Meridian orchestration lessons

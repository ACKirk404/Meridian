# Prime Queue Runway Policy

## Overview

The Prime queue runway policy defines the invariant that **Prime keeps build queues fed before workers become idle**. A healthy queue has one executable Active Task, at least one Next Candidate Task, and enough review/cadence context for the worker to know whether it may proceed.

This policy is a Session Lifecycle and Prime Autonomy contract. It exists because human-pasted queue management repeatedly left lanes idle, sent review lanes to build queues, and created noisy read-check commits that looked like progress while no product work moved.

## Core Invariant

**No build queue shall enter an empty runnable state.** At all times, each build lane should have:

- **Active Task**: one executable task currently running or ready to run.
- **Next Candidate Task**: one staged task waiting for promotion.
- **Gate State**: an explicit reason when the Active Task cannot run: cadence pause, Codex review gate, human gate, provider/model limit, worktree violation, branch-permission block, or repair block.

An empty queue is allowed only when Prime has intentionally paused the lane and recorded the gate. "No visible task because the coordinator has not gotten around to it" is a Prime failure.

## Ahead-Of-Idle Assignment

Prime must prepare runway before a worker finishes:

- When assigning an Active Task, also keep a compatible Next Candidate Task in the file.
- When a task is marked Ready for Codex Review, promote or write the next non-conflicting Active Task unless cadence or review risk blocks the lane.
- When a review lane routes a repair, the repair takes priority over unrelated work in that lane.
- When a provider/model limit blocks workers, Prime reduces active lanes, switches to allowed providers/models, or assigns non-model-bound docs/reconciliation work.
- When queue state is stale, Prime archives or supersedes stale top tasks before workers poll them again.

## Cadence Gating

Build lanes operate on a three task-changing commit cadence:

1. **Commits 1-3**: execute task-changing slices inside the lane's assigned scope.
2. **After Commit 3**: pause risky implementation and route Codex Reviews before more task-changing work.
3. **During Pause**: Prime may still prepare Next Candidate tasks and low-risk docs/reconciliation work, but the lane must not execute gated implementation until review clearance.
4. **Cadence Clear**: resume work with fresh Active/Next tasks, or keep the lane explicitly paused with a recorded reason.

This prevents unbounded work accumulation and ensures review gates are respected before major phase transitions.

## Review Gating

- **Active Task Completion**: mark the slice "Ready for Codex Review" with commit hash, files changed, tests run, and proof status.
- **Codex Lane Ownership**: separate Codex Reviews lanes own independent review, findings, clearance, and repair routing.
- **Repair Tasks**: if a Codex lane writes a repair task into a queue, complete it before unrelated work.
- **No Self-Review**: build lanes do not perform their own Codex review.
- **Bounded Continuation**: a Ready marker alone does not always stop a lane before cadence, but Prime must stop the lane for CRITICAL/HIGH findings, routed repairs, explicit gates, or high-risk implementation.

## Idle Fallback And Heartbeats

When no new Active Task is assigned:

1. **Polling**: check the assigned queue every 30 seconds while Q mode is active.
2. **Visible State**: surface last read time, last write time, assigned queue, active task, next candidate, gate state, and blocker in the UI/status layer.
3. **Cross-Check**: every minute while idle, check for review notes, Codex findings, Aegis findings, failing tests, Obsidian updates, or completion markers that unblock the lane.
4. **No Dummy Commits**: read-check-only commits are not work and must not spam `main`. Heartbeat/read evidence belongs in session state, the Review Console, the Bifrost status surface, or a bounded coordinator note when a durable audit record is genuinely needed.
5. **Resteer Escalation**: if a lane polls the same idle/gated state repeatedly, Prime must assign work, record the explicit gate, reassign the lane, or reduce active lanes. Silent waiting is not acceptable orchestration.

## Lane Ownership

Each build lane owns a specific subset of files and tasks:

- **Allowed Files**: only edit files explicitly listed in the active task.
- **No Cross-Lane Edits**: do not edit other lanes' queue files or owned files.
- **Scope Discipline**: keep task scope tight; do not expand beyond listed files without coordination.
- **Assigned Queue**: build sessions read build queues; review sessions read review queues.

## Unique Worktrees

Multi-session build systems use dedicated worktrees per session:

- **Path Isolation**: each session operates in a unique worktree.
- **No Shared State**: local polling state, branch state, and uncommitted changes are isolated per session.
- **Main Worktree Block**: worker/review sessions must not edit from the shared main worktree.
- **Branch Movement Permission**: branch movement requires Scott or Prime permission.
- **Conflict Handling**: merge conflicts and index locks become explicit blockers or Prime recovery actions; workers must not improvise destructive branch movement.

## Why Read-Check-Only Commits Are Not Valid Work

Read checks are useful telemetry, but committing them to `main` as standalone changes creates false progress and buries real build history. Prime must distinguish:

1. **Telemetry**: last read/write heartbeat, queue assignment, active task, gate state, and blocker. Store this in runtime/session state or UI status.
2. **Durable Coordination**: task assignment, repair routing, review clearance, or architectural decision. Commit this when it changes the build plan.
3. **Product Work**: runtime code, tests, docs, contracts, FileMap, UI, or proofs that advance V2.

Only durable coordination and product work should normally commit to `main`. Read-check-only commits require an explicit coordinator reason and should be rare.

## Implementation

### Queue Structure

```text
## Active Task
Goal: <task title>
Allowed files only: <comma-separated file paths>
Task: <detailed description>

## Next Candidate Task
Goal: <next task title>
Allowed files only: <comma-separated file paths>
Task: <detailed description>

## Read Checks
<timestamped entries when a durable note is needed>

## Write/Completion Log
<task completion, review routing, and repair entries>
```

### Task Execution Format

1. Pull `origin/main`.
2. Verify the session is in its unique worktree and assigned queue.
3. Read queue file for the first executable Active Task.
4. Execute the task exactly as written.
5. Run tests/proofs if specified.
6. Commit task-changing changes with a clear message.
7. Push to `origin/main`.
8. Update Obsidian build notes for durable decisions or completions.
9. Mark slice "Ready for Codex Review" in the queue file.
10. Return to queue polling.

### Prime Recovery Actions

Prime may choose one of these actions when runway breaks:

- **Assign**: write or promote an Active Task.
- **Prepare**: add a Next Candidate Task without allowing execution yet.
- **Pause**: record cadence/review/human/provider gate.
- **Resteer**: replace a stale or wrong task with a correct one.
- **Reassign**: move suitable work to another lane with a unique worktree.
- **Reduce**: intentionally shrink active lanes when provider/model quotas are constrained.
- **Escalate**: ask Scott only for final plan review, human gate, or external decision Prime cannot safely make.

## Enforcement

- Prime promotes Next Candidate to Active when prior task reaches "Ready for Codex Review" unless a real gate blocks execution.
- Build lanes refuse tasks that specify files outside "Allowed files".
- Review sessions read review queues; build sessions read build queues.
- Every worker/review session uses a unique worktree.
- Branch movement requires Scott or Prime permission.
- Three task-changing commits per lane trigger Codex review cadence.
- Stale top tasks must be archived, completed, or superseded before the next Q poll can re-run them.

## Non-Invariant Scenarios

These are **not** violations of the runway invariant when explicitly recorded:

- **Review Pause**: cadence 3/3 awaiting Codex review.
- **Human Gate**: awaiting Scott approval for a high-risk plan or final plan review.
- **Provider Limit**: model/provider quota prevents the lane from using the assigned model.
- **Blocked Proof**: test/proof failure requires repair before continuation.
- **Worktree Violation**: worker is in main/shared worktree and must stop.

These are violations:

- No Active Task and no recorded gate.
- Active Task is stale/completed but still first in the file.
- Review lane is reading a build queue as its executable source.
- Build lane is reading a review queue as its executable source.
- Repeated read-check-only commits with no task-changing work or explicit coordinator reason.
- Provider/model limit leaves all lanes idle when Prime could reduce lanes or assign non-model-bound work.

---

**Version**: 2.0
**Effective**: 2026-05-31
**Authority**: Prime queue runway policy coordination

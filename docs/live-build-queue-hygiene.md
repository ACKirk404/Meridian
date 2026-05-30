# Live Build Queue Hygiene

**Status:** Operational guidance — no runtime code  
**Purpose:** Concrete rules for keeping live build queue files clean and useful  
**Derived from:** Build 3 queue polling experience, 2026-05-30

---

## Why Completed Active Tasks Must Be Replaced or Marked Complete

When a lane finishes a task and commits it, the Active Task section in the queue file still shows the old task. The worker has no way to distinguish "task I just completed" from "new task just assigned" without reading the Write/Completion Log.

**This causes:**
- Repeated queue reads with no progress
- Worker waste: each poll verifies the task is already done rather than starting new work
- Ambiguity: is this an old task, a repeated task, or a new assignment?

**Rule:** When a task is complete, the orchestrator/Codex must either replace the Active Task section with the next task or explicitly clear it with a `(none — awaiting assignment)` placeholder. The worker must never re-execute a task whose commit hash is already in the Write/Completion Log.

---

## How Stale Active Task Sections Cause Repeated Queue Checks

A stale Active Task is one whose goal was already delivered and logged. Every poll cycle, the worker reads the task, checks the Write/Completion Log, sees it's done, and logs another idle Read Check entry. After three or four idle polls, the Read Checks section fills with near-identical lines and the signal-to-noise ratio drops.

**Signs of a stale Active Task:**
- The same goal text appears in both Active Task and Write/Completion Log
- The commit hash in the log matches a real commit on main
- No new changes to any allowed file since that commit

**Rule:** The orchestrator should update the Active Task section within one polling cycle (≤30 seconds) of receiving a completion report. If a new task isn't ready yet, write `## Active Task\n\n(none — awaiting next assignment)` rather than leaving the completed task in place.

---

## Why the Four Heartbeat Sections Should Remain Separate

The four sections serve different purposes and different readers:

| Section | Purpose | Writer | Reader |
|---|---|---|---|
| **Read Checks** | Heartbeat — proves the lane is alive and polling | Worker | Orchestrator (detects dead lane) |
| **Write/Completion Log** | Task record — what was delivered and when | Worker | Orchestrator, Prime, audit |
| **Cross-Check Activity** | Finding and fix record — Aegis/review findings | Worker | Codex review, Prime |
| **Codex Review Cadence** | Review record — every 3 commits, findings, repairs | Worker + Codex | Codex, Prime |

Mixing them makes it hard to answer "is this lane alive?" vs "what did it ship?" vs "what did Codex find?" separately. Separate sections also make it easier to trim stale Read Checks entries (which are low-value after a few days) without touching the audit record.

**Rule:** Never merge or abbreviate these into a single log. If a finding or fix also completes a task, log both: one entry in Write/Completion Log, one in Cross-Check Activity.

---

## How Allowed-File Ownership Prevents Lane Collisions

Each Active Task lists explicit `Allowed files only`. This is the lane's ownership boundary for that task.

**Without it:**
- Two lanes edit the same file simultaneously → merge conflict on push
- One lane silently overwrites another lane's in-progress changes
- Blame and rollback become ambiguous

**With it:**
- Each lane knows exactly which files it may touch
- A worker can detect a collision before starting: if an allowed file shows recent changes by another lane, log it in Cross-Check Activity and surface it before editing
- Review is scoped: Codex only needs to check files that belong to this lane

**Rule:** If a task requires a file not in its Allowed list, the worker must not touch it and must report the gap to the orchestrator rather than expanding scope unilaterally.

---

## How Queue Files Should Eventually Map to Meridian Session-Harness Queue State

Today the queue is a plain markdown file that humans and workers read by convention. This works for a build phase but will not scale to a running harness.

**Target state:**
- Queue state lives in a structured object (e.g., a `QueueState` dataclass or a JSON file) read by the harness at wake time
- Each task has explicit fields: `goal`, `allowed_files`, `status` (pending/active/complete), `commit`, `tests`
- The harness sets `status = active` when dispatching a task and `status = complete` when it receives the commit hash
- Workers read the structured state via a harness API, not by parsing markdown
- The markdown queue files become human-readable mirrors of the structured state, not the source of truth

**Intermediate step (before harness integration):**
- Add a `## Status` line to the Active Task section: `status: pending | active | complete`
- Workers check this field first; if `complete`, they skip without re-reading the full task body
- Orchestrator sets `status: pending` when writing a new task, `status: complete` after the commit hash is confirmed

---

## What Prime Should Do When a Lane Is Idle

An idle lane is a worker with no task. Leaving it idle wastes potential build throughput and creates ambiguity about whether the lane is alive.

**Prime's responsibilities when a lane is idle:**

1. **Check Read Checks.** If the most recent Read Check is older than 5 minutes, the lane may be hung or disconnected. Surface a warning in the Review Console.

2. **Assign the next task immediately.** Pull the next queued item from the backlog, scope it to Haiku size, write it into the Active Task section, push, and notify the worker.

3. **If no task is ready:** Write `(none — awaiting next assignment)` in the Active Task section rather than leaving a stale task. This tells the worker that idle is expected, not a bug.

4. **Check Codex review cadence.** If the lane has completed 3 commits without a review, assign a Codex review task before assigning new build work.

5. **Do not let idle accumulate.** Three consecutive idle polls without a new task assignment signals a queue planning gap. Prime should escalate to Scott or pull from the next phase backlog.

---

## Summary

| Problem | Rule |
|---|---|
| Stale Active Task | Replace or clear after completion; never leave a completed task in place |
| Lane can't tell what's new | Worker checks Write/Completion Log before re-executing any task |
| Section mixing | Keep Read Checks, Write/Completion Log, Cross-Check Activity, Codex Review Cadence separate |
| Lane collision | Honor Allowed files only; report gaps rather than expanding scope |
| Long-term scaling | Move queue state to structured object; markdown becomes a human mirror |
| Idle lane | Prime assigns next task immediately or writes explicit `(none)` placeholder |

These rules apply to all live build queue files: `docs/live-build-1.md`, `docs/live-build-2.md`, `docs/live-build-3.md`, `docs/live-build-5.md`, and any future lane files.

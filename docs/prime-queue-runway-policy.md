# Prime Queue Runway Policy

## Overview

The Prime queue runway policy defines the invariant that **every build queue must always maintain at least one Active Task and one Next Candidate Task**. This ensures continuous forward progress, prevents queue stalls, and enables graceful transitions between work items.

## Core Invariant

**No build queue shall enter an empty state.** At all times:
- **Active Task**: One executable task currently running or ready to run
- **Next Candidate Task**: One staged task waiting for Active promotion
- **Fallback**: Read-check-only commits when no new work is available

## Cadence Gating

Build lanes operate on a three-commit cadence:

1. **Commits 1-3**: Execute tasks, append read checks every 10 minutes while idle
2. **After Commit 3**: Pause and await Codex Reviews cadence confirmation before starting new work
3. **Cadence Clear**: Resume work with fresh Active/Next tasks or continue idle polling

This prevents unbounded work accumulation and ensures review gates are respected before major phase transitions.

## Review Gating

- **Active Task Completion**: Mark slice "Ready for Codex Review" with commit hash, files changed, tests run
- **Codex Lane Ownership**: Separate Codex Reviews lane owns independent review, findings, and repair routing
- **Repair Tasks**: If Codex lane writes a repair task into this queue, complete before unrelated work
- **No Self-Review**: Build lanes do not perform their own Codex review

## Idle Fallback

When no new Active Task is assigned:

1. **Read Checks**: Append timestamped Read Checks entry every ~10 minutes indicating idle status
2. **Polling**: Check queue every 30 seconds for new Active Task promotions
3. **Cross-Check**: Every minute while idle, check for review notes, Codex findings, Aegis findings, failing tests, Obsidian updates
4. **No Dummy Work**: Read-check-only commits are valid progress markers—they track queue state and prevent queue abandonment

## Lane Ownership

Each build lane owns a specific subset of files and tasks:

- **Allowed Files**: Only edit files explicitly listed in the active task
- **No Cross-Lane Edits**: Do not edit other lanes' queue files or owned files
- **Scope Discipline**: Keep task scope tight; do not expand beyond listed files without coordination

## Unique Worktrees

Multi-session build systems use dedicated worktrees per session:

- **Path Isolation**: Each session operates in a unique worktree (e.g., `polaris-wt/chat_XXXXXXX`)
- **No Shared State**: Local polling state, branch state, uncommitted changes are isolated per session
- **Merge Conflicts**: Pull and merge gracefully before pushing; use `ort` strategy for automatic resolution
- **Lock Files**: Remove stale `.git/index.lock` files before retrying git operations if concurrent sessions interfere

## Why Read-Check-Only Commits Are Valid

Read-check-only commits (heartbeat entries with no code changes) serve critical functions:

1. **State Tracking**: Record queue state, Active Task status, cross-check activity, and cadence progress
2. **Handoff Prevention**: Prove the queue was checked and no new work was available, preventing abandonment
3. **Audit Trail**: Document idle periods and wait-for-promotion states for retrospectives
4. **CI Integration**: Allow scheduled polling loops to land heartbeat commits without task progress
5. **No Substitute**: However, heartbeat commits alone do not fulfill the "one Active Task" invariant—actual work must eventually run

## Implementation

### Queue Structure

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
YYYY-MM-DD HH:MM TZ - Build X checked queue; status: idle/running/complete; <details>
```

### Task Execution Format

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

## Enforcement

- Coordinator promotes Next Candidate → Active when prior task reaches "Ready for Codex Review"
- Build lanes refuse tasks that specify files outside "Allowed files"
- Merge conflicts are resolved gracefully; index locks are cleared on retry
- Three-commit cadence is enforced: pause after each 3rd commit for Codex cadence check

## Non-Invariant Scenarios

These are **not** violations of the runway invariant:

- **Idle Polling**: Queue checks with no work (valid heartbeat)
- **Staged Candidate**: Next Candidate task waiting for Active promotion (valid runway state)
- **Review Gating**: Pausing after 3 commits for Codex cadence (valid gating)
- **Cross-Check Activity**: Noting Codex findings or Aegis repairs (valid event logging)

The invariant is maintained as long as **one of these is true at any moment**:

1. Active Task is running (status: "running")
2. Next Candidate Task exists and is staged (status: "running" or "idle" with candidacy noted)
3. Cadence gating is active (status: "idle" and waiting for cadence clear from Reviews lane)

---

**Version**: 1.0  
**Effective**: 2026-06-09  
**Coordinator**: Scott  
**Authority**: Prime queue runway policy coordination

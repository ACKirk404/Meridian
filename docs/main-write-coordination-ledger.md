# Main Write Coordination Ledger

Purpose: coordinate every write to Meridian shared `main` between the Meridian V2 coordinator and the front-end developer.

## Hard Rule

Neither the Meridian coordinator nor the front-end developer may write to, push to, merge into, cherry-pick into, rebase, reset, salvage, or otherwise move `main` without coordinating with the other party first.

Coordination means:

1. Post an intent entry in this ledger.
2. Wait for an explicit ACK from the other party.
3. Verify the agreed window is still active.
4. Perform only the approved path-limited write.
5. Post the completion result in this ledger.

No read-check-only update counts as coordination approval.

## Shared Main Gate

Before any approved write to `main`, the writer must verify:

- `C:\Users\scott\Code\Meridian` is on `main`.
- `git fetch origin main` has completed.
- Shared main is clean: no staged files, no dirty files, no untracked worker artifacts.
- The writer's affected worktree or branch is clean.
- The movement scope is explicit and path-limited.
- No worker implementation files are being written directly from shared main unless both parties explicitly approved that exact movement.

## Coordination Cycle

Use this cadence whenever either party expects to write:

- **Intent:** post before touching `main`.
- **ACK:** other party confirms, rejects, or asks for a narrower scope.
- **Lease:** default write window is 10 minutes after ACK unless a different window is recorded.
- **Completion:** writer records commit hash, pushed/not pushed, files changed, proof, and final `main` status.
- **Handoff:** if the lease expires, the writer must post expired/aborted before trying again.

## Intent Template

```text
Time:
Writer: Meridian coordinator | Front-end developer
Requested action: commit | push | cherry-pick | merge | rebase | fast-forward | salvage | cleanup
Target base:
Path-limited scope:
Reason:
Proof to run:
Expected duration:
Requires other party ACK: yes
Status: Intent posted
```

## ACK Template

```text
Time:
ACK by:
Intent acknowledged:
Approved scope:
Lease expires:
Conditions:
Status: ACK granted | ACK denied | needs narrower scope
```

## Completion Template

```text
Time:
Writer:
Intent:
Action completed:
Commit(s):
Pushed to origin/main: yes | no
Files changed:
Proof run:
Final shared main status:
Notes/blockers:
Status: Complete | Aborted | Blocked
```

## Active Coordination

No active write lease.

## Completed Coordination Log

Start new entries below this line.

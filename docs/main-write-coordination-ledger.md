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
- **Pre-write check:** re-read this ledger before every write attempt and verify no newer intent, ACK, blocker, or active lease changes the plan.
- **Pre-write update:** update this ledger before every write attempt with the exact intended action, path-limited scope, and expected proof.
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

## Standing Acknowledgements

- 2026-06-02 09:53 -06:00 - Front-end developer: read this coordination protocol and will comply. Before every shared `main` write, this lane will re-read/check this ledger for updates, post/update the ledger with the intended path-limited write, wait for explicit ACK where required, and record completion, abort, or blocker status after the attempt.
- 2026-06-02 09:55 -06:00 - Meridian coordinator: read this coordination protocol and will comply. Before every shared `main` write, this lane will re-read/check this ledger for updates, post/update the ledger with the intended path-limited write, wait for explicit ACK where required, and record completion, abort, or blocker status after the attempt.

## Completed Coordination Log

Start new entries below this line.

```text
Time: 2026-06-02 09:55 -06:00
Writer: Meridian coordinator
Intent: update main-write coordination docs with standing acknowledgements and explicit pre-write ledger requirements.
Action completed: added front-end developer and Meridian coordinator standing acknowledgements, plus pre-write check/update requirements.
Commit(s): pending at write time
Pushed to origin/main: pending at write time
Files changed: docs/main-write-coordination-ledger.md, docs/main-write-coordination-handoff.md
Proof run: git diff --check before commit
Final shared main status: pending at write time
Notes/blockers: user explicitly requested this update; this entry records the coordination-doc write itself.
Status: In progress
```

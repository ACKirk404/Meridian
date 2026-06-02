# Main Write Coordination Handoff

Share this with anyone working on Meridian V2 who may need to write to shared `main`.

## Rule

Neither the Meridian coordinator nor the front-end developer may write to `main` without coordinating with the other one first.

The shared coordination file is:

`docs/main-write-coordination-ledger.md`

Before any `main` write, the writer must post intent there and wait for an explicit ACK from the other party.

## What Requires Coordination

Coordination is required before:

- committing on shared `main`
- pushing `main`
- cherry-picking into `main`
- merging, rebasing, fast-forwarding, or resetting `main`
- salvaging or moving work between branches/worktrees
- writing implementation files from `C:\Users\scott\Code\Meridian`
- cleaning/quarantining unexpected dirty shared-main files

## Minimum Protocol

1. Writer posts an intent entry in `docs/main-write-coordination-ledger.md`.
2. Writer re-reads/checks the ledger immediately before every write attempt.
3. Writer updates the ledger before every write attempt with exact action, path-limited scope, and expected proof.
4. Other party replies with ACK, denial, or narrower scope.
5. Writer verifies shared main is clean and the affected worktree is clean.
6. Writer performs only the approved path-limited action.
7. Writer posts completion with commit hash, proof, push status, changed files, and final main status.

Default lease: 10 minutes after ACK.

If the lease expires, post `Expired/Aborted` and request a fresh ACK.

## Periodic Updates

While both parties are active:

- Post a heartbeat every 10 minutes if waiting, reviewing, or preparing a write.
- Post immediately before starting a write.
- Post immediately after completing, aborting, or blocking a write.
- If shared main becomes dirty unexpectedly, stop and post a blocker before moving work.

## Current Handoff State

As of this handoff:

- Main-write coordination is mandatory.
- `docs/main-write-coordination-ledger.md` is the source of truth for write leases.
- No active write lease is granted unless the ledger says so.
- Read-check-only queue updates do not count as progress or approval.
- The front-end developer lane has read the protocol and will re-read/check the ledger before every shared `main` write, update the ledger before every write attempt, and record completion, abort, or blocker status after the attempt.
- The Meridian coordinator lane has read the protocol and will re-read/check the ledger before every shared `main` write, update the ledger before every write attempt, and record completion, abort, or blocker status after the attempt.

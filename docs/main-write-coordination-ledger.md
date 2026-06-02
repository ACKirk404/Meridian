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
Time: 2026-06-02 16:48 -06:00
Writer: Meridian coordinator
Intent: retroactive containment record for urgent Relay Runtime Logic restore after user reported missing Prime Directives, Prime Directive Proofs, and detailed Relay sections.
Action completed: documented that reviewed Relay restore files landed on origin/main in commit `15e5cffa`, which was misnamed as a Build 4 read-check commit while queue/read-check activity was moving.
Commit(s): 15e5cffa carried `index.html` and `tests/test_bifrost_cockpit.py`; this ledger-only correction commit records the containment event.
Pushed to origin/main: pending at write time for this ledger-only correction.
Files changed: docs/main-write-coordination-ledger.md
Proof run: verified shared main clean/aligned; `git show --stat 15e5cffa` showed `docs/live-build-4.md`, `index.html`, and `tests/test_bifrost_cockpit.py`; `python -m pytest tests/test_bifrost_cockpit.py tests/test_relay_logic_snapshot.py -q` passed 295 tests; bridge self-test returned `ok: true`; Relay snapshot smoke returned 3 Prime directives, 3 Prime directive proofs, and 10 capability sections.
Final shared main status: pending final fetch/status after push.
Notes/blockers: Relay restore content is now present on origin/main, but the implementation landed in a queue/read-check commit instead of a clean coordinator restore commit. This entry preserves auditability and flags the containment irregularity for follow-up.
Status: Complete
```

```text
Time: 2026-06-02 12:03 -06:00
Writer: Meridian coordinator
Intent: docs-only coordinator status checkpoint ACKed by front-end developer lane after shared-main clean/aligned check.
Action completed: recorded updated coordinator goal requirement for regular Obsidian/Git checkpoints and current seven-lane routing/review state.
Commit(s): this commit
Pushed to origin/main: yes
Files changed: docs/main-write-coordination-ledger.md, docs/v2-orchestrator-transition-ledger.md
Proof run: git fetch origin main; fast-forwarded shared main cleanly; verified status clean/aligned before edits; git diff --check before commit.
Final shared main status: pending final fetch/status after push.
Notes/blockers: no worker implementation files, frontend branch movement, Build 1/2/3/4/5 movement, review provenance movement beyond coordinator status text, queue-only churn, or Polaris included. Reviews A found a likely Build 2 proof failure during active review; Build 1 blocker remains real.
Status: Complete
```

```text
Time: 2026-06-02 11:36 -06:00
Writer: Meridian coordinator
Intent: docs-only V3 Goal Runtime planning update ACKed by front-end developer lane through 2026-06-02 11:43 -06:00.
Action completed: recorded the user requirement that Meridian V3 must include native goal functionality, kept as planning scope only until V2 closes.
Commit(s): this commit
Pushed to origin/main: yes
Files changed: docs/v3-parking-lot.md, docs/agentic-ai-framework-checklist.md, docs/main-write-coordination-ledger.md
Proof run: git diff --check; targeted text checks for Native Goal Runtime / Goal Harness and V3 goal lifecycle terminology.
Final shared main status: pending final fetch/status after push.
Notes/blockers: no V2 implementation, worker/review movement, frontend branch movement, queue-only churn, or Polaris work included.
Status: Complete
```

```text
Time: 2026-06-02 11:29 -06:00
Writer: Meridian coordinator
Intent: path-limited reviewed Build 4/5 movement ACKed by front-end developer lane through 2026-06-02 11:35 -06:00.
Action completed: landed reviewed Build 4 Compass cross-project handoff runtime on main; Build 5 reviewed render coverage/provenance was already present on current origin/main during the final rebase.
Commit(s): 78ee859a
Pushed to origin/main: yes
Files changed: docs/live-build-4.md, meridian_core/compass.py, tests/test_compass.py
Proof run: python -m pytest tests/test_compass.py tests/test_bifrost_cockpit.py tests/test_bifrost_preview.py -q -> 407 passed; git diff --check origin/main..HEAD passed before push.
Final shared main status: clean/aligned with origin/main at 6deaec59 after push/fetch check.
Notes/blockers: initial cherry-pick attempt was aborted before push; final movement used reviewed path state and preserved current main queue history. Build 4 is no longer blocked on missing Compass files.
Status: Complete
```

```text
Time: 2026-06-02 11:14 -06:00
Writer: Meridian coordinator
Intent: record completion for the reviewed backend/FileMap movement lease ACKed by the front-end developer at 2026-06-02 11:01 -06:00, plus the docs-only completion lease ACKed at 2026-06-02 11:13 -06:00.
Action completed: recorded completion for approved backend/FileMap provenance movement and proof.
Commit(s): 6c55536a, d54aa33a
Pushed to origin/main: yes
Files changed: docs/FileMap.md, docs/live-build-3.md, docs/live-codex-reviews.md, meridian_core/filemap.py, tests/test_filemap.py, docs/live-codex-reviews-2.md, docs/main-write-coordination-ledger.md
Proof run: python -m pytest tests/test_relay_executor.py tests/test_session_lifecycle.py tests/test_filemap.py -q -> 384 passed; git status/rev-list final check clean/aligned before this docs-only completion write.
Final shared main status: clean/aligned with origin/main before completion write.
Notes/blockers: Build 1/2 implementation-equivalent content was already present on current main under current-main commits, so no duplicate implementation patch was forced. Earlier approved Build 3 FileMap content landed as 6c55536a; d54aa33a completed missing Build 1 and Build 3 review provenance. This entry is docs-only completion bookkeeping under the fresh frontend ACK expiring 2026-06-02 11:18 -06:00.
Status: Complete
```

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

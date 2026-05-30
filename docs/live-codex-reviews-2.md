# Live Codex Reviews B Queue

This file is the standing queue for a second specialized Codex Reviews session.

Review A and Review B are a scaling prototype for Prime. When review pressure backs up, Prime should be able to spawn additional review capacity, assign bounded scope, and merge the results back into the shared checkpoint ledger.

## Role

Codex Reviews B owns docs, architecture, FileMap, Bifrost, and strategic consistency reviews unless Prime assigns a different scope.

Codex Reviews A (`docs/live-codex-reviews.md`) owns runtime, package API, tests, behavior, and code-level regression reviews unless Prime assigns a different scope.

Both review lanes must declare scope before reviewing, and neither lane may silently broaden scope into the other's territory.

## Rules

- Always pull latest `origin/main` before reviewing.
- Do not implement product code.
- Do not edit runtime files, package exports, or tests.
- Own review coordination files, docs/architecture review records, and repair routing only.
- Review completed build slices by commit hash.
- Inspect the target diff and directly necessary supporting docs only.
- For docs-only slices, check for stale claims, contradictions, missing references, FileMap gaps, and scope drift.
- Record review results in this file.
- If a docs/architecture finding requires repair, write the repair Active Task back into the original build lane queue.
- CRITICAL and HIGH findings block the lane until repaired.
- MEDIUM findings should usually be repaired before more work unless intentionally deferred.
- LOW findings may be deferred, but must be recorded.
- Update Obsidian build notes in `G:\My Drive\Aesop Academy\Obsidian\Meridian_Build` when a review finds or clears important architecture issues.

## Review Inputs

Poll these files:

- `docs/live-build-3.md`
- `docs/live-build-4.md`
- `docs/live-build-5.md`
- `docs/live-codex-reviews.md`

Look for:

- `Ready for Codex Review`
- completed docs/architecture commits without a review result
- FileMap changes that need consistency checks
- Bifrost/cockpit/interface briefs that need architecture alignment
- repair tasks waiting for verification

## Checkpoint Ledger

| Build lane | Last reviewed commit | Last reviewed task | Review status | Pending finding / repair | Next action |
| --- | --- | --- | --- | --- | --- |
| Build 3 | ef934b1 | FileMap refresh + FileMap Relay maturity repair (Round 1, reviewed by Review A) | passed | none | review `4075ef4` in Round B1 |
| Build 4 | 736b6af | architecture consistency pass (Round 1, reviewed by Review A) | passed | none | review `1d17fa1` in Round B1 |
| Build 5 | d1d32af | Bifrost cockpit queue status + V0 cockpit layout (Round 1, reviewed by Review A) | passed | none | review `7c34566` in Round B1 |

## Review Round Scope

Before starting each review round, write the scope here.

```text
YYYY-MM-DD HH:MM TZ - Round B<n> scope
Build lanes: <Build 3, Build 4, Build 5>
Commit range(s): <Build 3 abc; Build 4 def; Build 5 ghi>
Allowed review files: <diff files only or named supporting files>
Tests to run: <targeted tests or docs-only>
Out of scope: <runtime/API/test areas owned by Review A>
Reason: <ready marker, cadence review, repair verification, user request>
```

## Read Checks

Append entries here when this file is checked while idle.

```text
YYYY-MM-DD HH:MM TZ - Codex Reviews B checked queue; status: idle/running/blocked; notes: <short note>
```

## Review Log

Append one entry per reviewed slice.

```text
YYYY-MM-DD HH:MM TZ - Reviewed Build <n> commit <hash>; result: pass/finding/blocked; tests: <summary>; notes: <short note>
```

## Findings

Append findings here before routing repairs.

```text
YYYY-MM-DD HH:MM TZ - Build <n> commit <hash>; severity: CRITICAL/HIGH/MEDIUM/LOW; file: <path>; finding: <short note>; action: clear/defer/repair-task-written
```

## Repair Routing Log

Append entries when writing repair work into a build lane.

```text
YYYY-MM-DD HH:MM TZ - Routed repair to Build <n>; queue: docs/live-build-<n>.md; finding: <short note>; status: pending
```

## Active Task

Current Active Task:

Goal: perform Codex Reviews B Round B1 for docs/architecture slices currently blocking reassignment.

Allowed files:

- `docs/live-codex-reviews-2.md`
- `docs/live-build-3.md`
- `docs/live-build-4.md`
- `docs/live-build-5.md`

Review scope to declare before deep review:

- Build 3: review `4075ef4` (FileMap refresh for `relay_dispatch.py`, live Codex Reviews, Prime prototype, and diagrams) plus queue marker `6879bd9` as needed.
- Build 4: review `1d17fa1` (Prime orchestration state model) plus queue marker `14ae1e9` as needed.
- Build 5: review `7c34566` (Bifrost Harness dashboard brief) plus queue marker `3026216` as needed.

Required review process:

1. Pull latest `origin/main`.
2. Append a Round B1 entry under `## Review Round Scope`.
3. Review only the target diffs and directly necessary supporting docs.
4. Run `python -m pytest tests/test_filemap.py -q` for Build 3.
5. Treat Build 4 and Build 5 as docs-only unless their diffs unexpectedly touch runtime code.
6. Update the Checkpoint Ledger, Review Log, Findings, and Repair Routing Log.
7. If findings require repair, write the repair Active Task into the original build lane queue.
8. Do not touch runtime files or tests except to run tests.
9. Commit only review/queue file changes and push to `origin/main`.
10. Update Obsidian if Round B1 finds or clears important issues.

Completion marker:

- Mark Round B1 complete, passed, repair routed, or blocked with exact commit hashes and tests run.

Write log:

- 2026-05-30 12:22 -06:00 - Coordinator created Codex Reviews B and queued Round B1 for docs/architecture review scaling.

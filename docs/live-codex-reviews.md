# Live Codex Reviews Queue

This file is the standing queue for Codex Reviews A, the runtime/code review session.

The build lanes build. Review lanes review.

This queue is also a Prime prototype. The checkpoint ledger, review scope declaration, repair routing, and lane-clearing logic are not throwaway process. They are intended to become part of Meridian's orchestration harness: Prime should eventually own this loop natively instead of relying on humans to paste work between sessions.

When idle, check this file every 30 seconds. Also inspect `docs/live-build-1.md` through `docs/live-build-5.md` for slices marked `Ready for Codex Review`, stale active tasks, or repair completions.

Codex Reviews A owns runtime, package API, tests, behavior, and code-level regression reviews unless Prime assigns a different scope.

Codex Reviews B (`docs/live-codex-reviews-2.md`) owns docs, architecture, FileMap, Bifrost, and strategic consistency reviews unless Prime assigns a different scope.

This split is deliberate: Meridian must be able to dynamically spawn review sessions when the review queue becomes the bottleneck. Every review session must declare scope and checkpoints before it starts so parallel review capacity does not create duplicate or conflicting findings.

## Rules

- Treat this workflow as future Prime behavior: review state, checkpoints, scope, and repair routing are orchestration-harness responsibilities.
- Always pull latest `origin/main` before reviewing.
- Do not implement product code.
- Do not edit runtime files, package exports, tests, or architecture docs except when an Active Task explicitly says this review lane may update queue/review records.
- Coordinate scope with `docs/live-codex-reviews-2.md` before reviewing docs/architecture slices.
- Own review coordination files and live queue routing only.
- Review completed build slices by commit hash.
- Inspect the diff, compare it to the lane's allowed files and task text, and run targeted tests when code changed.
- For docs-only slices, inspect for stale claims, contradictions, missing references, and scope drift.
- Record each review result in this file.
- If there are no actionable findings, mark the source build lane clear and eligible for new work.
- If there are actionable findings, write a repair Active Task back into the original build lane's queue file. The original builder repairs its own slice.
- CRITICAL and HIGH findings block the lane until repaired.
- MEDIUM findings should usually be repaired before more work unless the finding is intentionally deferred by Codex.
- LOW findings may be deferred, but must be recorded.
- After every three task-changing commits from any one build lane, perform a cadence review before that lane receives more normal build work.
- Update Obsidian build notes in `G:\My Drive\Aesop Academy\Obsidian\Meridian_Build` when a review finds or clears important issues.

## Review Inputs

Poll these files:

- `docs/live-build-1.md`
- `docs/live-build-2.md`
- `docs/live-build-3.md`
- `docs/live-build-4.md`
- `docs/live-build-5.md`

Look for:

- `Ready for Codex Review`
- completed commits without a review result
- three-commit cadence triggers
- CRITICAL/HIGH/MEDIUM/LOW findings
- stale Active Task sections that were already completed
- repair tasks waiting for verification

## Checkpoint Ledger

This is the review lane's cursor. Update it after every review pass so the next poll knows exactly what has and has not been cleared.

| Build lane | Last reviewed commit | Last reviewed task | Review status | Pending finding / repair | Next action |
| --- | --- | --- | --- | --- | --- |
| Build 1 | fd35a81 | Relay PromptPacket assembly helper + RelayDispatchPlan domain model (6af04d4..fd35a81) | passed | observational: FileMap entry for `meridian_core/relay_dispatch.py` is missing — fold into next Build 3 FileMap refresh (no repair routed) | await next Ready for Codex Review marker |
| Build 2 | bf15569 | PromptPacket package API note cleanup + is_valid/validation_errors claim repair (4be1117..bf15569) | passed | none | await next Ready for Codex Review marker |
| Build 3 | ef934b1 | FileMap refresh + FileMap Relay maturity repair (7ec16ac..ef934b1) | passed | observational: next FileMap refresh should add `meridian_core/relay_dispatch.py` (introduced by Build 1 fd35a81 after this commit) | await next Ready for Codex Review marker |
| Build 4 | 736b6af | architecture consistency pass — Q button reference + cadence closure | passed | none | await next Ready for Codex Review marker |
| Build 5 | d1d32af | Bifrost cockpit queue status brief + V0 cockpit layout brief (818bb31..d1d32af) | passed | none — Build 5 cadence pause cleared by this review | await next Ready for Codex Review marker |

Checkpoint rules:

- `Last reviewed commit` must be an actual commit hash, not "latest".
- `Review status` must be one of: `pending review`, `passed`, `repair routed`, `repair pending verification`, `blocked`, `deferred`.
- When a repair is routed, keep the original commit in `Last reviewed commit` and put the repair requirement in `Pending finding / repair`.
- When the repair lands and passes verification, update `Last reviewed commit` to the repair commit and set `Review status` to `passed`.
- Do not advance a lane's checkpoint just because a newer commit exists. Advance only after review.
- If multiple commits land before the next review, review the full range from the checkpoint to the newest completed commit and record the range in `Last reviewed task`.

## Review Round Scope

Before starting each review round, write the scope here. This prevents the review lane from silently reviewing a different set of files than the build lane intended.

```text
YYYY-MM-DD HH:MM TZ - Round <n> scope
Build lanes: <Build 1, Build 2, ...>
Commit range(s): <Build 1 abc..def; Build 2 ghi>
Allowed review files: <files or "diff files only">
Tests to run: <targeted tests or docs-only>
Out of scope: <files/areas explicitly not reviewed>
Reason: <ready marker, cadence review, repair verification, user request>

2026-05-30 15:30 CDT - Round 1 scope
Build lanes: Build 1, Build 2, Build 3, Build 4, Build 5
Commit range(s): Build 1 6af04d4..fd35a81; Build 2 4be1117..bf15569; Build 3 7ec16ac..ef934b1; Build 4 736b6af; Build 5 818bb31..d1d32af
Allowed review files: diff files in each commit range only
Tests to run: Build 1 — pytest tests/test_relay_packet.py tests/test_relay_dispatch.py; Build 3 — pytest tests/test_filemap.py; Build 2/4/5 — docs-only
Out of scope: working-tree modifications to .mcp.json, meridian_core/review_console.py, tests/test_prompt_budget.py (not part of any reviewed commit; left untouched)
Reason: first centralized review sweep — Ready for Codex Review markers on all 5 lanes
```

Scope rules:

- Declare scope before reading deeply or writing findings.
- If scope changes mid-review, add a new scope entry instead of silently broadening it.
- Review only files changed by the target commit/range unless the scope explicitly names supporting files needed for correctness.
- If the changed files include areas owned by another active lane, record that as a scope concern before reviewing.
- For repair verification, scope is the repair commit plus the original finding.
- For cadence review, scope is the lane's commits since the last passed checkpoint.

## Read Checks

Append entries here when this file is checked while idle.

```text
YYYY-MM-DD HH:MM TZ - Codex Reviews checked queue; status: idle/running/blocked; notes: <short note>

2026-05-30 15:30 CDT - Codex Reviews checked queue; status: running; notes: starting Round 1 centralized review sweep — Build 1 through Build 5 all have Ready for Codex Review markers.
2026-05-30 15:45 CDT - Codex Reviews checked queue; status: idle (Round 1 complete); notes: 9 commits reviewed, all passed, no findings, no repairs routed; all 5 lanes cleared for next assignment.
```

## Review Log

Append one entry per reviewed slice.

```text
YYYY-MM-DD HH:MM TZ - Reviewed Build <n> commit <hash>; result: pass/finding/blocked; tests: <summary>; notes: <short note>

2026-05-30 15:30 CDT - Reviewed Build 1 commit 6af04d4; result: pass; tests: pytest tests/test_relay_packet.py 18/18 passed (covered jointly with fd35a81); notes: assemble_relay_packet() helper is pure-domain glue; reads route.prompt_budget; defaults source_lineage to direct_input; validates via build_prompt_packet(); thorough test coverage.
2026-05-30 15:30 CDT - Reviewed Build 1 commit fd35a81; result: pass; tests: pytest tests/test_relay_dispatch.py 23/23 passed; notes: RelayDispatchPlan + RelayDispatchLane frozen dataclasses; build_relay_dispatch_plan() maps route+packet to per-lane payloads using packet.model_payload() only; Tier 0 produces empty lanes; lane order preserved; payload exactly equals model_payload() with no metadata leakage.
2026-05-30 15:30 CDT - Reviewed Build 2 commit 4be1117; result: pass; tests: docs-only (no tests required); notes: prompt-packet-package-api-note.md cleanly rewritten as post-export record; correct PromptPacketError → PromptPacketValidationError; references commits 0ce0cf9, f2f69ff, e73b840 (all present in history).
2026-05-30 15:30 CDT - Reviewed Build 2 commit bf15569; result: pass; tests: docs-only (no tests required); notes: removed stale is_valid/validation_errors claim; replaced with accurate exception-based contract description; verified by grep — no is_valid/validation_errors symbols exist in meridian_core/prompt_packet.py.
2026-05-30 15:30 CDT - Reviewed Build 3 commit 7ec16ac; result: pass; tests: covered jointly with ef934b1; notes: 6-line FileMap.md additions for tokens.py, review-console contract, relay-packet plan, queue hygiene, bifrost brief, live-build-5 — narrow and scope-appropriate.
2026-05-30 15:30 CDT - Reviewed Build 3 commit ef934b1; result: pass; tests: pytest tests/test_filemap.py 46/46 passed; notes: FileMap repair is comprehensive — relay.py now correctly states "carries CouncilPlan and PromptBudgetPlan for every dispatch"; prompt_budget.py reclassified from "no integration yet" to integrated; relay_packet.py added with related_tests=[tests/test_relay_packet.py]; bifrost-cockpit-queue-status-brief.md added; FileArea.BIFROST enum added; required-path coverage updated.
2026-05-30 15:30 CDT - Reviewed Build 4 commit 736b6af; result: pass; tests: docs-only (no tests required); notes: narrow consistency pass — Q button note in meridian-capabilities-architecture-map.md now correctly cross-references docs/bifrost-session-queue-activation-brief.md (verified present); Codex review cadence closed in live-build-4.md log.
2026-05-30 15:30 CDT - Reviewed Build 5 commit 818bb31; result: pass; tests: docs-only (no tests required); notes: bifrost-cockpit-queue-status-brief.md is a coherent 13-section strategic brief; cross-references docs/cockpit-ui-architecture.md and docs/polaris-ui-lessons-for-meridian.md (both verified present); canonical lane status set + Beacon contract + Polaris lessons clearly documented.
2026-05-30 15:30 CDT - Reviewed Build 5 commit d1d32af; result: pass; tests: docs-only (no tests required); notes: bifrost-v0-cockpit-layout-brief.md is a coherent 14-section V0 layout brief; cross-references both companion briefs (verified present); ASCII layout sketch + scaling rules + "leave out" list are scope-appropriate; cadence pause cleared.
```

## Findings

Append findings here before routing repairs.

```text
YYYY-MM-DD HH:MM TZ - Build <n> commit <hash>; severity: CRITICAL/HIGH/MEDIUM/LOW; file: <path>; finding: <short note>; action: clear/defer/repair-task-written

2026-05-30 15:30 CDT - Round 1 sweep: no CRITICAL, HIGH, MEDIUM, or LOW findings across Build 1 (6af04d4, fd35a81), Build 2 (4be1117, bf15569), Build 3 (7ec16ac, ef934b1), Build 4 (736b6af), Build 5 (818bb31, d1d32af). All 9 reviewed commits cleared. No repair tasks routed.
2026-05-30 15:30 CDT - Observational (not a finding): Build 1 fd35a81 introduced meridian_core/relay_dispatch.py after Build 3's most recent FileMap refresh (ef934b1). Next Build 3 FileMap refresh should add a FileMapEntry for relay_dispatch.py and its tests. Not routed as a repair — this is normal forward FileMap work, not stale wording.
```

## Repair Routing Log

Append entries when writing repair work into a build lane.

```text
YYYY-MM-DD HH:MM TZ - Routed repair to Build <n>; queue: docs/live-build-<n>.md; finding: <short note>; status: pending

2026-05-30 15:30 CDT - No repairs routed in Round 1. All 5 lanes clear and eligible for next assignment.
```

## Active Task

Current Active Task:

Goal: perform centralized Codex Review sweep Round 2.

Review lane split:

- Codex Reviews A handles Build 1 and Build 2 runtime/API/code review.
- Codex Reviews B handles Build 3, Build 4, and Build 5 docs/architecture review in `docs/live-codex-reviews-2.md`.
- Do not duplicate Review B's docs/architecture review unless Prime explicitly reassigns it back here.

Allowed files:

- `docs/live-codex-reviews.md`
- `docs/live-build-1.md`
- `docs/live-build-2.md`

Review scope to declare before deep review:

- Build 1: review `d2820d2` (`WorkerLaneState` domain model) plus queue marker `13b4b48` as needed.
- Build 2: review `46e4eb3` (Relay package API policy note) plus queue markers `c8f7a35`, `3e1de48`, and `37bcd7a` as needed.

Required review process:

1. Pull latest `origin/main`.
2. Append a Round 2 entry under `## Review Round Scope` before reviewing deeply.
3. Review only the target diffs and directly necessary supporting files.
4. Run targeted tests:
   - `python -m pytest tests/test_lane_state.py -q`
   - Run broader `python -m pytest -q` only if review finds integration risk.
5. Treat Build 2 as docs-only unless its diff touches runtime code.
6. Update the Checkpoint Ledger, Review Log, Findings, and Repair Routing Log.
7. If findings require repair, write the repair Active Task into the original build lane queue. Do not repair it in the Codex Reviews lane.
8. Commit only review/queue file changes and push to `origin/main`.
9. Update Obsidian if Round 2 finds or clears important issues.

Completion marker:

- Mark Round 2 complete, passed, repair routed, or blocked with exact commit hashes and tests run.

Write log:

- 2026-05-30 12:06 -06:00 - Coordinator queued Round 2 centralized review sweep for Build 1 through Build 5.
- 2026-05-30 12:22 -06:00 - Coordinator split Round 2: Review A keeps Build 1/2 code/API review; Review B now owns Build 3/4/5 docs/architecture review in `docs/live-codex-reviews-2.md`.

Previous state:

No active task. Round 1 centralized review sweep complete (2026-05-30 15:45 CDT).

- Build 1 (6af04d4..fd35a81): passed
- Build 2 (4be1117..bf15569): passed
- Build 3 (7ec16ac..ef934b1): passed
- Build 4 (736b6af): passed
- Build 5 (818bb31..d1d32af): passed — cadence pause cleared

No CRITICAL / HIGH / MEDIUM / LOW findings. No repairs routed.

When idle, continue polling `docs/live-codex-reviews.md` and `docs/live-build-1.md`..`docs/live-build-5.md` every 30 seconds for new `Ready for Codex Review` markers, cadence triggers, or repair-verification needs.

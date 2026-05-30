# Live Codex Reviews Queue

This file is the standing queue for Codex Reviews A, the runtime/code review session.

The build lanes build. Review lanes review.

## Q Polling Source of Truth

When the Polaris `Q` button is enabled for **Codex Reviews A**, the session must read this file first and treat this file as its executable queue. Build queue files are review inputs only: inspect them for `Ready for Codex Review` markers, cadence triggers, commit hashes, and repair status, but do not execute build-lane Active Tasks from a review session.

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
- Record proofs for every review pass. A pass without proof is not a clearance; it is only an opinion.
- For docs-only slices, inspect for stale claims, contradictions, missing references, and scope drift.
- Record each review result in this file.
- If there are no actionable findings, mark the source build lane clear and eligible for new work.
- If there are actionable findings, write a repair Active Task back into the original build lane's queue file. The original builder repairs its own slice.
- CRITICAL and HIGH findings block the lane until repaired.
- MEDIUM findings should usually be repaired before more work unless the finding is intentionally deferred by Codex.
- LOW findings may be deferred, but must be recorded.
- After every three task-changing commits from any one build lane, perform a cadence review before that lane receives more normal build work.
- A single `Ready for Codex Review` marker is a review signal, not automatically a build stop. Normal build work may continue until the lane reaches three task-changing commits since its last checkpoint, unless a reviewer has routed a repair, marked the lane blocked, or Prime explicitly escalates the slice as high risk.
- Reviews should catch up in parallel while builders keep moving. Prime's default throughput target is three build slices per active lane per review cadence.
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
| Build 1 | 190e527 (Reviews C delegated) | Build 1 V0 Relay executor skeleton (delegated to Reviews C Round C1); Reviews A Round 2 covered d2820d2; Round 1 covered 6af04d4..fd35a81 | passed | LOW observational: lane_state transition helpers can't clear fields through helper surface (use dataclasses.replace); FileMap entry for `meridian_core/relay_dispatch.py` still missing — Build 3 to fold into next refresh (no repair routed) | await next Ready for Codex Review marker |
| Build 2 | d821106 (A) + 989366f (Reviews C delegated) | Relay executor API policy note (Reviews A Round 3) + prime_wake/prime_console/prime_status/route_to_console (Reviews C Round C1); Round 2 covered 46e4eb3; Round 1 covered 4be1117..bf15569 | passed | LOW deferred (Reviews C): route_to_console accepts any ReviewConsoleItemType but always creates a non-promptable INFO ACKNOWLEDGE item — V1 doc/narrow item_type recommended; LOW observational (Reviews A Round 2): Build 2 self-recorded APPROVE cadence entry in 3e1de48 before Codex Reviews A's Round 2 result existed | Build 2 cadence cleared for window ending at 989366f; await next Ready for Codex Review marker |
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
- Do not use a pending review alone as a reason to stop a builder lane before the three-commit cadence threshold. Stop the lane only for cadence, routed repair, explicit block, or high-risk Prime escalation.

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

2026-05-31 16:25 CDT - Round 2 scope (Codex Reviews A — code/API portion)
Build lanes: Build 1, Build 2
Commit range(s): Build 1 d2820d2 (+ queue marker 13b4b48); Build 2 46e4eb3 (+ queue markers c8f7a35, 3e1de48, 37bcd7a)
Allowed review files: diff files in d2820d2, 46e4eb3 only; queue markers verified as Build 2 queue log entries with no code/docs changes
Tests to run: pytest tests/test_lane_state.py (Build 1 code); Build 2 — docs-only
Out of scope: Build 3, Build 4, Build 5 (owned by Codex Reviews B per coordinator split 2026-05-30 12:22 -06:00); persistent working-tree modifications to .mcp.json, meridian_core/review_console.py, tests/test_prompt_budget.py
Reason: Round 2 centralized review sweep — Codex Reviews A handles runtime/code/API only
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
2026-05-31 16:25 CDT - Codex Reviews A checked queue; status: running; notes: starting Round 2 — Build 1 d2820d2 (WorkerLaneState code) + Build 2 46e4eb3 (Relay policy note); Build 3/4/5 owned by Codex Reviews B.
2026-05-31 16:35 CDT - Codex Reviews A checked queue; status: idle (Round 2 A-portion complete); notes: 2 commits reviewed, both passed; 1 LOW observational + 1 LOW process note recorded; no repairs routed.
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
2026-05-31 16:30 CDT - Reviewed Build 1 commit d2820d2; result: pass; tests: pytest tests/test_lane_state.py 37/37 passed; notes: WorkerLaneState frozen dataclass + LaneStatus (9 states) + LaneReviewState (5 states); transition helpers (mark_running/mark_blocked/mark_ready_for_review/mark_review_passed) use dataclasses.replace and return new instances; pure domain — no I/O, no datetime parsing; mark_review_passed correctly clears active_task to "" using raw literal not the if-pattern.
2026-05-31 16:30 CDT - Reviewed Build 2 commit 46e4eb3; result: pass; tests: docs-only (no tests required); notes: relay-package-api-policy-note.md correctly records assemble_relay_packet, RelayDispatchLane, RelayDispatchPlan, build_relay_dispatch_plan, count_tokens as intentional internals — verified by grep that none appear in meridian_core/__init__.py; package-api-surface-note.md updated with cross-reference and matching "What Stays Internal" entry; three-condition export gate (external need / stable shape / no undocumented dependencies) is reasonable and explicit; build_prompt_packet() correctly noted as already exported.
```

## Proof Log

Append proof entries here before marking a slice passed.

Proof is the evidence behind the review result. It should be short, specific, and reproducible enough that Prime can later turn it into Aegis evidence or Review Console proof cards.

```text
YYYY-MM-DD HH:MM TZ - Proof for Build <n> commit <hash>; proof type: diff/test/reference/manual; evidence: <short reproducible evidence>; result: pass/fail/deferred

2026-05-30 15:30 CDT - Proof for Build 1 commits 6af04d4..fd35a81; proof type: test; evidence: pytest tests/test_relay_packet.py and tests/test_relay_dispatch.py passed; result: pass
2026-05-30 15:30 CDT - Proof for Build 3 commits 7ec16ac..ef934b1; proof type: test/reference; evidence: pytest tests/test_filemap.py passed and FileMap entries matched expected paths; result: pass
2026-05-30 15:30 CDT - Proof for Build 4 commit 736b6af; proof type: reference; evidence: referenced bifrost-session-queue-activation brief exists and doc claims match current architecture notes; result: pass
2026-05-30 15:30 CDT - Proof for Build 5 commits 818bb31..d1d32af; proof type: reference/manual; evidence: referenced cockpit/UI briefs exist and docs-only scope matched allowed files; result: pass
2026-05-31 16:30 CDT - Proof for Build 1 commit d2820d2; proof type: test/diff; evidence: pytest tests/test_lane_state.py 37/37 passed; diff inspection confirms frozen dataclass, dataclasses.replace transitions, no I/O, all 9 LaneStatus + 5 LaneReviewState members and all 4 transition helpers present; result: pass
2026-05-31 16:30 CDT - Proof for Build 2 commit 46e4eb3; proof type: reference/diff; evidence: `grep -n "assemble_relay_packet|RelayDispatchLane|RelayDispatchPlan|build_relay_dispatch_plan|count_tokens" meridian_core/__init__.py` returned zero matches; package-api-surface-note.md now contains cross-reference to relay-package-api-policy-note.md; result: pass
```

Minimum proof expectations:

- Runtime/code slices: targeted tests plus diff inspection.
- Package/API slices: import/export smoke check or targeted tests plus diff inspection.
- FileMap slices: `tests/test_filemap.py` plus path/reference verification.
- Docs/architecture slices: referenced-file existence checks plus contradiction/scope inspection.
- Repair verification: original finding, repair commit, and test/reference evidence that the finding is closed.

## Findings

Append findings here before routing repairs.

```text
YYYY-MM-DD HH:MM TZ - Build <n> commit <hash>; severity: CRITICAL/HIGH/MEDIUM/LOW; file: <path>; finding: <short note>; action: clear/defer/repair-task-written

2026-05-30 15:30 CDT - Round 1 sweep: no CRITICAL, HIGH, MEDIUM, or LOW findings across Build 1 (6af04d4, fd35a81), Build 2 (4be1117, bf15569), Build 3 (7ec16ac, ef934b1), Build 4 (736b6af), Build 5 (818bb31, d1d32af). All 9 reviewed commits cleared. No repair tasks routed.
2026-05-30 15:30 CDT - Observational (not a finding): Build 1 fd35a81 introduced meridian_core/relay_dispatch.py after Build 3's most recent FileMap refresh (ef934b1). Next Build 3 FileMap refresh should add a FileMapEntry for relay_dispatch.py and its tests. Not routed as a repair — this is normal forward FileMap work, not stale wording.
2026-05-31 16:30 CDT - Round 2 A-portion sweep: no CRITICAL, HIGH, or MEDIUM findings across Build 1 (d2820d2) and Build 2 (46e4eb3). Two LOW observational items only. No repair tasks routed.
2026-05-31 16:30 CDT - Build 1 commit d2820d2; severity: LOW; file: meridian_core/lane_state.py; finding: transition helpers use `value if value else self.value` pattern, so callers cannot pass `""` through the helpers to deliberately clear `active_task`/`last_commit`/`last_poll_at`/`notes` — they would need `dataclasses.replace` directly; `mark_blocked` and `mark_ready_for_review` also omit a `last_poll_at` parameter while `mark_running` accepts it (mild API asymmetry); action: defer — design choice, not a bug; revisit if Prime needs to clear fields through the helper surface.
2026-05-31 16:30 CDT - Build 2 commit 3e1de48; severity: LOW; file: docs/live-build-2.md (Codex Review Cadence section); finding: Build 2 self-recorded a "Codex review result: APPROVE" for commits 4be1117/bf15569/46e4eb3 at 16:55 -06:00, before Codex Reviews A had recorded a Round 2 result for 46e4eb3; coordinator queued Round 2 at 12:06 -06:00 the same minute, so this was likely a coordinator-driven cross-check rather than a procedural violation; action: defer — record only. Codex Reviews A's own Round 2 result (this entry) is the authoritative review of 46e4eb3.
2026-06-01 04:00 CDT - Round 3 A-portion sweep: no CRITICAL, HIGH, MEDIUM, or LOW findings for Build 2 d821106. Delegated Round C1 (Build 1 190e527, Build 2 e800c03, Build 2 989366f) was already cleared by Reviews C with one LOW deferred on route_to_console; that LOW is tracked in `docs/live-codex-reviews-3.md` and does not duplicate here. No repair tasks routed by Reviews A.
```

## Repair Routing Log

Append entries when writing repair work into a build lane.

```text
YYYY-MM-DD HH:MM TZ - Routed repair to Build <n>; queue: docs/live-build-<n>.md; finding: <short note>; status: pending

2026-05-30 15:30 CDT - No repairs routed in Round 1. All 5 lanes clear and eligible for next assignment.
2026-05-31 16:30 CDT - No repairs routed in Round 2 A-portion. Build 1 and Build 2 (code/API scope) clear and eligible for next assignment.
2026-06-01 04:00 CDT - No repairs routed in Round 3 A-portion. Build 2 d821106 clear; Reviews C Round C1 already cleared Build 1 190e527 + Build 2 e800c03/989366f. Build 2 cadence now fully clear.
```

## Active Task

Round 3 complete (2026-06-01 04:00 CDT).

- Build 2 d821106 (Relay executor API policy note): passed — policy correctly defers exports as future work; verified by grep that none of the 5 names (ModelCallFn, RelayExecutionResult, RelayExecutionError, RelayExecutionSummary, execute_relay_dispatch_plan) appear in meridian_core/__init__.py.
- Reviews C Round C1 delegated scope verified complete in docs/live-codex-reviews-3.md: Build 1 190e527 (Relay executor skeleton), Build 2 e800c03 (prime_wake), Build 2 989366f (prime_console/prime_status/route_to_console) — all passed with one LOW deferred (route_to_console type-vs-semantics doc note).

Build 2 cadence cleared for the three-commit window ending at 989366f. Build 1 cadence cleared by Reviews C for the window covering 190e527. No repairs routed by Reviews A in Round 3.

Round 3 write log:

- 2026-06-01 03:55 CDT - Codex Reviews A started Round 3 (Build 2 d821106 + delegation verification).
- 2026-06-01 04:00 CDT - Codex Reviews A completed Round 3. 1 commit passed (d821106); delegated Round C1 confirmed clear in docs/live-codex-reviews-3.md.

When idle, continue polling `docs/live-codex-reviews.md` and `docs/live-build-1.md`/`docs/live-build-2.md` every 30 seconds for new Ready-for-Codex-Review markers, cadence triggers, or repair-verification needs.

Stale prior status follows.

Round 2 A-portion complete (2026-05-31 16:35 CDT).

- Build 1 d2820d2 (WorkerLaneState): passed — pytest tests/test_lane_state.py 37/37
- Build 2 46e4eb3 (Relay package API policy note): passed — docs-only, internal-name claim verified via grep against meridian_core/__init__.py

No CRITICAL / HIGH / MEDIUM findings. Two LOW observational items recorded in Findings. No repairs routed. Build 1 and Build 2 cleared and eligible for next assignment.

Build 3, Build 4, Build 5 remain Codex Reviews B's scope per coordinator split (2026-05-30 12:22 -06:00) — tracked in `docs/live-codex-reviews-2.md`.

Round 2 write log:

- 2026-05-30 12:06 -06:00 - Coordinator queued Round 2 centralized review sweep for Build 1 through Build 5.
- 2026-05-30 12:22 -06:00 - Coordinator split Round 2: Review A keeps Build 1/2 code/API review; Review B now owns Build 3/4/5 docs/architecture review in `docs/live-codex-reviews-2.md`.
- 2026-05-31 16:35 CDT - Codex Reviews A completed Round 2 A-portion. 2 commits passed, 2 LOW observational items, no repairs routed.

When idle, continue polling `docs/live-codex-reviews.md` and `docs/live-build-1.md`/`docs/live-build-2.md` every 30 seconds for new Ready-for-Codex-Review markers, cadence triggers, or repair-verification needs.

Previous state:

No active task. Round 1 centralized review sweep complete (2026-05-30 15:45 CDT).

- Build 1 (6af04d4..fd35a81): passed
- Build 2 (4be1117..bf15569): passed
- Build 3 (7ec16ac..ef934b1): passed
- Build 4 (736b6af): passed
- Build 5 (818bb31..d1d32af): passed — cadence pause cleared

No CRITICAL / HIGH / MEDIUM / LOW findings. No repairs routed.

When idle, continue polling `docs/live-codex-reviews.md` and `docs/live-build-1.md`..`docs/live-build-5.md` every 30 seconds for new `Ready for Codex Review` markers, cadence triggers, or repair-verification needs.

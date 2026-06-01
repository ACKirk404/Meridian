# FileMap V2/V3 Discoverability Audit

**Owner:** Build 3 / FileMap
**Purpose:** Keep Prime from losing important V2/V3 architecture context at wake by listing which planning, contract, and horizon files must be discoverable through `meridian_core/filemap.py`.
**Scope:** Docs-only audit. This file records follow-up tasks; it does not authorize runtime edits.

## Rule

Every V2/V3 architecture file that changes Prime behavior, harness ownership, provider trust, session lifecycle, Bifrost cockpit behavior, or V3 intake must be discoverable in the runtime FileMap before Prime can rely on it during orchestration.

## Current Coverage

- [x] `docs/v2-detailed-build-plan.md` - V2 roadmap and build sequencing.
- [x] `docs/v2-progress-tracker.md` - countable V2 status source.
- [x] `docs/agentic-ai-framework-checklist.md` - V3 entry point and framework checklist.
- [x] `docs/v3-parking-lot.md` - V3 horizon parking lot.
- [x] `docs/federation-harness-horizon.md` - Federation planning/horizon contract.
- [x] `docs/workflow-subagent-harness-contract.md` - workflow/sub-agent contract baseline.
- [x] `docs/session-lifecycle-v2-contract.md` - session lifecycle contract baseline.
- [x] `docs/session-card-queue-activation-contract.md` - Q-mode/session card product contract.
- [x] `docs/deepseek-provider-validation-gate.md` - DeepSeek provider trust gate.

## Resolved FileMap Tasks

- [x] Register `docs/workflows-subagent-harness-architecture.md`.
  - Reason: this is the architecture note for using workflow/sub-agent contexts to prevent Prime's orchestrator context from filling with harness working memory.
  - Owner: Build 3.
  - Resolution: registered in `meridian_core/filemap.py` and `_REQUIRED_PATHS` in `tests/test_filemap.py`.

## Pending Upstream Outputs

These files are expected from queued work but do not exist yet, so they are not FileMap misses today:

- [ ] `docs/bifrost-voice-command-contract.md` - Build 5 active task.
- [ ] `docs/bifrost-balance-payload-surface-contract.md` - Build 5 next candidate.
- [ ] `docs/workflow-subagent-usage-checklist.md` - Build 4 active task.
- [ ] `docs/deepseek-validation-benchmark-plan.md` - Build 4 next candidate.
- [ ] `docs/session-lifecycle-implementation-checklist.md` - Build 2 active task.

## Prime Wake Implication

Prime can now find both the workflow contract baseline and the newer architecture note that explains why harness work should move into bounded workflow/sub-agent contexts. The remaining items in this audit are pending upstream outputs, not current FileMap misses.

## Completion Criteria

This audit is complete when it is committed, review-routed, and the listed current miss is registered. Future missing files should be added as explicit Build 3 FileMap tasks after their source documents exist. Do not silently bundle future missing files into unrelated runtime work.

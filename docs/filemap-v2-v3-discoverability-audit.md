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

## Resolved Upstream Outputs

All previously pending files have now landed and been registered in FileMap:

- [x] `docs/bifrost-voice-command-contract.md` - completed by Build 5, registered in FileMap.
- [x] `docs/bifrost-balance-payload-surface-contract.md` - completed by Build 5, registered in FileMap.
- [x] `docs/workflow-subagent-usage-checklist.md` - completed by Build 4, registered in FileMap.
- [x] `docs/deepseek-validation-benchmark-plan.md` - completed by Build 4, registered in FileMap.
- [x] `docs/session-lifecycle-implementation-checklist.md` - completed by Build 2, registered in FileMap.

## Prime Wake Implication

Prime can now find all V2 architecture files needed for wake: V2 contract baselines, implementation guides, provider validation gates, and horizon planning. All built-and-review-cleared V2 artifacts are discoverable in the runtime FileMap.

## Completion Criteria

This audit is complete when it is committed, review-routed, and the listed current miss is registered. Future missing files should be added as explicit Build 3 FileMap tasks after their source documents exist. Do not silently bundle future missing files into unrelated runtime work.

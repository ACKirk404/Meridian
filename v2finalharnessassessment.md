# Meridian V2 Final Harness Assessment

This assessment looks beyond the current V2 wiring status and asks what each
harness would still need to reach its full potential. V2 currently gives many
harnesses truthful, display-safe visibility; it does not make every harness
fully executable or fully mature.

## Summary

Every harness still has meaningful headroom. The strongest V2 completion risk is
not that the harnesses are absent, but that detailed capability review can be
mistaken for full execution authority. V2 should close the display-safe review
surface for the harness system, while treating the deeper executable features as
V3/V4 roadmap unless explicitly pulled into scope.

## Roadmap Alignment Note

After checking the Obsidian Meridian build vault, this assessment should not be
treated as a standalone V3/V4 roadmap. Obsidian already has a V3 intake path:

- `G:\My Drive\Obsidian\Meridian_Build\2026-05-31 Build 4 V3 Parking Lot.md`
  mirrors the repo `docs/v3-parking-lot.md` decision that V3 starts only after
  V2 closes.
- `docs/agentic-ai-framework-checklist.md` is the V3 entry gate.
- `docs/v3-intake-resolution.md` resolves the framework gaps into V3,
  move-earlier, later-horizon, or reject decisions.
- `docs/v3-goal-runtime-contract.md` already gives the native Goal Runtime /
  Goal Harness a bounded V3 contract.

Therefore the right use of this file is as a **V2.5 harness hardening and triage
list**, not as a competing roadmap. Items already promoted to V3 by
`docs/v3-intake-resolution.md` should stay in V3. Items parked for later should
stay V4+ unless Scott explicitly promotes them. V2.5 should capture only the
near-term harness improvements that are too small or too operationally necessary
to wait for V3, while not reopening V2 completion.

Known V2-facing closeout gap at assessment time:

- `HMS5`: Relay-mediated model interaction remains a checklist closeout gate.
- `HMS10`: Harness diagnostics remains a checklist closeout gate.

## Orchestrator Harnesses

### Prime

Missing full-potential features:

- Durable decision memory.
- Explicit intent graph across active work.
- Priority arbitration across sessions and projects.
- Risk budget management.
- Rollback and undo planning.
- Clear "why this next" explanation for orchestration choices.

### Bifrost

Missing full-potential features:

- Real voice capture, STT, TTS, mute, interruption, and voice-selection runtime.
- Adaptive layouts by task state and risk.
- Accessibility audit mode.
- User correction memory.
- Live reconciliation when backend snapshots drift from visible UI state.

### Relay

Missing full-potential features:

- True Auto routing.
- Provider selection authority.
- Fallback execution.
- Model-route simulation before dispatch.
- Confidence scoring per route.
- Cost, latency, trust, and proof tradeoff optimization.
- Post-call route quality learning.

### Beacon

Missing full-potential features:

- Active intervention policy.
- Escalation thresholds.
- Heartbeat anomaly clustering.
- Stale-worker recovery recommendations.
- Longitudinal reliability scoring per harness/session.

### Security

Security is the largest full-potential gap because it is still mostly a reserved
identity rather than a mature guardrail runtime.

Missing full-potential features:

- Secret scanning.
- Permission policy engine.
- Local path and data-leak scanner.
- Risky-action approval gates.
- Account and credential boundary enforcement.
- Audit-grade redaction proofs.

### Aegis

Missing full-potential features:

- Executable crosscheck runs.
- Repair routing authority.
- Proof sufficiency scoring.
- Waiver and exception lifecycle.
- Evidence freshness tracking.
- "What would falsify this?" proof planning.

### Compass

Missing full-potential features:

- Richer project ontology.
- Dependency graph between projects.
- Scope conflict detection.
- Objective drift alerts.
- Cross-project handoff plans.
- Project health and trajectory scoring.

### Vulcan / Session Lifecycle

Missing full-potential features:

- Real session close/write-through execution.
- Recovery workflow.
- Stale session repair.
- Suspend/resume semantics.
- Session provenance graph.
- Safe session migration between worktrees.

### Atlas

Missing full-potential features:

- Semantic retrieval.
- Citation ranking.
- Chunk lineage.
- Context packing.
- Stale knowledge detection.
- Retrieval evaluation.
- Explanation of why context was selected.

### Charon / FileMap

Missing full-potential features:

- Live ownership graph.
- Impact analysis.
- Stale FileMap detection.
- Automatic related-test inference.
- Architecture boundary checks.
- Safe navigation from capability to code to proof.

### Arbiter / Codex Reviews

Missing full-potential features:

- Review queue prioritization.
- Duplicate finding collapse.
- Severity calibration.
- Review assignment.
- Repair verification loop.
- Waiver ledger.
- Regression-risk scoring.

### Workflow

Missing full-potential features:

- Executable sub-agent dispatch.
- Dependency-aware task planning.
- Lane capacity management.
- Worker handoff protocol.
- Failure recovery.
- Structured task-result ingestion.

### Federation

Missing full-potential features:

- Real multi-node protocol.
- Trust handshake.
- Remote capability discovery.
- Packet signing.
- Degraded/offline behavior.
- External collaboration boundaries.

### Echo

Missing full-potential features:

- Writable memory.
- Memory conflict handling.
- Decay and expiry.
- Retrieval by situation.
- User preference learning.
- Mistake memory.
- Memory provenance and audit controls.

### Ratchet / Tool

Missing full-potential features:

- Real tool registry.
- Permissioned execution.
- Dry-run mode.
- Reversible action planning.
- Tool result normalization.
- Sandbox policy.
- Tool failure repair routing.

### Source / Git

Missing full-potential features:

- Branch lease automation.
- Merge conflict planner.
- Commit intent verification.
- Diff risk scoring.
- Rollback bundle creation.
- Provenance tags.
- Main-write safety automation.

### Vision / Browser

Missing full-potential features:

- Real browser/page state capture.
- Visual diffing.
- Screenshot evidence linking.
- DOM/action planner.
- Safe navigation policy.
- Browser-task replay.

### Autonomy / Release

Missing full-potential features:

- Release readiness scoring.
- Deployment plan generation.
- Changelog and proof packaging.
- Rollback gates.
- Release risk forecast.
- Automated "cannot release because..." summaries.

## Model Harness Layer

The model harness layer is the richest full-potential area. The UI already names
many of the right aspects, but the full system still needs deeper backend-backed
authority.

Missing full-potential features:

- Provider adapters with verified identity and health.
- Exact prompt payload assembly and hashing.
- Response artifact capture.
- Cost, latency, and token metering.
- Trust state expiration.
- Model comparison/council mode.
- Policy and privacy enforcement before dispatch.
- Route replay and debugging.
- Per-model evaluation history.
- Fallback quality learning.
- Full evidence chain from intent to payload to provider to response to
  validation.

## V2.5 Recommendation

V2 should close the display-safe capability review for all harnesses. It should
not attempt to build every full-potential executable feature.

The immediate V2 closeout should focus on:

- Promoting or explicitly scoping `HMS5`.
- Promoting or explicitly scoping `HMS10`.
- Keeping executable Tool, Git, Browser, Security, model routing, release, and
  session-control powers blocked until reviewed backend authority exists.

After V2 closes, convert this assessment into a V2.5 build list by reconciling
each item against `docs/v3-intake-resolution.md`:

- If already promoted to V3, leave it in V3.
- If already moved earlier, verify whether V2 actually delivered it or whether a
  narrow V2.5 hardening item is needed.
- If parked for later, leave it V4+ unless Scott explicitly promotes it.
- If it is a small operational hardening gap with no V3 owner, keep it in V2.5.

The full-potential features above should not become an implicit V2 requirement.

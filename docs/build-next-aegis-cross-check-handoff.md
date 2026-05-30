# Future Handoff: Aegis Cross-Check Evidence

Do not run this until Build 2 has completed and committed the Review Console slice.

## Goal

Build the first Aegis proof/evidence slice that can accept automatic cross-check findings and connect them to Review Console items.

## Read First

- `context.md`
- `docs/cross-check-aegis-integration-brief.md`
- `docs/build-2-review-console-handoff.md`
- `docs/claude-handoff-completion-protocol.md`

## Scope

Allowed files after Review Console is complete:

```text
meridian_core/aegis.py
tests/test_aegis.py
```

You may import from `meridian_core.review_console`, but do not rewrite the Review Console API unless a small compatibility change is required and tested.

## Product Rule

Automatic cross-check findings are evidence.

They should feed:

```text
cross-check finding
  -> Aegis evidence record
  -> Review Console item
  -> Prime adjudication
```

## Suggested Objects

```text
AegisEvidence
EvidenceType
EvidenceStatus
EvidenceSeverity
ProofTrail
```

## Required Behavior

- Can create evidence from an automatic cross-check finding.
- Evidence records source, target, status, severity, and summary.
- Evidence can be marked resolved, waived, escalated, or open.
- Proof-blocking evidence can be identified.
- Evidence can produce or reference a Review Console item.
- Domain-only; no model calls, no UI, no persistence.

## Tests

Add focused tests for:

- cross-check finding becomes Aegis evidence
- failing/high-severity evidence can be proof-blocking
- resolved evidence is no longer proof-blocking
- waived evidence records waiver reason
- evidence can create/reference Review Console item
- output is deterministic

## Completion

Follow `docs/claude-handoff-completion-protocol.md`:

- Run `python -m pytest -q`.
- Commit only files for this slice.
- Push to origin.
- Update Meridian Obsidian build notes.

Keep scope tight.

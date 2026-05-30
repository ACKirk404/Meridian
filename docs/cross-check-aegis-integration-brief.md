# Cross-Check And Aegis Integration Brief

## Purpose

Define how automatic cross-check findings should eventually feed Aegis proof and the Review Console.

This is a planning note, not an implementation slice yet.

## Product Rule

Cross-check is automatic in Meridian.

Cross-check findings should appear in the Review Console, not the main Orchestrator Queue, unless Prime chooses to summarize them conversationally.

## Architecture Shape

```text
Prime action or worker output
  -> automatic cross-check
  -> Review Console item
  -> Aegis proof/evidence record
  -> Prime adjudication
  -> retry, repair, approve, gate, or escalate
```

## Review Console Responsibility

The Review Console shows promptable cross-check findings:

- pass/fail
- severity
- affected file/artifact/session
- suggested action
- whether Scott must respond
- whether Prime can continue autonomously

## Aegis Responsibility

Aegis treats cross-check as evidence.

It should preserve:

- check type
- source
- target artifact
- result
- confidence/severity
- timestamp
- proof trail link
- whether the finding was resolved, waived, or escalated

## Prime Responsibility

Prime should not automatically treat every cross-check finding as a human interruption.

Prime should classify:

- informational: visible in Review Console, no action required
- repairable: route back to builder/reviewer/verifier loop
- proof-blocking: Aegis prevents completion claim
- human-gated: Scott must approve, reject, waive, or redirect

## Future Slice

Build a domain-only Aegis proof event model that can accept cross-check evidence and emit Review Console items.

Do not implement until Review Console domain exists.

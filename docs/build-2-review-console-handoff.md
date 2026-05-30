# Build 2 Handoff: Review Console And Automatic Cross-Check Surface

Build 2, please build the Review Console domain slice.

## Read First

- `context.md`
- `docs/non-orchestrator-surface-naming.md`
- `docs/meridian-capabilities.md`
- `docs/claude-handoff-completion-protocol.md`

## Scope

Allowed files:

```text
meridian_core/review_console.py
tests/test_review_console.py
```

You may update docs only if needed to clarify naming.

Do not edit Relay, Risk, Mission, Wake, Intention, Objectives, Builds, or CLI files in this slice.

## Naming

Use `Review Console` as the working product name for the old "non-orchestrator window."

Definition:

```text
Review Console: promptable review/gating surface for artifacts, proof, automatic cross-check findings, system findings, and gates outside the main Prime conversation.
```

## Product Rules

- Automatic cross-check should remain automatic in Meridian.
- Cross-check findings belong in the Review Console, not the main Orchestrator Queue.
- Review Console is not a passive log.
- Review Console is a prompt window: Scott can respond directly to the artifact, proof, plan, comparison, or gate Prime placed there.

## Suggested Objects

```text
ReviewConsoleItem
ReviewConsoleItemType
ReviewConsoleSeverity
ReviewConsoleAction
ReviewConsoleQueue
```

## Item Types

Include at least:

```text
cross_check
plan_review
proof
system_finding
artifact
approval_gate
comparison
```

## Required Behavior

- Can create a cross-check item.
- Can create a plan-review item.
- Can mark whether an item is promptable.
- Can list pending items deterministically.
- Can distinguish informational system findings from user-gated items.
- Can expose suggested actions such as approve, reject, modify, inspect, acknowledge.

## Tests

Add focused tests for:

- cross-check item belongs to Review Console
- cross-check item can be automatic
- Review Console item can be promptable
- approval gate requires user response
- pending items sort deterministically
- item type and severity are explicit

## Completion

Follow `docs/claude-handoff-completion-protocol.md`:

- Run `python -m pytest -q`.
- Commit only files for Build 2.
- Push to origin.
- Update Meridian Obsidian build notes.

Keep scope tight. No UI, persistence, model calls, or worker automation yet.

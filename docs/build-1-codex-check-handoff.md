# Build 1 Follow-Up: Codex Check For Unchecked Slices

Build 1, after finishing your current slice, run a Codex-style check for Meridian work that has not yet had focused Codex review.

## Purpose

Review the recently built Meridian domain slices for correctness, scope control, test coverage, and architecture fit.

## Read First

- `context.md`
- `MISSION.md`
- `docs/meridian-capabilities.md`
- `docs/meridian-pillars.md`
- `docs/claude-handoff-completion-protocol.md`

## Review Scope

Focus on committed Meridian slices that may not have had focused review yet:

```text
meridian_core/risk.py
tests/test_risk.py
meridian_core/relay.py
tests/test_relay.py
```

If Build 1 has completed and committed harness maturity before this check, include:

```text
meridian_core/builds.py
tests/test_builds.py
```

Do not review Build 2's active Review Console files until Build 2 says they are done.

## Review Questions

Check for:

- Does the code match the Meridian architecture in `context.md`?
- Is the slice domain-only and inside scope?
- Are models native Python objects rather than JSON blobs?
- Are risk tier and Relay semantics deterministic?
- Are tests meaningful, not just shallow existence checks?
- Are there duplicate enums or competing concepts?
- Is there any unused import, dead code, or API ambiguity?
- Does CLI/demo output remain useful without becoming UI implementation?

## Output

Write a concise review note with:

- Findings ordered by severity.
- File/line references.
- Any suggested fixes.
- Tests run.

If there are no findings, say that clearly and mention residual risk.

## Completion

If you make no code changes:

- Update Obsidian with the review result.
- Do not commit unless you changed files.

If you make code changes:

- Run `python -m pytest -q`.
- Commit only the review-fix files.
- Push to origin.
- Update Obsidian.

Keep this a review/fix pass, not a new feature build.

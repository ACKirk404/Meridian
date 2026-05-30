# Build 1 Handoff: File Map Knowledge Tracker

Build 1, please build the File Map Knowledge Tracker slice.

## Read First

- `context.md`
- `docs/FileMap.md`
- `docs/package-api-surface-note.md`
- `docs/claude-handoff-completion-protocol.md`

## Goal

Create a domain-level knowledge tracker for important Meridian files so Prime, Echo, Atlas, and worker sessions can find key repository context without rediscovering the codebase every session.

This is the first step toward automatic memory injection of the important-file map.

## Scope

Allowed files:

```text
meridian_core/filemap.py
tests/test_filemap.py
docs/FileMap.md
```

You may update:

```text
meridian_core/__init__.py
```

only if you add stable public exports for the file map API.

Do not edit Aegis, Review Console, Relay, Risk, Builds, or CLI files in this slice.

## Product Intent

Meridian needs a living knowledge tracker for important files and what they do.

It should support:

- quick lookup by path
- lookup by architecture area/harness
- related test discovery
- future visualization
- future Echo/Atlas memory injection

The canonical human-readable file is:

```text
docs/FileMap.md
```

The Obsidian mirror is:

```text
G:\My Drive\Aesop Academy\Obsidian\Meridian_Build\FileMap.md
```

## Suggested Objects

```text
FileMapEntry
FileMap
FileArea
RelatedTest
```

Keep it simple. Native Python objects, not JSON blobs.

## Required Behavior

- Can create entries for important files.
- Each entry includes path, area, purpose, related tests, and notes/cautions.
- Can look up an entry by exact path.
- Can list entries by area.
- Can list entries that have related tests.
- Can produce a small memory-injection summary for a session.
- Unknown file lookup fails clearly or returns explicit `None` behavior with tests.
- Deterministic sample/default map exists for current important Meridian files.

## Initial Important Files

Include at least:

```text
MISSION.md
context.md
docs/FileMap.md
meridian_core/models.py
meridian_core/mission.py
meridian_core/wake.py
meridian_core/intention.py
meridian_core/objectives.py
meridian_core/risk.py
meridian_core/relay.py
meridian_core/review_console.py
meridian_core/builds.py
```

## Tests

Add focused tests for:

- default map contains the core files
- exact path lookup works
- area lookup works
- related tests are tracked
- memory-injection summary includes purpose and related tests
- unknown path behavior is explicit
- output order is deterministic

## Completion

Follow `docs/claude-handoff-completion-protocol.md`:

- Run `python -m pytest -q`.
- Commit only Build 1 files.
- Push to origin.
- Update Meridian Obsidian build notes.

Also update the Obsidian mirror of `docs/FileMap.md` if you change that file:

```text
G:\My Drive\Aesop Academy\Obsidian\Meridian_Build\FileMap.md
```

Keep scope tight. No UI, persistence, model calls, or worker automation yet.

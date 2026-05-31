# Echo Memory Contract

**Status:** V2 first-wave contract — domain slice not yet implemented; runtime in `meridian_core/echo.py` to be built by Build 1 (or other runtime lane) after this contract lands.
**Owner harness:** Echo (durable memory).
**Owner lane (doc):** Build 4 (Opus high-level thinking).
**Audience:** Prime, Atlas, Relay, Aegis, Bifrost, Scott, future contributors.
**Purpose:** Define what Echo stores, how Prime queries it, how results rank, how it fails soft, and how it stays out of Relay's prompt budget without Aegis consent.

Echo is Meridian's **durable memory harness**. It exists so Prime's effective memory is not bounded by any single model context window. Echo holds decisions, project facts, prior plans, gate outcomes, and Scott's standing instructions in a deterministic local store. Prime queries Echo through a typed surface; Atlas and Bifrost render Echo hits without ever feeding raw records into a model prompt.

This document is implementation-facing. It pins the domain shape, ranking rules, failure-soft behavior, prompt-drag guardrails, and the first runtime tests. It does not describe vector search, federation, or cross-Meridian sync — those belong to later horizons.

---

## What Echo Is Not

Echo is not the chat history. Echo is not the worker log. Echo is not the FileMap. Echo is not the Review Console. Echo is not a vector database in the first slice.

Echo only contains what Prime (or Scott via Prime) chose to remember. Writes are explicit. There is no background scraping of conversations, prompts, or queues.

---

## Harness Ownership

| Concern | Owner |
|---|---|
| Store and retrieve memory records | Echo |
| Decide what should be remembered | Prime |
| Decide what enters a model prompt | Relay (with Aegis policy) |
| Render Echo hits to Scott | Bifrost |
| Combine Echo hits with file/doc hits | Atlas (see `docs/atlas-retrieval-contract.md`) |
| Gate destructive memory operations | Aegis + Review Console |

Echo does not call models. Echo does not edit prompts. Echo does not decide what is "important enough" — it accepts a typed importance signal from Prime and ranks accordingly.

---

## Domain Shape

The Echo runtime slice (`meridian_core/echo.py`) introduces three frozen dataclasses. Names and field semantics are normative; field types and exact module layout follow existing `meridian_core` conventions (frozen dataclasses, enums, tuples for collections, no mutation).

### `MemoryRecord`

A single durable memory entry.

- `record_id` — stable identifier, deterministic from content + project + created_at where possible.
- `project` — project key matching existing Meridian project identifiers (e.g., `meridian`, `polaris`, `aesop`).
- `kind` — `MemoryKind` enum: `DECISION`, `FACT`, `PLAN`, `GATE_OUTCOME`, `STANDING_INSTRUCTION`, `NOTE`.
- `summary` — short human-readable string. This is what may be shown in Bifrost and what Atlas may surface in a hit excerpt.
- `body` — longer text. Never injected raw into a prompt without Aegis consent (see prompt-drag guardrails).
- `source` — `MemorySource` enum: `PRIME`, `SCOTT`, `REVIEW_CONSOLE`, `WORKER`, `IMPORT`.
- `created_at` — UTC timestamp.
- `importance` — integer 1–5. Prime sets this when writing. Echo does not infer importance.
- `pinned` — bool. Pinned records are always returned for a matching project query regardless of recency.
- `tags` — tuple of short tag strings for narrow filtering. No free-text indexing in the first slice.
- `superseded_by` — optional `record_id` pointer when a later record replaces this one. Superseded records are excluded from default queries.

`MemoryRecord` is immutable. Updates create a new record and set `superseded_by` on the prior one.

### `MemoryQuery`

A typed query Prime sends to Echo.

- `project` — required. Echo never serves cross-project records by default.
- `kinds` — optional tuple of `MemoryKind`. Empty means "any kind".
- `tags` — optional tuple of tags. Records must contain all listed tags.
- `since` — optional UTC timestamp. Records older than `since` are excluded unless pinned.
- `limit` — maximum hits to return. Echo enforces a hard upper bound (recommended 25 in first slice) regardless of caller value, to prevent prompt-budget abuse downstream.
- `include_superseded` — bool, default false.

### `MemoryHit`

A single ranked result.

- `record` — the `MemoryRecord`.
- `score` — float in `[0.0, 1.0]`. Deterministic from inputs.
- `reason` — short string explaining why the record matched (e.g., `"pinned"`, `"recent + tagged"`, `"importance=5"`). Used by Atlas and Bifrost for explainability.

A query returns `tuple[MemoryHit, ...]` ordered by score descending. Ties break on `pinned` desc, then `importance` desc, then `created_at` desc, then `record_id` asc.

---

## Ranking Inputs

Echo ranks deterministically. No model calls, no learned weights, no random tie-breaks. The first-slice ranker combines four inputs.

| Input | Effect | Notes |
|---|---|---|
| **Project match** | Hard filter | Wrong project ⇒ not returned at all. |
| **Pinning** | Strong boost | Pinned records always score above unpinned for the same project, unless `since` excludes them. |
| **Recency** | Soft boost | Newer records score higher within the same project + pinning band. Use a bounded decay (e.g., linear over a configurable window) so very old records are not equal to fresh ones. |
| **Importance** | Soft boost | Higher `importance` adds to score within the same project + pinning + recency band. |

Tag filters and `kinds` are treated as hard filters, not score inputs.

The scoring function must be a pure function of the record and query. Two calls with the same inputs must return the same hits in the same order.

---

## Deterministic Local Repository

The first slice ships a single repository implementation backed by the local filesystem. There is no remote store, no shared mutable state across machines, no concurrent-writer protocol.

- The repository exposes `add(record)`, `query(query) -> tuple[MemoryHit, ...]`, `get(record_id) -> MemoryRecord | None`, and `supersede(old_id, new_record) -> MemoryRecord`.
- Storage layout, file format, and on-disk path are implementation details of the runtime lane and not pinned by this contract. They must be deterministic, replayable, and safe to commit to git if Scott chooses to.
- Reads are pure functions of on-disk state. Writes are append-only or supersede-only; there is no destructive in-place edit in the first slice.
- The repository must work with zero records — an empty store returns empty results, never an exception.

A single Meridian checkout has one Echo store. Cross-project records are partitioned by `project`. There is no cross-Meridian sync in V2 first wave.

---

## Failure-Soft Behavior

Echo must fail soft. Prime calling Echo should never raise on a missing or empty store, and should never block Relay dispatch on Echo errors.

| Condition | Behavior |
|---|---|
| Store missing or empty | Return empty `tuple[MemoryHit, ...]`. |
| Unknown project | Return empty result. No error. |
| Query with `limit=0` | Return empty result. |
| Query exceeds repository limit | Truncate to repository limit; do not raise. |
| Corrupt record on read | Skip that record; surface a single repository warning to Bifrost; do not raise. |
| Repository write failure | Raise to caller (Prime) — Prime decides whether to retry, escalate to Review Console, or drop the memory. Writes are the only path that may raise. |

"Empty result is normal" is a hard rule. Atlas and Prime must treat an empty Echo result as "no relevant durable memory" — not as a failure.

---

## Prompt-Drag Guardrails

Echo records are durable text. If Relay let them flow into prompts unchecked, Echo would silently inflate every prompt budget. That is the failure mode this contract prevents.

The following rules are normative.

1. **Echo never edits prompts.** Echo returns `MemoryHit` objects to its caller. The caller decides what, if anything, to render or inject.
2. **Relay never injects `MemoryRecord.body` raw.** Only `summary` may flow into a model prompt, and only when Aegis's `CognitionPolicy` for the current action permits it.
3. **`body` is for human inspection.** Bifrost may render `body` for Scott. Prime may quote portions of `body` only after summarizing through an Aegis-approved path.
4. **Default injection is zero.** The default Relay behavior for any new action is "no Echo content in prompt." Inclusion is opt-in per route and per risk tier.
5. **Hard cap on injected hits.** Even when injection is permitted, Relay must cap the number of Echo summaries per prompt (recommended ≤ 5 in first slice) and must record the count in `PromptPacket` telemetry.
6. **Pinned ≠ injected.** Pinning controls retrieval ranking. It does not authorize prompt injection.
7. **Standing instructions are policy, not context.** `MemoryKind.STANDING_INSTRUCTION` records are read by Prime for behavior choice but must not be pasted verbatim into model prompts. Aegis enforces this.
8. **No log dumping.** Worker logs, raw queue text, and chat transcripts are not Echo content. Prime must distill before writing.

Violations of these rules are Aegis findings, not Echo findings. Echo exposes the data; Aegis enforces use.

---

## How Prime Uses Echo

Prime's typical sequence in V2 first wave:

1. Prime decides to act on a project. It issues a `MemoryQuery(project=..., kinds=...)` to Echo.
2. Echo returns ranked hits. Prime reads `summary` and `reason` to choose what is relevant.
3. Prime asks Aegis for the `CognitionPolicy` for the planned action. The policy says whether any Echo content may enter the prompt.
4. If allowed, Prime hands Relay the chosen `MemoryHit` summaries (not bodies, not raw records) with the prompt packet. Relay records the count and total token estimate as telemetry.
5. After the action, Prime writes a new `MemoryRecord` capturing the decision or outcome. Importance and pinning are set explicitly.

Atlas may also query Echo as one of its sources (see `docs/atlas-retrieval-contract.md`). Atlas applies its own re-ranking and never bypasses these prompt-drag rules.

---

## First Runtime Tests

Build 1 (or whichever runtime lane picks up `meridian_core/echo.py`) should land at minimum the following tests in `tests/test_echo.py` before the slice is marked built. These are the proof gates the V2 first-wave Echo slice must clear.

### Domain shape

- `MemoryRecord`, `MemoryQuery`, `MemoryHit` are frozen dataclasses.
- `MemoryRecord` rejects mutation (assignment raises `FrozenInstanceError`).
- `MemoryKind` and `MemorySource` enums cover the values listed above.

### Add and query

- `add` then `query` returns the added record in a single-hit tuple.
- Querying with `project` matching no records returns an empty tuple.
- Querying with an unknown project returns an empty tuple (no exception).
- Querying with `kinds=(DECISION,)` excludes records of other kinds.
- Querying with `tags=("scott",)` excludes records missing the tag.
- Querying with `since=T` excludes records older than `T` unless pinned.

### Ranking

- Pinned record outranks unpinned record of the same project + same recency + same importance.
- Newer record outranks older record of the same project + same pinning + same importance.
- Higher importance outranks lower importance of the same project + same pinning + same recency.
- Score is in `[0.0, 1.0]`.
- Two identical queries return identical hit order (determinism test, run twice and compare).

### Supersession

- A record marked `superseded_by` is excluded by default.
- `include_superseded=True` includes it.
- `supersede(old_id, new_record)` returns the new record and links the old one.

### Limits and safety

- `limit=0` returns an empty tuple.
- `limit` larger than the repository hard cap is truncated, not raised.
- An empty store returns empty tuples for every query.
- A repository read error on one record is skipped; other records still return.

### Failure-soft

- Missing store directory ⇒ empty result, no exception.
- Corrupt single record ⇒ skipped, other records returned.
- Write failure ⇒ raises to caller (Prime), so Prime can route to Review Console.

These tests are domain-only. They do not require model calls, real session lifecycle, or Bifrost rendering. Prompt-injection cap tests live with Relay/Aegis, not Echo.

---

## Out of Scope for V2 First Wave

- Vector embeddings, similarity search, or any non-deterministic ranking.
- Cross-Meridian or cross-machine sync.
- Automatic memory extraction from chat or logs.
- Background "what should I remember?" inference.
- Public/account-level memory adapters.
- Destructive deletion of records (supersede instead).
- Echo-driven prompt injection (Relay + Aegis own that path).

These belong to later V2 waves or to the federation horizon documented in `docs/federation-harness-horizon.md` when it is written.

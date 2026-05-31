# Atlas Retrieval Contract

**Status:** V2 first-wave contract — domain slice not yet implemented; runtime in `meridian_core/atlas.py` to be built by Build 1 (or other runtime lane) after this contract lands.
**Owner harness:** Atlas (retrieval / RAG).
**Owner lane (doc):** Build 4 (Opus high-level thinking).
**Audience:** Prime, Echo, FileMap, Relay, Aegis, Bifrost, Scott, future contributors.
**Purpose:** Define what Atlas retrieves, how `AtlasHit` is shaped, how ranking stays deterministic, what is explicitly excluded from the first slice, how Atlas differs from Echo, and the first runtime tests.

Atlas is Meridian's **retrieval harness**. FileMap declares what matters in the repository; Atlas retrieves the right entries at the right time. The first V2 slice is **docs- and FileMap-first** — no broad filesystem crawl, no embeddings, no vector store. Atlas serves Prime with ranked, source-attributed hits over a known, curated surface.

This document is implementation-facing. It pins the domain shape, the deterministic ranking rules, the source contract, the relationship to Echo, the prompt-drag guardrails, and the first runtime tests.

---

## What Atlas Is Not

Atlas is not a search engine over the whole disk. Atlas is not a vector store. Atlas is not a web fetcher. Atlas does not call models. Atlas does not edit prompts. Atlas does not pull from Echo's `body` text into prompts.

If a file is not in FileMap and is not on a small allowlist of "always-known" docs, Atlas does not see it in the first slice. The implicit claim is: **if it matters enough to retrieve, it matters enough to be in FileMap.**

---

## Harness Ownership

| Concern | Owner |
|---|---|
| Rank and return retrieval hits | Atlas |
| Declare which files matter and why | FileMap |
| Provide durable memory records | Echo (see `docs/echo-memory-contract.md`) |
| Choose what enters a model prompt | Relay (with Aegis policy) |
| Render hits to Scott | Bifrost |
| Issue retrieval queries | Prime |
| Gate model use of hit content | Aegis |

Atlas reads. It does not write FileMap, does not mutate Echo, and does not edit prompts.

---

## Sources in the First Slice

Atlas's first-slice index is the union of two source kinds, both deterministic and cheap to read.

### `FILEMAP` source

FileMap entries are the primary source. Each entry already carries:

- `path` — repository-relative path.
- `area` — coarse grouping (e.g., `meridian_core`, `bifrost`, `docs`).
- `purpose` — short purpose string.
- `notes` — optional notes string.

Atlas reads FileMap through whatever read-only accessor `meridian_core/filemap.py` already exposes. It does not re-parse FileMap files itself.

### `DOC` source

A small allowlist of repository docs that are load-bearing regardless of FileMap state — for example, the V2 detailed build plan, V2 horizon plan, and other top-level contract docs in `docs/`. The allowlist is a tuple of relative paths defined in `meridian_core/atlas.py`. Adding to the allowlist is a code change reviewed by the Build/Codex review cadence.

For `DOC` sources, Atlas reads the file's first heading and an introductory excerpt. It does not parse the entire document.

### `ECHO` source (optional second pass)

Atlas may, in a second pass within the same query, call Echo with a derived `MemoryQuery` and fold the resulting `MemoryHit` summaries into its hit set. In the first runtime slice this pass is optional and disabled by default. When enabled, Atlas:

- Uses only `MemoryHit.record.summary`, never `body`.
- Tags those hits with `source = ECHO`.
- Defers Echo's own ranking; Atlas re-ranks the combined set with its own rules.
- Honors Echo's prompt-drag guardrails — Atlas hits are still subject to Relay/Aegis injection policy downstream.

No other source kinds exist in the first slice. No web fetch, no shell traversal, no git log scrape.

---

## Domain Shape

The Atlas runtime slice introduces a small set of frozen dataclasses in `meridian_core/atlas.py`. Names and field semantics are normative; field types follow existing `meridian_core` conventions (frozen dataclasses, enums, tuples).

### `AtlasHit`

A single retrieval result.

- `path` — repository-relative path to the file or doc. For `ECHO` source, this is the conceptual project key (e.g., `echo://meridian/<record_id>`), not a real path.
- `title` — short human-readable title. For `FILEMAP` source, derived from FileMap purpose or path basename. For `DOC` source, derived from the first heading. For `ECHO`, from `MemoryRecord.summary`.
- `reason` — short string explaining why the hit matched (e.g., `"path token match"`, `"area+purpose"`, `"required path"`, `"notes match"`, `"echo summary"`). Used by Bifrost for explainability and by Aegis for audit.
- `excerpt` — optional short excerpt or summary. For `FILEMAP`, the FileMap `purpose` + `notes`. For `DOC`, the introductory paragraph. For `ECHO`, the `MemoryRecord.summary`.
- `source` — `AtlasSource` enum: `FILEMAP`, `DOC`, `ECHO`.
- `score` — float in `[0.0, 1.0]`, deterministic from query and source data.

### `AtlasQuery`

A typed query Prime sends to Atlas.

- `terms` — tuple of lowercased term strings (e.g., `("echo", "memory")`). Atlas does not do its own tokenization in the first slice; Prime passes the terms it wants matched.
- `areas` — optional tuple of FileMap area names. Hits outside listed areas are excluded.
- `required_paths` — optional tuple of repository-relative paths. Each listed path that exists in FileMap or the doc allowlist is always returned in the hit set with a high score, regardless of term matches. Missing paths are dropped silently and noted in `AtlasResult.missing_paths`.
- `include_echo` — bool. Default false in first slice.
- `project` — optional project key passed through to Echo when `include_echo=True`.
- `limit` — maximum hits to return. Atlas enforces a hard upper bound (recommended 25 in first slice).

### `AtlasResult`

The full response.

- `hits` — `tuple[AtlasHit, ...]` ordered by score descending. Ties break on `source` (FILEMAP > DOC > ECHO), then `path` ascending.
- `missing_paths` — tuple of `required_paths` that were not found. Empty if all required paths resolved.
- `truncated` — bool. True if more candidates existed than `limit` allowed.

Returning a structured result (not a bare tuple) lets Prime and Bifrost surface `missing_paths` and `truncated` without out-of-band channels.

---

## Deterministic Ranking

Atlas ranks deterministically. No model calls, no learned weights, no embeddings, no randomness.

The first-slice ranker combines these inputs.

| Input | Effect | Notes |
|---|---|---|
| **Required path presence** | Hard inclusion + max score | A `required_paths` entry that resolves is always in the hit set with score at or near 1.0. |
| **Path token match** | Strong score | A query term that appears in the path is a strong match. |
| **Title/purpose token match** | Strong score | A query term that appears in the FileMap `purpose` or DOC first heading. |
| **Area filter** | Hard filter | If `areas` is set, non-matching entries are excluded. |
| **Notes token match** | Soft score | A query term that appears in FileMap `notes`. |
| **Excerpt token match** | Soft score | A query term that appears in the DOC introductory excerpt. |
| **Source preference** | Tie-break only | FILEMAP > DOC > ECHO when scores tie. |

The ranker must be a pure function of `AtlasQuery` and the current FileMap/doc snapshot. Two identical calls in the same repository state must return the same hits in the same order.

Matching is case-insensitive substring matching on lowercased text. There is no stemming, no synonym table, no fuzzy match in the first slice. If Prime wants synonym expansion, Prime expands the term list before calling Atlas.

---

## No Broad Crawl, No Embeddings

These rules are normative for the first slice.

1. **No `os.walk` of the repository.** Atlas reads only FileMap entries and the doc allowlist.
2. **No embeddings or vector store.** Ranking is substring + structural, period.
3. **No background indexing job.** Atlas computes per-query against the current FileMap/doc state.
4. **No network calls.** No web fetch, no remote index, no model API.
5. **No write-back to FileMap.** If a useful file is missing from FileMap, Atlas reports it via `missing_paths` (for the required-paths case) and Prime routes a FileMap registration request to Build 3. Atlas does not edit FileMap.

These constraints are what keep Atlas cheap, replayable, and reviewable.

---

## How Atlas Differs From Echo

Echo and Atlas both surface "what should Prime see" but from different sources and with different rules. Confusing them collapses both contracts.

| Dimension | Echo | Atlas |
|---|---|---|
| Source of content | Records Prime/Scott chose to write | Repository files + docs (and optionally Echo summaries) |
| What it stores | Decisions, facts, plans, gate outcomes, standing instructions | Nothing — Atlas is read-only over other sources |
| Determinism | Deterministic ranking over typed inputs | Deterministic ranking over text + structure |
| Mutation | Append/supersede only | None |
| Empty-store behavior | Empty tuple is normal | Empty hits is normal |
| Prompt-drag risk | High (durable text bodies) | Medium (file excerpts, doc intros, FileMap notes) |
| Failure mode | Fail soft on read, raise on write | Fail soft on all reads |

The integration model is simple: **Prime queries Atlas to find files and docs; Prime queries Echo to recall decisions. Atlas may optionally fold Echo summaries into its result set when `include_echo=True`, but the two harnesses remain independently testable and independently owned.**

---

## How Prime Uses Atlas

Typical sequence in V2 first wave:

1. Prime is about to act on a project (e.g., advance a backlog task).
2. Prime constructs an `AtlasQuery` with project-relevant terms, the FileMap areas it cares about, and any `required_paths` for docs Prime knows must be present (e.g., the project's brief, the active contract).
3. Atlas returns an `AtlasResult`. Prime reads `hits[*].title` and `reason` to choose what is actually relevant.
4. Prime asks Aegis for the `CognitionPolicy` for the planned action. The policy says whether any Atlas excerpt may enter the prompt and at what cap.
5. If allowed, Prime hands Relay the chosen `AtlasHit.excerpt` strings (not raw files) with the prompt packet. Relay records the count and total token estimate as telemetry.
6. If `AtlasResult.missing_paths` is non-empty, Prime routes a FileMap registration request to the FileMap lane (Build 3) and continues with what it has.
7. Prime may then issue a follow-up Echo query for decisions tied to the chosen files. Atlas and Echo are independent — Prime composes them.

---

## Prompt-Drag Guardrails

Atlas excerpts are short and structural, but they are still prompt-bearing text. The following rules are normative.

1. **Atlas never edits prompts.** Atlas returns `AtlasHit` objects. The caller decides what, if anything, to render or inject.
2. **Relay never injects whole files.** Only `AtlasHit.excerpt` may flow into a model prompt, and only when Aegis's `CognitionPolicy` permits.
3. **Hard cap on injected hits.** Even when injection is permitted, Relay must cap the number of Atlas excerpts per prompt (recommended ≤ 5 in first slice) and must record the count in `PromptPacket` telemetry.
4. **No transitive Echo body bleed.** When `include_echo=True`, Atlas takes only Echo `summary`. Echo `body` text is never reachable through Atlas.
5. **No log or queue text in excerpts.** Worker logs, live-build-N.md queue files, and chat transcripts are not Atlas content even if they appear in FileMap. Atlas should refuse to surface excerpts from FileMap entries whose `area` is reserved for queue/log content — that exclusion list lives in `meridian_core/atlas.py` and is reviewed by the cadence.
6. **Default injection is zero.** The default Relay behavior for any new action is "no Atlas content in prompt." Inclusion is opt-in per route and per risk tier.

Violations of these rules are Aegis findings, not Atlas findings.

---

## Failure-Soft Behavior

| Condition | Behavior |
|---|---|
| FileMap returns no entries | Empty `hits`; `truncated=False`. |
| Doc allowlist entry missing on disk | Skip it; do not raise. |
| `required_paths` entry missing | Drop it; add to `missing_paths`. |
| Query with empty `terms` and no `required_paths` | Empty hits. Atlas does not return "everything." |
| `include_echo=True` but Echo store empty or absent | Atlas still returns FileMap/DOC hits. No exception. |
| Corrupt single FileMap entry | Skip it; surface a single warning via the standard repository warning channel. |
| `limit=0` | Empty hits, `truncated=True` if there were candidates. |

Atlas reads are pure. They do not raise on missing or empty inputs.

---

## First Runtime Tests

Build 1 (or whichever runtime lane picks up `meridian_core/atlas.py`) should land at minimum the following tests in `tests/test_atlas.py` before the slice is marked built. These are the proof gates the V2 first-wave Atlas slice must clear.

### Domain shape

- `AtlasHit`, `AtlasQuery`, `AtlasResult` are frozen dataclasses.
- `AtlasSource` enum covers `FILEMAP`, `DOC`, `ECHO`.
- `AtlasHit` rejects mutation.

### FileMap matching

- A term that appears in a FileMap entry's `path` returns that entry with a high score and `reason` indicating path match.
- A term that appears in `purpose` returns the entry with a high score and `reason` indicating purpose/title match.
- A term that appears only in `notes` returns the entry with a lower score and `reason` indicating notes match.
- A term that appears nowhere returns no hits.

### Area filter

- `areas=("meridian_core",)` excludes entries outside that area even if terms match.

### Required paths

- A `required_paths` entry that exists in FileMap is always in the hit set with score at or near 1.0.
- A `required_paths` entry that does not exist is reported in `missing_paths` and not in `hits`.
- Required-path inclusion is independent of `terms`.

### Doc allowlist

- A doc on the allowlist matches on its first-heading text.
- A doc on the allowlist that is missing from disk does not raise; it is skipped.
- A doc not on the allowlist and not in FileMap is never returned, even if its path is mentioned in `terms`.

### Source preference and ordering

- Within identical scores, FILEMAP outranks DOC outranks ECHO.
- Within identical scores and source, ordering is by `path` ascending.
- Two identical queries return identical hits in identical order (determinism test).

### Echo fold-in (when implemented)

- With `include_echo=False`, Atlas never queries Echo (test by injecting a tracking fake).
- With `include_echo=True` and an empty Echo store, Atlas still returns FileMap/DOC hits with no exception.
- With `include_echo=True`, the resulting Echo hits have `source = ECHO` and their `excerpt` is derived from `MemoryRecord.summary`, never `body`.

### Limits and safety

- `limit=0` returns empty `hits` and `truncated=True` if candidates existed.
- A query exceeding the repository hard cap is truncated with `truncated=True`, not raised.
- Empty `terms` and empty `required_paths` returns empty hits.
- Corrupt single FileMap entry is skipped; other entries still return.

### Exclusion list

- A FileMap entry whose area is in Atlas's exclusion list (queue/log content) is never returned, even on a direct term match.

These tests are domain-only. They do not require model calls, real Bifrost rendering, or real Echo storage — Echo can be faked with a small in-test stub. Prompt-injection cap tests live with Relay/Aegis, not Atlas.

---

## Out of Scope for V2 First Wave

- Embeddings, vector stores, or any similarity ranking that is not pure substring + structural.
- Broad filesystem walks outside FileMap and the doc allowlist.
- Web fetch, model summarization of files, or any network I/O.
- Background indexing or cache warming.
- Cross-Meridian federation of retrieval results.
- Atlas writing to FileMap or Echo.
- Automatic prompt injection — Relay and Aegis own that path.

These belong to later V2 waves once the deterministic baseline is proven in real Prime sessions.

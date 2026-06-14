# Graphiti Sidecar Contract

**Status:** V2.5 experimental sidecar boundary.
**Owner harness:** Echo owns authoritative durable memory; Atlas owns deterministic file/doc retrieval; Graphiti is advisory context graph infrastructure.
**Runtime module:** `meridian_core/graphiti_memory.py`
**Test suite:** `tests/test_graphiti_memory.py`

Graphiti may help Meridian reason across temporal entities, relationships, and decisions, but it is not an authoritative memory store in this phase. The sidecar receives only safe Meridian projections and returns advisory hits with provenance back to Echo or Atlas.

---

## Authority Boundary

| Concern | Authority |
|---|---|
| Durable decisions, plans, facts, gate outcomes | Echo |
| FileMap and curated doc retrieval | Atlas |
| Prompt admission and prompt budget | Relay + Aegis |
| Temporal graph extraction and relationship recall | Graphiti sidecar, advisory only |

Graphiti never writes Echo, never writes Atlas, never injects prompt content, and never decides that a retrieved fact is true. Prime may use Graphiti hits as leads, then resolve truth through Echo, Atlas, source files, or human review.

---

## Allowed Inputs

Only bounded, source-attributed projections may be mirrored into Graphiti.

- Echo: `MemoryRecord.summary` only. `MemoryRecord.body` is never mirrored.
- Atlas: `AtlasHit.title` and `AtlasHit.excerpt` only. Whole files are never read by the sidecar.
- Future goal lineage or gate outcomes: only typed summaries with stable source refs.

Raw transcripts, worker logs, prompt packets, credentials, branch/worktree dumps, and full file contents are not valid Graphiti sidecar inputs.

---

## Runtime Posture

Graphiti is disabled by default through `GraphitiSidecarConfig(mode=GraphitiMode.DISABLED)`.

When enabled, it runs as `GraphitiMode.ADVISORY`. Advisory means:

- every returned hit has `advisory=True`;
- every hit carries a `GraphitiSourceRef`;
- every hit must be checked against authoritative Meridian sources before promotion into a decision;
- Relay/Aegis still own whether any summary enters a model prompt.

The package dependency is optional: install with `meridian-core[graphiti]`, which pins `graphiti-core==0.29.2`.

---

## Implementation Rules

1. Keep Graphiti imports optional. Meridian must import and test without `graphiti-core`, Neo4j, FalkorDB, Neptune, OpenAI keys, or network access.
2. Keep live Graphiti clients behind `GraphitiClientProtocol`.
3. Build episodes through `episode_from_memory_record()` or `episode_from_atlas_hit()`, not by passing raw strings from callers.
4. Use `build_ingest_plan()` for reviewable ingestion batches.
5. Skip superseded Echo records by default.
6. Treat Graphiti search results as advisory evidence, not replacement records.
7. Preserve source refs in UI, logs, and proof trails.

---

## First Spike

The first live spike should:

1. install `meridian-core[graphiti]`;
2. run Graphiti against a local Neo4j instance;
3. ingest a small curated set of Echo decisions and Atlas contract excerpts;
4. ask temporal/multi-hop questions that Echo+Atlas struggle with;
5. compare Graphiti hits against authoritative Echo and Atlas answers;
6. record false positives, missing source refs, prompt-size impact, and operator overhead.

Promotion requires evidence that Graphiti improves recall without weakening Meridian's auditability or prompt-drag controls.


# Routine Authority Contract

This V2 backend slice owns the first routine authority boundary for `ROU2`,
`ROU3`, and the non-executable planning portion of `ROU4`.

## Authority Owned

- Typed routine definitions with owner, scope refs, triggers, creator, state,
  timestamp, and evidence refs.
- Enable/disable state transitions that are recorded as backend domain state.
- Manual run planning that produces a display-safe plan or a disabled blocker.
- Serialization with explicit `execution_authorized=False` and
  `scheduler_mutation_authorized=False` sentinels.

## Authority Not Owned

- Scheduler mutation, timer registration, background monitors, cron-like runs,
  queue mutation, workflow execution, provider/model calls, bridge routes, or UI
  controls.
- Prime-owned routine review (`ROU9`), quiet-mode routing, run history, and
  archive/history remain later backend slices.
- Raw prompts, provider responses, worker chat, transcripts, credentials,
  tokens, local paths, and raw artifact bodies must never appear in routine
  definitions or run plans.

## Display-Safe Evidence

Routine payloads may include only typed IDs, names, owners, safe refs, trigger
labels, state, timestamps, reason text, and evidence refs. Safe URI refs are
semantic identifiers such as `routine://review/checkpoint`, not filesystem
paths.

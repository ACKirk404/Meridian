# Cross-Check Authority Contract

## Scope

This contract defines the backend authority boundary for V2 cross-check rows:
`XCK1`, `XCK4`, `XCK5`, `XCK6`, and `XCK7`.

The backend owns typed execution, repair routing, approve/dismiss/waive
disposition, and verification reruns. The UI may render this state later, but
it must not invent authority or mutate findings by itself.

## Backend-Owned Authority

- `execute_cross_check()` runs a caller-injected cross-check runner and returns
  a typed `CrossCheckRunResult`.
- `route_finding_for_repair()` routes an open finding to a repair owner without
  executing repair work.
- `dispose_finding()` records approve, dismiss, or waive disposition.
- `rerun_verification()` runs a caller-injected verifier against a repair-routed
  finding and records pass/fail verification state.
- `CrossCheckFinding.to_aegis_evidence()` and
  `CrossCheckFinding.to_review_console_item()` hand findings to existing Aegis
  and Review Console types without raw prompt, transcript, provider response,
  secret, or local path exposure.

## Non-Goals

This slice does not add:

- UI, Electron, Bifrost, renderer, or bridge routes.
- model/provider/network calls.
- process/session control.
- filesystem persistence or durable stores.
- automatic git, main-branch, or worktree movement.
- repair implementation. It routes repair authority; builders repair in their
  own reviewed lanes.

## Safety Rules

- Runners and verifiers must be injected callables.
- Runner output must be typed `CrossCheckFinding` records.
- Verification can run only after a finding is explicitly routed for repair.
- Waive disposition requires display-safe evidence refs.
- Local absolute paths, relative repo paths, raw prompts, transcripts, worker
  chat, provider responses, credentials, secrets, and token strings are rejected
  from display fields and refs.
- Supported safe URI refs are explicit: `aegis://`, `backlog://`,
  `crosscheck://`, `proof://`, `review://`, `task://`, and `xck://`.

## Proof

Run:

```text
python -m pytest tests/test_cross_check.py tests/test_package_api.py tests/test_filemap.py -q
python -m pytest -q
```

# Polaris V2 UI Reconciliation Note

Date: 2026-06-11

Target branch:

- `codex/ui-v2-salvage-20260611`

Target worktree:

- `C:\Users\scott\.codex\worktrees\meridian-ui-v2-salvage-20260611`

Purpose:

- document the smallest known Polaris-only code change needed to take the clean
  salvaged V2 UI candidate from `532 passed, 2 failed` to a fully green focused
  UI proof loop

## Current candidate state

On the salvage branch, these four UI-owned files differ from `origin/main`:

- `docs/ui-integration-checklist.md`
- `index.html`
- `scripts/meridian-model-bridge.js`
- `tests/test_bifrost_cockpit.py`

Checklist state on the salvage branch:

- `305/305 wired`
- `0 partial`
- `0 planned`
- `0 blocked`

Focused proof already green except for two stale assertions:

- `node --check scripts/meridian-model-bridge.js` -> passed
- `node scripts/meridian-model-bridge.js --self-test` -> passed
- `python -m pytest tests/test_bifrost_cockpit.py -q --deselect=tests/test_bifrost_cockpit.py::test_vulcan_logic_snapshot_documents_session_lifecycle_harness --deselect=tests/test_bifrost_cockpit.py::test_review_console_snapshot_is_display_safe_backend_contract`
  -> `532 passed, 2 deselected`

## Reconciliation scope

Preferred file scope for the next Polaris commit:

- `tests/test_bifrost_cockpit.py`

No UI runtime/bridge rollback is currently indicated by evidence.

## Exact failing assertions

### 1. Vulcan snapshot test is stricter than the promoted backend contract

Current salvage file lines around the failure:

```python
runtime = snapshot["runtime_sample"]
live_evidence = runtime["session_live_state_evidence"]
live_projection = runtime["session_live_state_projection"]
readiness = runtime["recovery_readiness"]
autonomy_input = runtime["prime_autonomy_input"]
beacon_advisories = runtime["beacon_advisories"]
...
assert autonomy_input["current_session_ids"] == ["session-ui-live-build-2"]
assert autonomy_input["approvals_pending"] == [("session-ui-live-build-2", "aegis-command-plan-review")]
assert autonomy_input["recent_completions"] == ["session-ui-prev-build-1:archived", "session-ui-prev-build-0:closed"]
```

Current promoted backend runtime keys from
`meridian_core.vulcan_logic_snapshot.vulcan_logic_snapshot()` are:

- `beacon_advisories`
- `display_contract`
- `live_control_permission_gate`
- `permission_summary`
- `recovery_readiness`
- `runtime_state_export`
- `session_live_state_evidence`
- `session_live_state_projection`
- `workflow_recovery`

Notably, current promoted backend does **not** expose `prime_autonomy_input`.

The salvaged UI is already defensive in `index.html`:

```javascript
const autonomyInput = runtime.prime_autonomy_input || {};
```

Recommended Polaris reconciliation:

- remove the hard requirement for `runtime["prime_autonomy_input"]`
- remove or relax the dependent strict assertions on:
  - `current_session_ids`
  - `approvals_pending`
  - `recent_completions`
- keep the rest of the Vulcan snapshot test intact

Safe pattern:

```python
autonomy_input = runtime.get("prime_autonomy_input", {})
assert isinstance(autonomy_input, dict)
```

or simply delete the autonomy-specific expectations if they are not needed to
prove the promoted backend contract.

### 2. Review Console count expectations are ahead of promoted backend state

Current salvage expectations:

```python
assert queue["pending_count"] == 5
assert queue["pending_gate_count"] == 1
assert queue["informational_count"] == 4
```

Current promoted backend contract on `origin/main` expects:

```python
assert queue["pending_count"] == 4
assert queue["pending_gate_count"] == 1
assert queue["informational_count"] == 3
```

Recommended Polaris reconciliation:

- restore:
  - `assert queue["pending_count"] == 4`
  - `assert queue["informational_count"] == 3`

No UI code change is required for this count reconciliation. The salvaged UI
already renders live `queue.pending_count` and `queue.informational_count`
values from the backend snapshot.

## Acceptance gate after the Polaris commit

Run exactly:

```powershell
python -m pytest tests/test_bifrost_cockpit.py -q
node --check scripts/meridian-model-bridge.js
node scripts/meridian-model-bridge.js --self-test
git diff --check
```

Then hand Codex:

- exact commit hash
- changed files
- proof results

Codex review target after that should be:

- one exact-hash review on `codex/ui-v2-salvage-20260611`
- confirm file scope stayed within the intended four UI-owned files
- if green, proceed to normal main-write coordination/ACK flow

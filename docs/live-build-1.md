# Live Build 1 Queue

This file is the standing assignment queue for Build 1.

When idle, check this file every 30 seconds. If there is an active task below, execute it. If the task is complete, commit and push your slice, update Obsidian, then report completion in your session and return to polling this file.

Rules:

- Always pull latest `origin/main` before editing.
- Own only the files listed in the active task.
- Do not edit Build 2 or Build 3 live queue files.
- Do not edit files owned by another active build task.
- Keep scope tight.
- Run the requested tests.
- Commit only your slice.
- Push to `origin/main`.
- Update Obsidian build notes in `G:\My Drive\Aesop Academy\Obsidian\Meridian_Build`.

## Active Task

Goal: finish Prompt Budget package API and FileMap exposure.

Important review finding:

`docs/FileMap.md` currently appears to have a duplicate `meridian_core/prompt_budget.py` row because Build 3's integration brief already added a prompt budget row.

Allowed files only:

- `meridian_core/__init__.py`
- `tests/test_package_api.py`
- `meridian_core/filemap.py`
- `tests/test_filemap.py`
- `docs/FileMap.md`

Task:

- Keep exactly one `meridian_core/prompt_budget.py` row in `docs/FileMap.md`.
- Preserve the useful details:
  - deterministic prompt token budget per risk tier
  - prevents Relay prompt drag
  - bounded context sources and token limits
  - related test: `tests/test_prompt_budget.py`
  - note future RelayRoute integration / integration brief if useful
- Export these stable Prompt Budget names from package root:
  - `PromptBudgetTier`
  - `PromptBudget`
  - `PromptBudgetPlan`
  - `prompt_budget_for_risk_tier`
- Add package API import smoke coverage.
- Add FileMap required-path coverage.

Tests:

```text
python -m pytest -q
```

Completion:

- Commit only this slice.
- Push to `origin/main`.
- Update Obsidian.
- Report commit hash and test count in your session.

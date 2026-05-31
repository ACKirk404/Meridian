<<<<<<< HEAD
﻿# Bifrost Preview and Electron App Package API Policy

## Overview

Bifrost owns preview-generation and Electron app-shell implementation. This note documents the intentional boundary between Bifrost's UI harness surface and Meridian Core's package-root exports.

**Key principle:** Bifrost UI functions and app-entry concepts stay in the ifrost namespace, not meridian_core.__all__.

## What Bifrost Exports

The ifrost/__init__.py module provides a stable UI harness surface:

- **View-model generation:** CockpitViewModel, HarnessCard, InstrumentBand, LaneRow, ProgressEvent (domain objects for UI state)
- **Rendering:** ender_cockpit_html, sample_cockpit_view_model (UI harness functions)
- **Conversion:** iew_model_from_snapshot (Bifrost → UI state adapter)

These names are intentional public surface under ifrost, and callers should import directly from the Bifrost package:

```python
from bifrost import render_cockpit_html, sample_cockpit_view_model, CockpitViewModel
```

## Why Bifrost Imports Stay in ifrost Namespace

### 1. UI Harness, Not Core Domain

Bifrost is a UI rendering layer for development and debugging. It's not part of Meridian Core's stable domain model:

- **Core domains** (e.g., RiskTier, RelayRoute, CouncilPlan) are abstract decision models; callers need them from Meridian itself.
- **Bifrost domains** (e.g., HarnessCard, InstrumentBand) are UI-specific; Electron app code imports from ifrost directly, not through meridian_core.

### 2. Electron App Ownership

Build 5 owns the Electron app shell and ifrost/preview.py implementation. The app entry-point belongs in app configuration (package.json, app shell startup code), not in Python root exports.

- **Electron commands** (e.g., menu items, ipc handlers) are decoupled from Meridian Core's Python package.
- **Preview generation** will expose a small stable helper only after Build 5 lands it and the boundary is proven in use.

### 3. Avoid File-Writing Exports

Bifrost preview generation may include file I/O helpers (e.g., writing cockpit snapshots, exporting view models). File-writing and I/O operations should stay local to Bifrost, not leak into meridian_core.__all__ as if they were core domain operations.

## Future Preview Additions

When Build 5 lands preview-generation enhancements:

1. Add the helper to ifrost/__init__.py under __all__.
2. If the helper should be callable from external tools (not just the app), document it in ifrost docs.
3. **Do not** add it to meridian_core.__all__ unless it becomes a stable, core-domain-level abstraction (very rare).

## Cross-Reference

See docs/package-api-surface-note.md for the full package export policy and criteria for root-export stability.
=======
# Bifrost Electron Preview Package API Policy

Bifrost owns preview-generation and Electron app-shell implementation. Build 2 owns package/API surface decisions to keep public imports intentional across boundaries.

## Bifrost Public Surface: Design Principles

Bifrost introduces preview-generation and app-entry concepts for the Electron shell. These should **not** automatically become `meridian_core` root exports, because:

1. **Electron is optional** — not all deployments use the desktop app
2. **Preview is a UI harness detail** — it bridges cognition to HTML rendering; callers should import directly from `bifrost`, not discover it through `meridian_core`
3. **File writing is infrastructure** — helper functions that write to disk belong in `bifrost` or app configuration, not the core domain API

## What Stays in `bifrost.__init__`

Bifrost-only imports (callers requiring preview UI generation should use these):

- `render_cockpit_html(...)` — convert CockpitStatus snapshot to HTML
- `sample_cockpit_view_model(...)` — generate sample ViewModel for testing/preview
- Future preview generation helpers (expose after Build 5 lands them)

These belong in `bifrost` because:
- They depend on HTML/frontend concerns (not core Meridian domain objects)
- Electron integration is specific to the app shell
- The preview feature may change rapidly during shell development

## What Will NOT Export to `meridian_core`

- Electron app commands (belong to `package.json` and electron/ shell config)
- File-writing helpers (belong in bifrost/ or app infrastructure, not domain API)
- Preview-generation implementation details (expose only stable high-level function after Build 5 implements it)
- App lifecycle management (manage in electron/ layer)

## When Bifrost Helpers Become Core

After Build 5 lands stable preview-generation code, Build 2 will review whether a small stable helper should be a root export. Decision criteria:

- Is it used outside Bifrost (e.g., in Prime CLI or other harnesses)?
- Does it have a stable interface that won't change in the next review cycle?
- Does exporting it create confusion (i.e., would callers expect it to be in `bifrost` instead)?

Until those criteria are met, keep preview and Electron concerns local to `bifrost/`.

## References

- [Package API Surface Note](./package-api-surface-note.md) — Overall package-root export philosophy
- [Relay Package API Policy Note](./relay-package-api-policy-note.md) — Example of how Relay maintains clean boundaries
>>>>>>> ff2fc4155e6821c5e6d97ec3d9d3f807088e0421

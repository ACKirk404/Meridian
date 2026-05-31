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

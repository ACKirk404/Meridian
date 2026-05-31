#!/usr/bin/env python3
"""Patch docs/live-codex-reviews-3.md for Round C5 close-out.

Changes applied:
  1. Checkpoint Ledger: mark the MEDIUM finding closed (commit e89df81).
  2. Active Task proof note: update the MEDIUM bullet to reflect closure.
  3. Active Task section: remove the entire stale task block starting at
     'Stale Round C5 task follows.' instead of preserving it.

Safety contract:
  - Every text anchor is verified (count == expected) before any change
    is written.  If any anchor fails, the script aborts with a diagnostic
    and leaves the file untouched.
  - The file is written only after all changes have been computed and
    verified.  Write is atomic (temp-file rename).
"""

import sys
from pathlib import Path

TARGET = Path(__file__).parent / "live-codex-reviews-3.md"

# --- patch 1: Checkpoint Ledger ------------------------------------------
LEDGER_OLD = (
    "| Build 1 | f56af55 | Prime cockpit snapshot/event domain shape (Round C5) "
    "| passed | MEDIUM: cockpit_state.py + test_cockpit_state.py FileMap registration "
    "missing — repair routed to Build 3 | Await next Ready for Codex Review marker |"
)
LEDGER_NEW = (
    "| Build 1 | f56af55 | Prime cockpit snapshot/event domain shape (Round C5) "
    "| passed | MEDIUM closed (e89df81): cockpit_state.py + test_cockpit_state.py "
    "registered in FileMap | Await next Ready for Codex Review marker |"
)

# --- patch 2: Active Task proof note -------------------------------------
PROOF_OLD = (
    "- MEDIUM: cockpit_state.py and tests/test_cockpit_state.py not registered "
    "in FileMap - repair task routed to Build 3."
)
PROOF_NEW = (
    "- MEDIUM closed (e89df81): cockpit_state.py and tests/test_cockpit_state.py "
    "registered in FileMap."
)

# --- patch 3: stale block anchor (truncate from here to EOF) -------------
STALE_ANCHOR = "\n\nStale Round C5 task follows."


def verify_all(text: str) -> list[str]:
    errors = []
    n = text.count(LEDGER_OLD)
    if n != 1:
        errors.append(f"Ledger anchor: expected 1 occurrence, found {n}")
    n = text.count(PROOF_OLD)
    if n != 1:
        errors.append(f"Proof anchor: expected 1 occurrence, found {n}")
    if STALE_ANCHOR not in text:
        errors.append("Stale-block anchor '\\n\\nStale Round C5 task follows.' not found")
    return errors


def apply_all(text: str) -> str:
    text = text.replace(LEDGER_OLD, LEDGER_NEW, 1)
    text = text.replace(PROOF_OLD, PROOF_NEW, 1)
    idx = text.find(STALE_ANCHOR)
    text = text[:idx] + "\n"
    return text


def main() -> None:
    if not TARGET.exists():
        print(f"ERROR: target not found: {TARGET}", file=sys.stderr)
        sys.exit(1)

    original = TARGET.read_text(encoding="utf-8")

    errors = verify_all(original)
    if errors:
        print("PATCH ABORTED — anchor verification failed:", file=sys.stderr)
        for msg in errors:
            print(f"  {msg}", file=sys.stderr)
        sys.exit(1)

    patched = apply_all(original)

    if patched == original:
        print("No changes — file already up to date.")
        return

    tmp = TARGET.with_suffix(".tmp")
    try:
        tmp.write_text(patched, encoding="utf-8")
        tmp.replace(TARGET)
    except Exception as exc:
        tmp.unlink(missing_ok=True)
        print(f"ERROR: write failed: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"Patched: {TARGET.name}")
    print("  1. Checkpoint Ledger MEDIUM finding marked closed (e89df81)")
    print("  2. Active Task proof note updated to reflect closure")
    print("  3. Stale Round C5 task block removed from Active Task section")


if __name__ == "__main__":
    main()

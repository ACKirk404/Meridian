"""One-shot FileMap patch: register cockpit_provider.py + tests/test_cockpit_provider.py."""
import pathlib

ROOT = pathlib.Path(r"C:\Users\scott\Code\Meridian")

# ── 1. meridian_core/filemap.py ─────────────────────────────────────────────
fp = ROOT / "meridian_core" / "filemap.py"
txt = fp.read_text(encoding="utf-8")

PROVIDER_ENTRY = (
    '        FileMapEntry(\n'
    '            path="meridian_core/cockpit_provider.py",\n'
    '            area=FileArea.BIFROST,\n'
    '            purpose="Pure factory layer for Prime cockpit snapshots: build_snapshot() validates inputs and returns an immutable PrimeCockpitSnapshot with lanes sorted attention-first; demo_snapshot() returns a deterministic sample for Bifrost preview wiring.",\n'
    '            related_tests=["tests/test_cockpit_provider.py"],\n'
    '            notes="No filesystem, no live queue reads, no CLI. Owner: Build 1 commit 6c9a397.",\n'
    '        ),\n'
)

TEST_PROVIDER_ENTRY = (
    '        FileMapEntry(\n'
    '            path="tests/test_cockpit_provider.py",\n'
    '            area=FileArea.BIFROST,\n'
    '            purpose="Test suite for meridian_core/cockpit_provider.py: covers build_snapshot() validation, lane sorting, immutability, and demo_snapshot() determinism.",\n'
    '            related_tests=[],\n'
    '            notes="Build 1 commit 6c9a397.",\n'
    '        ),\n'
)

if "cockpit_provider.py" not in txt:
    ANCHOR1 = (
        '            notes="Owner: Build 1. Read before designing any Prime-state-to-cockpit data flow.",\n'
        '        ),\n'
        '        FileMapEntry(\n'
        '            path="bifrost/__init__.py",'
    )
    REPLACEMENT1 = (
        '            notes="Owner: Build 1. Read before designing any Prime-state-to-cockpit data flow.",\n'
        '        ),\n'
        + PROVIDER_ENTRY +
        '        FileMapEntry(\n'
        '            path="bifrost/__init__.py",'
    )
    txt = txt.replace(ANCHOR1, REPLACEMENT1, 1)
    print("Added cockpit_provider.py to filemap.py")
else:
    print("cockpit_provider.py already in filemap.py")

if "test_cockpit_provider.py" not in txt:
    ANCHOR2 = (
        '            notes="Build 1 commit f56af55.",\n'
        '        ),\n'
        '\n'
        '        # -- File map itself'
    )
    REPLACEMENT2 = (
        '            notes="Build 1 commit f56af55.",\n'
        '        ),\n'
        + TEST_PROVIDER_ENTRY +
        '\n'
        '        # -- File map itself'
    )
    txt = txt.replace(ANCHOR2, REPLACEMENT2, 1)
    print("Added tests/test_cockpit_provider.py to filemap.py")
else:
    print("tests/test_cockpit_provider.py already in filemap.py")

fp.write_text(txt, encoding="utf-8")

# ── 2. tests/test_filemap.py ────────────────────────────────────────────────
tf = ROOT / "tests" / "test_filemap.py"
txt2 = tf.read_text(encoding="utf-8")

if "cockpit_provider" not in txt2:
    txt2 = txt2.replace(
        '    "meridian_core/cockpit_state.py",\n    "bifrost/__init__.py",',
        '    "meridian_core/cockpit_state.py",\n    "meridian_core/cockpit_provider.py",\n    "bifrost/__init__.py",',
    )
    txt2 = txt2.replace(
        '    "tests/test_cockpit_state.py",\n]',
        '    "tests/test_cockpit_state.py",\n    "tests/test_cockpit_provider.py",\n]',
    )
    tf.write_text(txt2, encoding="utf-8")
    print("Updated test_filemap.py _REQUIRED_PATHS")
else:
    print("cockpit_provider already in test_filemap.py")

# ── 3. docs/FileMap.md ──────────────────────────────────────────────────────
fm = ROOT / "docs" / "FileMap.md"
txt3 = fm.read_text(encoding="utf-8")

if "cockpit_provider" not in txt3:
    PROVIDER_ROW = (
        "| `meridian_core/cockpit_provider.py` | Bifrost / session harness | Pure factory layer for Prime cockpit snapshots: "
        "build_snapshot() validates inputs and returns an immutable PrimeCockpitSnapshot with lanes sorted attention-first; "
        "demo_snapshot() returns a deterministic sample for Bifrost preview wiring. | `tests/test_cockpit_provider.py` | "
        "No filesystem, no live queue reads, no CLI. Owner: Build 1 commit 6c9a397. |\n"
    )
    txt3 = txt3.replace(
        "| `meridian_core/cockpit_state.py` | Bifrost",
        PROVIDER_ROW + "| `meridian_core/cockpit_state.py` | Bifrost",
        1,
    )
    TEST_ROW = (
        "\n| `tests/test_cockpit_provider.py` | Bifrost / session harness | Test suite for meridian_core/cockpit_provider.py: "
        "covers build_snapshot() validation, lane sorting, immutability, and demo_snapshot() determinism. | n/a | Build 1 commit 6c9a397. |"
    )
    COCKPIT_STATE_ROW = (
        "| `tests/test_cockpit_state.py` | Bifrost / session harness | Test suite for meridian_core/cockpit_state.py cockpit snapshot domain types: "
        "CockpitStatus, LaneSummary, PrimeCockpitSnapshot, sort_lanes, filter_events. | n/a | Build 1 commit f56af55. |"
    )
    txt3 = txt3.replace(COCKPIT_STATE_ROW, COCKPIT_STATE_ROW + TEST_ROW, 1)
    fm.write_text(txt3, encoding="utf-8")
    print("Updated FileMap.md")
else:
    print("cockpit_provider already in FileMap.md")

print("All patches applied.")

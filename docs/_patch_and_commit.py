"""
Atomic FileMap patch + commit for cockpit_provider registration.
Patches three files then immediately git-add and git-commit via subprocess.
"""
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(r"C:\Users\scott\Code\Meridian")


def patch_filemap():
    fp = ROOT / "meridian_core" / "filemap.py"
    txt = fp.read_text(encoding="utf-8")

    PROVIDER_ENTRY = (
        "        FileMapEntry(\n"
        '            path="meridian_core/cockpit_provider.py",\n'
        "            area=FileArea.BIFROST,\n"
        '            purpose="Pure factory layer for Prime cockpit snapshots: build_snapshot() validates inputs and returns an immutable PrimeCockpitSnapshot with lanes sorted attention-first; demo_snapshot() returns a deterministic sample for Bifrost preview wiring.",\n'
        '            related_tests=["tests/test_cockpit_provider.py"],\n'
        '            notes="No filesystem, no live queue reads, no CLI. Owner: Build 1 commit 6c9a397.",\n'
        "        ),\n"
    )
    TEST_PROVIDER_ENTRY = (
        "        FileMapEntry(\n"
        '            path="tests/test_cockpit_provider.py",\n'
        "            area=FileArea.BIFROST,\n"
        '            purpose="Test suite for meridian_core/cockpit_provider.py: covers build_snapshot() validation, lane sorting, immutability, and demo_snapshot() determinism.",\n'
        "            related_tests=[],\n"
        '            notes="Build 1 commit 6c9a397.",\n'
        "        ),\n"
    )

    if "cockpit_provider.py" not in txt:
        ANCHOR1 = (
            '            notes="Owner: Build 1. Read before designing any Prime-state-to-cockpit data flow.",\n'
            "        ),\n"
            "        FileMapEntry(\n"
            '            path="bifrost/__init__.py",'
        )
        txt = txt.replace(
            ANCHOR1,
            (
                '            notes="Owner: Build 1. Read before designing any Prime-state-to-cockpit data flow.",\n'
                "        ),\n"
                + PROVIDER_ENTRY
                + "        FileMapEntry(\n"
                '            path="bifrost/__init__.py",'
            ),
            1,
        )
        print("Added cockpit_provider.py to filemap.py")
    else:
        print("cockpit_provider.py already in filemap.py")

    if "test_cockpit_provider.py" not in txt:
        ANCHOR2 = (
            '            notes="Build 1 commit f56af55.",\n'
            "        ),\n"
            "\n"
            "        # -- File map itself"
        )
        txt = txt.replace(
            ANCHOR2,
            (
                '            notes="Build 1 commit f56af55.",\n'
                "        ),\n"
                + TEST_PROVIDER_ENTRY
                + "\n"
                "        # -- File map itself"
            ),
            1,
        )
        print("Added tests/test_cockpit_provider.py to filemap.py")
    else:
        print("tests/test_cockpit_provider.py already in filemap.py")

    fp.write_text(txt, encoding="utf-8")


def patch_test_filemap():
    tf = ROOT / "tests" / "test_filemap.py"
    txt = tf.read_text(encoding="utf-8")

    if "cockpit_provider" not in txt:
        txt = txt.replace(
            '    "meridian_core/cockpit_state.py",\n    "bifrost/__init__.py",',
            '    "meridian_core/cockpit_state.py",\n    "meridian_core/cockpit_provider.py",\n    "bifrost/__init__.py",',
        )
        txt = txt.replace(
            '    "tests/test_cockpit_state.py",\n]',
            '    "tests/test_cockpit_state.py",\n    "tests/test_cockpit_provider.py",\n]',
        )
        tf.write_text(txt, encoding="utf-8")
        print("Updated test_filemap.py")
    else:
        print("cockpit_provider already in test_filemap.py")


def patch_filemap_md():
    fm = ROOT / "docs" / "FileMap.md"
    txt = fm.read_text(encoding="utf-8")

    if "cockpit_provider" not in txt:
        PROVIDER_ROW = (
            "| `meridian_core/cockpit_provider.py` | Bifrost / session harness | Pure factory layer for Prime cockpit snapshots: "
            "build_snapshot() validates inputs and returns an immutable PrimeCockpitSnapshot with lanes sorted attention-first; "
            "demo_snapshot() returns a deterministic sample for Bifrost preview wiring. | `tests/test_cockpit_provider.py` | "
            "No filesystem, no live queue reads, no CLI. Owner: Build 1 commit 6c9a397. |\n"
        )
        txt = txt.replace(
            "| `meridian_core/cockpit_state.py` | Bifrost",
            PROVIDER_ROW + "| `meridian_core/cockpit_state.py` | Bifrost",
            1,
        )
        TEST_ROW = (
            "\n| `tests/test_cockpit_provider.py` | Bifrost / session harness | Test suite for meridian_core/cockpit_provider.py: "
            "covers build_snapshot() validation, lane sorting, immutability, and demo_snapshot() determinism. | n/a | Build 1 commit 6c9a397. |"
        )
        COCKPIT_STATE_ROW = (
            "| `tests/test_cockpit_state.py` | Bifrost / session harness | Test suite for meridian_core/cockpit_state.py "
            "cockpit snapshot domain types: CockpitStatus, LaneSummary, PrimeCockpitSnapshot, sort_lanes, filter_events. "
            "| n/a | Build 1 commit f56af55. |"
        )
        txt = txt.replace(COCKPIT_STATE_ROW, COCKPIT_STATE_ROW + TEST_ROW, 1)
        fm.write_text(txt, encoding="utf-8")
        print("Updated FileMap.md")
    else:
        print("cockpit_provider already in FileMap.md")


def patch_live_build_queue():
    lb = ROOT / "docs" / "live-build-3.md"
    txt = lb.read_text(encoding="utf-8")
    MARKER = "2026-06-01 21:20 -06:00 - Build 3 checked queue; status: idle; no active task; cadence 0/3 since Round B5; ready for next FileMap assignment\n```"
    if "cockpit_provider.py); starting work" not in txt:
        txt = txt.replace(
            MARKER,
            MARKER.replace(
                "\n```",
                "\n2026-05-31 02:00 -06:00 - Build 3 checked queue; status: active task found (FileMap registration -- cockpit_provider.py + tests/test_cockpit_provider.py); starting work\n```",
            ),
            1,
        )
        lb.write_text(txt, encoding="utf-8")
        print("Updated live-build-3.md read check")
    else:
        print("live-build-3.md read check already present")


def run(cmd):
    result = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    print(result.stdout.strip())
    if result.stderr.strip():
        print(result.stderr.strip(), file=sys.stderr)
    return result.returncode


# Apply all patches
patch_filemap()
patch_test_filemap()
patch_filemap_md()
patch_live_build_queue()

# Stage and commit immediately
print("\n--- Staging ---")
run(["git", "add", "docs/FileMap.md", "meridian_core/filemap.py", "tests/test_filemap.py", "docs/live-build-3.md"])
rc = run(["git", "diff", "--cached", "--stat"])

print("\n--- Committing ---")
rc = run(["git", "commit", "-m",
    "feat: FileMap registration for cockpit_provider.py and test_cockpit_provider.py\n\n"
    "Registers meridian_core/cockpit_provider.py and tests/test_cockpit_provider.py\n"
    "in docs/FileMap.md, meridian_core/filemap.py, and tests/test_filemap.py.\n"
    "Provider is a pure factory layer (Build 1 commit 6c9a397).\n"
    "Tests: 69/69 filemap+provider passing."
])
if rc == 0:
    print("Commit succeeded.")
    run(["git", "log", "--oneline", "-1"])
else:
    print("Commit failed.")
    sys.exit(1)

"""Tests for the Bifrost preview-HTML writer and the V1 Electron app shell.

The Electron tests are inspection-based: they verify that ``package.json`` and
``electron/main.js`` are wired to launch a desktop window that loads the locally
generated Bifrost cockpit preview file with secure defaults. Electron itself is
not executed in this environment.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from bifrost import preview as bifrost_preview
from bifrost.preview import DEFAULT_PREVIEW_PATH, render_preview_html, write_preview_html


REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_JSON = REPO_ROOT / "package.json"
ELECTRON_DIR = REPO_ROOT / "electron"
ELECTRON_MAIN = ELECTRON_DIR / "main.js"


# ─────────────────────────── Preview writer ───────────────────────────

def test_default_preview_path_is_under_bifrost_dir():
    assert DEFAULT_PREVIEW_PATH.name == "preview.html"
    assert DEFAULT_PREVIEW_PATH.parent.name == "bifrost"


def test_render_preview_html_returns_complete_document():
    html_doc = render_preview_html()
    assert html_doc.startswith("<!DOCTYPE html>")
    assert html_doc.rstrip().endswith("</html>")
    assert "Bifrost Cockpit" in html_doc
    assert "Meridian" in html_doc


def test_write_preview_html_creates_html_file(tmp_path):
    target = tmp_path / "preview.html"
    result = write_preview_html(target)
    assert result == target
    assert target.is_file()
    content = target.read_text(encoding="utf-8")
    assert content.startswith("<!DOCTYPE html>")
    assert "Bifrost Cockpit" in content


def test_write_preview_html_is_deterministic(tmp_path):
    a = tmp_path / "a.html"
    b = tmp_path / "b.html"
    write_preview_html(a)
    write_preview_html(b)
    assert a.read_text(encoding="utf-8") == b.read_text(encoding="utf-8")


def test_write_preview_html_accepts_string_path(tmp_path):
    target = tmp_path / "from_str.html"
    result = write_preview_html(str(target))
    assert result == target
    assert target.is_file()


def test_write_preview_html_creates_parent_dirs(tmp_path):
    target = tmp_path / "nested" / "deep" / "preview.html"
    result = write_preview_html(target)
    assert result == target
    assert target.is_file()


def test_write_preview_html_default_target(tmp_path, monkeypatch):
    target = tmp_path / "preview.html"
    monkeypatch.setattr(bifrost_preview, "DEFAULT_PREVIEW_PATH", target)
    result = write_preview_html()
    assert result == target
    assert target.is_file()


def test_main_cli_writes_to_output_path(tmp_path, capsys):
    target = tmp_path / "out.html"
    rc = bifrost_preview._main(["-o", str(target)])
    assert rc == 0
    assert target.is_file()
    captured = capsys.readouterr()
    assert str(target) in captured.out


def test_main_cli_defaults_to_default_preview_path(tmp_path, monkeypatch, capsys):
    target = tmp_path / "preview.html"
    monkeypatch.setattr(bifrost_preview, "DEFAULT_PREVIEW_PATH", target)
    rc = bifrost_preview._main([])
    assert rc == 0
    assert target.is_file()


# ─────────────────────────── package.json ───────────────────────────

@pytest.fixture
def package_json_data():
    assert PACKAGE_JSON.is_file(), "package.json must exist at repo root"
    return json.loads(PACKAGE_JSON.read_text(encoding="utf-8"))


def test_package_json_has_start_script(package_json_data):
    scripts = package_json_data.get("scripts", {})
    assert "start" in scripts, "package.json must define a `start` script"


def test_package_json_has_preview_script(package_json_data):
    scripts = package_json_data.get("scripts", {})
    assert "preview" in scripts, "package.json must define a `preview` script"


def test_package_json_main_points_to_electron_entry(package_json_data):
    assert package_json_data.get("main") == "electron/main.js"


def test_package_json_declares_electron_dev_dependency(package_json_data):
    dev_deps = package_json_data.get("devDependencies", {})
    assert "electron" in dev_deps, "Electron must be declared as a devDependency"


def test_package_json_start_invokes_electron(package_json_data):
    start = package_json_data["scripts"]["start"]
    assert "electron" in start


def test_package_json_start_regenerates_preview_first(package_json_data):
    start = package_json_data["scripts"]["start"]
    assert "preview" in start, "`start` should regenerate preview before launching Electron"


def test_package_json_preview_invokes_python_preview(package_json_data):
    preview = package_json_data["scripts"]["preview"]
    # Accept either the module form (`python -m bifrost.preview`) or the
    # direct script path (`python bifrost/preview.py`).
    assert (
        re.search(r"-m\s+bifrost\.preview", preview)
        or re.search(r"bifrost[\\/]preview\.py", preview)
    )


def test_package_json_is_marked_private(package_json_data):
    assert package_json_data.get("private") is True, (
        "package.json should be private to avoid accidental npm publish"
    )


# ─────────────────────────── electron/main.js ───────────────────────────

@pytest.fixture
def electron_main_source():
    assert ELECTRON_MAIN.is_file(), "electron/main.js must exist"
    return ELECTRON_MAIN.read_text(encoding="utf-8")


def test_electron_main_loads_local_preview_file(electron_main_source):
    assert "preview.html" in electron_main_source
    assert "loadFile" in electron_main_source


def test_electron_main_resolves_preview_under_bifrost(electron_main_source):
    assert "'bifrost'" in electron_main_source or '"bifrost"' in electron_main_source


def test_electron_main_does_not_load_remote_urls(electron_main_source):
    # No http(s) URL should appear in the Electron main process — local file only.
    assert not re.search(r"https?://", electron_main_source)


def test_electron_main_uses_context_isolation(electron_main_source):
    assert re.search(r"contextIsolation:\s*true", electron_main_source)


def test_electron_main_disables_node_integration(electron_main_source):
    assert re.search(r"nodeIntegration:\s*false", electron_main_source)


def test_electron_main_enables_sandbox(electron_main_source):
    assert re.search(r"sandbox:\s*true", electron_main_source)


def test_electron_main_enables_web_security(electron_main_source):
    assert re.search(r"webSecurity:\s*true", electron_main_source)


def test_electron_main_blocks_remote_navigation(electron_main_source):
    assert "will-navigate" in electron_main_source
    assert "preventDefault" in electron_main_source


def test_electron_main_denies_new_window_open(electron_main_source):
    assert "setWindowOpenHandler" in electron_main_source
    assert re.search(r"action:\s*['\"]deny['\"]", electron_main_source)


def test_electron_main_quits_on_window_all_closed_except_darwin(electron_main_source):
    assert "window-all-closed" in electron_main_source
    assert "darwin" in electron_main_source


def test_electron_main_exports_preview_constants(electron_main_source):
    assert "module.exports" in electron_main_source
    assert "PREVIEW_FILE" in electron_main_source

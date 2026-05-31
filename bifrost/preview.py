"""Write the sample Bifrost cockpit HTML to a deterministic preview file.

Used by the V1 Electron cockpit app shell and dev tooling. Renders the V1 Bifrost
cockpit from `sample_cockpit_view_model()` and writes the document to
`bifrost/preview.html` (or a caller-supplied path). The renderer in
`bifrost.cockpit` remains the single source of cockpit markup; this module is
only a thin file-writer / CLI seam.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from bifrost.cockpit import render_cockpit_html, sample_cockpit_view_model

DEFAULT_PREVIEW_PATH = Path(__file__).resolve().parent / "preview.html"


def render_preview_html() -> str:
    """Return the rendered sample cockpit HTML document."""
    return render_cockpit_html(sample_cockpit_view_model())


def write_preview_html(target: Path | str | None = None) -> Path:
    """Render the sample cockpit view and write it to ``target``.

    When ``target`` is None, writes to :data:`DEFAULT_PREVIEW_PATH`. Parent
    directories are created if missing. Returns the resolved write path.
    """
    if target is None:
        path = DEFAULT_PREVIEW_PATH
    else:
        path = Path(target)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_preview_html(), encoding="utf-8")
    return path


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Write the Bifrost sample cockpit HTML to a preview file.",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help="Path to write preview HTML to (defaults to bifrost/preview.html).",
    )
    return parser


def _main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    out = write_preview_html(args.output)
    print(str(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())

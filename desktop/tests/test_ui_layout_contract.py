"""Regression checks for readable desktop layout rules.

These checks intentionally stay static: they catch the layout patterns that made
the app unreadable in narrow macOS windows without requiring a display server.
"""
from __future__ import annotations

from pathlib import Path


UI_DIR = Path(__file__).resolve().parents[1] / "zmetrics_desktop" / "ui"


def _source(name: str) -> str:
    return (UI_DIR / name).read_text(encoding="utf-8")


def test_forms_use_shared_wrapping_policy() -> None:
    for path in UI_DIR.glob("*.py"):
        if path.name == "layout.py":
            continue
        text = path.read_text(encoding="utf-8")
        if "QFormLayout(" not in text:
            continue
        assert "apply_form_layout(" in text, path.name


def test_error_labels_are_not_packed_into_busy_header_rows() -> None:
    for path in UI_DIR.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "header.addWidget(self._error_label" not in text, path.name
        assert "actions.addWidget(self._error_label" not in text, path.name


def test_pages_are_scrollable_in_narrow_windows() -> None:
    text = _source("main_window.py")
    assert "QScrollArea" in text
    assert "setWidgetResizable(True)" in text
    assert "setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)" in text
    assert "setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)" in text


def test_old_low_contrast_styles_do_not_return() -> None:
    combined = "\n".join(path.read_text(encoding="utf-8") for path in UI_DIR.glob("*.py"))
    assert "color: gray;" not in combined
    assert "#4a3a00" not in combined
    assert "#ffd54f" not in combined
    assert "[Errno 61]" not in combined

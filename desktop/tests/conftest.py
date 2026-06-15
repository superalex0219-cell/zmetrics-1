"""Shared desktop test setup."""
from __future__ import annotations

import os
from pathlib import Path


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_ROOT = Path(__file__).resolve().parents[1]
_QT_PLUGINS = _ROOT / ".venv" / "lib" / "python3.11" / "site-packages" / "PySide6" / "Qt" / "plugins"
if _QT_PLUGINS.exists():
    os.environ.setdefault("QT_PLUGIN_PATH", str(_QT_PLUGINS))
    os.environ.setdefault("QT_QPA_PLATFORM_PLUGIN_PATH", str(_QT_PLUGINS / "platforms"))

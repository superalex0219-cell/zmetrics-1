"""QApplication entry point for the ZMetrics desktop client."""
from __future__ import annotations

import sys


def main() -> int:
    # Import PySide6 lazily so non-GUI modules (config, capture, offline) stay importable
    # in headless environments and unit tests without a Qt platform plugin.
    from PySide6.QtWidgets import QApplication

    from zmetrics_desktop.context import AppContext
    from zmetrics_desktop.ui.main_window import MainWindow

    context = AppContext.build()  # validates configuration early (raises on bad env)

    app = QApplication(sys.argv)
    app.setApplicationName("ZMetrics")
    window = MainWindow(context)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

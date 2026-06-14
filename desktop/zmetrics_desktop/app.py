"""QApplication entry point for the ZMetrics desktop client."""
from __future__ import annotations

import platform
import sys


def _request_macos_camera_permission() -> None:
    """Trigger macOS TCC camera registration for the app bundle."""
    if platform.system() != "Darwin":
        return
    try:
        import cv2

        capture = cv2.VideoCapture(0, cv2.CAP_AVFOUNDATION)
        capture.release()
    except Exception:
        return


def main() -> int:
    # Import PySide6 lazily so non-GUI modules (config, capture, offline) stay importable
    # in headless environments and unit tests without a Qt platform plugin.
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication

    from zmetrics_desktop.context import AppContext
    from zmetrics_desktop.ui.main_window import MainWindow

    context = AppContext.build()  # validates configuration early (raises on bad env)

    app = QApplication(sys.argv)
    app.setApplicationName("ZMetrics")
    window = MainWindow(context)
    window.show()
    QTimer.singleShot(750, _request_macos_camera_permission)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

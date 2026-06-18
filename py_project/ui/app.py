"""PySide6 application bootstrap."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from ..config import APP_NAME, WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_TITLE
from .main_window import MainWindow


def run() -> int:
    """Create QApplication and show the main window."""
    # High-DPI support — must be set before creating QApplication
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("PyKnowledge")

    window = MainWindow()
    window.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
    window.setWindowTitle(WINDOW_TITLE)
    window.show()

    return app.exec()

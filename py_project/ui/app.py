"""PySide6 application bootstrap."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from ..config import APP_NAME, WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_TITLE
from .main_window import MainWindow


def run() -> int:
    """Create QApplication and show the main window."""
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("PyKnowledge")

    # High-DPI support
    app.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    window = MainWindow()
    window.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
    window.setWindowTitle(WINDOW_TITLE)
    window.show()

    return app.exec()

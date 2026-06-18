"""Version diff dialog — side-by-side comparison of two versions."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QSplitter,
    QTextBrowser, QLabel, QPushButton, QWidget,
)
from PySide6.QtCore import Qt

from ...engine.diff_engine import compute_diff, DiffResult


class VersionDiffDialog(QDialog):
    """Modal dialog showing a side-by-side diff of two versions."""

    def __init__(self, old_text: str, new_text: str,
                 old_label: str = "Previous", new_label: str = "Current",
                 parent=None):
        super().__init__(parent)
        self.setWindowTitle("Version Comparison")
        self.resize(1000, 700)
        self._setup_ui(old_text, new_text, old_label, new_label)

    def _setup_ui(self, old_text: str, new_text: str,
                  old_label: str, new_label: str) -> None:
        layout = QVBoxLayout(self)

        # Stats
        diff = compute_diff(old_text, new_text)
        stats = QLabel(
            f"Changes: {diff.insertions} additions, "
            f"{diff.deletions} deletions, "
            f"{diff.modifications} modifications"
        )
        stats.setStyleSheet("color: #cdd6f4; padding: 8px; font-size: 13px;")
        layout.addWidget(stats)

        # Side-by-side
        splitter = QSplitter(Qt.Horizontal)

        # Old version
        old_widget = QWidget()
        old_layout = QVBoxLayout(old_widget)
        old_layout.setContentsMargins(0, 0, 0, 0)
        old_header = QLabel(f"← {old_label}")
        old_header.setStyleSheet("color: #f38ba8; font-weight: bold; padding: 4px 8px;")
        old_layout.addWidget(old_header)

        old_browser = QTextBrowser()
        old_browser.setStyleSheet("""
            QTextBrowser {
                background-color: #181825;
                color: #cdd6f4;
                border: 1px solid #313244;
                font-family: Consolas, monospace;
                font-size: 13px;
            }
        """)
        old_browser.setPlainText(old_text if old_text else "(empty)")
        old_layout.addWidget(old_browser)
        splitter.addWidget(old_widget)

        # New version
        new_widget = QWidget()
        new_layout = QVBoxLayout(new_widget)
        new_layout.setContentsMargins(0, 0, 0, 0)
        new_header = QLabel(f"→ {new_label}")
        new_header.setStyleSheet("color: #a6e3a1; font-weight: bold; padding: 4px 8px;")
        new_layout.addWidget(new_header)

        new_browser = QTextBrowser()
        new_browser.setStyleSheet("""
            QTextBrowser {
                background-color: #181825;
                color: #cdd6f4;
                border: 1px solid #313244;
                font-family: Consolas, monospace;
                font-size: 13px;
            }
        """)
        new_browser.setPlainText(new_text if new_text else "(empty)")
        new_layout.addWidget(new_browser)
        splitter.addWidget(new_widget)

        layout.addWidget(splitter)

        # Close button
        close_btn = QPushButton("Close")
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #313244;
                color: #cdd6f4;
                border: none;
                border-radius: 4px;
                padding: 8px 20px;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #45475a; }
        """)
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn, alignment=Qt.AlignRight)

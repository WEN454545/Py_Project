"""Version history panel — version list with compare/restore actions."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QHBoxLayout, QLabel,
)
from PySide6.QtCore import Qt, Signal

from ...services.version_service import VersionService
from ...core.version import Version
from ...utils.time_utils import format_relative


class VersionPanel(QWidget):
    """Dockable right-panel showing version history for the current note."""

    version_selected = Signal(str)    # version_id
    compare_requested = Signal(str, str)  # version_id_a, version_id_b
    restore_requested = Signal(str)   # version_id

    def __init__(self, version_service: VersionService, parent=None):
        super().__init__(parent)
        self.version_service = version_service
        self._versions: list[Version] = []
        self._current_note_id: str | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # Header
        header = QLabel("📜 Version History")
        header.setStyleSheet("color: #cdd6f4; font-weight: bold; padding: 4px 8px;")
        layout.addWidget(header)

        # Version list
        self._list = QListWidget()
        self._list.setStyleSheet("""
            QListWidget {
                background-color: #1e1e2e;
                color: #cdd6f4;
                border: none;
                font-size: 12px;
            }
            QListWidget::item {
                padding: 6px 8px;
                border-bottom: 1px solid #313244;
            }
            QListWidget::item:selected {
                background-color: #313244;
            }
        """)
        self._list.setSelectionMode(QListWidget.ExtendedSelection)
        layout.addWidget(self._list)

        # Actions
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(4)

        compare_btn = QPushButton("Compare")
        compare_btn.setStyleSheet(self._btn_style())
        compare_btn.clicked.connect(self._on_compare)
        actions_layout.addWidget(compare_btn)

        restore_btn = QPushButton("Restore")
        restore_btn.setStyleSheet(self._btn_style())
        restore_btn.clicked.connect(self._on_restore)
        actions_layout.addWidget(restore_btn)

        layout.addLayout(actions_layout)

    def _btn_style(self) -> str:
        return """
            QPushButton {
                background-color: #313244;
                color: #cdd6f4;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #45475a;
            }
        """

    def load_for_note(self, note_id: str) -> None:
        """Load version history for a specific note."""
        self._current_note_id = note_id
        self._versions = self.version_service.get_history(note_id)
        self._list.clear()

        for v in self._versions:
            relative_time = format_relative(v.created_at)
            label = f"v{v.version_number} — {relative_time}"
            if v.change_summary:
                label += f" ({v.change_summary})"
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, v.id)
            self._list.addItem(item)

    def _on_compare(self) -> None:
        selected = self._list.selectedItems()
        if len(selected) == 2:
            id_a = selected[0].data(Qt.UserRole)
            id_b = selected[1].data(Qt.UserRole)
            self.compare_requested.emit(id_a, id_b)

    def _on_restore(self) -> None:
        selected = self._list.selectedItems()
        if selected:
            version_id = selected[0].data(Qt.UserRole)
            self.restore_requested.emit(version_id)

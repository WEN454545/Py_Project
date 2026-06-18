"""Note list panel — shows all notes with title and snippet."""

from __future__ import annotations

from PySide6.QtWidgets import QWidget, QVBoxLayout, QListWidget, QListWidgetItem, QLabel
from PySide6.QtCore import Qt, Signal

from ...core.note import Note


class NoteListPanel(QWidget):
    """Dockable left-panel showing the list of all notes."""

    note_selected = Signal(str)  # note_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self._notes: list[Note] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        header = QLabel("📝 Notes")
        header.setStyleSheet("color: #cdd6f4; font-weight: bold; padding: 4px 8px;")
        layout.addWidget(header)

        self._list = QListWidget()
        self._list.setStyleSheet("""
            QListWidget {
                background-color: #1e1e2e;
                color: #cdd6f4;
                border: none;
                font-size: 13px;
            }
            QListWidget::item {
                padding: 6px 8px;
                border-bottom: 1px solid #313244;
            }
            QListWidget::item:selected {
                background-color: #313244;
            }
            QListWidget::item:hover {
                background-color: #282840;
            }
        """)
        self._list.clicked.connect(self._on_clicked)
        layout.addWidget(self._list)

    def set_notes(self, notes: list[Note]) -> None:
        """Populate the list with notes."""
        self._notes = notes
        self._list.clear()
        for note in notes:
            item = QListWidgetItem(note.title)
            item.setData(Qt.UserRole, note.id)
            self._list.addItem(item)

    def _on_clicked(self, index) -> None:
        item = self._list.itemFromIndex(index)
        if item:
            note_id = item.data(Qt.UserRole)
            self.note_selected.emit(note_id)

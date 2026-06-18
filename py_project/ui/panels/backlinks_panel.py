"""Backlinks panel — shows incoming [[wikilinks]] for the current note."""

from __future__ import annotations

from PySide6.QtWidgets import QWidget, QVBoxLayout, QListWidget, QListWidgetItem, QLabel
from PySide6.QtCore import Qt, Signal

from ...engine.link_resolver import LinkResolver


class BacklinksPanel(QWidget):
    """Dockable right-panel showing notes that link TO the current note."""

    note_selected = Signal(str)  # note_id

    def __init__(self, link_resolver: LinkResolver, parent=None):
        super().__init__(parent)
        self.link_resolver = link_resolver
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        header = QLabel("🔗 Backlinks")
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

    def load_for_note(self, note_id: str) -> None:
        """Show backlinks for the given note."""
        backlinks = self.link_resolver.get_backlinks(note_id)
        self._list.clear()

        if not backlinks:
            empty = QListWidgetItem("No backlinks")
            empty.setFlags(Qt.NoItemFlags)
            self._list.addItem(empty)
            return

        for bl in backlinks:
            source_title = bl.get("source_title", "Unknown")
            link_text = bl.get("link_text") or ""
            label = f"{source_title}"
            if link_text:
                label += f" → {link_text}"
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, bl["source_note_id"])
            self._list.addItem(item)

    def _on_clicked(self, index) -> None:
        item = self._list.itemFromIndex(index)
        if item and item.data(Qt.UserRole):
            self.note_selected.emit(item.data(Qt.UserRole))

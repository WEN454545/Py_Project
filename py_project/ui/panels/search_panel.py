"""Search panel — query input + results list."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLineEdit, QListView, QLabel,
)
from PySide6.QtCore import Qt, Signal, QStringListModel

from ...services.search_service import SearchService
from ...core.search_result import SearchResult


class SearchPanel(QWidget):
    """Dockable right-panel for full-text search."""

    search_requested = Signal(str)           # query string
    result_selected = Signal(str)            # note_id

    def __init__(self, search_service: SearchService, parent=None):
        super().__init__(parent)
        self.search_service = search_service
        self._results: list[SearchResult] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # Search input
        self._input = QLineEdit()
        self._input.setPlaceholderText("Search notes... (tag:, title:)")
        self._input.setStyleSheet("""
            QLineEdit {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #89b4fa;
            }
        """)
        self._input.returnPressed.connect(self._on_search)
        layout.addWidget(self._input)

        # Results count
        self._count_label = QLabel("")
        self._count_label.setStyleSheet("color: #585b70; font-size: 11px; padding: 2px 8px;")
        layout.addWidget(self._count_label)

        # Results list
        self._list_view = QListView()
        self._list_view.setStyleSheet("""
            QListView {
                background-color: #1e1e2e;
                color: #cdd6f4;
                border: none;
                font-size: 13px;
            }
            QListView::item {
                padding: 6px 8px;
                border-bottom: 1px solid #313244;
            }
            QListView::item:selected {
                background-color: #313244;
            }
            QListView::item:hover {
                background-color: #282840;
            }
        """)
        self._list_view.clicked.connect(self._on_result_clicked)
        layout.addWidget(self._list_view)

    def _on_search(self) -> None:
        query = self._input.text().strip()
        if not query:
            return

        self.search_requested.emit(query)
        results = self.search_service.search(query)

        self._results = results
        display = [
            f"🔍 {r.title} — {r.snippet}"
            for r in results
        ]

        model = QStringListModel(display)
        self._list_view.setModel(model)

        self._count_label.setText(f"{len(results)} result(s)")

    def _on_result_clicked(self, index) -> None:
        if 0 <= index.row() < len(self._results):
            note_id = self._results[index.row()].note_id
            self.result_selected.emit(note_id)

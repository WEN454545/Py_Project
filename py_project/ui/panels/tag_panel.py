"""Tag tree panel — dockable widget showing hierarchical tags."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTreeView, QPushButton, QHBoxLayout, QMenu,
)
from PySide6.QtCore import Qt, Signal

from ...services.tag_service import TagService
from .tag_model import TagTreeModel


class TagPanel(QWidget):
    """Dockable left-panel showing the tag hierarchy."""

    tag_selected = Signal(str)    # tag_id
    tag_double_clicked = Signal(str)  # tag_id (for filtering notes)

    def __init__(self, tag_service: TagService, parent=None):
        super().__init__(parent)
        self.tag_service = tag_service
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Header
        header = QHBoxLayout()
        header.setContentsMargins(8, 4, 8, 4)
        title_button = QPushButton("🏷 Tags")
        title_button.setFlat(True)
        title_button.setStyleSheet("color: #cdd6f4; font-weight: bold; text-align: left;")
        header.addWidget(title_button)
        header.addStretch()

        add_btn = QPushButton("+")
        add_btn.setFixedSize(24, 24)
        add_btn.setToolTip("Add tag")
        add_btn.setStyleSheet("""
            QPushButton { background: #313244; color: #cdd6f4; border: none; border-radius: 4px; font-size: 16px; }
            QPushButton:hover { background: #45475a; }
        """)
        header.addWidget(add_btn)
        layout.addLayout(header)

        # Tree view
        self._tree = QTreeView()
        self._tree.setStyleSheet("""
            QTreeView {
                background-color: #1e1e2e;
                color: #cdd6f4;
                border: none;
                font-size: 13px;
            }
            QTreeView::item {
                padding: 4px 8px;
            }
            QTreeView::item:selected {
                background-color: #313244;
            }
            QTreeView::item:hover {
                background-color: #282840;
            }
            QTreeView::branch {
                background-color: #1e1e2e;
            }
        """)
        self._tree.setHeaderHidden(True)
        self._tree.setIndentation(16)
        self._tree.setContextMenuPolicy(Qt.CustomContextMenu)

        self._model = TagTreeModel(self.tag_service, self)
        self._tree.setModel(self._model)

        # Signals
        self._tree.clicked.connect(self._on_clicked)
        self._tree.doubleClicked.connect(self._on_double_clicked)

        layout.addWidget(self._tree)

    def _on_clicked(self, index) -> None:
        tag_id = index.data(Qt.UserRole)
        if tag_id:
            self.tag_selected.emit(tag_id)

    def _on_double_clicked(self, index) -> None:
        tag_id = index.data(Qt.UserRole)
        if tag_id:
            self.tag_double_clicked.emit(tag_id)

    def refresh(self) -> None:
        self._model.refresh()
        self._tree.expandAll()

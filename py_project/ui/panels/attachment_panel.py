"""Attachment panel — browse, insert, and manage file attachments."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QHBoxLayout, QLabel, QFileDialog, QMenu,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QIcon

from ...core.attachment import Attachment, AttachmentType
from ...services.attachment_service import AttachmentService
from ...config import ATTACHMENT_DIR


class AttachmentPanel(QWidget):
    """Dockable panel showing attachments for the current note."""

    attachment_selected = Signal(str)   # attachment_id
    insert_requested = Signal(str)      # attachment_id (insert into editor)

    def __init__(self, attachment_service: AttachmentService, parent=None):
        super().__init__(parent)
        self.attachment_service = attachment_service
        self._attachments: list[Attachment] = []
        self._current_note_id: str | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # Header
        header = QHBoxLayout()
        header.setContentsMargins(4, 4, 4, 4)

        title = QLabel("📎 Attachments")
        title.setStyleSheet("color: #cdd6f4; font-weight: bold;")
        header.addWidget(title)
        header.addStretch()

        add_btn = QPushButton("+")
        add_btn.setFixedSize(24, 24)
        add_btn.setToolTip("Add attachment")
        add_btn.setStyleSheet("""
            QPushButton { background: #313244; color: #cdd6f4; border: none; border-radius: 4px; font-size: 16px; }
            QPushButton:hover { background: #45475a; }
        """)
        add_btn.clicked.connect(self._add_attachment)
        header.addWidget(add_btn)

        layout.addLayout(header)

        # List
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
            QListWidget::item:hover {
                background-color: #282840;
            }
        """)
        self._list.setContextMenuPolicy(Qt.CustomContextMenu)
        self._list.customContextMenuRequested.connect(self._on_context_menu)
        self._list.doubleClicked.connect(self._on_double_click)
        layout.addWidget(self._list)

    def load_for_note(self, note_id: str) -> None:
        """Load attachments for the given note."""
        self._current_note_id = note_id
        self._attachments = self.attachment_service.get_attachments(note_id)
        self._list.clear()

        if not self._attachments:
            empty = QListWidgetItem("No attachments — click + to add")
            empty.setFlags(Qt.NoItemFlags)
            self._list.addItem(empty)
            return

        for att in self._attachments:
            icon = "🖼" if att.attachment_type in (AttachmentType.IMAGE, AttachmentType.SCREENSHOT, AttachmentType.ANNOTATION) else "📄"
            size_kb = att.file_size / 1024
            label = f"{icon} {att.file_name} ({size_kb:.1f} KB)"
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, att.id)
            self._list.addItem(item)

    def _add_attachment(self) -> None:
        """Open file dialog and import selected files."""
        files, _ = QFileDialog.getOpenFileNames(
            self, "Add Attachments", "",
            "All Files (*);;Images (*.png *.jpg *.jpeg *.gif *.webp);;Documents (*.pdf *.md *.txt)",
        )
        for file_path in files:
            try:
                att = self.attachment_service.import_file(
                    file_path,
                    note_id=self._current_note_id,
                )
                if self._current_note_id:
                    self.load_for_note(self._current_note_id)
            except Exception as e:
                pass  # Silently skip errors for now

    def _on_double_click(self, index) -> None:
        item = self._list.itemFromIndex(index)
        if item and item.data(Qt.UserRole):
            self.insert_requested.emit(item.data(Qt.UserRole))

    def _on_context_menu(self, pos) -> None:
        item = self._list.itemAt(pos)
        if not item or not item.data(Qt.UserRole):
            return

        attachment_id = item.data(Qt.UserRole)
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #1e1e2e; color: #cdd6f4;
                border: 1px solid #313244;
            }
            QMenu::item:selected { background-color: #313244; }
        """)

        insert_action = menu.addAction("Insert into note")
        insert_action.triggered.connect(lambda: self.insert_requested.emit(attachment_id))

        unlink_action = menu.addAction("Unlink from note")
        unlink_action.triggered.connect(lambda: self._unlink(attachment_id))

        delete_action = menu.addAction("Delete")
        delete_action.triggered.connect(lambda: self._delete(attachment_id))

        menu.exec(self._list.mapToGlobal(pos))

    def _unlink(self, attachment_id: str) -> None:
        self.attachment_service.unlink_from_note(attachment_id)
        if self._current_note_id:
            self.load_for_note(self._current_note_id)

    def _delete(self, attachment_id: str) -> None:
        self.attachment_service.delete(attachment_id)
        if self._current_note_id:
            self.load_for_note(self._current_note_id)

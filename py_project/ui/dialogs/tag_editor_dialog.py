"""Tag editor dialog — create, rename, or recolor a tag."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QComboBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from ...core.tag import Tag
from ...services.tag_service import TagService


class TagEditorDialog(QDialog):
    """Dialog for creating or editing a tag."""

    def __init__(
        self, tag_service: TagService,
        tag: Tag | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.tag_service = tag_service
        self.tag = tag
        self.setWindowTitle("New Tag" if tag is None else "Edit Tag")
        self.resize(350, 200)
        self._setup_ui()

        if tag:
            self._name_edit.setText(tag.name)
            if tag.parent_tag_id:
                # Find parent in combo
                for i in range(self._parent_combo.count()):
                    if self._parent_combo.itemData(i) == tag.parent_tag_id:
                        self._parent_combo.setCurrentIndex(i)
                        break

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Name
        layout.addWidget(QLabel("Tag Name:"))
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("e.g., python")
        self._name_edit.setStyleSheet("""
            QLineEdit {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        layout.addWidget(self._name_edit)

        # Parent
        layout.addWidget(QLabel("Parent Tag (optional):"))
        self._parent_combo = QComboBox()
        self._parent_combo.setStyleSheet("""
            QComboBox {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 4px;
                padding: 6px;
            }
            QComboBox::drop-down { border: none; }
        """)
        self._parent_combo.addItem("(none — root level)", None)
        for tag in self.tag_service.get_all_tags():
            path = self.tag_service.get_full_path(tag)
            self._parent_combo.addItem(path, tag.id)
        layout.addWidget(self._parent_combo)

        layout.addStretch()

        # Buttons
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #89b4fa;
                color: #1e1e2e;
                border: none;
                border-radius: 4px;
                padding: 6px 16px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #b4d0fb; }
        """)
        save_btn.clicked.connect(self._save)
        btn_layout.addWidget(save_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #313244;
                color: #cdd6f4;
                border: none;
                border-radius: 4px;
                padding: 6px 16px;
            }
            QPushButton:hover { background-color: #45475a; }
        """)
        cancel_btn.clicked.connect(self.close)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def _save(self) -> None:
        name = self._name_edit.text().strip()
        if not name:
            return

        parent_id = self._parent_combo.currentData()

        if self.tag:
            # Edit existing
            self.tag.name = name
            self.tag.parent_tag_id = parent_id
            self.tag_service.tag_repo.update(self.tag)
        else:
            # Create new
            self.tag_service.create_tag(name, parent_tag_id=parent_id)

        self.accept()

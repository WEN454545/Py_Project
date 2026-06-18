"""Import dialog — wizard for importing Obsidian vaults."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QFileDialog, QListWidget, QListWidgetItem,
    QProgressBar, QCheckBox,
)
from PySide6.QtCore import Qt

from ...services.import_export_service import ImportExportService


class ImportDialog(QDialog):
    """Dialog for previewing and executing an Obsidian vault import."""

    def __init__(self, import_export_service: ImportExportService, parent=None):
        super().__init__(parent)
        self.service = import_export_service
        self._preview_data: list[dict] = []
        self.setWindowTitle("Import from Obsidian")
        self.resize(600, 500)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Vault path selection
        path_layout = QHBoxLayout()
        self._path_edit = QLineEdit()
        self._path_edit.setPlaceholderText("Select Obsidian vault directory...")
        self._path_edit.setStyleSheet("""
            QLineEdit {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        path_layout.addWidget(self._path_edit)

        browse_btn = QPushButton("Browse...")
        browse_btn.setStyleSheet(self._btn_style())
        browse_btn.clicked.connect(self._browse)
        path_layout.addWidget(browse_btn)
        layout.addLayout(path_layout)

        # Scan button
        scan_btn = QPushButton("Scan Vault")
        scan_btn.setStyleSheet(self._btn_style())
        scan_btn.clicked.connect(self._scan)
        layout.addWidget(scan_btn)

        # Preview list
        self._list = QListWidget()
        self._list.setStyleSheet("""
            QListWidget {
                background-color: #1e1e2e;
                color: #cdd6f4;
                border: 1px solid #313244;
                font-size: 12px;
            }
        """)
        layout.addWidget(self._list)

        # Select all checkbox
        self._select_all_cb = QCheckBox("Select All")
        self._select_all_cb.setStyleSheet("color: #cdd6f4;")
        self._select_all_cb.stateChanged.connect(self._toggle_select_all)
        layout.addWidget(self._select_all_cb)

        # Progress
        self._progress = QProgressBar()
        self._progress.setVisible(False)
        layout.addWidget(self._progress)

        # Action buttons
        btn_layout = QHBoxLayout()
        self._import_btn = QPushButton("Import Selected")
        self._import_btn.setStyleSheet(self._btn_style())
        self._import_btn.clicked.connect(self._execute_import)
        self._import_btn.setEnabled(False)
        btn_layout.addWidget(self._import_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet(self._btn_style())
        cancel_btn.clicked.connect(self.close)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def _btn_style(self) -> str:
        return """
            QPushButton {
                background-color: #313244;
                color: #cdd6f4;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #45475a; }
        """

    def _browse(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select Obsidian Vault")
        if path:
            self._path_edit.setText(path)

    def _scan(self) -> None:
        vault_path = self._path_edit.text().strip()
        if not vault_path:
            return

        try:
            self._preview_data = self.service.preview_import(vault_path)
            self._list.clear()
            for info in self._preview_data:
                item = QListWidgetItem(
                    f"{info['title']}  ({info['relative_path']})  "
                    f"[{len(info.get('tags', []))} tags, "
                    f"{len(info.get('wikilinks', []))} links]"
                )
                item.setData(Qt.UserRole, info["relative_path"])
                item.setCheckState(Qt.Checked)
                self._list.addItem(item)

            self._import_btn.setEnabled(True)
            self._select_all_cb.setChecked(True)

        except Exception as e:
            self._list.clear()
            self._list.addItem(f"Error: {e}")

    def _toggle_select_all(self, state) -> None:
        checked = state == Qt.Checked
        for i in range(self._list.count()):
            item = self._list.item(i)
            item.setCheckState(Qt.Checked if checked else Qt.Unchecked)

    def _execute_import(self) -> None:
        selected = []
        for i in range(self._list.count()):
            item = self._list.item(i)
            if item.checkState() == Qt.Checked:
                selected.append(item.data(Qt.UserRole))

        if not selected:
            return

        self._progress.setVisible(True)
        self._progress.setMaximum(len(selected))

        try:
            result = self.service.execute_import(
                self._path_edit.text().strip(),
                selected,
            )
            self._list.clear()
            self._list.addItem(
                f"✅ Imported: {result['imported']}, "
                f"Skipped: {result['skipped']}, "
                f"Errors: {len(result['errors'])}"
            )
            for err in result["errors"]:
                self._list.addItem(f"❌ {err}")
            self._import_btn.setEnabled(False)
        except Exception as e:
            self._list.addItem(f"Error: {e}")
        finally:
            self._progress.setVisible(False)

"""Export dialog — choose output directory and options."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QFileDialog, QCheckBox, QProgressBar,
)
from PySide6.QtCore import Qt

from ...services.import_export_service import ImportExportService


class ExportDialog(QDialog):
    """Dialog for exporting notes to Markdown files."""

    def __init__(self, import_export_service: ImportExportService, parent=None):
        super().__init__(parent)
        self.service = import_export_service
        self.setWindowTitle("Export to Markdown")
        self.resize(500, 250)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Output directory
        layout.addWidget(QLabel("Output Directory:"))
        path_layout = QHBoxLayout()
        self._path_edit = QLineEdit()
        self._path_edit.setPlaceholderText("Select output directory...")
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
        browse_btn.setStyleSheet("""
            QPushButton {
                background-color: #313244;
                color: #cdd6f4;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover { background-color: #45475a; }
        """)
        browse_btn.clicked.connect(self._browse)
        path_layout.addWidget(browse_btn)
        layout.addLayout(path_layout)

        # Options
        self._flat_cb = QCheckBox("Flat structure (all files in one folder)")
        self._flat_cb.setStyleSheet("color: #cdd6f4;")
        layout.addWidget(self._flat_cb)

        # Progress
        self._progress = QProgressBar()
        self._progress.setVisible(False)
        layout.addWidget(self._progress)

        # Status
        self._status = QLabel("")
        self._status.setStyleSheet("color: #a6adc8; font-size: 12px;")
        self._status.setWordWrap(True)
        layout.addWidget(self._status)

        # Buttons
        btn_layout = QHBoxLayout()
        export_btn = QPushButton("Export")
        export_btn.setStyleSheet("""
            QPushButton {
                background-color: #89b4fa;
                color: #1e1e2e;
                border: none;
                border-radius: 4px;
                padding: 8px 20px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #b4d0fb; }
        """)
        export_btn.clicked.connect(self._export)
        btn_layout.addWidget(export_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #313244;
                color: #cdd6f4;
                border: none;
                border-radius: 4px;
                padding: 8px 20px;
            }
            QPushButton:hover { background-color: #45475a; }
        """)
        cancel_btn.clicked.connect(self.close)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def _browse(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if path:
            self._path_edit.setText(path)

    def _export(self) -> None:
        output_dir = self._path_edit.text().strip()
        if not output_dir:
            self._status.setText("Please select an output directory.")
            return

        self._progress.setVisible(True)
        self._progress.setRange(0, 0)  # Indeterminate

        try:
            result = self.service.export_all(
                output_dir,
                flat=self._flat_cb.isChecked(),
            )
            self._status.setText(
                f"✅ Exported {result['files_created']} files "
                f"({result['total_bytes']} bytes)."
            )
            if result["errors"]:
                self._status.setText(
                    self._status.text() + f"\nErrors: {result['errors']}"
                )
        except Exception as e:
            self._status.setText(f"❌ Export failed: {e}")
        finally:
            self._progress.setVisible(False)

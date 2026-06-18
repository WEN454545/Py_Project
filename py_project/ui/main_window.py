"""Main application window.

Central QMainWindow with menu bar, splitter layout for editor/preview,
and dock areas for side panels. All services and panels wired together.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QSplitter, QVBoxLayout, QLabel,
    QStatusBar, QMenuBar, QMenu, QToolBar, QDockWidget, QPushButton,
    QInputDialog, QMessageBox,
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QAction, QKeySequence, QFont

from ..config import DEBOUNCE_MS, WINDOW_TITLE, EDITOR_FONT_FAMILY, EDITOR_FONT_SIZE
from ..storage.database import Database
from ..services.note_service import NoteService
from ..services.tag_service import TagService
from ..services.search_service import SearchService
from ..services.version_service import VersionService
from ..services.attachment_service import AttachmentService
from ..services.import_export_service import ImportExportService
from ..engine.link_resolver import LinkResolver
from .editor.editor_widget import EditorWidget
from .preview.preview_widget import PreviewWidget
from .panels.tag_panel import TagPanel
from .panels.search_panel import SearchPanel
from .panels.version_panel import VersionPanel
from .panels.note_list_panel import NoteListPanel
from .panels.backlinks_panel import BacklinksPanel
from .panels.attachment_panel import AttachmentPanel
from .dialogs.version_diff_dialog import VersionDiffDialog
from .dialogs.import_dialog import ImportDialog
from .dialogs.export_dialog import ExportDialog
from .dialogs.tag_editor_dialog import TagEditorDialog
from .dialogs.screenshot_dialog import ScreenshotDialog
from .preview.preview_styles import get_theme, generate_css


class MainWindow(QMainWindow):
    """Top-level application window — all panels and services wired."""

    note_opened = Signal(str)
    note_saved = Signal(str)

    # Theme color maps for the main window chrome
    _THEME_STYLES = {
        "dark": """
            QMainWindow {{ background-color: {bg}; }}
            QStatusBar {{ background-color: {surface}; color: {text}; border-top: 1px solid {border}; }}
            QMenuBar {{ background-color: {surface}; color: {text}; border-bottom: 1px solid {border}; }}
            QMenuBar::item:selected {{ background-color: {border}; }}
            QMenu {{ background-color: {bg}; color: {text}; border: 1px solid {border}; }}
            QMenu::item:selected {{ background-color: {border}; }}
            QToolBar {{ background-color: {surface}; border-bottom: 1px solid {border}; spacing: 4px; padding: 2px; }}
            QDockWidget {{ background-color: {surface}; color: {text}; border: 1px solid {border}; }}
            QDockWidget::title {{ background-color: {surface}; padding: 4px 8px; border-bottom: 1px solid {border}; }}
            QSplitter::handle {{ background-color: {border}; width: 2px; height: 2px; }}
        """,
        "light": """
            QMainWindow {{ background-color: {bg}; }}
            QStatusBar {{ background-color: {surface}; color: {text}; border-top: 1px solid {border}; }}
            QMenuBar {{ background-color: {surface}; color: {text}; border-bottom: 1px solid {border}; }}
            QMenuBar::item:selected {{ background-color: {border}; }}
            QMenu {{ background-color: {bg}; color: {text}; border: 1px solid {border}; }}
            QMenu::item:selected {{ background-color: {border}; }}
            QToolBar {{ background-color: {surface}; border-bottom: 1px solid {border}; spacing: 4px; padding: 2px; }}
            QDockWidget {{ background-color: {surface}; color: {text}; border: 1px solid {border}; }}
            QDockWidget::title {{ background-color: {surface}; padding: 4px 8px; border-bottom: 1px solid {border}; }}
            QSplitter::handle {{ background-color: {border}; width: 2px; height: 2px; }}
        """,
    }

    def __init__(self, db: Database | None = None) -> None:
        super().__init__()
        self.setWindowTitle(WINDOW_TITLE)

        # ── Database and services ───────────────────────────────
        self._db = db or Database.from_default()
        self._db.connect()

        self._note_service = NoteService(self._db)
        self._tag_service = TagService(self._db)
        self._search_service = SearchService(self._db)
        self._version_service = VersionService(self._db)
        self._attachment_service = AttachmentService(self._db)
        self._import_export_service = ImportExportService(self._db)
        self._link_resolver = LinkResolver(self._db)

        # Current note state
        self._current_note_id: str | None = None
        self._panels_visible = True
        self._current_theme = "dark"

        self._setup_menu_bar()
        self._setup_toolbar()
        self._setup_central_area()
        self._setup_panels()
        self._setup_status_bar()
        self._apply_styles()

        # Create an initial note
        self._new_note()

    # ── Menu Bar ────────────────────────────────────────────────

    def _setup_menu_bar(self) -> None:
        mb = self.menuBar()

        # ── File ────────────────────────────────────────────────
        fm = mb.addMenu("&File")
        fm.addAction(self._action("&New Note", "Ctrl+N", self._new_note))
        fm.addAction(self._action("&Save", "Ctrl+S", self._save_note))
        fm.addSeparator()
        fm.addAction(self._action("&Import Obsidian...", None, self._import_obsidian))
        fm.addAction(self._action("&Export Markdown...", None, self._export_markdown))
        fm.addSeparator()
        fm.addAction(self._action("E&xit", "Alt+F4", self.close))

        # ── Edit ────────────────────────────────────────────────
        em = mb.addMenu("&Edit")
        em.addAction(self._action("&Undo", "Ctrl+Z",
                     lambda: self._editor.undo()))
        em.addAction(self._action("&Redo", "Ctrl+Y",
                     lambda: self._editor.redo()))
        em.addSeparator()
        em.addAction(self._action("Cu&t", "Ctrl+X",
                     lambda: self._editor.cut()))
        em.addAction(self._action("&Copy", "Ctrl+C",
                     lambda: self._editor.copy()))
        em.addAction(self._action("&Paste", "Ctrl+V",
                     lambda: self._editor.paste()))
        em.addSeparator()
        em.addAction(self._action("&Find...", "Ctrl+F", self._find_in_note))

        # ── View ────────────────────────────────────────────────
        vm = mb.addMenu("&View")
        vm.addAction(self._action("Toggle &Panels", "Ctrl+B", self._toggle_panels))
        vm.addSeparator()
        vm.addAction(self._action("Toggle &Theme (Dark/Light)", "Ctrl+Shift+T", self._toggle_theme))
        vm.addSeparator()
        vm.addAction(self._action("Zoom &In", "Ctrl+=", self._zoom_in))
        vm.addAction(self._action("Zoom &Out", "Ctrl+-", self._zoom_out))

        # ── Note ────────────────────────────────────────────────
        nm = mb.addMenu("&Note")
        nm.addAction(self._action("&Delete Note", "Ctrl+D", self._delete_note))
        nm.addAction(self._action("&Rename Note...", "F2", self._rename_note))
        nm.addSeparator()
        nm.addAction(self._action("&Add Tag...", "Ctrl+T", self._add_tag))

        # ── Version ─────────────────────────────────────────────
        vm2 = mb.addMenu("&Version")
        vm2.addAction(self._action("View &History", "Ctrl+H", self._show_version_history))
        vm2.addAction(self._action("&Cleanup Old Versions...", None, self._cleanup_versions))

        # ── Tools ───────────────────────────────────────────────
        tm = mb.addMenu("&Tools")
        tm.addAction(self._action("&Screenshot Capture", "Ctrl+Shift+S", self._capture_screenshot))

        # ── Help ────────────────────────────────────────────────
        hm = mb.addMenu("&Help")
        hm.addAction(self._action("&About", None, self._show_about))

    def _action(self, text: str, shortcut: str | None, callback) -> QAction:
        action = QAction(text, self)
        if shortcut:
            action.setShortcut(QKeySequence(shortcut))
        if callable(callback):
            action.triggered.connect(callback)
        return action

    # ── Toolbar ─────────────────────────────────────────────────

    def _setup_toolbar(self) -> None:
        tb = QToolBar("Main Toolbar", self)
        tb.setMovable(False)
        self.addToolBar(tb)

        for label, shortcut, slot in [
            ("New", "Ctrl+N", self._new_note),
            ("Save", "Ctrl+S", self._save_note),
            ("Find", "Ctrl+F", self._find_in_note),
        ]:
            btn = QPushButton(label)
            btn.setStyleSheet("""
                QPushButton { background: #313244; color: #cdd6f4; border: none;
                    border-radius: 4px; padding: 4px 12px; }
                QPushButton:hover { background: #45475a; }
            """)
            btn.clicked.connect(slot)
            btn.setToolTip(f"{label} ({shortcut})")
            tb.addWidget(btn)

    # ── Central Area ────────────────────────────────────────────

    def _setup_central_area(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        self._editor = EditorWidget(self)
        self._preview = PreviewWidget(self)
        self._preview.set_placeholder()

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self._editor)
        splitter.addWidget(self._preview)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter)

        # Wire editor → preview
        self._editor.text_changed_debounced.connect(self._on_editor_changed)

    # ── Panels ──────────────────────────────────────────────────

    def _setup_panels(self) -> None:
        # Left dock area
        left_dock = QDockWidget("Notes", self)
        self._note_list_panel = NoteListPanel()
        left_dock.setWidget(self._note_list_panel)
        left_dock.setFeatures(QDockWidget.DockWidgetMovable)
        self.addDockWidget(Qt.LeftDockWidgetArea, left_dock)

        left_dock2 = QDockWidget("Tags", self)
        self._tag_panel = TagPanel(self._tag_service)
        left_dock2.setWidget(self._tag_panel)
        left_dock2.setFeatures(QDockWidget.DockWidgetMovable)
        self.addDockWidget(Qt.LeftDockWidgetArea, left_dock2)

        # Right dock area
        right_dock = QDockWidget("Search", self)
        self._search_panel = SearchPanel(self._search_service)
        right_dock.setWidget(self._search_panel)
        right_dock.setFeatures(QDockWidget.DockWidgetMovable)
        self.addDockWidget(Qt.RightDockWidgetArea, right_dock)

        right_dock2 = QDockWidget("Backlinks", self)
        self._backlinks_panel = BacklinksPanel(self._link_resolver)
        right_dock2.setWidget(self._backlinks_panel)
        right_dock2.setFeatures(QDockWidget.DockWidgetMovable)
        self.addDockWidget(Qt.RightDockWidgetArea, right_dock2)

        right_dock3 = QDockWidget("Versions", self)
        self._version_panel = VersionPanel(self._version_service)
        right_dock3.setWidget(self._version_panel)
        right_dock3.setFeatures(QDockWidget.DockWidgetMovable)
        self.addDockWidget(Qt.RightDockWidgetArea, right_dock3)

        # Bottom dock area
        bottom_dock = QDockWidget("Attachments", self)
        self._attachment_panel = AttachmentPanel(self._attachment_service)
        bottom_dock.setWidget(self._attachment_panel)
        bottom_dock.setFeatures(QDockWidget.DockWidgetMovable)
        self.addDockWidget(Qt.BottomDockWidgetArea, bottom_dock)

        # Wire panel signals
        self._note_list_panel.note_selected.connect(self._open_note)
        self._tag_panel.tag_double_clicked.connect(self._filter_by_tag)
        self._search_panel.result_selected.connect(self._open_note)
        self._search_panel.search_requested.connect(self._on_search_requested)
        self._backlinks_panel.note_selected.connect(self._open_note)
        self._version_panel.compare_requested.connect(self._compare_versions)
        self._version_panel.restore_requested.connect(self._restore_version)
        self._attachment_panel.insert_requested.connect(self._insert_attachment)

        # Initial refresh
        self._refresh_panels()

    # ── Panel refresh ───────────────────────────────────────────

    def _refresh_panels(self) -> None:
        """Refresh all panels after data changes."""
        self._tag_panel.refresh()
        self._note_list_panel.set_notes(
            self._note_service.list_notes(limit=200)
        )
        if self._current_note_id:
            self._version_panel.load_for_note(self._current_note_id)
            self._backlinks_panel.load_for_note(self._current_note_id)
            self._attachment_panel.load_for_note(self._current_note_id)

    # ── Editor → Preview ────────────────────────────────────────

    def _on_editor_changed(self, text: str) -> None:
        if self._current_note_id is None:
            return
        try:
            html = self._note_service.render_preview(self._current_note_id, text)
            # Inject theme-aware CSS into the rendered HTML
            themed_css = generate_css(self._current_theme)
            html = html.replace(
                "<style>\n    :root {",
                f"<style>\n    {themed_css.split(chr(10))[2] if '{' in themed_css else ''}",
            )
            # Simpler: replace the entire <style> block
            import re
            html = re.sub(
                r"<style>.*?</style>",
                f"<style>{themed_css}</style>",
                html,
                flags=re.DOTALL,
            )
            self._preview.set_html(html)
            self._update_status(f"Editing — {len(text)} chars")
        except Exception:
            pass

    # ── Note actions ────────────────────────────────────────────

    def _new_note(self) -> None:
        note = self._note_service.create_note("Untitled")
        self._current_note_id = note.id
        self._editor.set_content("")
        self._preview.set_placeholder("Start typing to see the preview...")
        self._update_status("New note created")
        self._refresh_panels()
        self.note_opened.emit(note.id)

    def _open_note(self, note_id: str) -> None:
        note = self._note_service.get_note(note_id)
        if note is None:
            return
        self._current_note_id = note_id
        text = self._note_service.load_note(note_id) or ""
        self._editor.set_content(text)
        self._update_status(f"Opened: {note.title}")
        self._refresh_panels()
        self.note_opened.emit(note_id)

    def _save_note(self) -> None:
        if self._current_note_id is None:
            return
        text = self._editor.toPlainText()
        try:
            # Save note content
            self._note_service.save_note(self._current_note_id, text)

            # Create version snapshot
            self._version_service.create_version(self._current_note_id, text)

            # Update FTS index
            self._search_service.update_note_index(self._current_note_id)

            # Resolve links
            from ..engine.markdown_parser import parse_markdown
            blocks = parse_markdown(text, self._current_note_id)
            self._link_resolver.resolve_all(self._current_note_id, blocks)

            self._editor.mark_clean()
            self._update_status(f"Saved — {len(text)} chars")
            self._refresh_panels()
            self.note_saved.emit(self._current_note_id)
        except Exception as e:
            self._update_status(f"Save failed: {e}")

    def _delete_note(self) -> None:
        if self._current_note_id is None:
            return
        note = self._note_service.get_note(self._current_note_id)
        if note is None:
            return
        reply = QMessageBox.question(
            self, "Delete Note",
            f'Delete "{note.title}"?',
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self._note_service.delete_note(self._current_note_id)
            self._current_note_id = None
            self._editor.set_content("")
            self._preview.set_placeholder()
            self._update_status("Note deleted")
            self._refresh_panels()

    def _rename_note(self) -> None:
        if self._current_note_id is None:
            return
        note = self._note_service.get_note(self._current_note_id)
        if note is None:
            return
        name, ok = QInputDialog.getText(
            self, "Rename Note", "New title:", text=note.title,
        )
        if ok and name.strip():
            self._note_service.rename_note(self._current_note_id, name.strip())
            self._update_status(f"Renamed to: {name.strip()}")
            self._refresh_panels()

    # ── Tag actions ─────────────────────────────────────────────

    def _add_tag(self) -> None:
        if self._current_note_id is None:
            return
        dialog = TagEditorDialog(self._tag_service, parent=self)
        if dialog.exec() == TagEditorDialog.Accepted:
            self._refresh_panels()

    def _filter_by_tag(self, tag_id: str) -> None:
        """Filter note list by tag and show results."""
        note_ids = self._tag_service.get_note_ids_for_tag(tag_id)
        notes = []
        for nid in note_ids:
            n = self._note_service.get_note(nid)
            if n:
                notes.append(n)
        self._note_list_panel.set_notes(notes)
        self._update_status(f"{len(notes)} note(s) with tag")

    # ── Search ──────────────────────────────────────────────────

    def _on_search_requested(self, query: str) -> None:
        self._update_status(f"Search: {query}")

    # ── Find in note ────────────────────────────────────────────

    def _find_in_note(self) -> None:
        text, ok = QInputDialog.getText(
            self, "Find in Note", "Search for:",
        )
        if ok and text:
            self._editor.find(text)

    # ── Version actions ─────────────────────────────────────────

    def _show_version_history(self) -> None:
        if self._current_note_id:
            self._version_panel.load_for_note(self._current_note_id)

    def _compare_versions(self, id_a: str, id_b: str) -> None:
        try:
            diff = self._version_service.diff_versions(id_a, id_b)
            old_text = self._version_service.restore_version(id_a) or ""
            new_text = self._version_service.restore_version(id_b) or ""
            dialog = VersionDiffDialog(
                old_text, new_text,
                old_label=f"Version A",
                new_label=f"Version B",
                parent=self,
            )
            dialog.exec()
        except Exception as e:
            QMessageBox.warning(self, "Diff Error", str(e))

    def _restore_version(self, version_id: str) -> None:
        text = self._version_service.restore_version(version_id)
        if text is not None:
            reply = QMessageBox.question(
                self, "Restore Version",
                "Restore this version? Current unsaved changes will be lost.",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply == QMessageBox.Yes:
                self._editor.set_content(text)

    def _cleanup_versions(self) -> None:
        if self._current_note_id is None:
            return
        count = self._version_service.get_count(self._current_note_id)
        reply = QMessageBox.question(
            self, "Cleanup Versions",
            f"This note has {count} versions. Remove excess versions?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            deleted = self._version_service.cleanup_versions(self._current_note_id)
            self._update_status(f"Cleaned up {deleted} old version(s)")
            self._refresh_panels()

    # ── Import / Export ─────────────────────────────────────────

    def _import_obsidian(self) -> None:
        dialog = ImportDialog(self._import_export_service, self)
        dialog.exec()
        self._refresh_panels()
        # Rebuild search index after import
        self._search_service.rebuild_index()

    def _export_markdown(self) -> None:
        dialog = ExportDialog(self._import_export_service, self)
        dialog.exec()

    # ── Screenshot ──────────────────────────────────────────────

    def _capture_screenshot(self) -> None:
        dialog = ScreenshotDialog(self._attachment_service, self)
        dialog.screenshot_ready.connect(self._on_screenshot_ready)
        dialog.exec()

    def _on_screenshot_ready(self, png_bytes: bytes, rects: list, arrows: list, texts: list) -> None:
        """Handle completed screenshot: save to attachment store."""
        import json
        annotation_json = json.dumps({
            "rectangles": rects, "arrows": arrows, "texts": texts,
        }) if (rects or arrows or texts) else None

        att = self._attachment_service.save_screenshot(
            png_bytes,
            note_id=self._current_note_id,
            annotation_json=annotation_json,
        )

        # Insert image reference into editor
        if self._current_note_id:
            path = self._attachment_service.get_full_path(att)
            cursor = self._editor.textCursor()
            cursor.insertText(f"\n![{att.file_name}](attachment://{att.id})\n")
            self._refresh_panels()

        self._update_status(f"Screenshot saved: {att.file_name}")

    # ── Attachments ─────────────────────────────────────────────

    def _insert_attachment(self, attachment_id: str) -> None:
        """Insert an attachment reference into the editor."""
        att = self._attachment_service.get(attachment_id)
        if att is None:
            return
        cursor = self._editor.textCursor()
        if att.mime_type and att.mime_type.startswith("image/"):
            cursor.insertText(f"![{att.file_name}](attachment://{att.id})")
        else:
            cursor.insertText(f"[{att.file_name}](attachment://{att.id})")

    # ── View ────────────────────────────────────────────────────

    def _toggle_panels(self) -> None:
        self._panels_visible = not self._panels_visible
        for dock in self.findChildren(QDockWidget):
            dock.setVisible(self._panels_visible)

    def _toggle_theme(self) -> None:
        """Toggle between dark and light themes."""
        self._current_theme = "light" if self._current_theme == "dark" else "dark"
        self._apply_styles()
        # Re-render preview with new theme
        if self._current_note_id:
            self._on_editor_changed(self._editor.toPlainText())
        self._update_status(f"Theme: {self._current_theme}")

    def _zoom_in(self) -> None:
        font = self._editor.font()
        font.setPointSize(font.pointSize() + 1)
        self._editor.setFont(font)

    def _zoom_out(self) -> None:
        font = self._editor.font()
        if font.pointSize() > 6:
            font.setPointSize(font.pointSize() - 1)
            self._editor.setFont(font)

    # ── Help ────────────────────────────────────────────────────

    def _show_about(self) -> None:
        QMessageBox.about(
            self, "About PyKnowledge",
            "PyKnowledge v0.1.0\n\n"
            "Personal Knowledge Management System\n\n"
            "Features:\n"
            "• Markdown editing with live preview\n"
            "• Hierarchical tag organization\n"
            "• Full-text search (FTS5)\n"
            "• Version history with diff\n"
            "• Bidirectional [[wikilinks]]\n"
            "• Screenshot capture + annotation\n"
            "• Obsidian import / Markdown export",
        )

    # ── Status Bar ──────────────────────────────────────────────

    def _setup_status_bar(self) -> None:
        status = QStatusBar()
        self.setStatusBar(status)
        status.showMessage("Ready")

    def _update_status(self, message: str) -> None:
        self.statusBar().showMessage(message)

    # ── Styles ──────────────────────────────────────────────────

    def _apply_styles(self) -> None:
        """Apply application-wide stylesheet based on current theme."""
        t = get_theme(self._current_theme)
        style_template = self._THEME_STYLES.get(self._current_theme, self._THEME_STYLES["dark"])
        self.setStyleSheet(style_template.format(
            bg=t["bg"], surface=t["surface"], text=t["text"],
            subtext=t["subtext"], border=t["border"],
        ))

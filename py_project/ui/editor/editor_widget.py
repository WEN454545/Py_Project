"""Markdown editor widget — QPlainTextEdit subclass with line numbers."""

from __future__ import annotations

from PySide6.QtWidgets import QPlainTextEdit, QWidget, QTextEdit
from PySide6.QtCore import Qt, QRect, QSize, Signal
from PySide6.QtGui import (
    QFont,
    QColor,
    QPainter,
    QTextFormat,
    QTextOption,
    QKeyEvent,
)

from ...config import EDITOR_FONT_FAMILY, EDITOR_FONT_SIZE, EDITOR_TAB_WIDTH
from .syntax_highlighter import MarkdownSyntaxHighlighter


class LineNumberArea(QWidget):
    """Gutter widget that displays line numbers alongside the editor."""

    def __init__(self, editor: EditorWidget) -> None:
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self) -> QSize:
        return QSize(self.editor.line_number_area_width(), 0)

    def paintEvent(self, event) -> None:
        self.editor.line_number_area_paint_event(event)


class EditorWidget(QPlainTextEdit):
    """Markdown source editor with line numbers and debounced change signal.

    Signals:
        text_changed_debounced(str): Emitted 300ms after the last keystroke
            with the full text content.
    """

    text_changed_debounced = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_appearance()
        self._setup_line_numbers()
        self._setup_debounce()

        # Track if content changed since last save
        self._dirty = False

    # ── Appearance ──────────────────────────────────────────────

    def _setup_appearance(self) -> None:
        """Configure font, colors, and tab behavior."""
        font = QFont(EDITOR_FONT_FAMILY, EDITOR_FONT_SIZE)
        font.setStyleHint(QFont.Monospace)
        self.setFont(font)

        self.setTabStopDistance(
            self.fontMetrics().horizontalAdvance(" ") * EDITOR_TAB_WIDTH
        )

        self.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: #1e1e2e;
                color: #cdd6f4;
                border: none;
                padding: 12px 16px;
                selection-background-color: #45475a;
                selection-color: #cdd6f4;
            }}
        """)

        self.setLineWrapMode(QPlainTextEdit.WidgetWidth)
        self.setWordWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)

        # Attach syntax highlighter
        self._highlighter = MarkdownSyntaxHighlighter(self.document())

    # ── Line Numbers ────────────────────────────────────────────

    def _setup_line_numbers(self) -> None:
        self.line_number_area = LineNumberArea(self)

        self.blockCountChanged.connect(self._update_line_number_area_width)
        self.updateRequest.connect(self._update_line_number_area)
        self.cursorPositionChanged.connect(self._highlight_current_line)

        self._update_line_number_area_width(0)
        self._highlight_current_line()

    def line_number_area_width(self) -> int:
        """Compute width needed for the line number gutter."""
        digits = max(1, len(str(self.blockCount())))
        # 3 → three digits + small padding
        space = 6 + self.fontMetrics().horizontalAdvance("9") * digits
        return space

    def _update_line_number_area_width(self, _new_block_count: int) -> None:
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def _update_line_number_area(self, rect: QRect, dy: int) -> None:
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(
                0, rect.y(), self.line_number_area.width(), rect.height()
            )

        if rect.contains(self.viewport().rect()):
            self._update_line_number_area_width(0)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(
            QRect(cr.left(), cr.top(),
                  self.line_number_area_width(), cr.height())
        )

    def line_number_area_paint_event(self, event) -> None:
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), QColor("#181825"))

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        offset = self.contentOffset()
        top = int(self.blockBoundingGeometry(block).translated(offset).top())
        bottom = top + int(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(QColor("#585b70"))
                painter.drawText(
                    0, top,
                    self.line_number_area.width() - 3,
                    self.fontMetrics().height(),
                    Qt.AlignRight, number,
                )

            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            block_number += 1

    def _highlight_current_line(self) -> None:
        """Highlight the line the cursor is on."""
        extra_selections: list = []

        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            selection.format.setBackground(QColor("#313244"))
            selection.format.setProperty(QTextFormat.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extra_selections.append(selection)

        self.setExtraSelections(extra_selections)

    # ── Debounce ─────────────────────────────────────────────────

    def _setup_debounce(self) -> None:
        """Debounce text change events to avoid excessive parsing."""
        from PySide6.QtCore import QTimer

        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(300)  # 300ms
        self._debounce_timer.timeout.connect(self._emit_debounced)
        self.textChanged.connect(self._on_text_changed)

    def _on_text_changed(self) -> None:
        self._dirty = True
        self._debounce_timer.start()

    def _emit_debounced(self) -> None:
        self.text_changed_debounced.emit(self.toPlainText())

    # ── Public API ───────────────────────────────────────────────

    @property
    def is_dirty(self) -> bool:
        return self._dirty

    def mark_clean(self) -> None:
        self._dirty = False

    def set_content(self, text: str) -> None:
        """Set editor content programmatically (resets dirty flag)."""
        self.setPlainText(text)
        self._dirty = False

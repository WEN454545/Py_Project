"""Screenshot capture and annotation dialog.

Shows a fullscreen transparent overlay for region selection,
then opens the annotation overlay for marking up the capture.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QPushButton, QHBoxLayout,
    QLabel, QApplication,
)
from PySide6.QtCore import Qt, QRect, QPoint, Signal
from PySide6.QtGui import (
    QPixmap, QPainter, QPen, QColor, QBrush,
    QMouseEvent, QKeyEvent,
)

from ...services.screenshot_service import ScreenshotService
from ...services.attachment_service import AttachmentService


class RegionSelector(QDialog):
    """Fullscreen transparent overlay for selecting a capture region."""

    region_selected = Signal(QRect)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setWindowState(Qt.WindowFullScreen)
        self.setCursor(Qt.CrossCursor)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self._start: QPoint | None = None
        self._end: QPoint | None = None
        self._drawing = False

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        # Semi-transparent dark overlay
        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))

        if self._start and self._end:
            # Clear the selected region
            rect = QRect(self._start, self._end).normalized()
            painter.setCompositionMode(QPainter.CompositionMode_Clear)
            painter.fillRect(rect, Qt.transparent)

            # Draw selection border
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
            pen = QPen(QColor("#89b4fa"), 2)
            pen.setStyle(Qt.DashLine)
            painter.setPen(pen)
            painter.drawRect(rect)

            # Draw size label
            label = f"{rect.width()} × {rect.height()}"
            painter.setPen(QColor("#cdd6f4"))
            painter.drawText(
                rect.x() + 5, rect.y() - 5 if rect.y() > 30 else rect.bottom() + 15,
                label,
            )

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self._start = event.pos()
            self._end = event.pos()
            self._drawing = True
            self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drawing:
            self._end = event.pos()
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton and self._drawing:
            self._drawing = False
            self._end = event.pos()
            rect = QRect(self._start, self._end).normalized()
            if rect.width() > 10 and rect.height() > 10:
                self.region_selected.emit(rect)
                self.close()
            else:
                # Too small — cancel
                self.close()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key_Escape:
            self.close()


class AnnotationOverlay(QDialog):
    """Annotation overlay for drawing rectangles, arrows, and text on a screenshot."""

    annotation_done = Signal(bytes, list, list, list)  # PNG bytes, rects, arrows, texts

    def __init__(self, pixmap: QPixmap, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Annotate Screenshot")
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.Tool)

        self._pixmap = pixmap
        self._rectangles: list[dict] = []
        self._arrows: list[dict] = []
        self._texts: list[dict] = []
        self._tool = "rect"  # 'rect', 'arrow', 'text'
        self._start: QPoint | None = None
        self._current: QPoint | None = None
        self._drawing = False

        self.resize(pixmap.size())
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Canvas
        self._canvas = _AnnotationCanvas(self)
        self._canvas.setFixedSize(self._pixmap.size())
        self._canvas.setMouseTracking(True)
        self._canvas.mouse_pressed.connect(self._on_mouse_press)
        self._canvas.mouse_moved.connect(self._on_mouse_move)
        self._canvas.mouse_released.connect(self._on_mouse_release)
        layout.addWidget(self._canvas)

        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(8, 4, 8, 4)

        for tool_id, label in [("rect", "▭ Rect"), ("arrow", "→ Arrow"), ("text", "T Text")]:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setChecked(tool_id == self._tool)
            btn.setStyleSheet(self._toolbar_btn_style())
            btn.clicked.connect(lambda checked, t=tool_id: self._set_tool(t))
            toolbar.addWidget(btn)

        toolbar.addStretch()

        # Color
        for color, hex in [("Red", "#f38ba8"), ("Yellow", "#f9e2af"), ("Blue", "#89b4fa")]:
            color_btn = QPushButton("●")
            color_btn.setStyleSheet(f"color: {hex}; font-size: 16px; background: transparent; border: none;")
            color_btn.clicked.connect(lambda checked, h=hex: self._set_color(h))
            toolbar.addWidget(color_btn)

        toolbar.addStretch()

        done_btn = QPushButton("✓ Done")
        done_btn.setStyleSheet("""
            QPushButton {
                background-color: #a6e3a1; color: #1e1e2e;
                border: none; border-radius: 4px; padding: 6px 16px; font-weight: bold;
            }
            QPushButton:hover { background-color: #c0f0b8; }
        """)
        done_btn.clicked.connect(self._on_done)
        toolbar.addWidget(done_btn)

        layout.addLayout(toolbar)

    def _toolbar_btn_style(self) -> str:
        return """
            QPushButton {
                background-color: #313244; color: #cdd6f4;
                border: none; border-radius: 4px; padding: 6px 12px;
            }
            QPushButton:checked { background-color: #45475a; border: 1px solid #89b4fa; }
            QPushButton:hover { background-color: #45475a; }
        """

    def _set_tool(self, tool: str) -> None:
        self._tool = tool

    def _set_color(self, color: str) -> None:
        self._color = color

    def _on_mouse_press(self, pos: QPoint) -> None:
        self._start = pos
        self._current = pos
        self._drawing = True

    def _on_mouse_move(self, pos: QPoint) -> None:
        if self._drawing:
            self._current = pos
            self._canvas.update()

    def _on_mouse_release(self, pos: QPoint) -> None:
        if not self._drawing or not self._start:
            return
        self._current = pos

        if self._tool == "rect":
            rect = QRect(self._start, self._current).normalized()
            if rect.width() > 5 and rect.height() > 5:
                self._rectangles.append({
                    "x": rect.x(), "y": rect.y(),
                    "w": rect.width(), "h": rect.height(),
                    "color": getattr(self, "_color", "#f38ba8"),
                    "width": 3,
                })
        elif self._tool == "arrow":
            self._arrows.append({
                "x1": self._start.x(), "y1": self._start.y(),
                "x2": self._current.x(), "y2": self._current.y(),
                "color": getattr(self, "_color", "#f9e2af"),
                "width": 3,
            })
        elif self._tool == "text":
            self._texts.append({
                "x": self._start.x(), "y": self._start.y(),
                "text": "Note",  # User can edit later
                "color": getattr(self, "_color", "#ffffff"),
                "size": 18,
            })

        self._drawing = False
        self._start = None
        self._current = None
        self._canvas.update()

    def _on_done(self) -> None:
        """Composite annotations onto the image and emit the result."""
        annotated = ScreenshotService.composite_annotations(
            self._pixmap,
            self._rectangles,
            self._arrows,
            self._texts,
        )
        png_bytes = ScreenshotService.pixmap_to_png_bytes(annotated)
        self.annotation_done.emit(png_bytes, self._rectangles, self._arrows, self._texts)
        self.close()


from PySide6.QtCore import Signal as _Signal
from PySide6.QtWidgets import QWidget


class _AnnotationCanvas(QWidget):
    """Widget that paints the screenshot and live annotation preview."""

    mouse_pressed = _Signal(QPoint)
    mouse_moved = _Signal(QPoint)
    mouse_released = _Signal(QPoint)

    def paintEvent(self, event) -> None:
        parent = self.parent()
        if not isinstance(parent, AnnotationOverlay):
            return

        painter = QPainter(self)
        # Draw the base screenshot
        painter.drawPixmap(0, 0, parent._pixmap)

        # Draw existing rectangles
        for rect in parent._rectangles:
            pen = QPen(QColor(rect["color"]), rect["width"])
            painter.setPen(pen)
            painter.drawRect(rect["x"], rect["y"], rect["w"], rect["h"])

        # Draw existing arrows
        for arrow in parent._arrows:
            pen = QPen(QColor(arrow["color"]), arrow["width"])
            painter.setPen(pen)
            painter.drawLine(
                arrow["x1"], arrow["y1"],
                arrow["x2"], arrow["y2"],
            )

        # Draw existing texts
        for text in parent._texts:
            font = self.font()
            font.setPointSize(text["size"])
            font.setBold(True)
            painter.setFont(font)
            painter.setPen(QColor(text["color"]))
            painter.drawText(text["x"], text["y"], text["text"])

        # Draw live preview of current shape
        if parent._drawing and parent._start and parent._current:
            pen = QPen(QColor(getattr(parent, "_color", "#89b4fa")), 2)
            pen.setStyle(Qt.DashLine)
            painter.setPen(pen)
            if parent._tool == "rect":
                rect = QRect(parent._start, parent._current).normalized()
                painter.drawRect(rect)
            elif parent._tool == "arrow":
                painter.drawLine(parent._start, parent._current)

        painter.end()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self.mouse_pressed.emit(event.pos())

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        self.mouse_moved.emit(event.pos())

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self.mouse_released.emit(event.pos())


class ScreenshotDialog(QDialog):
    """Orchestrates the full screenshot → annotate → save flow."""

    screenshot_ready = Signal(bytes, list, list, list)  # png_bytes, rects, arrows, texts

    def __init__(self, attachment_service: AttachmentService, parent=None):
        super().__init__(parent)
        self.attachment_service = attachment_service
        self._pixmap: QPixmap | None = None
        self._start_capture()

    def _start_capture(self) -> None:
        """Step 1: Show region selector."""
        self.hide()  # Hide the dialog itself
        selector = RegionSelector(self)
        selector.region_selected.connect(self._on_region_selected)
        selector.exec()

    def _on_region_selected(self, rect: QRect) -> None:
        """Step 2: Capture the region and open annotation overlay."""
        self._pixmap = ScreenshotService.capture_region(rect)
        self._show_annotation()

    def _show_annotation(self) -> None:
        """Step 3: Show annotation overlay."""
        if self._pixmap is None:
            return

        overlay = AnnotationOverlay(self._pixmap, self.parent())
        overlay.annotation_done.connect(self._on_annotation_done)
        overlay.exec()

    def _on_annotation_done(self, png_bytes: bytes, rects: list, arrows: list, texts: list) -> None:
        """Step 4: Emit final result."""
        self.screenshot_ready.emit(png_bytes, rects, arrows, texts)
        self.accept()

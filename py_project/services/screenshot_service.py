"""Screenshot service — screen region capture and annotation compositing.

Qt-dependent methods (capture, compositing) use lazy imports so that
serialize_annotations and other pure-data methods work without PySide6.
"""

from __future__ import annotations

import io
import json
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from PySide6.QtGui import QPixmap, QPainter, QColor
    from PySide6.QtCore import QRect, QPoint


class ScreenshotService:
    """Captures screen regions and composites annotations onto images.

    Methods that require a display server (capture_fullscreen, capture_region,
    pixmap_to_png_bytes, composite_annotations) need PySide6 installed.
    serialize_annotations works without any Qt dependency.
    """

    @staticmethod
    def capture_fullscreen():
        """Capture the entire screen. Requires PySide6 + display."""
        from PySide6.QtWidgets import QApplication
        screen = QApplication.primaryScreen()
        if screen is None:
            raise RuntimeError("No screen available")
        return screen.grabWindow(0)

    @staticmethod
    def capture_region(rect):
        """Capture a specific screen region. Requires PySide6."""
        from PySide6.QtCore import QRect
        full = ScreenshotService.capture_fullscreen()
        return full.copy(rect)

    @staticmethod
    def pixmap_to_png_bytes(pixmap) -> bytes:
        """Convert a QPixmap to PNG bytes."""
        buffer = io.BytesIO()
        pixmap.save(buffer, "PNG")
        return buffer.getvalue()

    @staticmethod
    def composite_annotations(
        pixmap,
        rectangles: list[dict],
        arrows: list[dict],
        texts: list[dict],
    ):
        """Draw annotation shapes onto a copy of the pixmap. Requires PySide6."""
        from PySide6.QtGui import QPixmap, QPainter, QPen, QColor, QFont, QPolygon
        from PySide6.QtCore import QPoint, Qt

        result = QPixmap(pixmap)
        painter = QPainter(result)
        painter.setRenderHint(QPainter.Antialiasing)

        for rect in rectangles:
            pen = QPen(QColor(rect.get("color", "#f38ba8")))
            pen.setWidth(rect.get("width", 3))
            painter.setPen(pen)
            painter.drawRect(rect["x"], rect["y"], rect["w"], rect["h"])

        for arrow in arrows:
            pen = QPen(QColor(arrow.get("color", "#f9e2af")))
            pen.setWidth(arrow.get("width", 3))
            painter.setPen(pen)
            p1 = QPoint(arrow["x1"], arrow["y1"])
            p2 = QPoint(arrow["x2"], arrow["y2"])
            painter.drawLine(p1, p2)
            _draw_arrowhead_qt(painter, p1, p2, pen.color(), arrow.get("width", 3))

        for text in texts:
            font = QFont("sans-serif", text.get("size", 16))
            font.setBold(True)
            painter.setFont(font)
            painter.setPen(QColor(text.get("color", "#ffffff")))
            painter.drawText(text["x"], text["y"], text.get("text", ""))

        painter.end()
        return result

    @staticmethod
    def serialize_annotations(
        rectangles: list[dict],
        arrows: list[dict],
        texts: list[dict],
    ) -> str:
        """Serialize annotation data to JSON. Pure Python — no Qt needed."""
        return json.dumps({
            "rectangles": rectangles,
            "arrows": arrows,
            "texts": texts,
        })


def _draw_arrowhead_qt(painter, p1, p2, color, width: int) -> None:
    """Draw an arrowhead at p2. Requires QPainter, QPoint, QColor, QPolygon."""
    import math
    from PySide6.QtCore import QPoint
    from PySide6.QtGui import QPolygon

    dx = p2.x() - p1.x()
    dy = p2.y() - p1.y()
    length = math.sqrt(dx * dx + dy * dy)
    if length < 1:
        return

    ux, uy = dx / length, dy / length
    head_size = max(10, width * 3)
    px, py = -uy, ux

    tip = p2
    left = QPoint(
        int(p2.x() - head_size * ux + head_size * 0.5 * px),
        int(p2.y() - head_size * uy + head_size * 0.5 * py),
    )
    right = QPoint(
        int(p2.x() - head_size * ux - head_size * 0.5 * px),
        int(p2.y() - head_size * uy - head_size * 0.5 * py),
    )

    painter.setBrush(color)
    painter.setPen(color)
    painter.drawPolygon(QPolygon([tip, left, right]))

"""HTML preview widget — renders Markdown as styled HTML."""

from __future__ import annotations

from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import QUrl


class PreviewWidget(QWidget):
    """Right-pane widget that renders Markdown as HTML via QWebEngineView.

    Displays the parsed-and-rendered HTML output from the markdown engine.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._web_view = QWebEngineView(self)
        self._web_view.setStyleSheet("background-color: #1e1e2e; border: none;")
        self._web_view.setUrl(QUrl("about:blank"))
        layout.addWidget(self._web_view)

    def set_html(self, html: str) -> None:
        """Render the given HTML string in the preview pane.

        Args:
            html: Complete HTML document string from markdown_to_html.
        """
        self._web_view.setHtml(html)

    def set_placeholder(self, text: str = "Preview will appear here...") -> None:
        """Show a placeholder message when no content is loaded."""
        self._web_view.setHtml(f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
    body {{
        background-color: #1e1e2e;
        color: #585b70;
        display: flex;
        align-items: center;
        justify-content: center;
        height: 100vh;
        font-family: -apple-system, BlinkMacSystemFont, sans-serif;
        font-size: 16px;
    }}
</style></head><body><p>{text}</p></body></html>""")

    def reload(self) -> None:
        """Reload the current preview content."""
        self._web_view.reload()

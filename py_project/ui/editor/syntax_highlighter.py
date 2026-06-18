"""Markdown syntax highlighter for the editor.

Applies foreground color and font weight rules to different
Markdown constructs using QSyntaxHighlighter.
"""

from __future__ import annotations

import re

from PySide6.QtGui import (
    QSyntaxHighlighter,
    QTextCharFormat,
    QFont,
    QColor,
)
from PySide6.QtCore import QRegularExpression


# ── Catppuccin Mocha palette ────────────────────────────────────
C_TEXT = QColor("#cdd6f4")
C_SUBTEXT = QColor("#a6adc8")
C_SURFACE = QColor("#313244")
C_RED = QColor("#f38ba8")
C_GREEN = QColor("#a6e3a1")
C_YELLOW = QColor("#f9e2af")
C_BLUE = QColor("#89b4fa")
C_MAUVE = QColor("#cba6f7")
C_TEAL = QColor("#94e2d5")
C_PEACH = QColor("#fab387")
C_PINK = QColor("#f5c2e7")
C_OVERLAY = QColor("#585b70")


class MarkdownSyntaxHighlighter(QSyntaxHighlighter):
    """Applies Markdown-aware syntax highlighting to a QTextDocument."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rules: list[tuple[QRegularExpression, QTextCharFormat]] = []
        self._multi_line_rules: list[tuple[QRegularExpression, QTextCharFormat, int, int]] = []
        self._setup_rules()

    def _setup_rules(self) -> None:
        """Define all highlighting rules."""

        # ── Heading (# H1 through ###### H6) ──────────────────
        heading_fmt = QTextCharFormat()
        heading_fmt.setForeground(C_BLUE)
        heading_fmt.setFontWeight(QFont.Bold)
        self._rules.append((
            QRegularExpression(r"^#{1,6}\s+.*$"),
            heading_fmt,
        ))

        # ── Bold **text** ─────────────────────────────────────
        bold_fmt = QTextCharFormat()
        bold_fmt.setFontWeight(QFont.Bold)
        bold_fmt.setForeground(C_TEXT)
        self._rules.append((
            QRegularExpression(r"\*\*[^*\n]+?\*\*"),
            bold_fmt,
        ))

        # ── Italic *text* ─────────────────────────────────────
        italic_fmt = QTextCharFormat()
        italic_fmt.setFontItalic(True)
        italic_fmt.setForeground(C_SUBTEXT)
        self._rules.append((
            QRegularExpression(r"(?<!\*)\*[^*\n]+?\*(?!\*)"),
            italic_fmt,
        ))

        # ── Inline code `text` ─────────────────────────────────
        code_fmt = QTextCharFormat()
        code_fmt.setForeground(C_PEACH)
        code_fmt.setBackground(QColor("#11111b"))
        self._rules.append((
            QRegularExpression(r"`[^`\n]+?`"),
            code_fmt,
        ))

        # ── Wikilinks [[target]] or [[target|alias]] ───────────
        wiki_fmt = QTextCharFormat()
        wiki_fmt.setForeground(C_MAUVE)
        wiki_fmt.setFontWeight(QFont.Medium)
        self._rules.append((
            QRegularExpression(r"\[\[[^\]]+?\]\]"),
            wiki_fmt,
        ))

        # ── Block refs ((block-id)) ────────────────────────────
        blockref_fmt = QTextCharFormat()
        blockref_fmt.setForeground(C_YELLOW)
        self._rules.append((
            QRegularExpression(r"\(\([a-f0-9]{12}\)\)"),
            blockref_fmt,
        ))

        # ── URLs ───────────────────────────────────────────────
        url_fmt = QTextCharFormat()
        url_fmt.setForeground(C_TEAL)
        url_fmt.setUnderlineStyle(QTextCharFormat.SingleUnderline)
        self._rules.append((
            QRegularExpression(r"https?://[^\s)]+"),
            url_fmt,
        ))

        # ── Images ![alt](url) ─────────────────────────────────
        img_fmt = QTextCharFormat()
        img_fmt.setForeground(C_GREEN)
        self._rules.append((
            QRegularExpression(r"!\[[^\]]*\]\([^)]+\)"),
            img_fmt,
        ))

        # ── Standard links [text](url) ─────────────────────────
        link_fmt = QTextCharFormat()
        link_fmt.setForeground(C_TEAL)
        self._rules.append((
            QRegularExpression(r"\[[^\]]+\]\([^)]+\)"),
            link_fmt,
        ))

        # ── Horizontal rules --- / *** / ___ ───────────────────
        hr_fmt = QTextCharFormat()
        hr_fmt.setForeground(C_OVERLAY)
        self._rules.append((
            QRegularExpression(r"^[-*_]{3,}\s*$"),
            hr_fmt,
        ))

        # ── Blockquote > ───────────────────────────────────────
        quote_fmt = QTextCharFormat()
        quote_fmt.setForeground(C_OVERLAY)
        self._rules.append((
            QRegularExpression(r"^>\s?.*$"),
            quote_fmt,
        ))

        # ── List markers - / * / + / 1. ────────────────────────
        list_fmt = QTextCharFormat()
        list_fmt.setForeground(C_PINK)
        self._rules.append((
            QRegularExpression(r"^(\s*[-*+]|\s*\d+\.)\s"),
            list_fmt,
        ))

        # ── Table pipes | ──────────────────────────────────────
        table_fmt = QTextCharFormat()
        table_fmt.setForeground(C_OVERLAY)
        self._rules.append((
            QRegularExpression(r"\|"),
            table_fmt,
        ))

        # ── Inline math $...$ ──────────────────────────────────
        math_fmt = QTextCharFormat()
        math_fmt.setForeground(C_TEAL)
        self._rules.append((
            QRegularExpression(r"\$[^$\n]+?\$"),
            math_fmt,
        ))

        # ── Multi-line: fenced code blocks ```...``` ───────────
        fence_fmt = QTextCharFormat()
        fence_fmt.setForeground(C_PEACH)
        fence_fmt.setBackground(QColor("#11111b"))
        self._multi_line_rules.append((
            QRegularExpression(r"^```[\w]*$"),
            fence_fmt,
            1,  # Group 1 (not used, we track start/end by matching)
            0,  # Not used
        ))

        # ── Multi-line: math blocks $$...$$ ─────────────────────
        math_block_fmt = QTextCharFormat()
        math_block_fmt.setForeground(C_TEAL)
        self._multi_line_rules.append((
            QRegularExpression(r"^\$\$$"),
            math_block_fmt,
            1, 0,
        ))

    def highlightBlock(self, text: str) -> None:
        """Called automatically by Qt for each visible text block."""

        # Apply single-line rules
        for pattern, fmt in self._rules:
            iterator = pattern.globalMatch(text)
            while iterator.hasNext():
                match = iterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), fmt)

        # Apply multi-line rules (fenced blocks)
        self.setCurrentBlockState(0)

        self._highlight_fenced_blocks(text)
        self._highlight_math_blocks(text)

    def _highlight_fenced_blocks(self, text: str) -> None:
        """Highlight content inside fenced code blocks ``` ... ```."""
        # Track state across blocks: 0 = outside fence, 1 = inside fence
        prev_state = self.previousBlockState()

        fence_match = re.match(r"^```", text)
        if fence_match:
            if prev_state == 0:
                # Opening fence
                self.setFormat(0, len(text),
                               self._multi_line_rules[0][1])
                self.setCurrentBlockState(1)
            else:
                # Closing fence
                self.setFormat(0, len(text),
                               self._multi_line_rules[0][1])
                self.setCurrentBlockState(0)
        elif prev_state == 1:
            # Inside code block
            fmt = QTextCharFormat()
            fmt.setForeground(C_PEACH)
            self.setFormat(0, len(text), fmt)
            self.setCurrentBlockState(1)

    def _highlight_math_blocks(self, text: str) -> None:
        """Highlight content inside math blocks $$ ... $$."""
        prev_state = self.previousBlockState()

        if re.match(r"^\$\$$", text):
            self.setFormat(0, len(text),
                           self._multi_line_rules[1][1])
            self.setCurrentBlockState(2 if prev_state != 2 else 0)
        elif prev_state == 2:
            fmt = QTextCharFormat()
            fmt.setForeground(C_TEAL)
            self.setFormat(0, len(text), fmt)
            self.setCurrentBlockState(2)

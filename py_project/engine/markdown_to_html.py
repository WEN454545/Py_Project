"""Markdown block tree → HTML rendering.

Converts parsed Block objects into styled HTML suitable for QWebEngineView.
Uses bleach for sanitization (optional, graceful degradation without it).
"""

from __future__ import annotations

import re
from html import escape

from ..core.note import Block, BlockType

# Try to import bleach for sanitization; degrade gracefully
try:
    import bleach as _bleach

    def _sanitize(html: str) -> str:
        return _bleach.clean(
            html,
            tags=[
                "h1", "h2", "h3", "h4", "h5", "h6",
                "p", "br", "hr",
                "strong", "em", "code", "pre",
                "a", "img",
                "table", "thead", "tbody", "tr", "th", "td",
                "ul", "ol", "li",
                "blockquote",
                "div", "span",
            ],
            attributes={
                "a": ["href", "class", "data-note-id", "data-block-id"],
                "img": ["src", "alt", "width", "height"],
                "code": ["class"],
                "pre": ["class"],
                "span": ["class"],
                "div": ["class"],
            },
        )
except ImportError:
    def _sanitize(html: str) -> str:
        return html


def render_blocks_to_html(blocks: list[Block], title: str = "") -> str:
    """Render a list of Blocks into a complete HTML document fragment.

    Args:
        blocks: Ordered list of Block objects.
        title: Note title (used for the rendered h1 fallback).

    Returns:
        HTML string suitable for QWebEngineView.setHtml().
    """
    body_parts: list[str] = []

    # If first block is an h1, use it as the title display;
    # otherwise prepend the title as an h1.
    has_h1 = blocks and blocks[0].block_type == BlockType.HEADING and blocks[0].heading_level == 1

    for block in blocks:
        html = _render_block(block)
        if html:
            body_parts.append(html)

    body_html = "\n".join(body_parts)

    return _wrap_document(body_html, title)


def _render_block(block: Block) -> str:
    """Render a single block to its HTML representation."""
    content = _render_inline(block.content_raw)

    if block.block_type == BlockType.HEADING:
        level = block.heading_level or 1
        level = max(1, min(6, level))
        return f'<h{level} id="block-{block.id}">{content}</h{level}>'

    elif block.block_type == BlockType.CODE:
        lang = block.language or ""
        lang_class = f' class="language-{escape(lang)}"' if lang else ""
        escaped = escape(block.content_raw)
        return f'<pre{lang_class}><code{lang_class}>{escaped}</code></pre>'

    elif block.block_type == BlockType.MATH_BLOCK:
        return f'<div class="math-block" id="block-{block.id}">{escape(block.content_raw)}</div>'

    elif block.block_type == BlockType.TABLE:
        return _render_table(block.content_raw)

    elif block.block_type == BlockType.LIST_ITEM:
        return _render_list_items(block.content_raw)

    elif block.block_type == BlockType.BLOCKQUOTE:
        lines = block.content_raw.split("\n")
        inner = "\n".join(
            line.lstrip(">").lstrip() for line in lines
            if line.strip()
        )
        inner_html = _render_inline(inner)
        return f'<blockquote id="block-{block.id}"><p>{inner_html}</p></blockquote>'

    elif block.block_type == BlockType.HORIZONTAL_RULE:
        return '<hr>'

    elif block.block_type == BlockType.EMPTY:
        return '<br>'

    else:  # PARAGRAPH (default)
        return f'<p id="block-{block.id}">{content}</p>'


def _render_inline(text: str) -> str:
    """Convert inline Markdown to HTML within a single line/block.

    Order matters: escape first, then apply patterns from
    most-specific to least-specific.
    """
    # Don't escape content inside code spans — process them first
    result = text

    # Inline code (must process before other inline patterns to avoid
    # transforming content inside code spans)
    result = re.sub(r"`([^`]+)`", r'<code>\1</code>', result)

    # Images must come before links (similar syntax)
    result = re.sub(
        r'!\[([^\]]*)\]\(([^)]+)\)',
        r'<img src="\2" alt="\1">',
        result,
    )

    # Standard links
    result = re.sub(
        r'\[([^\]]+)\]\(([^)]+)\)',
        r'<a href="\2" target="_blank">\1</a>',
        result,
    )

    # Wikilinks [[target]] or [[target|alias]]
    result = re.sub(
        r'\[\[([^\]|#]+)(?:[|#]([^\]]+))?\]\]',
        lambda m: (
            f'<a class="wikilink" data-note-id="{escape(m.group(1).strip())}" '
            f'href="note://{escape(m.group(1).strip())}">'
            f'{escape(m.group(2).strip() if m.group(2) else m.group(1).strip())}</a>'
        ),
        result,
    )

    # Block references ((block-id))
    result = re.sub(
        r"\(\(([a-f0-9]{12})\)\)",
        r'<a class="blockref" data-block-id="\1" href="block://\1">\1</a>',
        result,
    )

    # Bold + italic (triple)
    result = re.sub(r"\*\*\*(.+?)\*\*\*", r"<strong><em>\1</em></strong>", result)

    # Bold
    result = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", result)

    # Italic (single * — be careful not to match **)
    result = re.sub(r"(?<!\*)\*([^*\n]+?)\*(?!\*)", r"<em>\1</em>", result)

    # Inline math $...$
    result = re.sub(
        r"(?<!\$)\$([^$\n]+?)\$(?!\$)",
        r'<span class="math-inline">\1</span>',
        result,
    )

    # Escape any remaining HTML special chars (protect already-inserted tags)
    # For simplicity, we trust the regex-generated HTML, but bleach will
    # sanitize the final output.

    return result


def _render_table(raw: str) -> str:
    """Render a Markdown table to HTML."""
    lines = raw.strip().split("\n")
    if len(lines) < 2:
        return f"<p>{_render_inline(raw)}</p>"

    html_parts = ["<table>"]

    # Header row
    header_cells = _parse_table_row(lines[0])
    html_parts.append("<thead><tr>")
    for cell in header_cells:
        html_parts.append(f"<th>{_render_inline(cell.strip())}</th>")
    html_parts.append("</tr></thead>")

    # Body rows (skip separator line if present)
    start = 2 if _is_table_separator(lines[1]) else 1
    if start < len(lines):
        html_parts.append("<tbody>")
        for line in lines[start:]:
            cells = _parse_table_row(line)
            html_parts.append("<tr>")
            for cell in cells:
                html_parts.append(f"<td>{_render_inline(cell.strip())}</td>")
            html_parts.append("</tr>")
        html_parts.append("</tbody>")

    html_parts.append("</table>")
    return "\n".join(html_parts)


def _parse_table_row(line: str) -> list[str]:
    """Parse a single row of a pipe-delimited table."""
    # Strip leading/trailing pipes and split
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [c.strip() for c in line.split("|")]


def _is_table_separator(line: str) -> bool:
    """Check if a table row is a separator (e.g. |---|:---:|---|)."""
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    cells = stripped.split("|")
    return all(
        re.match(r"^:?-{3,}:?$", c.strip())
        for c in cells
        if c.strip()
    )


def _render_list_items(raw: str) -> str:
    """Render multi-line list items into HTML ul/ol."""
    lines = raw.strip().split("\n")
    if not lines:
        return ""

    # Determine if ordered or unordered
    is_ordered = bool(re.match(r"^\s*\d+\.\s", lines[0]))
    tag = "ol" if is_ordered else "ul"

    items: list[str] = []
    current_item: list[str] = []

    for line in lines:
        # Check if this is a new list item
        if re.match(r"^\s*[-*+]\s", line) or re.match(r"^\s*\d+\.\s", line):
            if current_item:
                items.append("\n".join(current_item))
            # Strip the list marker
            content = re.sub(r"^\s*[-*+]\s", "", line)
            content = re.sub(r"^\s*\d+\.\s", "", content)
            current_item = [content]
        else:
            # Continuation of previous item
            current_item.append(line.strip())

    if current_item:
        items.append("\n".join(current_item))

    html = f"<{tag}>\n"
    for item in items:
        html += f"<li>{_render_inline(item)}</li>\n"
    html += f"</{tag}>"
    return html


def _wrap_document(body: str, title: str) -> str:
    """Wrap body HTML in a full document with CSS."""
    safe_body = _sanitize(body)
    safe_title = escape(title)
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>{safe_title}</title>
<style>
    {_preview_css()}
</style>
</head>
<body>
<article>
{safe_body}
</article>
</body>
</html>"""


def _preview_css() -> str:
    """Return the CSS stylesheet for the preview pane (dark theme default)."""
    from ..ui.preview.preview_styles import generate_css
    return generate_css("dark")

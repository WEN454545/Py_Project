"""Mind map → OPML export.

Converts a note's block tree (headings = nodes, content = notes)
into OPML format compatible with XMind, FreeMind, and other
mind-mapping tools.
"""

from __future__ import annotations

from html import escape
from xml.etree import ElementTree as ET
from typing import Optional

from ..core.note import Block, BlockType


def blocks_to_opml(blocks: list[Block], title: str = "Mind Map") -> str:
    """Convert a list of blocks into an OPML XML string.

    Headings (h1-h6) become nested outline nodes.
    Content blocks under a heading become _note attributes on that node.
    Non-heading blocks at the root level become top-level notes.

    Args:
        blocks: Ordered block list from markdown_parser.
        title: Root title for the OPML document.

    Returns:
        Pretty-printed OPML XML string.
    """
    # Build a tree of outline nodes
    root_node = _OutlineNode(text=title)

    # Stack tracks the current nesting level
    # stack[0] = h1, stack[1] = h2 nested under that h1, etc.
    stack: list[_OutlineNode] = [root_node]
    current_level = 0

    for block in blocks:
        if block.block_type == BlockType.HEADING and block.heading_level:
            level = block.heading_level
            text = block.content_raw

            # Pop stack until we're at the right parent level
            while len(stack) > 1 and len(stack) - 1 >= level:
                stack.pop()

            # Ensure we're at the parent of this heading
            while len(stack) <= level:
                # Create placeholder parent nodes if needed
                stack.append(stack[-1])

            # Pop to correct parent
            while len(stack) > level:
                stack.pop()

            parent = stack[-1] if stack else root_node
            node = _OutlineNode(text=text)
            parent.children.append(node)
            stack.append(node)

        elif block.block_type in (BlockType.PARAGRAPH, BlockType.LIST_ITEM,
                                   BlockType.CODE, BlockType.BLOCKQUOTE,
                                   BlockType.TABLE):
            # Attach content block as a note to the current heading
            if len(stack) > 1:
                current = stack[-1]
                note_text = block.content_raw[:200]
                if len(block.content_raw) > 200:
                    note_text += "..."
                current.note = (current.note + "\n" + note_text).strip() if current.note else note_text

    # Render to OPML XML
    return _render_opml(root_node)


class _OutlineNode:
    """Internal tree node for OPML outline structure."""

    def __init__(self, text: str = ""):
        self.text = text
        self.note: Optional[str] = None
        self.children: list[_OutlineNode] = []


def _render_opml(root: _OutlineNode) -> str:
    """Render an outline tree to OPML XML string."""
    opml = ET.Element("opml", version="2.0")

    head = ET.SubElement(opml, "head")
    title_el = ET.SubElement(head, "title")
    title_el.text = root.text
    ET.SubElement(head, "dateCreated").text = ""
    ET.SubElement(head, "dateModified").text = ""

    body = ET.SubElement(opml, "body")
    for child in root.children:
        _render_outline(body, child)

    # Pretty-print
    ET.indent(opml, space="  ")
    xml_str = ET.tostring(opml, encoding="unicode", method="xml")
    return f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_str}'


def _render_outline(parent_el: ET.Element, node: _OutlineNode) -> None:
    """Recursively render an outline node and its children."""
    attrib = {"text": node.text}
    if node.note:
        attrib["_note"] = node.note

    outline_el = ET.SubElement(parent_el, "outline", attrib)

    for child in node.children:
        _render_outline(outline_el, child)


def blocks_to_mindmap_json(blocks: list[Block]) -> dict:
    """Convert blocks to a mind-map JSON structure for D3.js / vis.js rendering.

    Returns:
        A nested dict with {name, children, note} suitable for frontend rendering.
    """
    root: dict = {"name": "Root", "children": []}
    stack: list[dict] = [root]
    current_level = 0

    for block in blocks:
        if block.block_type == BlockType.HEADING and block.heading_level:
            level = block.heading_level

            while len(stack) - 1 >= level:
                stack.pop()
            while len(stack) < level:
                dummy = {"name": "", "children": []}
                stack[-1]["children"].append(dummy)
                stack.append(dummy)

            parent = stack[-1]
            node = {"name": block.content_raw, "children": []}
            parent["children"].append(node)
            stack.append(node)

        elif block.block_type in (BlockType.PARAGRAPH, BlockType.LIST_ITEM,
                                   BlockType.CODE, BlockType.BLOCKQUOTE):
            if len(stack) > 1:
                current = stack[-1]
                snippet = block.content_raw[:150]
                if "note" not in current:
                    current["note"] = snippet
                else:
                    current["note"] += "\n" + snippet

    return root

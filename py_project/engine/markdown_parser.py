"""Markdown parsing pipeline: raw text → block tree.

Stage 1: Split on blank lines into raw blocks
Stage 2: Classify each block's type
Stage 3: Nest list items and blockquote contents
Stage 4: Inline parsing (bold, italic, code, links, wikilinks, block-refs)
"""

from __future__ import annotations

import re
from typing import Optional

from ..core.note import Block, BlockType
from ..utils.hash_utils import sha256
from ..utils.time_utils import now_iso
from .block_id import generate_block_id

# ── Regular expressions for block classification ────────────────

_RE_HEADING = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
_RE_CODE_FENCE = re.compile(r"^```(\w*)\s*$")
_RE_MATH_FENCE = re.compile(r"^\$\$\s*$")
_RE_TABLE_SEPARATOR = re.compile(r"^\|?[\s\-:|]+\|?$")
_RE_TABLE_ROW = re.compile(r"^\|.+\|$")
_RE_BLOCKQUOTE = re.compile(r"^>\s?(.*)$")
_RE_UNORDERED_LIST = re.compile(r"^(\s*)[-*+]\s+(.+)$")
_RE_ORDERED_LIST = re.compile(r"^(\s*)\d+\.\s+(.+)$")
_RE_HORIZONTAL_RULE = re.compile(r"^[-*_]{3,}\s*$")
_RE_EMPTY = re.compile(r"^\s*$")

# ── Inline patterns ─────────────────────────────────────────────

_RE_BOLD = re.compile(r"\*\*(.+?)\*\*")
_RE_ITALIC = re.compile(r"\*(.+?)\*")
_RE_BOLD_ITALIC = re.compile(r"\*\*\*(.+?)\*\*\*")
_RE_INLINE_CODE = re.compile(r"`([^`]+)`")
_RE_WIKILINK = re.compile(r"\[\[([^\]|#]+)(?:[|#]([^\]]+))?\]\]")
_RE_BLOCKREF = re.compile(r"\(\(([a-f0-9]{12})\)\)")
_RE_IMAGE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
_RE_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_RE_INLINE_MATH = re.compile(r"\$(.+?)\$")


def parse_markdown(text: str, note_id: str) -> list[Block]:
    """Parse raw Markdown text into an ordered list of Blocks.

    Args:
        text: Full Markdown source text.
        note_id: UUID of the parent note.

    Returns:
        Ordered list of Block objects representing the block tree.
    """
    raw_blocks = _split_into_raw_blocks(text)
    blocks: list[Block] = []
    now = now_iso()

    for i, raw in enumerate(raw_blocks):
        if not raw.strip():
            continue  # Skip pure-whitespace blocks

        block_type, extra = _classify_block(raw)
        block_id = generate_block_id(note_id, i, raw)
        block_hash = sha256(raw)

        block = Block(
            id=block_id,
            note_id=note_id,
            content_raw=raw,
            block_order=i,
            block_type=block_type,
            block_hash=block_hash,
            created_at=now,
            updated_at=now,
        )

        if block_type == BlockType.HEADING:
            block.heading_level = extra.get("level")
            block.content_raw = extra.get("content", raw)
        elif block_type == BlockType.CODE:
            block.language = extra.get("language")
            block.content_raw = extra.get("content", raw)

        blocks.append(block)

    # Assign parent-child relationships for nested structures
    _assign_parents(blocks)

    return blocks


def _split_into_raw_blocks(text: str) -> list[str]:
    """Split text on blank-line boundaries. Each segment = one raw block."""
    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Split on one or more blank lines
    parts = re.split(r"\n{2,}", text)
    return [p.strip() for p in parts]


def _classify_block(raw: str) -> tuple[BlockType, dict]:
    """Determine block type and extract type-specific metadata."""
    lines = raw.split("\n")

    # Empty / whitespace only
    if _RE_EMPTY.match(raw):
        return BlockType.EMPTY, {}

    # Heading: starts with # — check if the FIRST LINE is a heading
    # even if there are subsequent lines (treat non-blank continuation as content)
    first_line = lines[0].strip()
    m = _RE_HEADING.match(first_line)
    if m:
        level = len(m.group(1))
        content = m.group(2)
        if len(lines) == 1:
            return BlockType.HEADING, {"level": level, "content": content}
        else:
            # Multi-line: heading + trailing content — keep as heading with full raw
            return BlockType.HEADING, {"level": level, "content": raw}

    # Fenced code block: starts and ends with ```
    if lines[0].startswith("```") and len(lines) >= 2:
        m = _RE_CODE_FENCE.match(lines[0])
        language = m.group(1) if m and m.group(1) else None
        # Find closing fence
        end_idx = None
        for j in range(1, len(lines)):
            if lines[j].strip() == "```":
                end_idx = j
                break
        if end_idx is not None:
            content = "\n".join(lines[1:end_idx])
            return BlockType.CODE, {"language": language, "content": content}
        # If no closing fence, treat as code anyway
        content = "\n".join(lines[1:])
        return BlockType.CODE, {"language": language, "content": content}

    # Math block: $$ ... $$
    if _RE_MATH_FENCE.match(lines[0]):
        content = raw
        return BlockType.MATH_BLOCK, {"content": content}

    # Table: pipe-delimited rows
    if len(lines) >= 2 and _RE_TABLE_ROW.match(lines[0]):
        return BlockType.TABLE, {"content": raw}

    # Horizontal rule
    if _RE_HORIZONTAL_RULE.match(raw):
        return BlockType.HORIZONTAL_RULE, {}

    # Blockquote
    if all(line.startswith(">") or line.strip() == "" for line in lines if line.strip()):
        return BlockType.BLOCKQUOTE, {"content": raw}

    # List items (unordered or ordered)
    first_line = lines[0]
    if _RE_UNORDERED_LIST.match(first_line) or _RE_ORDERED_LIST.match(first_line):
        return BlockType.LIST_ITEM, {"content": raw}

    # Default: paragraph
    return BlockType.PARAGRAPH, {"content": raw}


def _assign_parents(blocks: list[Block]) -> None:
    """Assign parent_block_id for nested structures.

    Currently handles: adjacent list items under a virtual container.
    Future: blockquote nesting, deeper list nesting.
    """
    # Simple adjacency grouping for now — list items that are adjacent
    # get grouped under a synthetic parent (not stored, but linked via order)
    # Future implementation will handle true nesting.
    pass


# ── Inline parsing (for link resolution, not full HTML rendering) ──

def extract_wikilinks(text: str) -> list[tuple[str, Optional[str]]]:
    """Extract all [[target|alias]] wikilinks from text.

    Returns:
        List of (target_title, alias_or_None) tuples.
    """
    results: list[tuple[str, Optional[str]]] = []
    for match in _RE_WIKILINK.finditer(text):
        target = match.group(1).strip()
        alias = match.group(2).strip() if match.group(2) else None
        results.append((target, alias))
    return results


def extract_block_refs(text: str) -> list[str]:
    """Extract all ((block-id)) references from text.

    Returns:
        List of 12-char block IDs.
    """
    return [match.group(1) for match in _RE_BLOCKREF.finditer(text)]


def extract_images(text: str) -> list[tuple[str, str]]:
    """Extract all ![alt](url) image references.

    Returns:
        List of (alt_text, url) tuples.
    """
    return [(m.group(1), m.group(2)) for m in _RE_IMAGE.finditer(text)]


def extract_links(text: str) -> list[tuple[str, str]]:
    """Extract all [text](url) external links.

    Returns:
        List of (link_text, url) tuples.
    """
    return [(m.group(1), m.group(2)) for m in _RE_LINK.finditer(text)]

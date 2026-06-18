"""Note and Block domain models."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional

from ..utils.time_utils import now_iso


class BlockType(Enum):
    PARAGRAPH = "paragraph"
    HEADING = "heading"
    CODE = "code"
    MATH_BLOCK = "math_block"
    TABLE = "table"
    LIST_ITEM = "list_item"
    BLOCKQUOTE = "blockquote"
    HORIZONTAL_RULE = "horizontal_rule"
    EMPTY = "empty"


@dataclass
class Block:
    """A single paragraph-level chunk within a note.

    Blocks form a tree via parent_block_id for nested structures
    (list items, blockquotes). Flat order is by block_order.
    """

    id: str
    note_id: str
    content_raw: str
    block_order: int = 0
    block_type: BlockType = BlockType.PARAGRAPH
    parent_block_id: Optional[str] = None
    language: Optional[str] = None
    heading_level: Optional[int] = None
    block_hash: str = ""
    metadata_json: str = "{}"
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)


@dataclass
class Note:
    """A note is the root of a block tree.

    Metadata lives here; content is stored in Block records.
    """

    id: str
    title: str
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)
    is_deleted: bool = False
    sort_order: int = 0
    metadata_json: str = "{}"

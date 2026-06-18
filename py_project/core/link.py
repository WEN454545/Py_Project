"""Link domain model — bidirectional note connections."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from ..utils.time_utils import now_iso


class LinkType(Enum):
    WIKI = "wiki"
    BLOCK_REF = "block_ref"
    URL = "url"


@dataclass
class Link:
    """A directed link from one note to another.

    source_note_id contains [[target_note_id]].
    Backlinks are the reverse query: WHERE target_note_id = ?.
    """

    id: str
    source_note_id: str
    target_note_id: str
    source_block_id: Optional[str] = None
    link_text: Optional[str] = None
    link_type: LinkType = LinkType.WIKI
    created_at: str = field(default_factory=now_iso)

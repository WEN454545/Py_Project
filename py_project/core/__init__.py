"""Core domain models for PyKnowledge.

The core package has zero internal dependencies on other py_project packages.
All models are plain dataclasses — no persistence or UI logic.
"""

from .note import Note, Block, BlockType
from .tag import Tag
from .link import Link, LinkType
from .attachment import Attachment, AttachmentType
from .version import Version
from .search_result import SearchResult

__all__ = [
    "Note",
    "Block",
    "BlockType",
    "Tag",
    "Link",
    "LinkType",
    "Attachment",
    "AttachmentType",
    "Version",
    "SearchResult",
]

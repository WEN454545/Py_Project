"""Search result domain model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SearchResult:
    """A single full-text search hit."""

    note_id: str
    title: str
    snippet: str  # HTML snippet with <mark> highlights
    rank: float = 0.0
    tag_names: list[str] = field(default_factory=list)
    updated_at: str = ""

"""Tag domain model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ..utils.time_utils import now_iso


@dataclass
class Tag:
    """A hierarchical tag node.

    Tags form a tree via parent_tag_id. The full path is derived
    by walking the parent chain (e.g., "dev/python/async").
    """

    id: str
    name: str
    parent_tag_id: Optional[str] = None
    color: str = "#3B82F6"
    icon: Optional[str] = None
    sort_order: int = 0
    created_at: str = field(default_factory=now_iso)

"""Version domain model — note revision history."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ..utils.time_utils import now_iso


@dataclass
class Version:
    """A full-text snapshot of a note at a point in time.

    Created on manual Ctrl+S; stored for diff comparison and rollback.
    """

    id: str
    note_id: str
    version_number: int
    content_full: str
    content_hash: str
    change_summary: Optional[str] = None
    created_at: str = field(default_factory=now_iso)

"""Attachment domain model."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from ..utils.time_utils import now_iso


class AttachmentType(Enum):
    FILE = "file"
    IMAGE = "image"
    SCREENSHOT = "screenshot"
    ANNOTATION = "annotation"


@dataclass
class Attachment:
    """Metadata for a file attached to a note.

    Files are stored on disk under the attachment directory.
    annotation_json stores screenshot markup data (rectangles, arrows, text).
    """

    id: str
    file_name: str
    file_path: str  # Relative path within attachment store
    note_id: Optional[str] = None
    mime_type: Optional[str] = None
    file_size: int = 0
    width: Optional[int] = None
    height: Optional[int] = None
    attachment_type: AttachmentType = AttachmentType.FILE
    annotation_json: Optional[str] = None
    created_at: str = field(default_factory=now_iso)

"""Attachment repository — metadata persistence for file attachments."""

from __future__ import annotations

from typing import Optional

from ..core.attachment import Attachment, AttachmentType
from .database import Database
from ..utils.time_utils import now_iso


class AttachmentRepository:
    """Persists attachment metadata; actual files live on disk."""

    def __init__(self, db: Database):
        self.db = db

    def insert(self, attachment: Attachment) -> Attachment:
        self.db.insert(
            """INSERT INTO attachments (id, note_id, file_name, file_path,
               mime_type, file_size, width, height, attachment_type,
               annotation_json, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                attachment.id, attachment.note_id,
                attachment.file_name, attachment.file_path,
                attachment.mime_type, attachment.file_size,
                attachment.width, attachment.height,
                attachment.attachment_type.value,
                attachment.annotation_json,
                attachment.created_at,
            ),
        )
        return attachment

    def get(self, attachment_id: str) -> Optional[Attachment]:
        row = self.db.fetch_one(
            "SELECT * FROM attachments WHERE id = ?",
            (attachment_id,),
        )
        return self._row_to_attachment(row) if row else None

    def get_for_note(self, note_id: str) -> list[Attachment]:
        rows = self.db.fetch_all(
            """SELECT * FROM attachments
               WHERE note_id = ?
               ORDER BY created_at DESC""",
            (note_id,),
        )
        return [self._row_to_attachment(r) for r in rows]

    def get_all(self, limit: int = 100) -> list[Attachment]:
        rows = self.db.fetch_all(
            """SELECT * FROM attachments
               ORDER BY created_at DESC LIMIT ?""",
            (limit,),
        )
        return [self._row_to_attachment(r) for r in rows]

    def delete(self, attachment_id: str) -> None:
        """Delete attachment metadata (file cleanup handled by service)."""
        self.db.insert(
            "DELETE FROM attachments WHERE id = ?",
            (attachment_id,),
        )

    def unlink_from_note(self, attachment_id: str) -> None:
        """Remove note association without deleting the attachment."""
        self.db.insert(
            "UPDATE attachments SET note_id = NULL WHERE id = ?",
            (attachment_id,),
        )

    def link_to_note(self, attachment_id: str, note_id: str) -> None:
        """Associate an attachment with a note."""
        self.db.insert(
            "UPDATE attachments SET note_id = ? WHERE id = ?",
            (note_id, attachment_id),
        )

    def count_for_note(self, note_id: str) -> int:
        row = self.db.fetch_one(
            "SELECT COUNT(*) FROM attachments WHERE note_id = ?",
            (note_id,),
        )
        return row[0] if row else 0

    # ── Helpers ──────────────────────────────────────────────────

    @staticmethod
    def _row_to_attachment(row) -> Attachment:
        return Attachment(
            id=row["id"],
            note_id=row["note_id"],
            file_name=row["file_name"],
            file_path=row["file_path"],
            mime_type=row["mime_type"],
            file_size=row["file_size"],
            width=row["width"],
            height=row["height"],
            attachment_type=AttachmentType(row["attachment_type"]),
            annotation_json=row["annotation_json"],
            created_at=row["created_at"],
        )

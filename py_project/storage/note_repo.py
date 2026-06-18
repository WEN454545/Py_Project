"""Notes repository — CRUD operations for notes and their block trees."""

from __future__ import annotations

from typing import Optional

from ..core.note import Note, Block
from ..utils.time_utils import now_iso
from .database import Database


class NoteRepository:
    """Persists Note and Block domain objects to SQLite."""

    def __init__(self, db: Database):
        self.db = db

    # ── Notes ───────────────────────────────────────────────────

    def create(self, note: Note) -> Note:
        """Insert a new note."""
        self.db.insert(
            """INSERT INTO notes (id, title, created_at, updated_at,
               is_deleted, sort_order, metadata_json)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                note.id, note.title, note.created_at, note.updated_at,
                int(note.is_deleted), note.sort_order, note.metadata_json,
            ),
        )
        return note

    def get(self, note_id: str) -> Optional[Note]:
        """Fetch a note by ID."""
        row = self.db.fetch_one(
            "SELECT * FROM notes WHERE id = ? AND is_deleted = 0",
            (note_id,),
        )
        if row is None:
            return None
        return Note(
            id=row["id"],
            title=row["title"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            is_deleted=bool(row["is_deleted"]),
            sort_order=row["sort_order"],
            metadata_json=row["metadata_json"],
        )

    def get_by_title(self, title: str) -> Optional[Note]:
        """Find a note by exact title (case-insensitive)."""
        row = self.db.fetch_one(
            "SELECT * FROM notes WHERE LOWER(title) = LOWER(?) AND is_deleted = 0",
            (title,),
        )
        if row is None:
            return None
        return Note(
            id=row["id"],
            title=row["title"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            is_deleted=bool(row["is_deleted"]),
            sort_order=row["sort_order"],
            metadata_json=row["metadata_json"],
        )

    def list_all(self, limit: int = 100, offset: int = 0) -> list[Note]:
        """List all non-deleted notes, newest first."""
        rows = self.db.fetch_all(
            """SELECT * FROM notes
               WHERE is_deleted = 0
               ORDER BY updated_at DESC
               LIMIT ? OFFSET ?""",
            (limit, offset),
        )
        return [
            Note(
                id=r["id"], title=r["title"],
                created_at=r["created_at"], updated_at=r["updated_at"],
                is_deleted=bool(r["is_deleted"]), sort_order=r["sort_order"],
                metadata_json=r["metadata_json"],
            )
            for r in rows
        ]

    def update(self, note: Note) -> None:
        """Update note metadata."""
        note.updated_at = now_iso()
        self.db.insert(
            """UPDATE notes SET title = ?, updated_at = ?,
               is_deleted = ?, sort_order = ?, metadata_json = ?
               WHERE id = ?""",
            (
                note.title, note.updated_at,
                int(note.is_deleted), note.sort_order, note.metadata_json,
                note.id,
            ),
        )

    def soft_delete(self, note_id: str) -> None:
        """Soft-delete a note."""
        self.db.insert(
            "UPDATE notes SET is_deleted = 1, updated_at = ? WHERE id = ?",
            (now_iso(), note_id),
        )

    def count(self) -> int:
        row = self.db.fetch_one("SELECT COUNT(*) FROM notes WHERE is_deleted = 0")
        return row[0] if row else 0

    # ── Blocks ──────────────────────────────────────────────────

    def save_blocks(self, note_id: str, blocks: list[Block]) -> None:
        """Replace all blocks for a note in a transaction.

        Deletes existing blocks, then inserts the new set.
        """
        conn = self.db.conn
        conn.execute("DELETE FROM blocks WHERE note_id = ?", (note_id,))
        for block in blocks:
            conn.execute(
                """INSERT INTO blocks (id, note_id, parent_block_id,
                   block_order, block_type, content_raw, language,
                   heading_level, block_hash, created_at, updated_at,
                   metadata_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    block.id, block.note_id, block.parent_block_id,
                    block.block_order, block.block_type.value,
                    block.content_raw, block.language,
                    block.heading_level, block.block_hash,
                    block.created_at, block.updated_at,
                    block.metadata_json,
                ),
            )
        conn.commit()

    def get_blocks(self, note_id: str) -> list[Block]:
        """Fetch all blocks for a note, ordered by block_order."""
        rows = self.db.fetch_all(
            """SELECT * FROM blocks
               WHERE note_id = ?
               ORDER BY block_order""",
            (note_id,),
        )
        from ..core.note import BlockType

        return [
            Block(
                id=r["id"], note_id=r["note_id"],
                parent_block_id=r["parent_block_id"],
                block_order=r["block_order"],
                block_type=BlockType(r["block_type"]),
                content_raw=r["content_raw"],
                language=r["language"],
                heading_level=r["heading_level"],
                block_hash=r["block_hash"],
                created_at=r["created_at"],
                updated_at=r["updated_at"],
                metadata_json=r["metadata_json"],
            )
            for r in rows
        ]

    def get_full_text(self, note_id: str) -> str:
        """Reassemble the full Markdown text from blocks."""
        blocks = self.get_blocks(note_id)
        return "\n\n".join(b.content_raw for b in blocks)

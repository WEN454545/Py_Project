"""Links repository — bidirectional link storage and queries."""

from __future__ import annotations

from typing import Optional

from ..core.link import Link, LinkType
from .database import Database


class LinkRepository:
    """Manages the directed link graph between notes."""

    def __init__(self, db: Database):
        self.db = db

    # ── Link CRUD ───────────────────────────────────────────────

    def upsert_link(
        self,
        source_note_id: str,
        target_note_id: str,
        source_block_id: Optional[str] = None,
        link_text: Optional[str] = None,
        link_type: LinkType = LinkType.WIKI,
    ) -> Link:
        """Create or update a link. Deduplicates on (source, target, block, type)."""
        import uuid
        from ..utils.time_utils import now_iso

        # Check for existing
        row = self.db.fetch_one(
            """SELECT id FROM links
               WHERE source_note_id = ? AND target_note_id = ?
                 AND COALESCE(source_block_id, '') = COALESCE(?, '')
                 AND link_type = ?""",
            (source_note_id, target_note_id, source_block_id or "", link_type.value),
        )
        if row:
            link_id = row["id"]
            self.db.insert(
                "UPDATE links SET link_text=? WHERE id=?",
                (link_text, row["id"]),
            )
        else:
            link_id = str(uuid.uuid4())
            self.db.insert(
                """INSERT INTO links (id, source_note_id, target_note_id,
                   source_block_id, link_text, link_type, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (link_id, source_note_id, target_note_id,
                 source_block_id, link_text, link_type.value, now_iso()),
            )

        return Link(
            id=link_id,
            source_note_id=source_note_id,
            target_note_id=target_note_id,
            source_block_id=source_block_id,
            link_text=link_text,
            link_type=link_type,
        )

    def delete_links_from(self, source_note_id: str) -> None:
        """Remove all outgoing links from a note."""
        self.db.insert(
            "DELETE FROM links WHERE source_note_id = ?",
            (source_note_id,),
        )

    # ── Forward links (outgoing) ─────────────────────────────────

    def get_outgoing_links(self, note_id: str) -> list[Link]:
        """Get all links originating from a note."""
        rows = self.db.fetch_all(
            """SELECT * FROM links
               WHERE source_note_id = ?
               ORDER BY created_at DESC""",
            (note_id,),
        )
        return [self._row_to_link(r) for r in rows]

    # ── Backlinks (incoming) ─────────────────────────────────────

    def get_incoming_links(self, note_id: str) -> list[dict]:
        """Get all links pointing TO this note (backlinks).

        Returns enriched data with source note title for display.
        """
        rows = self.db.fetch_all(
            """SELECT l.*, n.title AS source_title
               FROM links l
               JOIN notes n ON n.id = l.source_note_id
               WHERE l.target_note_id = ? AND n.is_deleted = 0
               ORDER BY l.created_at DESC""",
            (note_id,),
        )
        return [
            {
                "id": r["id"],
                "source_note_id": r["source_note_id"],
                "source_title": r["source_title"],
                "link_text": r["link_text"],
                "link_type": r["link_type"],
                "source_block_id": r["source_block_id"],
                "created_at": r["created_at"],
            }
            for r in rows
        ]

    # ── Helpers ──────────────────────────────────────────────────

    @staticmethod
    def _row_to_link(row) -> Link:
        return Link(
            id=row["id"],
            source_note_id=row["source_note_id"],
            target_note_id=row["target_note_id"],
            source_block_id=row["source_block_id"],
            link_text=row["link_text"],
            link_type=LinkType(row["link_type"]),
            created_at=row["created_at"],
        )

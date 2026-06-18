"""Search repository — FTS5 full-text search wrapper."""

from __future__ import annotations

from typing import Optional

from ..core.search_result import SearchResult
from .database import Database


class SearchRepository:
    """Wraps SQLite FTS5 virtual table for full-text search."""

    def __init__(self, db: Database):
        self.db = db

    # ── FTS sync ────────────────────────────────────────────────

    def update_fts(self, note_id: str) -> None:
        """Rebuild the FTS index for a single note.

        Aggregates block content and tag names into the FTS content columns.
        """
        conn = self.db.conn

        # Gather note data
        note = conn.execute(
            "SELECT title FROM notes WHERE id = ?", (note_id,)
        ).fetchone()
        if not note:
            return

        title = note["title"]

        # Aggregate all block content
        blocks = conn.execute(
            "SELECT content_raw FROM blocks WHERE note_id = ? ORDER BY block_order",
            (note_id,),
        ).fetchall()
        body = " ".join(b["content_raw"] for b in blocks)

        # Aggregate tag names
        tag_rows = conn.execute(
            """SELECT t.name FROM tags t
               JOIN note_tags nt ON nt.tag_id = t.id
               WHERE nt.note_id = ?""",
            (note_id,),
        ).fetchall()
        tags = " ".join(r["name"] for r in tag_rows)

        # Remove old entry, insert new
        conn.execute("DELETE FROM notes_fts WHERE rowid = (SELECT rowid FROM notes WHERE id = ?)", (note_id,))

        # Insert new FTS entry. Match the rowid from the notes table for reference.
        note_row = conn.execute("SELECT rowid FROM notes WHERE id = ?", (note_id,)).fetchone()
        if note_row:
            conn.execute(
                "INSERT INTO notes_fts (rowid, title, body, tags) VALUES (?, ?, ?, ?)",
                (note_row["rowid"], title, body, tags),
            )
        conn.commit()

    def rebuild_all_fts(self) -> None:
        """Rebuild the entire FTS index."""
        conn = self.db.conn
        conn.execute("DELETE FROM notes_fts")
        note_ids = [
            r["id"] for r in
            conn.execute("SELECT id FROM notes WHERE is_deleted = 0").fetchall()
        ]
        for nid in note_ids:
            self.update_fts(nid)

    # ── Search ──────────────────────────────────────────────────

    def search(
        self,
        query: str,
        limit: int = 50,
        tag_filter: Optional[str] = None,
    ) -> list[SearchResult]:
        """Execute a full-text search query.

        Args:
            query: FTS5 MATCH expression.
            limit: Max results.
            tag_filter: Optional tag name to filter by.

        Returns:
            List of SearchResult with highlighted snippets.
        """
        conn = self.db.conn

        # Base query
        sql = """SELECT n.id, n.title, n.updated_at,
                        snippet(notes_fts, 2, '<mark>', '</mark>', '...', 40) AS snippet,
                        rank
                 FROM notes_fts
                 JOIN notes n ON n.rowid = notes_fts.rowid
                 WHERE n.is_deleted = 0
                   AND notes_fts MATCH ?"""

        params: list = [query]

        if tag_filter:
            sql += " AND notes_fts MATCH ?"
            params.append(f"tags:{tag_filter}")

        sql += " ORDER BY rank LIMIT ?"
        params.append(limit)

        rows = conn.execute(sql, tuple(params)).fetchall()

        results = []
        for r in rows:
            # Get tag names for this note
            tag_rows = conn.execute(
                """SELECT t.name FROM tags t
                   JOIN note_tags nt ON nt.tag_id = t.id
                   WHERE nt.note_id = ?""",
                (r["id"],),
            ).fetchall()

            results.append(SearchResult(
                note_id=r["id"],
                title=r["title"],
                snippet=r["snippet"] or "",
                rank=r["rank"] if r["rank"] is not None else 0.0,
                tag_names=[t["name"] for t in tag_rows],
                updated_at=r["updated_at"],
            ))

        return results

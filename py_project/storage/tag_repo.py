"""Tags repository — hierarchical tag CRUD and tree queries."""

from __future__ import annotations

from typing import Optional

from ..core.tag import Tag
from .database import Database
from ..utils.time_utils import now_iso


class TagRepository:
    """Persists hierarchical tags and note-tag associations."""

    def __init__(self, db: Database):
        self.db = db

    # ── Tag CRUD ────────────────────────────────────────────────

    def create(self, tag: Tag) -> Tag:
        self.db.insert(
            """INSERT OR IGNORE INTO tags (id, name, parent_tag_id, color, icon, sort_order, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (tag.id, tag.name, tag.parent_tag_id, tag.color, tag.icon, tag.sort_order, tag.created_at),
        )
        return tag

    def get(self, tag_id: str) -> Optional[Tag]:
        row = self.db.fetch_one("SELECT * FROM tags WHERE id = ?", (tag_id,))
        return self._row_to_tag(row) if row else None

    def get_by_path(self, path: str) -> Optional[Tag]:
        """Find a tag by its full path (e.g., 'dev/python/async')."""
        parts = [p.strip() for p in path.split("/") if p.strip()]
        if not parts:
            return None

        # Start from root-level tags matching the first part
        row = self.db.fetch_one(
            "SELECT * FROM tags WHERE name = ? AND parent_tag_id IS NULL",
            (parts[0],),
        )
        if not row:
            return None

        current = self._row_to_tag(row)

        for part in parts[1:]:
            row = self.db.fetch_one(
                "SELECT * FROM tags WHERE name = ? AND parent_tag_id = ?",
                (part, current.id),
            )
            if not row:
                return None
            current = self._row_to_tag(row)

        return current

    def get_children(self, parent_tag_id: Optional[str] = None) -> list[Tag]:
        """Get direct children of a tag. parent_tag_id=None fetches root tags."""
        if parent_tag_id is None:
            rows = self.db.fetch_all(
                "SELECT * FROM tags WHERE parent_tag_id IS NULL ORDER BY sort_order, name"
            )
        else:
            rows = self.db.fetch_all(
                "SELECT * FROM tags WHERE parent_tag_id = ? ORDER BY sort_order, name",
                (parent_tag_id,),
            )
        return [self._row_to_tag(r) for r in rows]

    def get_all(self) -> list[Tag]:
        """Get all tags."""
        rows = self.db.fetch_all("SELECT * FROM tags ORDER BY sort_order, name")
        return [self._row_to_tag(r) for r in rows]

    def update(self, tag: Tag) -> None:
        self.db.insert(
            """UPDATE tags SET name=?, parent_tag_id=?, color=?, icon=?, sort_order=?
               WHERE id=?""",
            (tag.name, tag.parent_tag_id, tag.color, tag.icon, tag.sort_order, tag.id),
        )

    def delete(self, tag_id: str) -> None:
        """Delete a tag and all its descendants (cascade)."""
        # SQLite foreign key with ON DELETE CASCADE handles children
        self.db.insert("DELETE FROM tags WHERE id = ?", (tag_id,))

    def get_full_path(self, tag: Tag) -> str:
        """Compute the full path string for a tag (e.g., 'dev/python/async')."""
        parts = [tag.name]
        current_id = tag.parent_tag_id
        while current_id:
            row = self.db.fetch_one(
                "SELECT name, parent_tag_id FROM tags WHERE id = ?",
                (current_id,),
            )
            if not row:
                break
            parts.insert(0, row["name"])
            current_id = row["parent_tag_id"]
        return "/".join(parts)

    # ── Note-Tag associations ────────────────────────────────────

    def tag_note(self, note_id: str, tag_id: str) -> None:
        self.db.insert(
            "INSERT OR IGNORE INTO note_tags (note_id, tag_id) VALUES (?, ?)",
            (note_id, tag_id),
        )

    def untag_note(self, note_id: str, tag_id: str) -> None:
        self.db.insert(
            "DELETE FROM note_tags WHERE note_id = ? AND tag_id = ?",
            (note_id, tag_id),
        )

    def get_tags_for_note(self, note_id: str) -> list[Tag]:
        rows = self.db.fetch_all(
            """SELECT t.* FROM tags t
               JOIN note_tags nt ON nt.tag_id = t.id
               WHERE nt.note_id = ?""",
            (note_id,),
        )
        return [self._row_to_tag(r) for r in rows]

    def get_notes_for_tag(self, tag_id: str) -> list[str]:
        """Return note IDs tagged with this tag (including descendants)."""
        # Collect all descendant tag IDs first
        all_tag_ids = self._get_descendant_ids(tag_id)

        placeholders = ",".join("?" for _ in all_tag_ids)
        rows = self.db.fetch_all(
            f"""SELECT DISTINCT note_id FROM note_tags
                WHERE tag_id IN ({placeholders})""",
            tuple(all_tag_ids),
        )
        return [r["note_id"] for r in rows]

    def _get_descendant_ids(self, tag_id: str) -> list[str]:
        """Recursively collect a tag and all its descendant IDs."""
        result = [tag_id]
        children = self.get_children(tag_id)
        for child in children:
            result.extend(self._get_descendant_ids(child.id))
        return result

    # ── Helpers ──────────────────────────────────────────────────

    @staticmethod
    def _row_to_tag(row) -> Tag:
        return Tag(
            id=row["id"],
            name=row["name"],
            parent_tag_id=row["parent_tag_id"],
            color=row["color"],
            icon=row["icon"],
            sort_order=row["sort_order"],
            created_at=row["created_at"],
        )

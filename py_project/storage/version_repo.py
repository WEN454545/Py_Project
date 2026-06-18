"""Versions repository — save, restore, and query note snapshots."""

from __future__ import annotations

from typing import Optional

from ..core.version import Version
from .database import Database


class VersionRepository:
    """Persists full-text snapshots of notes for version history."""

    def __init__(self, db: Database):
        self.db = db

    def insert(self, version: Version) -> Version:
        self.db.insert(
            """INSERT INTO versions (id, note_id, version_number, created_at,
               content_full, content_hash, change_summary)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                version.id, version.note_id, version.version_number,
                version.created_at, version.content_full, version.content_hash,
                version.change_summary,
            ),
        )
        return version

    def get_next_version_number(self, note_id: str) -> int:
        """Return the next version number for a note."""
        row = self.db.fetch_one(
            "SELECT COALESCE(MAX(version_number), 0) + 1 FROM versions WHERE note_id = ?",
            (note_id,),
        )
        return row[0] if row else 1

    def get_latest_hash(self, note_id: str) -> Optional[str]:
        """Get the content_hash of the most recent version, if any."""
        row = self.db.fetch_one(
            "SELECT content_hash FROM versions WHERE note_id = ? ORDER BY version_number DESC LIMIT 1",
            (note_id,),
        )
        return row["content_hash"] if row else None

    def get_versions(self, note_id: str) -> list[Version]:
        """Get all versions for a note, oldest first."""
        rows = self.db.fetch_all(
            "SELECT * FROM versions WHERE note_id = ? ORDER BY version_number ASC",
            (note_id,),
        )
        return [self._row_to_version(r) for r in rows]

    def get_version(self, version_id: str) -> Optional[Version]:
        row = self.db.fetch_one("SELECT * FROM versions WHERE id = ?", (version_id,))
        return self._row_to_version(row) if row else None

    def count(self, note_id: str) -> int:
        row = self.db.fetch_one(
            "SELECT COUNT(*) FROM versions WHERE note_id = ?", (note_id,),
        )
        return row[0] if row else 0

    def delete_versions(self, version_ids: list[str]) -> int:
        """Delete specific versions and return count deleted."""
        placeholders = ",".join("?" for _ in version_ids)
        self.db.insert(
            f"DELETE FROM versions WHERE id IN ({placeholders})",
            tuple(version_ids),
        )
        return len(version_ids)

    # ── Helpers ──────────────────────────────────────────────────

    @staticmethod
    def _row_to_version(row) -> Version:
        return Version(
            id=row["id"],
            note_id=row["note_id"],
            version_number=row["version_number"],
            content_full=row["content_full"],
            content_hash=row["content_hash"],
            change_summary=row["change_summary"],
            created_at=row["created_at"],
        )

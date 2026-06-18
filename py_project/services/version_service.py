"""Version service — snapshot, diff, restore, and cleanup."""

from __future__ import annotations

import uuid
from typing import Optional

from ..core.version import Version
from ..storage.database import Database
from ..storage.version_repo import VersionRepository
from ..engine.diff_engine import compute_diff, DiffResult
from ..utils.hash_utils import sha256
from ..utils.time_utils import now_iso


class VersionService:
    """Manages note version snapshots and diffs."""

    def __init__(self, db: Database):
        self.db = db
        self.version_repo = VersionRepository(db)

    # ── Snapshot ────────────────────────────────────────────────

    def create_version(
        self,
        note_id: str,
        content: str,
        change_summary: Optional[str] = None,
    ) -> Optional[Version]:
        """Create a new version snapshot if content has changed.

        Args:
            note_id: The note's UUID.
            content: Full Markdown text from the editor.
            change_summary: Optional user-provided label.

        Returns:
            The new Version, or None if content hasn't changed.
        """
        content_hash = sha256(content)

        # Skip if identical to latest version
        latest_hash = self.version_repo.get_latest_hash(note_id)
        if latest_hash == content_hash:
            return None

        version_number = self.version_repo.get_next_version_number(note_id)
        version = Version(
            id=str(uuid.uuid4()),
            note_id=note_id,
            version_number=version_number,
            content_full=content,
            content_hash=content_hash,
            change_summary=change_summary,
            created_at=now_iso(),
        )
        return self.version_repo.insert(version)

    # ── Query ───────────────────────────────────────────────────

    def get_history(self, note_id: str) -> list[Version]:
        """Get all versions for a note, oldest first."""
        return self.version_repo.get_versions(note_id)

    def get_count(self, note_id: str) -> int:
        return self.version_repo.count(note_id)

    # ── Diff ────────────────────────────────────────────────────

    def diff_versions(self, version_id_a: str, version_id_b: str) -> DiffResult:
        """Compute a paragraph-level diff between two versions."""
        v_a = self.version_repo.get_version(version_id_a)
        v_b = self.version_repo.get_version(version_id_b)

        if not v_a or not v_b:
            raise ValueError("Version not found")

        return compute_diff(
            v_a.content_full,
            v_b.content_full,
            old_version_id=version_id_a,
            new_version_id=version_id_b,
        )

    # ── Restore ─────────────────────────────────────────────────

    def restore_version(self, version_id: str) -> Optional[str]:
        """Get the full text of a specific version (for restoration).

        Returns:
            Full Markdown text, or None if version not found.
        """
        version = self.version_repo.get_version(version_id)
        if version is None:
            return None
        return version.content_full

    # ── Cleanup ─────────────────────────────────────────────────

    def cleanup_versions(self, note_id: str, max_versions: int = 50) -> int:
        """Remove excess versions, keeping important ones.

        Strategy:
        - Always keep the first version
        - Always keep the most recent version
        - Keep every 10th version as milestones
        - Remove the rest if over max_versions

        Args:
            note_id: The note's UUID.
            max_versions: Maximum versions to retain.

        Returns:
            Number of versions deleted.
        """
        versions = self.version_repo.get_versions(note_id)
        if len(versions) <= max_versions:
            return 0

        to_keep: set[str] = set()
        # Keep first
        to_keep.add(versions[0].id)
        # Keep last
        to_keep.add(versions[-1].id)
        # Keep every 10th
        for i, v in enumerate(versions):
            if i % 10 == 0:
                to_keep.add(v.id)

        # If still too many, trim from the middle
        if len(to_keep) < max_versions:
            # Add more from the end (most recent are more valuable)
            for v in reversed(versions):
                if len(to_keep) >= max_versions:
                    break
                to_keep.add(v.id)

        to_delete = [v.id for v in versions if v.id not in to_keep]
        if to_delete:
            return self.version_repo.delete_versions(to_delete)
        return 0

"""Tag service — hierarchical tag CRUD and tree manipulation."""

from __future__ import annotations

import uuid
from typing import Optional

from ..core.tag import Tag
from ..storage.database import Database
from ..storage.tag_repo import TagRepository
from ..utils.time_utils import now_iso


class TagService:
    """Manages the hierarchical tag tree."""

    def __init__(self, db: Database):
        self.db = db
        self.tag_repo = TagRepository(db)

    # ── Tag CRUD ────────────────────────────────────────────────

    def create_tag(
        self,
        name: str,
        parent_tag_id: Optional[str] = None,
        color: str = "#3B82F6",
    ) -> Tag:
        tag = Tag(
            id=str(uuid.uuid4()),
            name=name,
            parent_tag_id=parent_tag_id,
            color=color,
            created_at=now_iso(),
        )
        return self.tag_repo.create(tag)

    def get_tag(self, tag_id: str) -> Optional[Tag]:
        return self.tag_repo.get(tag_id)

    def get_root_tags(self) -> list[Tag]:
        return self.tag_repo.get_children(parent_tag_id=None)

    def get_children(self, tag_id: str) -> list[Tag]:
        return self.tag_repo.get_children(tag_id)

    def get_all_tags(self) -> list[Tag]:
        return self.tag_repo.get_all()

    def get_or_create_path(self, path: str) -> Tag:
        """Ensure a full tag path exists, creating missing tags.

        e.g., 'dev/python/async' creates dev, dev/python, dev/python/async.
        """
        existing = self.tag_repo.get_by_path(path)
        if existing:
            return existing

        parts = [p.strip() for p in path.split("/") if p.strip()]
        parent_id: Optional[str] = None

        for i, part in enumerate(parts):
            current_path = "/".join(parts[:i + 1])
            tag = self.tag_repo.get_by_path(current_path)
            if tag is None:
                tag = self.create_tag(part, parent_tag_id=parent_id)
            parent_id = tag.id

        return self.tag_repo.get_by_path(path)  # type: ignore

    def delete_tag(self, tag_id: str) -> None:
        self.tag_repo.delete(tag_id)

    def rename_tag(self, tag_id: str, new_name: str) -> None:
        tag = self.tag_repo.get(tag_id)
        if tag:
            tag.name = new_name
            self.tag_repo.update(tag)

    # ── Note-Tag operations ─────────────────────────────────────

    def tag_note(self, note_id: str, tag_id: str) -> None:
        self.tag_repo.tag_note(note_id, tag_id)

    def untag_note(self, note_id: str, tag_id: str) -> None:
        self.tag_repo.untag_note(note_id, tag_id)

    def get_tags_for_note(self, note_id: str) -> list[Tag]:
        return self.tag_repo.get_tags_for_note(note_id)

    def get_note_ids_for_tag(self, tag_id: str) -> list[str]:
        return self.tag_repo.get_notes_for_tag(tag_id)

    # ── Tree path ───────────────────────────────────────────────

    def get_full_path(self, tag: Tag) -> str:
        return self.tag_repo.get_full_path(tag)

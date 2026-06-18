"""Note service — orchestrates editing, parsing, storage, and rendering.

Sits between the UI (editor/preview) and the storage/engine layers.
"""

from __future__ import annotations

from typing import Optional
import uuid

from ..core.note import Note, Block
from ..storage.database import Database
from ..storage.note_repo import NoteRepository
from ..engine.markdown_parser import parse_markdown
from ..engine.markdown_to_html import render_blocks_to_html
from ..utils.time_utils import now_iso


class NoteService:
    """Orchestrates the full lifecycle of a note.

    - Creates/finds/updates notes
    - Parses Markdown into blocks
    - Renders blocks to HTML for preview
    - Coordinates with repos for persistence
    """

    def __init__(self, db: Database):
        self.db = db
        self.note_repo = NoteRepository(db)

    # ── Note lifecycle ──────────────────────────────────────────

    def create_note(self, title: str = "Untitled") -> Note:
        """Create a new empty note and return it."""
        now = now_iso()
        note = Note(
            id=str(uuid.uuid4()),
            title=title,
            created_at=now,
            updated_at=now,
        )
        self.note_repo.create(note)
        return note

    def get_note(self, note_id: str) -> Optional[Note]:
        """Fetch a note by ID."""
        return self.note_repo.get(note_id)

    def load_note(self, note_id: str) -> Optional[str]:
        """Load a note's full Markdown text."""
        return self.note_repo.get_full_text(note_id)

    def save_note(self, note_id: str, markdown_text: str) -> None:
        """Parse and persist a note's content.

        Args:
            note_id: The note's UUID.
            markdown_text: Raw Markdown source from the editor.
        """
        # Ensure note exists
        note = self.note_repo.get(note_id)
        if note is None:
            raise ValueError(f"Note not found: {note_id}")

        # Parse into blocks
        blocks = parse_markdown(markdown_text, note_id)

        # Persist blocks
        self.note_repo.save_blocks(note_id, blocks)

        # Update note timestamp
        note.updated_at = now_iso()
        self.note_repo.update(note)

    def delete_note(self, note_id: str) -> None:
        """Soft-delete a note."""
        self.note_repo.soft_delete(note_id)

    def list_notes(self, limit: int = 100, offset: int = 0) -> list[Note]:
        """List all notes."""
        return self.note_repo.list_all(limit, offset)

    def rename_note(self, note_id: str, new_title: str) -> None:
        """Rename a note."""
        note = self.note_repo.get(note_id)
        if note is None:
            raise ValueError(f"Note not found: {note_id}")
        note.title = new_title
        self.note_repo.update(note)

    # ── Preview rendering ───────────────────────────────────────

    def render_preview(self, note_id: str, markdown_text: str) -> str:
        """Parse and render note content to HTML for the preview pane.

        Args:
            note_id: The note's UUID.
            markdown_text: Raw Markdown source from the editor.

        Returns:
            Complete HTML document string.
        """
        note = self.note_repo.get(note_id)
        title = note.title if note else "Untitled"
        blocks = parse_markdown(markdown_text, note_id)
        return render_blocks_to_html(blocks, title)

    # ── Snapshot for versions ───────────────────────────────────

    def get_current_text(self, note_id: str) -> str:
        """Get the current full text of a note (for version snapshots)."""
        return self.note_repo.get_full_text(note_id)

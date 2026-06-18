"""Import/Export service — orchestrates Obsidian imports and Markdown exports."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from ..core.note import Note
from ..storage.database import Database
from ..storage.note_repo import NoteRepository
from ..engine.import_obsidian import scan_vault
from ..engine.export_markdown import export_notes
from ..engine.markdown_parser import parse_markdown
from .note_service import NoteService
from .tag_service import TagService


class ImportExportService:
    """Handles data migration in and out of PyKnowledge."""

    def __init__(self, db: Database):
        self.db = db
        self.note_repo = NoteRepository(db)
        self.note_service = NoteService(db)
        self.tag_service = TagService(db)

    # ── Import Obsidian ─────────────────────────────────────────

    def preview_import(self, vault_path: str) -> list[dict]:
        """Scan a vault and return preview data without importing."""
        return scan_vault(vault_path)

    def execute_import(self, vault_path: str, selected_paths: Optional[list[str]] = None) -> dict:
        """Import notes from an Obsidian vault.

        Args:
            vault_path: Root directory of the vault.
            selected_paths: If provided, only import these relative paths.

        Returns:
            dict with keys: imported, skipped, errors.
        """
        all_notes = scan_vault(vault_path)
        result = {"imported": 0, "skipped": 0, "errors": []}

        for info in all_notes:
            if selected_paths and info["relative_path"] not in selected_paths:
                result["skipped"] += 1
                continue

            try:
                # Create the note
                note = self.note_service.create_note(info["title"])

                # Import frontmatter metadata
                if info["frontmatter"]:
                    import json
                    note.metadata_json = json.dumps(info["frontmatter"])
                    self.note_repo.update(note)

                # Save content
                self.note_service.save_note(note.id, info["body"])

                # Import tags
                for tag_name in info.get("tags", []):
                    if isinstance(tag_name, list):
                        continue  # Skip nested lists
                    tag = self.tag_service.get_or_create_path(str(tag_name))
                    self.tag_service.tag_note(note.id, tag.id)

                result["imported"] += 1

            except Exception as e:
                result["errors"].append(f"{info['relative_path']}: {e}")

        return result

    # ── Export Markdown ─────────────────────────────────────────

    def export_all(self, output_dir: str, flat: bool = False) -> dict:
        """Export all notes to a Markdown folder."""
        notes = self.note_repo.list_all(limit=10000)
        note_texts: list[tuple[Note, str]] = []
        for note in notes:
            text = self.note_repo.get_full_text(note.id)
            note_texts.append((note, text))

        return export_notes(note_texts, output_dir, flat=flat)

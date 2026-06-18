"""Markdown folder exporter.

Exports notes from the database to standard .md files on disk.
Reassembles blocks, converts wikilinks to relative paths, adds frontmatter.
"""

from __future__ import annotations

import re
from pathlib import Path

from ..core.note import Note
from ..utils.file_utils import safe_filename


def export_notes(
    notes: list[tuple[Note, str]],
    output_dir: str | Path,
    flat: bool = False,
) -> dict:
    """Export notes to a Markdown folder.

    Args:
        notes: List of (Note, full_markdown_text) tuples.
        output_dir: Target directory for .md files.
        flat: If True, all files go in a single folder.
              If False, files are organized by tag subdirectories.

    Returns:
        dict with keys: files_created, total_bytes, errors.
    """
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    result = {"files_created": 0, "total_bytes": 0, "errors": []}

    # Build note title → filename mapping
    filenames: dict[str, str] = {}
    for note, _ in notes:
        filename = safe_filename(note.title) + ".md"
        # Handle duplicates
        base = filename
        counter = 1
        while filename in filenames.values():
            filename = f"{safe_filename(note.title)}_{counter}.md"
            counter += 1
        filenames[note.id] = filename

    for note, full_text in notes:
        try:
            filename = filenames[note.id]

            # Convert [[wikilinks]] to relative .md links
            exported_text = _convert_wikilinks(full_text, filenames)

            # Add YAML frontmatter
            frontmatter = _build_frontmatter(note)
            exported_text = frontmatter + "\n" + exported_text

            # Write file
            if flat:
                target_path = output / filename
            else:
                # Put in root for now; tag subdirs is future enhancement
                target_path = output / filename

            target_path.write_text(exported_text, encoding="utf-8")
            result["files_created"] += 1
            result["total_bytes"] += len(exported_text)

        except Exception as e:
            result["errors"].append(f"{note.title}: {e}")

    return result


def _convert_wikilinks(text: str, filenames: dict[str, str]) -> str:
    """Convert [[Note Title]] to [Note Title](./Note-Title.md)."""
    def replacer(match):
        target_title = match.group(1).strip()
        alias = match.group(2).strip() if match.group(2) else target_title

        # Find the filename for this title
        # We only have filenames by note ID, not by title, so this is approximate.
        # For the P0 version, convert to safe filename directly.
        safe = safe_filename(target_title) + ".md"
        return f"[{alias}](./{safe})"

    return re.sub(
        r'\[\[([^\]|#]+)(?:[|#]([^\]]+))?\]\]',
        replacer,
        text,
    )


def _build_frontmatter(note: Note) -> str:
    """Build YAML frontmatter for an exported note."""
    import json
    lines = ["---", f"title: {note.title}", f"created: {note.created_at}", f"updated: {note.updated_at}"]
    # Include any custom metadata
    if note.metadata_json and note.metadata_json != "{}":
        try:
            meta = json.loads(note.metadata_json)
            for k, v in meta.items():
                if k not in ("title", "created", "updated"):
                    lines.append(f"{k}: {v}")
        except json.JSONDecodeError:
            pass
    lines.append("---")
    return "\n".join(lines) + "\n"

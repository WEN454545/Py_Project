"""Obsidian vault importer.

Scans a vault directory, parses .md files with YAML frontmatter,
resolves [[wikilinks]], and imports into the PyKnowledge database.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from ..core.note import Note
from ..utils.hash_utils import sha256

# Try YAML; degrade gracefully
try:
    import yaml as _yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


def scan_vault(vault_path: str | Path) -> list[dict]:
    """Scan an Obsidian vault directory and return preview data.

    Args:
        vault_path: Root directory of the Obsidian vault.

    Returns:
        List of dicts with keys: relative_path, title, tags, frontmatter, size.
    """
    vault = Path(vault_path)
    if not vault.is_dir():
        raise NotADirectoryError(f"Not a directory: {vault_path}")

    results: list[dict] = []

    for md_file in sorted(vault.rglob("*.md")):
        # Skip hidden directories
        if any(part.startswith(".") for part in md_file.parts):
            continue

        try:
            content = md_file.read_text(encoding="utf-8")
        except (UnicodeDecodeError, PermissionError):
            continue

        info: dict = {
            "relative_path": str(md_file.relative_to(vault)),
            "absolute_path": str(md_file),
            "title": md_file.stem,
            "tags": [],
            "frontmatter": {},
            "body": content,
            "size": len(content),
        }

        # Parse frontmatter
        fm = _parse_frontmatter(content)
        if fm:
            info["frontmatter"] = fm
            info["title"] = fm.get("title", md_file.stem)
            tags = fm.get("tags", [])
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(",")]
            info["tags"] = tags

        # Extract wikilinks
        wikilinks = re.findall(r'\[\[([^\]|#]+)(?:[|#][^\]]+)?\]\]', content)
        info["wikilinks"] = list(set(wikilinks))

        results.append(info)

    return results


def _parse_frontmatter(text: str) -> dict:
    """Parse YAML frontmatter if present (delimited by ---)."""
    if not text.startswith("---"):
        return {}

    # Find closing ---
    end = text.find("---", 3)
    if end == -1:
        return {}

    fm_text = text[3:end].strip()
    if not fm_text:
        return {}

    if HAS_YAML:
        try:
            parsed = _yaml.safe_load(fm_text)
            if isinstance(parsed, dict):
                return parsed
        except _yaml.YAMLError:
            pass

    # Fallback: simple key: value parser
    result: dict = {}
    for line in fm_text.split("\n"):
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            # Handle simple lists like "tags: [a, b, c]"
            if value.startswith("[") and value.endswith("]"):
                value = [v.strip().strip('"').strip("'")
                         for v in value[1:-1].split(",")]
            result[key] = value
    return result

"""File system utilities."""

import re
import shutil
from pathlib import Path
from typing import Optional


def safe_filename(title: str) -> str:
    """Convert a note title into a filesystem-safe filename."""
    # Replace unsafe characters
    safe = re.sub(r'[<>:"/\\|?*]', "-", title)
    # Collapse multiple dashes/spaces
    safe = re.sub(r"[\s-]+", "-", safe)
    # Trim dashes from ends
    safe = safe.strip("-")
    return safe or "untitled"


def ensure_dir(path: Path) -> Path:
    """Create directory if it doesn't exist."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def copy_file_safe(src: Path, dst: Path) -> Optional[Path]:
    """Copy a file, renaming if destination exists. Returns the final path."""
    if not dst.parent.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)

    if not dst.exists():
        shutil.copy2(src, dst)
        return dst

    stem = dst.stem
    suffix = dst.suffix
    for n in range(1, 1000):
        alt = dst.parent / f"{stem}_{n}{suffix}"
        if not alt.exists():
            shutil.copy2(src, alt)
            return alt

    return None  # Too many duplicates

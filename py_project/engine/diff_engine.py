"""Diff engine — paragraph-level diff for version comparison.

Uses hash-based fast path for identical paragraphs, then difflib
for changed sequences. Falls back to stdlib difflib if diff-match-patch
is not installed.
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass, field
from typing import Optional

from ..utils.hash_utils import sha256


@dataclass
class DiffChunk:
    """A single chunk in a diff result."""
    operation: str  # 'equal', 'insert', 'delete', 'replace'
    old_text: Optional[str] = None
    new_text: Optional[str] = None
    old_start: int = 0
    old_end: int = 0
    new_start: int = 0
    new_end: int = 0


@dataclass
class DiffResult:
    """Complete diff between two versions."""
    old_version_id: str
    new_version_id: str
    chunks: list[DiffChunk] = field(default_factory=list)
    insertions: int = 0
    deletions: int = 0
    modifications: int = 0

    @property
    def total_changes(self) -> int:
        return self.insertions + self.deletions + self.modifications

    @property
    def is_empty(self) -> bool:
        return self.total_changes == 0


def compute_diff(
    old_text: str,
    new_text: str,
    old_version_id: str = "",
    new_version_id: str = "",
) -> DiffResult:
    """Compute a paragraph-level diff between two text versions.

    Args:
        old_text: The older version's full text.
        new_text: The newer version's full text.
        old_version_id: Identifier for the old version.
        new_version_id: Identifier for the new version.

    Returns:
        DiffResult with chunked diff details.
    """
    result = DiffResult(
        old_version_id=old_version_id,
        new_version_id=new_version_id,
    )

    old_paras = _split_paragraphs(old_text)
    new_paras = _split_paragraphs(new_text)

    # Hash-based fast path: match identical paragraphs
    old_hashes = [sha256(p) for p in old_paras]
    new_hashes = [sha256(p) for p in new_paras]

    # Use difflib SequenceMatcher for structural diff
    matcher = difflib.SequenceMatcher(
        a=old_hashes, b=new_hashes, autojunk=False,
    )

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        chunk = DiffChunk(
            operation=tag,
            old_start=i1, old_end=i2,
            new_start=j1, new_end=j2,
        )

        if tag == "equal":
            # No text needed for equal chunks
            pass
        elif tag == "delete":
            chunk.old_text = "\n\n".join(old_paras[i1:i2])
            result.deletions += (i2 - i1)
        elif tag == "insert":
            chunk.new_text = "\n\n".join(new_paras[j1:j2])
            result.insertions += (j2 - j1)
        elif tag == "replace":
            chunk.old_text = "\n\n".join(old_paras[i1:i2])
            chunk.new_text = "\n\n".join(new_paras[j1:j2])
            result.modifications += max(i2 - i1, j2 - j1)

        result.chunks.append(chunk)

    return result


def compute_unified_diff(old_text: str, new_text: str) -> str:
    """Generate a unified diff string for display.

    Args:
        old_text: Older version.
        new_text: Newer version.

    Returns:
        Unified diff as a string.
    """
    old_lines = old_text.splitlines(keepends=True)
    new_lines = new_text.splitlines(keepends=True)

    diff_lines = difflib.unified_diff(
        old_lines, new_lines,
        fromfile="Previous", tofile="Current",
        lineterm="",
    )
    return "\n".join(diff_lines)


def _split_paragraphs(text: str) -> list[str]:
    """Split text into paragraphs (blank-line separated)."""
    if not text.strip():
        return []
    parts = text.replace("\r\n", "\n").replace("\r", "\n").split("\n\n")
    return [p.strip() for p in parts]

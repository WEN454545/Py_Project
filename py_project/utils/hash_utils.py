"""Content hashing utilities."""

import hashlib


def sha256(content: str) -> str:
    """Compute SHA-256 hash of a string."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def short_hash(content: str, length: int = 12) -> str:
    """Return a truncated SHA-256 hash for use as a compact ID."""
    return sha256(content)[:length]

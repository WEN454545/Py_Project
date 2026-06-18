"""FTS5 query builder and search result ranker."""

from __future__ import annotations

import re
from typing import Optional


def build_query(user_input: str) -> tuple[str, Optional[str]]:
    """Parse user input and build an FTS5 MATCH expression.

    Supports special prefixes:
        tag:<name>    — filter by tag
        title:<text>  — search only in titles

    Everything else is treated as a body query.

    Args:
        user_input: Raw search query from the user.

    Returns:
        (fts5_match_expression, optional_tag_filter)
    """
    tag_filter: Optional[str] = None
    title_query: Optional[str] = None
    body_terms: list[str] = []

    # Extract special prefixes
    tag_pattern = re.compile(r"tag:(\S+)")
    title_pattern = re.compile(r"title:(\S+)")

    working = user_input

    # Extract tag:
    tag_match = tag_pattern.search(working)
    if tag_match:
        tag_filter = tag_match.group(1).strip()
        working = tag_pattern.sub("", working)

    # Extract title:
    title_match = title_pattern.search(working)
    if title_match:
        title_query = title_match.group(1).strip()
        working = title_pattern.sub("", working)

    # Remaining terms → body search
    body_terms = [t.strip() for t in working.split() if t.strip()]

    # Build FTS5 expression
    parts: list[str] = []

    if body_terms:
        body = " AND ".join(body_terms)
        parts.append(body)

    if title_query:
        parts.append(f"title:{title_query}")

    if not parts:
        return "", tag_filter

    fts_query = " AND ".join(parts)
    return fts_query, tag_filter

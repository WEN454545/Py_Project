"""Search service — full-text search orchestration."""

from __future__ import annotations

from ..core.search_result import SearchResult
from ..storage.database import Database
from ..storage.search_repo import SearchRepository
from ..engine.fts_engine import build_query


class SearchService:
    """Executes full-text search queries."""

    def __init__(self, db: Database):
        self.db = db
        self.search_repo = SearchRepository(db)

    def search(self, query_string: str, limit: int = 50) -> list[SearchResult]:
        """Parse user query and execute FTS5 search.

        Args:
            query_string: Raw user input (supports tag:, title: prefixes).
            limit: Maximum results.

        Returns:
            Ranked list of SearchResult with highlighted snippets.
        """
        if not query_string.strip():
            return []

        fts_query, tag_filter = build_query(query_string)
        if not fts_query and not tag_filter:
            return []

        if not fts_query:
            # Only tag filter — match everything
            fts_query = "*"

        return self.search_repo.search(fts_query, limit=limit, tag_filter=tag_filter)

    def rebuild_index(self) -> None:
        """Rebuild the entire FTS index."""
        self.search_repo.rebuild_all_fts()

    def update_note_index(self, note_id: str) -> None:
        """Update the FTS index for a single note."""
        self.search_repo.update_fts(note_id)

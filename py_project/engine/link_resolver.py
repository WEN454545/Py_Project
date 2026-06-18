"""Link resolver — extracts [[wikilinks]] and ((block-refs)), updates link graph."""

from __future__ import annotations

from ..core.note import Block
from ..core.link import LinkType
from ..storage.database import Database
from ..storage.link_repo import LinkRepository
from ..storage.note_repo import NoteRepository
from .markdown_parser import extract_wikilinks, extract_block_refs


class LinkResolver:
    """Resolves wiki-style links between notes during parsing.

    On each note save:
    1. Extracts all [[target]] and ((block-id)) references
    2. Resolves targets against existing notes
    3. Updates the links table (removes stale, inserts new)
    """

    def __init__(self, db: Database):
        self.db = db
        self.link_repo = LinkRepository(db)
        self.note_repo = NoteRepository(db)

    def resolve_all(self, note_id: str, blocks: list[Block]) -> dict:
        """Resolve all links from a note's blocks.

        Args:
            note_id: The source note's UUID.
            blocks: Parsed Block objects.

        Returns:
            dict with keys: 'wiki_links', 'block_refs', 'unresolved'
        """
        # Clear old outgoing links for this note
        self.link_repo.delete_links_from(note_id)

        wiki_links: list[dict] = []
        block_refs: list[dict] = []
        unresolved: list[str] = []

        for block in blocks:
            raw = block.content_raw

            # Extract and resolve [[wikilinks]]
            for target_title, alias in extract_wikilinks(raw):
                target_note = self.note_repo.get_by_title(target_title)
                if target_note:
                    self.link_repo.upsert_link(
                        source_note_id=note_id,
                        target_note_id=target_note.id,
                        source_block_id=block.id,
                        link_text=alias,
                        link_type=LinkType.WIKI,
                    )
                    wiki_links.append({
                        "target_title": target_title,
                        "target_note_id": target_note.id,
                        "alias": alias,
                        "resolved": True,
                    })
                else:
                    unresolved.append(target_title)
                    wiki_links.append({
                        "target_title": target_title,
                        "target_note_id": None,
                        "alias": alias,
                        "resolved": False,
                    })

            # Extract and resolve ((block-refs))
            for ref_id in extract_block_refs(raw):
                target_block = self._find_block(ref_id)
                if target_block:
                    # Also create a wiki-style link at note level
                    self.link_repo.upsert_link(
                        source_note_id=note_id,
                        target_note_id=target_block["note_id"],
                        source_block_id=block.id,
                        link_text=f"block:{ref_id}",
                        link_type=LinkType.BLOCK_REF,
                    )
                    block_refs.append({
                        "block_id": ref_id,
                        "target_note_id": target_block["note_id"],
                        "resolved": True,
                    })
                else:
                    unresolved.append(ref_id)
                    block_refs.append({
                        "block_id": ref_id,
                        "target_note_id": None,
                        "resolved": False,
                    })

        return {
            "wiki_links": wiki_links,
            "block_refs": block_refs,
            "unresolved": unresolved,
        }

    def get_backlinks(self, note_id: str) -> list[dict]:
        """Get all notes that link TO this note."""
        return self.link_repo.get_incoming_links(note_id)

    def _find_block(self, block_id: str) -> dict | None:
        """Find a block by its ID."""
        row = self.db.fetch_one(
            "SELECT id, note_id FROM blocks WHERE id = ?",
            (block_id,),
        )
        if row:
            return {"id": row["id"], "note_id": row["note_id"]}
        return None

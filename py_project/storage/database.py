"""SQLite database connection, schema bootstrap, and migration runner."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

# Schema version for migration tracking
CURRENT_SCHEMA_VERSION = 1

SCHEMA_SQL = """
-- ============================================================
-- META / HOUSEKEEPING
-- ============================================================

CREATE TABLE IF NOT EXISTS schema_version (
    version     INTEGER PRIMARY KEY,
    applied_at  TEXT NOT NULL DEFAULT (datetime('now')),
    description TEXT
);

-- ============================================================
-- NOTES
-- ============================================================

CREATE TABLE IF NOT EXISTS notes (
    id              TEXT PRIMARY KEY,
    title           TEXT NOT NULL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
    is_deleted      INTEGER NOT NULL DEFAULT 0,
    sort_order      INTEGER NOT NULL DEFAULT 0,
    metadata_json   TEXT DEFAULT '{}'
);

-- ============================================================
-- BLOCKS (paragraph-level content tree)
-- ============================================================

CREATE TABLE IF NOT EXISTS blocks (
    id              TEXT PRIMARY KEY,
    note_id         TEXT NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
    parent_block_id TEXT REFERENCES blocks(id) ON DELETE CASCADE,
    block_order     INTEGER NOT NULL,
    block_type      TEXT NOT NULL DEFAULT 'paragraph',
    content_raw     TEXT NOT NULL,
    language        TEXT,
    heading_level   INTEGER,
    block_hash      TEXT NOT NULL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
    metadata_json   TEXT DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_blocks_note ON blocks(note_id);
CREATE INDEX IF NOT EXISTS idx_blocks_parent ON blocks(parent_block_id);
CREATE INDEX IF NOT EXISTS idx_blocks_hash ON blocks(block_hash);

-- ============================================================
-- TAGS (hierarchical)
-- ============================================================

CREATE TABLE IF NOT EXISTS tags (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    parent_tag_id   TEXT REFERENCES tags(id) ON DELETE CASCADE,
    color           TEXT DEFAULT '#3B82F6',
    icon            TEXT,
    sort_order      INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_tag_name_parent
    ON tags(name, COALESCE(parent_tag_id, '__root__'));

CREATE TABLE IF NOT EXISTS note_tags (
    note_id     TEXT NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
    tag_id      TEXT NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (note_id, tag_id)
);

-- ============================================================
-- LINKS (bidirectional note connections)
-- ============================================================

CREATE TABLE IF NOT EXISTS links (
    id              TEXT PRIMARY KEY,
    source_note_id  TEXT NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
    target_note_id  TEXT NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
    source_block_id TEXT,
    link_text       TEXT,
    link_type       TEXT NOT NULL DEFAULT 'wiki',
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_links_source ON links(source_note_id);
CREATE INDEX IF NOT EXISTS idx_links_target ON links(target_note_id);
CREATE INDEX IF NOT EXISTS idx_links_block ON links(source_block_id);

-- ============================================================
-- BLOCK-LEVEL REFERENCES
-- ============================================================

CREATE TABLE IF NOT EXISTS block_references (
    id              TEXT PRIMARY KEY,
    source_block_id TEXT NOT NULL REFERENCES blocks(id) ON DELETE CASCADE,
    source_note_id  TEXT NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
    target_block_id TEXT NOT NULL REFERENCES blocks(id) ON DELETE CASCADE,
    target_note_id  TEXT NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_blockref_source ON block_references(source_block_id);
CREATE INDEX IF NOT EXISTS idx_blockref_target ON block_references(target_block_id);

-- ============================================================
-- VERSIONS (full snapshot on Ctrl+S)
-- ============================================================

CREATE TABLE IF NOT EXISTS versions (
    id              TEXT PRIMARY KEY,
    note_id         TEXT NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
    version_number  INTEGER NOT NULL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    content_full    TEXT NOT NULL,
    content_hash    TEXT NOT NULL,
    change_summary  TEXT
);

CREATE INDEX IF NOT EXISTS idx_versions_note ON versions(note_id, version_number);
CREATE UNIQUE INDEX IF NOT EXISTS idx_version_num ON versions(note_id, version_number);

-- ============================================================
-- ATTACHMENTS
-- ============================================================

CREATE TABLE IF NOT EXISTS attachments (
    id              TEXT PRIMARY KEY,
    note_id         TEXT,
    file_name       TEXT NOT NULL,
    file_path       TEXT NOT NULL,
    mime_type       TEXT,
    file_size       INTEGER NOT NULL DEFAULT 0,
    width           INTEGER,
    height          INTEGER,
    attachment_type TEXT NOT NULL DEFAULT 'file',
    annotation_json TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_attach_note ON attachments(note_id);

-- ============================================================
-- FULL-TEXT SEARCH (FTS5)
-- ============================================================

CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5(
    title,
    body,
    tags,
    tokenize='porter unicode61'
);

-- Record the initial schema version
INSERT OR IGNORE INTO schema_version (version, description)
VALUES (1, 'Initial schema bootstrap');
"""


class Database:
    """Manages the SQLite connection and schema lifecycle."""

    @classmethod
    def from_default(cls) -> "Database":
        """Create a Database using the default app data path."""
        from ..config import DATABASE_PATH

        return cls(DATABASE_PATH)

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self._conn: Optional[sqlite3.Connection] = None

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self._conn

    def connect(self) -> sqlite3.Connection:
        """Open connection and ensure schema is up to date."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(
            str(self.db_path),
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.row_factory = sqlite3.Row
        self._ensure_schema()
        return self._conn

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    def _ensure_schema(self) -> None:
        """Bootstrap schema and run any pending migrations."""
        current_version = self._get_schema_version()
        if current_version == 0:
            self._bootstrap()
        if current_version < CURRENT_SCHEMA_VERSION:
            self._migrate(current_version)

    def _get_schema_version(self) -> int:
        """Get current schema version, or 0 if uninitialized."""
        try:
            row = self.conn.execute(
                "SELECT MAX(version) FROM schema_version"
            ).fetchone()
            return row[0] if row and row[0] is not None else 0
        except sqlite3.OperationalError:
            return 0

    def _bootstrap(self) -> None:
        """Execute full schema creation (version INSERT is in SCHEMA_SQL)."""
        self.conn.executescript(SCHEMA_SQL)
        self.conn.commit()

    def _migrate(self, from_version: int) -> None:
        """Run incremental migrations."""
        # Future migrations go here.
        # Example:
        # if from_version < 2:
        #     self.conn.execute("ALTER TABLE notes ADD COLUMN pinned INTEGER DEFAULT 0")
        #     self.conn.execute("INSERT INTO schema_version (version, description)
        #                       VALUES (2, 'Add pinned column to notes')")
        pass

    # ── Convenience query methods ───────────────────────────────

    def insert(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        cur = self.conn.execute(sql, params)
        self.conn.commit()
        return cur

    def fetch_one(self, sql: str, params: tuple = ()) -> Optional[sqlite3.Row]:
        return self.conn.execute(sql, params).fetchone()

    def fetch_all(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        return self.conn.execute(sql, params).fetchall()

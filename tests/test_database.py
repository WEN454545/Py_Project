"""Tests for database schema bootstrap."""

import sqlite3
from py_project.storage.database import SCHEMA_SQL, Database, CURRENT_SCHEMA_VERSION


class TestSchemaBootstrap:
    """Verify schema creation runs without errors."""

    def test_schema_creates_all_tables(self, in_memory_db):
        """All expected tables should exist after bootstrap."""
        conn = in_memory_db
        tables = [
            row[0] for row in
            conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        ]
        # Core tables
        assert "notes" in tables
        assert "blocks" in tables
        assert "tags" in tables
        assert "note_tags" in tables
        assert "links" in tables
        assert "block_references" in tables
        assert "versions" in tables
        assert "attachments" in tables
        assert "schema_version" in tables

    def test_schema_version_recorded(self, in_memory_db):
        """schema_version should be set to CURRENT_SCHEMA_VERSION."""
        row = in_memory_db.execute(
            "SELECT MAX(version) FROM schema_version"
        ).fetchone()
        assert row[0] == CURRENT_SCHEMA_VERSION

    def test_fts_virtual_table_exists(self, in_memory_db):
        """FTS5 virtual table should be present."""
        tables = [
            row[0] for row in
            in_memory_db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        ]
        assert "notes_fts" in tables

    def test_foreign_keys_enabled(self, in_memory_db):
        """PRAGMA foreign_keys should be ON."""
        row = in_memory_db.execute("PRAGMA foreign_keys").fetchone()
        assert row[0] == 1


class TestDatabaseClass:
    """Tests for the Database wrapper class."""

    def test_connect_and_close(self, temp_db_path):
        db = Database(temp_db_path)
        conn = db.connect()
        assert conn is not None
        assert temp_db_path.exists()
        db.close()

    def test_idempotent_connect(self, temp_db_path):
        """Connecting twice should not break schema."""
        db = Database(temp_db_path)
        db.connect()
        db.close()
        db.connect()  # Second connect should be fine
        db.close()

    def test_note_insert(self, temp_db_path):
        """Basic note insertion should work."""
        db = Database(temp_db_path)
        db.connect()
        db.insert(
            "INSERT INTO notes (id, title) VALUES (?, ?)",
            ("test-1", "Hello World"),
        )
        row = db.fetch_one("SELECT title FROM notes WHERE id = ?", ("test-1",))
        assert row["title"] == "Hello World"
        db.close()


class TestCoreModels:
    """Verify core dataclasses are importable and usable."""

    def test_note_creation(self):
        from py_project.core import Note
        note = Note(id="n1", title="Test Note")
        assert note.title == "Test Note"
        assert not note.is_deleted
        assert note.metadata_json == "{}"

    def test_block_creation(self):
        from py_project.core import Block, BlockType
        block = Block(
            id="b1",
            note_id="n1",
            content_raw="Hello, world!",
            block_type=BlockType.PARAGRAPH,
            block_hash="abc123",
        )
        assert block.content_raw == "Hello, world!"

    def test_tag_creation(self):
        from py_project.core import Tag
        tag = Tag(id="t1", name="python", color="#3B82F6")
        assert tag.name == "python"
        assert tag.parent_tag_id is None

    def test_version_creation(self):
        from py_project.core import Version
        v = Version(
            id="v1",
            note_id="n1",
            version_number=1,
            content_full="# Hello",
            content_hash="abc",
        )
        assert v.version_number == 1


class TestUtils:
    """Verify utility functions work correctly."""

    def test_safe_filename(self):
        from py_project.utils.file_utils import safe_filename
        assert safe_filename("Hello: World?") == "Hello-World"
        assert safe_filename("untitled") == "untitled"
        assert safe_filename("a/b:c") == "a-b-c"

    def test_hash_functions(self):
        from py_project.utils.hash_utils import sha256, short_hash
        h = sha256("hello")
        assert len(h) == 64
        assert short_hash("hello") == h[:12]
        assert short_hash("hello", 8) == h[:8]

    def test_time_utils(self):
        from py_project.utils.time_utils import now_iso, format_relative, format_full
        ts = now_iso()
        assert "T" in ts
        assert ts.endswith("Z")
        # Historical timestamp
        old = "2020-01-01T00:00:00Z"
        result = format_relative(old)
        assert result != old  # Should be a relative string
        formatted = format_full(old)
        assert "2020" in formatted

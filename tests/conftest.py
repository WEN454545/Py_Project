"""Test fixtures and configuration."""

import os
import sys
import tempfile
from pathlib import Path

import pytest

# Ensure py_project is importable
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def temp_db_path():
    """Create a temporary directory for test databases."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / "test_knowledge.db"


@pytest.fixture
def in_memory_db():
    """Provide an in-memory SQLite database with schema."""
    import sqlite3
    from py_project.storage.database import SCHEMA_SQL

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(SCHEMA_SQL)
    yield conn
    conn.close()

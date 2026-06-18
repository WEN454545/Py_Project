"""Phase 2 integration tests — tags, versions, search, links, import/export."""

import os
import tempfile
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from py_project.storage.database import Database
from py_project.services.tag_service import TagService
from py_project.services.note_service import NoteService
from py_project.services.version_service import VersionService
from py_project.services.search_service import SearchService
from py_project.engine.diff_engine import compute_diff, compute_unified_diff
from py_project.engine.fts_engine import build_query
from py_project.engine.link_resolver import LinkResolver
from py_project.engine.markdown_parser import parse_markdown
from py_project.engine.import_obsidian import scan_vault
from py_project.engine.export_markdown import export_notes


def _setup():
    tmp = tempfile.TemporaryDirectory()
    db = Database(os.path.join(tmp.name, "test.db"))
    db.connect()
    return tmp, db


class TestTagService:
    def test_create_and_hierarchy(self):
        tmp, db = _setup()
        ts = TagService(db)

        dev = ts.create_tag("dev", color="#FF0000")
        assert dev.name == "dev"
        assert dev.parent_tag_id is None

        python = ts.create_tag("python", parent_tag_id=dev.id)
        assert python.parent_tag_id == dev.id

        path = ts.get_full_path(python)
        assert path == "dev/python"

        db.close()

    def test_get_or_create_path(self):
        tmp, db = _setup()
        ts = TagService(db)

        tag = ts.get_or_create_path("dev/web/frontend")
        assert tag.name == "frontend"

        # Idempotent
        tag2 = ts.get_or_create_path("dev/web/frontend")
        assert tag2.id == tag.id

        db.close()

    def test_tag_note(self):
        tmp, db = _setup()
        ts = TagService(db)
        ns = NoteService(db)

        note = ns.create_note("Tagged")
        tag = ts.create_tag("important")
        ts.tag_note(note.id, tag.id)

        tags = ts.get_tags_for_note(note.id)
        assert len(tags) == 1
        assert tags[0].name == "important"

        note_ids = ts.get_note_ids_for_tag(tag.id)
        assert note.id in note_ids

        db.close()


class TestVersionService:
    def test_create_and_detect_duplicate(self):
        tmp, db = _setup()
        ns = NoteService(db)
        vs = VersionService(db)

        note = ns.create_note("V Note")
        v1 = vs.create_version(note.id, "Hello world.")
        assert v1 is not None
        assert v1.version_number == 1

        # Same content should skip
        v1b = vs.create_version(note.id, "Hello world.")
        assert v1b is None

        # Different content
        v2 = vs.create_version(note.id, "Hello world!\n\nNew para.")
        assert v2 is not None
        assert v2.version_number == 2

        history = vs.get_history(note.id)
        assert len(history) == 2

        db.close()

    def test_diff_versions(self):
        tmp, db = _setup()
        ns = NoteService(db)
        vs = VersionService(db)

        note = ns.create_note("Diff Note")
        v1 = vs.create_version(note.id, "Line one.\n\nLine two.\n\nLine three.")
        v2 = vs.create_version(note.id, "Line one.\n\nLine two modified.\n\nLine three.\n\nLine four.")

        diff = vs.diff_versions(v1.id, v2.id)
        assert not diff.is_empty
        assert diff.total_changes > 0

        db.close()

    def test_restore(self):
        tmp, db = _setup()
        ns = NoteService(db)
        vs = VersionService(db)

        note = ns.create_note("Restore Note")
        vs.create_version(note.id, "Original content.")
        vs.create_version(note.id, "Modified content.")

        history = vs.get_history(note.id)
        restored = vs.restore_version(history[0].id)
        assert "Original content." in restored

        db.close()


class TestSearchService:
    def test_search(self):
        tmp, db = _setup()
        ns = NoteService(db)
        ss = SearchService(db)

        n1 = ns.create_note("Python Async Guide")
        ns.save_note(n1.id, "# Async Python\n\nUsing asyncio for concurrent programming.")
        n2 = ns.create_note("JavaScript Basics")
        ns.save_note(n2.id, "# JavaScript\n\nIntroduction to JS promises.")

        ss.update_note_index(n1.id)
        ss.update_note_index(n2.id)

        results = ss.search("python")
        assert len(results) > 0

        results2 = ss.search("javascript")
        assert len(results2) > 0

        db.close()


class TestDiffEngine:
    def test_compute_diff(self):
        old = "Line one.\n\nLine two.\n\nLine three."
        new = "Line one.\n\nLine two modified.\n\nLine three.\n\nLine four."
        diff = compute_diff(old, new)
        assert diff.total_changes > 0
        assert len(diff.chunks) > 0

    def test_unified_diff(self):
        unified = compute_unified_diff("a\nb\nc", "a\nx\nc")
        assert len(unified) > 0

    def test_empty_diff(self):
        diff = compute_diff("same", "same")
        assert diff.is_empty


class TestFtsEngine:
    def test_build_query_basic(self):
        q, tag = build_query("python async")
        assert "python" in q
        assert tag is None

    def test_build_query_with_tag(self):
        q, tag = build_query("python tag:programming")
        assert tag == "programming"

    def test_build_query_title(self):
        q, tag = build_query("title:guide")
        assert "title:guide" in q

    def test_build_query_empty(self):
        q, tag = build_query("")
        assert q == ""
        assert tag is None


class TestLinkResolver:
    def test_resolve_links(self):
        tmp, db = _setup()
        ns = NoteService(db)
        lr = LinkResolver(db)

        source = ns.create_note("Source")
        target = ns.create_note("Target")
        ns.save_note(target.id, "# Target\n\nContent.")

        blocks = parse_markdown("See [[Target]] for more.", source.id)
        result = lr.resolve_all(source.id, blocks)
        assert len(result["wiki_links"]) == 1
        assert result["wiki_links"][0]["resolved"] is True

        db.close()

    def test_unresolved_link(self):
        tmp, db = _setup()
        ns = NoteService(db)
        lr = LinkResolver(db)

        source = ns.create_note("Source")
        blocks = parse_markdown("See [[Ghost]] here.", source.id)
        result = lr.resolve_all(source.id, blocks)
        assert "Ghost" in result["unresolved"]

        db.close()

    def test_backlinks(self):
        tmp, db = _setup()
        ns = NoteService(db)
        lr = LinkResolver(db)

        source = ns.create_note("Source")
        target = ns.create_note("Target")
        ns.save_note(target.id, "Target content.")

        blocks = parse_markdown("Link to [[Target]].", source.id)
        lr.resolve_all(source.id, blocks)

        backlinks = lr.get_backlinks(target.id)
        assert len(backlinks) == 1
        assert backlinks[0]["source_note_id"] == source.id

        db.close()


class TestObsidianImport:
    def test_scan_vault(self):
        tmp, _ = _setup()
        vault = os.path.join(tmp.name, "test_vault")
        os.makedirs(vault)

        with open(os.path.join(vault, "Welcome.md"), "w", encoding="utf-8") as f:
            f.write('---\ntitle: Welcome\ntags: [intro, guide]\n---\n\n# Welcome\n\nHello!')

        with open(os.path.join(vault, "Projects.md"), "w", encoding="utf-8") as f:
            f.write("# Projects\n\nSee [[Welcome]] for intro.")

        preview = scan_vault(vault)
        assert len(preview) == 2

        welcome = [n for n in preview if n["title"] == "Welcome"][0]
        assert "intro" in welcome["tags"]
        assert "guide" in welcome["tags"]

        projects = [n for n in preview if n["title"] == "Projects"][0]
        assert "Welcome" in projects["wikilinks"]


class TestMarkdownExport:
    def test_export_notes(self):
        tmp, db = _setup()
        ns = NoteService(db)

        note = ns.create_note("Export Test")
        ns.save_note(note.id, "# Export\n\nContent here.")

        export_dir = os.path.join(tmp.name, "export")
        result = export_notes(
            [(note, ns.load_note(note.id))],
            export_dir,
        )
        assert result["files_created"] == 1
        assert result["total_bytes"] > 0

        db.close()

"""Comprehensive verification of all phases (0-3). Run without pytest."""

import sys, os, json, tempfile, uuid, traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

g_pass = 0
g_fail = 0
g_errors = []

def T(desc, expr):
    global g_pass, g_fail
    if expr:
        g_pass += 1
    else:
        g_fail += 1
        g_errors.append(desc)

def section(name):
    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"{'='*60}")

# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # PHASE 0: Core Models + Database + Utils
    # ═══════════════════════════════════════════════════════════════
    section("PHASE 0: Core Models, Database, Utils")

    # ── Imports ──────────────────────────────────────────────────
    from py_project.core.note import Note, Block, BlockType
    from py_project.core.tag import Tag
    from py_project.core.link import Link, LinkType
    from py_project.core.attachment import Attachment, AttachmentType
    from py_project.core.version import Version
    from py_project.core.search_result import SearchResult

    from py_project.utils.hash_utils import sha256, short_hash
    from py_project.utils.file_utils import safe_filename
    from py_project.utils.time_utils import now_iso, format_relative, format_full

    from py_project.storage.database import SCHEMA_SQL, Database, CURRENT_SCHEMA_VERSION
    from py_project.engine.block_id import generate_block_id
    import sqlite3

    T("All Phase 0 imports", True)

    # ── Core model defaults ──────────────────────────────────────
    note = Note(id="n1", title="Test")
    T("Note default is_deleted=False", not note.is_deleted)
    T("Note default metadata='{}'", note.metadata_json == "{}")

    block = Block(id="b1", note_id="n1", content_raw="**bold**", block_order=0,
                  block_type=BlockType.PARAGRAPH, block_hash="abc")
    T("Block PARAGRAPH type", block.block_type == BlockType.PARAGRAPH)
    T("Block content preserved", block.content_raw == "**bold**")

    tag = Tag(id="t1", name="python", parent_tag_id="root")
    T("Tag hierarchical", tag.parent_tag_id == "root")
    T("Tag default color", tag.color == "#3B82F6")

    link = Link(id="l1", source_note_id="s", target_note_id="t", link_type=LinkType.WIKI)
    T("Link wiki type", link.link_type == LinkType.WIKI)

    att = Attachment(id="a1", file_name="x.png", file_path="p/x.png",
                     attachment_type=AttachmentType.SCREENSHOT)
    T("Attachment screenshot type", att.attachment_type == AttachmentType.SCREENSHOT)

    ver = Version(id="v1", note_id="n1", version_number=1,
                  content_full="# Hi", content_hash="abc")
    T("Version number", ver.version_number == 1)

    sr = SearchResult(note_id="n1", title="T", snippet="<mark>x</mark>")
    T("SearchResult snippet", "<mark>" in sr.snippet)

    # ── Utils ────────────────────────────────────────────────────
    h = sha256("hello")
    T("sha256 length=64", len(h) == 64)
    T("short_hash length=12", len(short_hash("hello")) == 12)
    T("short_hash custom length", len(short_hash("hello", 8)) == 8)
    T("safe_filename clean", safe_filename("Hello: World?") == "Hello-World")
    T("safe_filename normal", safe_filename("untitled") == "untitled")
    ts = now_iso()
    T("now_iso format", "T" in ts and ts.endswith("Z"))
    old = "2020-01-01T00:00:00Z"
    T("format_relative works", format_relative(old) != old)
    T("format_full has year", "2020" in format_full(old))

    # ── Database schema ──────────────────────────────────────────
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(SCHEMA_SQL)
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    for t in ["notes", "blocks", "tags", "note_tags", "links",
              "block_references", "versions", "attachments", "notes_fts",
              "schema_version"]:
        T(f"Table '{t}' exists", t in tables)
    T("Schema version correct", CURRENT_SCHEMA_VERSION == 1)

    # ── CRUD + Cascade ───────────────────────────────────────────
    conn.execute("INSERT INTO notes (id, title) VALUES ('n1', 'CRUD Test')")
    conn.execute("INSERT INTO tags (id, name) VALUES ('t1', 'py')")
    conn.execute("INSERT INTO note_tags VALUES ('n1', 't1')")
    conn.execute("""INSERT INTO blocks (id, note_id, block_order, content_raw, block_hash)
        VALUES ('b1', 'n1', 0, 'Hello', 'h1')""")
    T("Insert note", conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0] == 1)
    T("Insert block", conn.execute("SELECT COUNT(*) FROM blocks").fetchone()[0] == 1)
    conn.execute("DELETE FROM notes WHERE id='n1'")
    T("Cascade delete blocks", conn.execute("SELECT COUNT(*) FROM blocks").fetchone()[0] == 0)
    T("Cascade delete note_tags", conn.execute("SELECT COUNT(*) FROM note_tags").fetchone()[0] == 0)
    conn.close()

    # ── Database wrapper ─────────────────────────────────────────
    with tempfile.TemporaryDirectory() as td:
        db = Database(os.path.join(td, "test.db"))
        db.connect()
        db.insert("INSERT INTO notes (id, title) VALUES ('w', 'Wrapper')")
        row = db.fetch_one("SELECT title FROM notes WHERE id=?", ("w",))
        T("DB wrapper insert", row["title"] == "Wrapper")
        db.close()
        db.connect()
        row2 = db.fetch_one("SELECT title FROM notes WHERE id=?", ("w",))
        T("DB reconnect persistence", row2["title"] == "Wrapper")
        db.close()


    # ═══════════════════════════════════════════════════════════════
    # PHASE 1: Markdown Engine + Note Service
    # ═══════════════════════════════════════════════════════════════
    section("PHASE 1: Markdown Parser, HTML Renderer, Note Service")

    from py_project.engine.markdown_parser import (
        parse_markdown, extract_wikilinks, extract_block_refs,
        extract_images, extract_links,
    )
    from py_project.engine.markdown_to_html import render_blocks_to_html
    from py_project.storage.note_repo import NoteRepository
    from py_project.services.note_service import NoteService

    # ── Parser: headings ─────────────────────────────────────────
    blocks = parse_markdown("# H1\n\n## H2\n\nText.", "n1")
    T("Heading H1", blocks[0].block_type == BlockType.HEADING and blocks[0].heading_level == 1)
    T("Heading H2", blocks[1].block_type == BlockType.HEADING and blocks[1].heading_level == 2)
    T("Paragraph after headings", blocks[2].block_type == BlockType.PARAGRAPH)

    # ── Parser: code blocks ──────────────────────────────────────
    md = "```python\nprint('hi')\n```\n\nAfter code."
    blocks = parse_markdown(md, "n1")
    T("Code block type", blocks[0].block_type == BlockType.CODE)
    T("Code language", blocks[0].language == "python")
    T("Code content", "print('hi')" in blocks[0].content_raw)

    # ── Parser: tables ───────────────────────────────────────────
    blocks = parse_markdown("| A | B |\n|---|---|\n| 1 | 2 |", "n1")
    T("Table block", blocks[0].block_type == BlockType.TABLE)

    # ── Parser: lists ────────────────────────────────────────────
    blocks = parse_markdown("- one\n- two\n- three", "n1")
    T("Unordered list", blocks[0].block_type == BlockType.LIST_ITEM)
    blocks = parse_markdown("1. first\n2. second", "n1")
    T("Ordered list", blocks[0].block_type == BlockType.LIST_ITEM)

    # ── Parser: blockquote ───────────────────────────────────────
    blocks = parse_markdown("> quoted text\n> more quote", "n1")
    T("Blockquote", blocks[0].block_type == BlockType.BLOCKQUOTE)

    # ── Parser: HR ───────────────────────────────────────────────
    blocks = parse_markdown("Before\n\n---\n\nAfter", "n1")
    T("Horizontal rule", any(b.block_type == BlockType.HORIZONTAL_RULE for b in blocks))

    # ── Parser: math ─────────────────────────────────────────────
    blocks = parse_markdown("$$\nx^2\n$$", "n1")
    T("Math block", blocks[0].block_type == BlockType.MATH_BLOCK)

    # ── Parser: empty skip ───────────────────────────────────────
    blocks = parse_markdown("# Title\n\n\n\n\n\nPara.", "n1")
    T("Empty blocks skipped", len(blocks) == 2)

    # ── Inline extraction ────────────────────────────────────────
    links = extract_wikilinks("See [[A]] and [[B|alias]].")
    T("Extract wikilinks count", len(links) == 2)
    T("Wikilink no alias", links[0] == ("A", None))
    T("Wikilink with alias", links[1] == ("B", "alias"))

    refs = extract_block_refs("Ref ((abcdef123456)) and ((789012345678)).")
    T("Extract block refs", len(refs) == 2 and refs[0] == "abcdef123456")

    imgs = extract_images("![Alt](img.png) ![](img2.jpg)")
    T("Extract images", len(imgs) == 2)

    urls = extract_links("[Google](https://g.com) [Bing](https://b.com)")
    T("Extract links", len(urls) == 2)

    # ── HTML rendering ───────────────────────────────────────────
    blocks = parse_markdown("# Hello\n\nThis is **bold** and *italic*.", "n1")
    html = render_blocks_to_html(blocks, "Test")
    T("HTML has h1", "<h1" in html)
    T("HTML has strong", "<strong>bold</strong>" in html)
    T("HTML has em", "<em>italic</em>" in html)

    # ── Table HTML ───────────────────────────────────────────────
    blocks = parse_markdown("| X | Y |\n|---|---|\n| a | b |", "n1")
    html = render_blocks_to_html(blocks, "T")
    T("Table HTML", "<table>" in html and "<th>X</th>" in html and "<td>a</td>" in html)

    # ── Block ID stability ───────────────────────────────────────
    id1 = generate_block_id("n1", 0, "hello")
    id2 = generate_block_id("n1", 0, "hello")
    id3 = generate_block_id("n1", 1, "hello")
    T("Block ID stable", id1 == id2)
    T("Block ID position-sensitive", id1 != id3)
    T("Block ID length", len(id1) == 12)

    # ── NoteService integration ──────────────────────────────────
    with tempfile.TemporaryDirectory() as td:
        db = Database(os.path.join(td, "ns.db"))
        db.connect()
        svc = NoteService(db)

        note = svc.create_note("Integration Test")
        T("Create note title", note.title == "Integration Test")

        md = "# Hello\n\n**Bold** and *italic*.\n\n| A | B |\n|---|---|\n| 1 | 2 |"
        svc.save_note(note.id, md)

        loaded = svc.load_note(note.id)
        T("Load note has content", "Hello" in loaded and "**Bold**" in loaded)

        html = svc.render_preview(note.id, md)
        T("Render preview has h1", "<h1" in html)
        T("Render preview has table", "<table>" in html)

        notes = svc.list_notes()
        T("List notes count", len(notes) == 1)

        svc.rename_note(note.id, "Renamed")
        n2 = svc.get_note(note.id)
        T("Rename note", n2.title == "Renamed")

        svc.delete_note(note.id)
        T("Soft delete", len(svc.list_notes()) == 0)

        db.close()


    # ═══════════════════════════════════════════════════════════════
    # PHASE 2: Tags, Versions, Search, Links, Import/Export
    # ═══════════════════════════════════════════════════════════════
    section("PHASE 2: Tags, Versions, Search, Links, Import/Export")

    from py_project.storage.tag_repo import TagRepository
    from py_project.storage.version_repo import VersionRepository
    from py_project.storage.search_repo import SearchRepository
    from py_project.storage.link_repo import LinkRepository
    from py_project.services.tag_service import TagService
    from py_project.services.version_service import VersionService
    from py_project.services.search_service import SearchService
    from py_project.services.import_export_service import ImportExportService
    from py_project.engine.link_resolver import LinkResolver
    from py_project.engine.diff_engine import compute_diff, compute_unified_diff
    from py_project.engine.fts_engine import build_query
    from py_project.engine.import_obsidian import scan_vault
    from py_project.engine.export_markdown import export_notes

    with tempfile.TemporaryDirectory() as td:
        db = Database(os.path.join(td, "p2.db"))
        db.connect()
        ts = TagService(db)
        ns = NoteService(db)
        vs = VersionService(db)
        ss = SearchService(db)
        lr = LinkResolver(db)

        # ── Tag hierarchy ────────────────────────────────────────
        dev = ts.create_tag("dev", color="#FF0000")
        T("Tag root creation", dev.parent_tag_id is None)

        py = ts.create_tag("python", parent_tag_id=dev.id)
        T("Tag child parent", py.parent_tag_id == dev.id)

        path = ts.get_full_path(py)
        T("Tag full path", path == "dev/python")

        web = ts.get_or_create_path("dev/web/frontend")
        T("Tag get_or_create", web.name == "frontend")
        T("Tag path deep", ts.get_full_path(web) == "dev/web/frontend")

        # Idempotent
        web2 = ts.get_or_create_path("dev/web/frontend")
        T("Tag get_or_create idempotent", web2.id == web.id)

        children = ts.get_children(dev.id)
        T("Tag children count", len(children) == 2)

        # Tag a note
        note = ns.create_note("Tagged Note")
        ts.tag_note(note.id, py.id)
        tags = ts.get_tags_for_note(note.id)
        T("Note tags count", len(tags) == 1)
        T("Note tag name", tags[0].name == "python")

        # Descendant query
        note_ids = ts.get_note_ids_for_tag(dev.id)
        T("Descendant tag query", note.id in note_ids)

        # ── Versions ─────────────────────────────────────────────
        v1 = vs.create_version(note.id, "# V1\n\nContent A.")
        T("Create version 1", v1 is not None and v1.version_number == 1)

        v1b = vs.create_version(note.id, "# V1\n\nContent A.")
        T("Duplicate version skipped", v1b is None)

        v2 = vs.create_version(note.id, "# V2\n\nContent B added.\n\nNew paragraph.")
        T("Create version 2", v2 is not None and v2.version_number == 2)

        history = vs.get_history(note.id)
        T("Version history count", len(history) == 2)

        diff = vs.diff_versions(v1.id, v2.id)
        T("Diff not empty", not diff.is_empty)
        T("Diff has changes", diff.total_changes > 0)

        restored = vs.restore_version(v1.id)
        T("Restore version", "V1" in restored)

        # ── Search ───────────────────────────────────────────────
        n1 = ns.create_note("Python Async Guide")
        ns.save_note(n1.id, "# Async Python\n\nUsing asyncio for concurrent programming.")
        n2 = ns.create_note("JavaScript Basics")
        ns.save_note(n2.id, "# JavaScript\n\nIntroduction to JS promises and callbacks.")

        ss.update_note_index(n1.id)
        ss.update_note_index(n2.id)

        results = ss.search("python")
        T("Search 'python'", len(results) > 0)

        results2 = ss.search("javascript")
        T("Search 'javascript'", len(results2) > 0)

        # ── Diff engine ──────────────────────────────────────────
        diff = compute_diff("A\n\nB\n\nC", "A\n\nB2\n\nC\n\nD")
        T("Diff engine empty check", not diff.is_empty)
        T("Diff engine chunks", len(diff.chunks) > 0)
        unified = compute_unified_diff("A\nB\nC", "A\nX\nC")
        T("Unified diff output", len(unified) > 0)

        # ── FTS query builder ────────────────────────────────────
        q, tag = build_query("python async")
        T("FTS basic query", "python" in q and "async" in q)
        T("FTS no tag filter", tag is None)
        q2, tag2 = build_query("python tag:programming")
        T("FTS tag filter", tag2 == "programming")
        q3, tag3 = build_query("title:guide")
        T("FTS title query", "title:guide" in q3)
        q4, tag4 = build_query("")
        T("FTS empty query", q4 == "")

        # ── Link resolver ───────────────────────────────────────
        src = ns.create_note("Source Note")
        tgt = ns.create_note("Target Note")
        ns.save_note(tgt.id, "# Target\n\nContent.")

        blocks = parse_markdown("See [[Target Note]] for info.", src.id)
        result = lr.resolve_all(src.id, blocks)
        T("Link resolved", result["wiki_links"][0]["resolved"] is True)
        T("Link target title", result["wiki_links"][0]["target_title"] == "Target Note")

        backlinks = lr.get_backlinks(tgt.id)
        T("Backlinks count", len(backlinks) == 1)
        T("Backlink source", backlinks[0]["source_note_id"] == src.id)

        ghosts = parse_markdown("See [[Ghost Note]] here.", src.id)
        ghost_result = lr.resolve_all(src.id, ghosts)
        T("Unresolved link", "Ghost Note" in ghost_result["unresolved"])

        # ── Obsidian import ──────────────────────────────────────
        vault = os.path.join(td, "vault")
        os.makedirs(vault)
        with open(os.path.join(vault, "Welcome.md"), "w", encoding="utf-8") as f:
            f.write('---\ntitle: Welcome\ntags: [intro, guide]\n---\n\n# Welcome\n\nHello world!')
        with open(os.path.join(vault, "Projects.md"), "w", encoding="utf-8") as f:
            f.write("# Projects\n\nSee [[Welcome]] for intro.")

        preview = scan_vault(vault)
        T("Scan vault count", len(preview) == 2)
        welcome = [n for n in preview if n["title"] == "Welcome"][0]
        T("Frontmatter tags", "intro" in welcome["tags"] and "guide" in welcome["tags"])
        projects = [n for n in preview if n["title"] == "Projects"][0]
        T("Wikilinks in vault", "Welcome" in projects["wikilinks"])

        # ── Markdown export ──────────────────────────────────────
        export_note = ns.create_note("Export Me")
        ns.save_note(export_note.id, "# Export\n\nThis is exported content.")
        export_dir = os.path.join(td, "export")
        result = export_notes(
            [(export_note, ns.load_note(export_note.id))],
            export_dir,
        )
        T("Export files created", result["files_created"] == 1)
        T("Export has bytes", result["total_bytes"] > 0)

        db.close()


    # ═══════════════════════════════════════════════════════════════
    # PHASE 3: Attachments + Screenshot logic
    # ═══════════════════════════════════════════════════════════════
    section("PHASE 3: Attachments + Screenshot Service")

    from py_project.storage.attachment_repo import AttachmentRepository
    from py_project.services.attachment_service import AttachmentService
    from py_project.services.screenshot_service import ScreenshotService

    with tempfile.TemporaryDirectory() as td:
        db = Database(os.path.join(td, "p3.db"))
        db.connect()
        svc = AttachmentService(db)

        # Import a file
        tf = os.path.join(td, "hello.txt")
        with open(tf, "w") as f:
            f.write("Hello World")
        att = svc.import_file(tf)
        T("Import filename", att.file_name.endswith(".txt"))
        T("Import file on disk", svc.get_full_path(att).exists())
        T("Import file size", att.file_size > 0)
        T("Get all count", len(svc.get_all()) == 1)

        # Link to note
        ns2 = NoteService(db)
        note = ns2.create_note("Attachment Note")
        svc.link_to_note(att.id, note.id)
        T("Link to note", len(svc.get_attachments(note.id)) == 1)
        svc.unlink_from_note(att.id)
        T("Unlink from note", len(svc.get_attachments(note.id)) == 0)
        svc.link_to_note(att.id, note.id)
        T("Re-link to note", len(svc.get_attachments(note.id)) == 1)

        # Delete
        svc.delete(att.id)
        T("Delete attachment", svc.get(att.id) is None)

        # ── Screenshot service logic ─────────────────────────────
        s = ScreenshotService.serialize_annotations(
            [{"x": 0, "y": 0, "w": 10, "h": 10, "color": "#fff", "width": 2}],
            [{"x1": 0, "y1": 0, "x2": 10, "y2": 10, "color": "#ff0", "width": 3}],
            [{"x": 5, "y": 5, "text": "hi", "color": "#fff", "size": 14}],
        )
        d = json.loads(s)
        T("Serialize rectangles", len(d["rectangles"]) == 1)
        T("Serialize arrows", len(d["arrows"]) == 1)
        T("Serialize texts", len(d["texts"]) == 1)

        # Verify annotation JSON in attachment
        now = now_iso()
        att2 = Attachment(
            id="anno-1", file_name="ss.png", file_path="x/ss.png",
            note_id=note.id, mime_type="image/png", file_size=5000,
            attachment_type=AttachmentType.ANNOTATION,
            annotation_json=s, created_at=now,
        )
        repo = AttachmentRepository(db)
        repo.insert(att2)
        got = repo.get("anno-1")
        T("Annotation attachment type", got.attachment_type == AttachmentType.ANNOTATION)
        parsed = json.loads(got.annotation_json)
        T("Annotation data preserved", len(parsed["arrows"]) == 1)

        db.close()


    # ═══════════════════════════════════════════════════════════════
    # FINAL RESULTS
    # ═══════════════════════════════════════════════════════════════
    print(f"\n{'='*60}")
    print(f"  VERIFICATION COMPLETE")
    print(f"{'='*60}")
    print(f"  PASSED: {g_pass}")
    print(f"  FAILED: {g_fail}")
    print(f"  TOTAL:  {g_pass + g_fail}")

    if g_fail > 0:
        print(f"\n  FAILURES:")
        for e in g_errors:
            print(f"    - {e}")
        sys.exit(1)
    else:
        print(f"\n  ALL TESTS PASSED [OK]")
        sys.exit(0)

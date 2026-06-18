# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PyKnowledge — a personal knowledge management desktop application built in pure Python with PySide6.

- **GUI:** PySide6 (Qt for Python, LGPL), single-window multi-panel
- **Storage:** SQLite database-native, notes stored as paragraph-level block trees
- **Editor:** Split-pane — left plain-text edit with syntax highlighting, right live HTML preview
- **Search:** SQLite FTS5 full-text search
- **Versions:** Snapshot on Ctrl+S, side-by-side diff comparison

## Repository

- **Remote:** https://github.com/WEN454545/Py_Project.git
- **Default branch:** `main`

## Getting Started

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Launch the application
python -m py_project.main

# Run all tests
pytest tests/ -v

# Run a specific test file
pytest tests/test_database.py -v
```

## Architecture

```
py_project/
├── main.py              # Entry point
├── config.py            # App settings, paths, constants
├── core/                # Domain models — plain dataclasses, zero dependencies
│   ├── note.py          # Note, Block, BlockType
│   ├── tag.py           # Tag (hierarchical via parent_tag_id)
│   ├── link.py          # Link (directed edge), LinkType
│   ├── attachment.py    # Attachment metadata, AttachmentType
│   ├── version.py       # Version (full-text snapshot)
│   └── search_result.py # SearchResult dataclass
├── storage/             # SQLite persistence layer
│   ├── database.py      # Connection manager, schema bootstrap, migrations
│   ├── note_repo.py     # Notes + blocks CRUD
│   ├── tag_repo.py      # Hierarchical tag operations
│   ├── link_repo.py     # Bidirectional link storage
│   ├── version_repo.py  # Version save/restore
│   ├── search_repo.py   # FTS5 wrapper
│   └── attachment_repo.py
├── engine/              # Business logic (imports only core/)
│   ├── markdown_parser.py    # Text → block tree
│   ├── markdown_to_html.py   # Block tree → HTML preview
│   ├── link_resolver.py      # [[wikilinks]] extraction + backlink compute
│   ├── diff_engine.py        # Paragraph-level diff (Myers)
│   ├── fts_engine.py         # FTS5 query builder
│   ├── import_obsidian.py    # Obsidian vault importer
│   ├── export_markdown.py    # Markdown folder exporter
│   └── export_opml.py        # Mind map → OPML (P2)
├── services/            # Orchestrators bridging UI ↔ storage/engine
│   ├── note_service.py
│   ├── tag_service.py
│   ├── search_service.py
│   ├── version_service.py
│   ├── attachment_service.py
│   └── screenshot_service.py
├── ui/                  # PySide6 presentation
│   ├── app.py           # QApplication bootstrap
│   ├── main_window.py   # QMainWindow, menu, splitters, dock areas
│   ├── editor/          # Left pane: QPlainTextEdit + syntax highlighter
│   ├── preview/         # Right pane: QWebEngineView HTML render
│   ├── panels/          # Dockable panels: tags, search, backlinks, versions
│   ├── dialogs/         # Modal dialogs: diff, import, export, screenshot
│   └── widgets/         # Reusable small widgets
├── utils/               # Hashing, file ops, timestamp formatting
├── resources/           # Icons, themes, templates
└── tests/               # pytest with in-memory SQLite fixtures
```

**Dependency rule:** `core/` ← `storage/` ← `engine/` ← `services/` ← `ui/`. `core/` imports nothing from other py_project packages. `ui/` never touches `storage/` or `engine/` directly — always through `services/`.

## Database

Tables: `notes`, `blocks` (paragraph-level, tree via `parent_block_id`), `tags` (hierarchical), `note_tags`, `links` (directed edges; backlinks are reverse queries), `block_references`, `versions` (full snapshot per Ctrl+S), `attachments`, `notes_fts` (FTS5 virtual table).

Schema is defined in `py_project/storage/database.py` as `SCHEMA_SQL`. Migration version tracked in `schema_version` table.

## Key Conventions

- All IDs are UUID strings (generated via `uuid.uuid4()`)
- Timestamps in ISO 8601 UTC (`YYYY-MM-DDTHH:MM:SSZ`)
- Block type enum: `paragraph`, `heading`, `code`, `math_block`, `table`, `list_item`, `blockquote`, `horizontal_rule`, `empty`
- Block IDs are content-addressable: `SHA256(note_id + ":" + str(block_order) + ":" + content_raw)[:12]`
- Soft deletes via `notes.is_deleted` flag — no hard delete by default
- Signal/slot wiring for editor → preview: 300ms debounce via QTimer

## Development Phases

| Phase | Status | Contents |
|---|---|---|
| 0: Scaffolding | ✅ Done | pyproject.toml, core models (6 dataclasses), database schema (9 tables + FTS5), empty main window, utils |
| 1: Editor + Preview | ✅ Done | EditorWidget (QPlainTextEdit + line numbers), PreviewWidget (QWebEngineView), markdown parser (4-stage pipeline), HTML renderer, NoteService + NoteRepository |
| 2: P0 Features | ✅ Done | Tables + LaTeX math, hierarchical tag tree (TagService + TagPanel), FTS5 search (SearchService + SearchPanel), version history + side-by-side diff (VersionService + VersionPanel + VersionDiffDialog), Obsidian import (ImportDialog), Markdown export (ExportDialog), bidirectional links (LinkResolver + BacklinksPanel) |
| 3: P1 Features | ✅ Done | Code syntax highlighting (QSyntaxHighlighter, 17 rules + multi-line fenced blocks), screenshot capture + annotation (RegionSelector + AnnotationOverlay with rect/arrow/text tools), attachment management (AttachmentService + AttachmentPanel with drag-drop import), block-level reference resolution, full MainWindow menu wiring (all 30 menu actions connected) |
| 4: P2 + Polish | ✅ Done | Mind map data model + OPML export (headings→outline tree, content blocks→_note attributes, JSON export for D3.js), theme support (dark/light toggle via View menu, CSS custom properties, full chrome re-theming), parser fix (multi-line heading detection) |

**Codebase stats:** 70 Python files, ~7,000 lines of code

**Codebase stats:** 66 Python files, ~6,500 lines of code

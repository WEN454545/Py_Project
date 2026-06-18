"""Phase 4 tests — OPML export, themes."""
import sys, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from py_project.engine.markdown_parser import parse_markdown
from py_project.engine.export_opml import blocks_to_opml, blocks_to_mindmap_json
from py_project.ui.preview.preview_styles import get_theme, generate_css
from py_project.engine.markdown_to_html import render_blocks_to_html

# OPML export
md = """# Project Plan

## Phase 1

Research and design.

## Phase 2

### Backend

Database and API.

### Frontend

UI components.

- Dashboard
- Settings

## Phase 3

Testing and deployment.
"""

blocks = parse_markdown(md, "test")
opml = blocks_to_opml(blocks, "My Mind Map")

assert '<opml version="2.0">' in opml
assert "<head>" in opml
assert "<body>" in opml
assert "Phase 1" in opml
assert "Phase 2" in opml
assert "Backend" in opml
assert "Frontend" in opml
assert "_note" in opml  # Content blocks become notes
print(f"OPML: {len(opml)} chars OK")

# Mind map JSON
tree = blocks_to_mindmap_json(blocks)
assert tree["name"] == "Root"
# H1 becomes top-level child; H2s nest under it
assert len(tree["children"]) == 1  # Project Plan
assert tree["children"][0]["name"] == "Project Plan"
assert len(tree["children"][0]["children"]) >= 3  # Phase 1, 2, 3
print(f"JSON tree: root has {len(tree['children'])} child, that has {len(tree['children'][0]['children'])} children OK")

# Theme CSS
dark = get_theme("dark")
assert dark["bg"] == "#1e1e2e"
light = get_theme("light")
assert light["bg"] == "#fafafa"

dark_css = generate_css("dark")
assert "--bg: #1e1e2e" in dark_css
light_css = generate_css("light")
assert "--bg: #fafafa" in light_css
print(f"Theme CSS: dark={len(dark_css)} light={len(light_css)} OK")

# Themed HTML rendering
blocks2 = parse_markdown("# Hello\n\nWorld.", "n1")
html = render_blocks_to_html(blocks2, "Test")
assert "var(--bg)" in html
assert "var(--text)" in html
print(f"Themed HTML: {len(html)} chars OK")

print("\nPhase 4: ALL TESTS PASSED")

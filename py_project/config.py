"""Application configuration and path management."""

import os
import sys
from pathlib import Path


def get_app_data_dir() -> Path:
    """Get platform-appropriate application data directory."""
    if sys.platform == "win32":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
    elif sys.platform == "darwin":
        base = os.path.join(os.path.expanduser("~"), "Library", "Application Support")
    else:
        base = os.environ.get("XDG_DATA_HOME", os.path.join(os.path.expanduser("~"), ".local", "share"))
    path = Path(base) / "PyKnowledge"
    path.mkdir(parents=True, exist_ok=True)
    return path


APP_NAME = "PyKnowledge"
APP_VERSION = "0.1.0"
APP_DATA_DIR = get_app_data_dir()

DATABASE_PATH = APP_DATA_DIR / "knowledge.db"
ATTACHMENT_DIR = APP_DATA_DIR / "attachments"

# Ensure attachment store exists
ATTACHMENT_DIR.mkdir(parents=True, exist_ok=True)

# Editor settings
EDITOR_FONT_FAMILY = "Consolas" if sys.platform == "win32" else "Menlo"
EDITOR_FONT_SIZE = 13
EDITOR_TAB_WIDTH = 4
DEBOUNCE_MS = 300

# Preview settings
PREVIEW_FONT_SIZE = 14
PREVIEW_MAX_IMAGE_WIDTH = 700

# Version settings
DEFAULT_MAX_VERSIONS = 50
VERSION_CLUSTER_THRESHOLD = 0.05  # 5% change threshold for clustering

# Search settings
SEARCH_MAX_RESULTS = 50
SEARCH_SNIPPET_LENGTH = 40

# Window defaults
WINDOW_WIDTH = 1400
WINDOW_HEIGHT = 900
WINDOW_TITLE = "PyKnowledge"

"""Attachment service — file import, storage, and metadata management."""

from __future__ import annotations

import uuid
import shutil
from pathlib import Path
from typing import Optional

from ..config import ATTACHMENT_DIR
from ..core.attachment import Attachment, AttachmentType
from ..storage.database import Database
from ..storage.attachment_repo import AttachmentRepository
from ..utils.time_utils import now_iso


class AttachmentService:
    """Manages file attachments for notes.

    Files are stored under ATTACHMENT_DIR organized by year/month.
    """

    def __init__(self, db: Database):
        self.db = db
        self.repo = AttachmentRepository(db)

    # ── Import / Store ──────────────────────────────────────────

    def import_file(
        self,
        source_path: str | Path,
        note_id: Optional[str] = None,
    ) -> Attachment:
        """Import a file into the attachment store.

        Args:
            source_path: Path to the file to import.
            note_id: Optional note to associate with.

        Returns:
            The created Attachment metadata.
        """
        source = Path(source_path)
        if not source.is_file():
            raise FileNotFoundError(f"File not found: {source_path}")

        # Determine storage path: attachments/<year>/<month>/<uuid>_<original_name>
        now = now_iso()
        year = now[:4]
        month = now[5:7]
        dest_dir = ATTACHMENT_DIR / year / month
        dest_dir.mkdir(parents=True, exist_ok=True)

        attachment_id = str(uuid.uuid4())
        ext = source.suffix
        dest_name = f"{attachment_id}_{source.name}"
        dest_path = dest_dir / dest_name

        # Handle duplicates
        counter = 1
        while dest_path.exists():
            dest_name = f"{attachment_id}_{source.stem}_{counter}{ext}"
            dest_path = dest_dir / dest_name
            counter += 1

        # Copy file
        shutil.copy2(source, dest_path)

        # Guess MIME type
        mime = _guess_mime(source)

        # Get image dimensions if applicable
        width, height = None, None
        if mime and mime.startswith("image/"):
            try:
                from PIL import Image
                with Image.open(dest_path) as img:
                    width, height = img.size
            except Exception:
                pass

        attachment = Attachment(
            id=attachment_id,
            file_name=dest_name,
            file_path=str(dest_path.relative_to(ATTACHMENT_DIR)),
            note_id=note_id,
            mime_type=mime,
            file_size=dest_path.stat().st_size,
            width=width,
            height=height,
            attachment_type=AttachmentType.FILE,
            created_at=now,
        )

        return self.repo.insert(attachment)

    # ── Screenshot / Annotation ─────────────────────────────────

    def save_screenshot(
        self,
        image_data: bytes,
        note_id: Optional[str] = None,
        annotation_json: Optional[str] = None,
    ) -> Attachment:
        """Save a screenshot (with optional annotation data) to the store.

        Args:
            image_data: Raw PNG image bytes.
            note_id: Optional note to associate with.
            annotation_json: Optional JSON string of annotation shapes.

        Returns:
            Attachment metadata.
        """
        now = now_iso()
        year, month = now[:4], now[5:7]
        dest_dir = ATTACHMENT_DIR / year / month
        dest_dir.mkdir(parents=True, exist_ok=True)

        attachment_id = str(uuid.uuid4())
        dest_name = f"{attachment_id}_screenshot.png"
        dest_path = dest_dir / dest_name

        dest_path.write_bytes(image_data)

        # Get dimensions
        width, height = None, None
        try:
            from PIL import Image
            import io
            with Image.open(io.BytesIO(image_data)) as img:
                width, height = img.size
        except Exception:
            pass

        attachment = Attachment(
            id=attachment_id,
            file_name=dest_name,
            file_path=str(dest_path.relative_to(ATTACHMENT_DIR)),
            note_id=note_id,
            mime_type="image/png",
            file_size=dest_path.stat().st_size,
            width=width,
            height=height,
            attachment_type=(
                AttachmentType.ANNOTATION if annotation_json
                else AttachmentType.SCREENSHOT
            ),
            annotation_json=annotation_json,
            created_at=now,
        )

        return self.repo.insert(attachment)

    # ── Query ───────────────────────────────────────────────────

    def get_attachments(self, note_id: str) -> list[Attachment]:
        return self.repo.get_for_note(note_id)

    def get_all(self, limit: int = 100) -> list[Attachment]:
        return self.repo.get_all(limit)

    def get(self, attachment_id: str) -> Optional[Attachment]:
        return self.repo.get(attachment_id)

    def get_full_path(self, attachment: Attachment) -> Path:
        """Get the absolute filesystem path for an attachment."""
        return ATTACHMENT_DIR / attachment.file_path

    # ── Link / Unlink ───────────────────────────────────────────

    def link_to_note(self, attachment_id: str, note_id: str) -> None:
        self.repo.link_to_note(attachment_id, note_id)

    def unlink_from_note(self, attachment_id: str) -> None:
        self.repo.unlink_from_note(attachment_id)

    # ── Delete ──────────────────────────────────────────────────

    def delete(self, attachment_id: str) -> None:
        """Delete both metadata and the disk file."""
        attachment = self.repo.get(attachment_id)
        if attachment:
            full_path = self.get_full_path(attachment)
            try:
                full_path.unlink(missing_ok=True)
            except OSError:
                pass
        self.repo.delete(attachment_id)


def _guess_mime(path: Path) -> Optional[str]:
    """Guess MIME type from file extension."""
    ext = path.suffix.lower()
    mapping = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".svg": "image/svg+xml",
        ".pdf": "application/pdf",
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".mp4": "video/mp4",
        ".zip": "application/zip",
        ".txt": "text/plain",
        ".md": "text/markdown",
        ".csv": "text/csv",
    }
    return mapping.get(ext)

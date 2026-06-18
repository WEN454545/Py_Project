"""QAbstractItemModel for the hierarchical tag tree."""

from __future__ import annotations

from PySide6.QtCore import Qt, QAbstractItemModel, QModelIndex

from ...core.tag import Tag
from ...services.tag_service import TagService


class TagTreeModel(QAbstractItemModel):
    """Tree model wrapping the hierarchical tag structure."""

    def __init__(self, tag_service: TagService, parent=None):
        super().__init__(parent)
        self.tag_service = tag_service
        self._root_tags: list[Tag] = []

    # ── Public API ───────────────────────────────────────────────

    def refresh(self) -> None:
        """Reload the tag tree from the database."""
        self.beginResetModel()
        self._root_tags = self.tag_service.get_root_tags()
        self.endResetModel()

    def get_tag(self, index: QModelIndex) -> Tag | None:
        if not index.isValid():
            return None
        return index.internalPointer()

    # ── QAbstractItemModel interface ────────────────────────────

    def index(self, row: int, column: int, parent=QModelIndex()) -> QModelIndex:
        if not self.hasIndex(row, column, parent):
            return QModelIndex()

        if not parent.isValid():
            # Root level
            if row < len(self._root_tags):
                return self.createIndex(row, column, self._root_tags[row])
        else:
            parent_tag = parent.internalPointer()
            if parent_tag:
                children = self.tag_service.get_children(parent_tag.id)
                if row < len(children):
                    return self.createIndex(row, column, children[row])

        return QModelIndex()

    def parent(self, index: QModelIndex) -> QModelIndex:
        if not index.isValid():
            return QModelIndex()

        tag = index.internalPointer()
        if tag and tag.parent_tag_id:
            parent_tag = self.tag_service.get_tag(tag.parent_tag_id)
            if parent_tag:
                # Find parent's row in its own parent's children
                if parent_tag.parent_tag_id:
                    grandparent = self.tag_service.get_tag(parent_tag.parent_tag_id)
                    if grandparent:
                        siblings = self.tag_service.get_children(grandparent.id)
                    else:
                        siblings = self._root_tags
                else:
                    siblings = self._root_tags

                for row, sib in enumerate(siblings):
                    if sib.id == parent_tag.id:
                        return self.createIndex(row, 0, parent_tag)

        return QModelIndex()

    def rowCount(self, parent=QModelIndex()) -> int:
        if not parent.isValid():
            return len(self._root_tags)

        tag = parent.internalPointer()
        if tag:
            return len(self.tag_service.get_children(tag.id))

        return 0

    def columnCount(self, parent=QModelIndex()) -> int:
        return 1

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        if not index.isValid():
            return None

        tag = index.internalPointer()
        if not tag:
            return None

        if role == Qt.DisplayRole:
            return tag.name
        elif role == Qt.UserRole:
            return tag.id
        elif role == Qt.DecorationRole:
            # Color indicator
            return None  # Future: color swatch

        return None

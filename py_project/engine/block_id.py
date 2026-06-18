"""Block ID generation — content-addressable, stable identifiers."""

from ..utils.hash_utils import short_hash


def generate_block_id(note_id: str, block_order: int, content_raw: str) -> str:
    """Generate a stable, content-addressable block ID.

    ID = SHA256(note_id + ":" + str(block_order) + ":" + content_raw)[:12]

    The same block at the same position with the same content gets the same ID.
    If block order changes (insert above), the ID changes — that's acceptable
    because the block's structural position changed.
    """
    seed = f"{note_id}:{block_order}:{content_raw}"
    return short_hash(seed, 12)

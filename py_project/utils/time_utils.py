"""Timestamp formatting utilities."""

from datetime import datetime, timezone


def now_iso() -> str:
    """Return current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def format_relative(timestamp: str) -> str:
    """Format a timestamp as a relative time string."""
    try:
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return timestamp

    now = datetime.now(timezone.utc)
    diff = now - dt

    if diff.total_seconds() < 60:
        return "just now"
    elif diff.total_seconds() < 3600:
        mins = int(diff.total_seconds() / 60)
        return f"{mins}m ago"
    elif diff.total_seconds() < 86400:
        hrs = int(diff.total_seconds() / 3600)
        return f"{hrs}h ago"
    elif diff.days < 30:
        return f"{diff.days}d ago"
    elif diff.days < 365:
        months = diff.days // 30
        return f"{months}mo ago"
    else:
        years = diff.days // 365
        return f"{years}y ago"


def format_full(timestamp: str) -> str:
    """Format a timestamp as a human-readable date string."""
    try:
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        return timestamp

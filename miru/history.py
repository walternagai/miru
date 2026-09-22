"""History management for prompts and sessions."""

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

from miru.config_manager import HISTORY_FILE, ensure_config_dir

logger = logging.getLogger(__name__)


@dataclass
class HistoryEntry:
    """History entry for a prompt execution."""

    timestamp: str
    command: str
    model: str
    prompt: str
    system_prompt: str | None = None
    response: str | None = None
    success: bool = True
    error: str | None = None
    metrics: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "HistoryEntry":
        """Create from dictionary."""
        return cls(**data)


def record_history(
    command: str,
    model: str,
    prompt: str,
    system_prompt: str | None = None,
    response: str | None = None,
    success: bool = True,
    error: str | None = None,
    metrics: dict[str, Any] | None = None,
) -> None:
    """Record a history entry.

    Args:
        command: Command name (run, chat, batch, compare)
        model: Model name
        prompt: Prompt text
        system_prompt: Optional system prompt
        response: Response text (truncated if too long)
        success: Whether execution succeeded
        error: Error message if failed
        metrics: Performance metrics
    """
    from miru.config_manager import load_config

    config = load_config()
    if not config.history_enabled:
        return

    ensure_config_dir()

    timestamp = datetime.now().isoformat()

    if response and len(response) > 1000:
        response = response[:1000] + "..."

    entry = HistoryEntry(
        timestamp=timestamp,
        command=command,
        model=model,
        prompt=prompt[:500] if prompt else "",
        system_prompt=system_prompt[:200] if system_prompt else None,
        response=response,
        success=success,
        error=error,
        metrics=metrics,
    )

    _append_history(entry, config.history_max_entries)


def _read_entries() -> list[HistoryEntry]:
    """Read all history entries, skipping corrupt lines.

    A corrupt line is logged and ignored so the valid entries survive;
    one bad line must never wipe the whole history.
    """
    if not HISTORY_FILE.exists():
        return []

    entries: list[HistoryEntry] = []
    try:
        with open(HISTORY_FILE, encoding="utf-8") as f:
            for lineno, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(HistoryEntry.from_dict(json.loads(line)))
                except (json.JSONDecodeError, TypeError, ValueError) as exc:
                    logger.debug(
                        "Skipping corrupt history line %d in %s: %s",
                        lineno,
                        HISTORY_FILE,
                        exc,
                    )
    except OSError as exc:
        logger.warning("Failed to read history from %s: %s", HISTORY_FILE, exc)
    return entries


def _append_history(entry: HistoryEntry, max_entries: int) -> None:
    """Append entry to history file with rotation."""
    ensure_config_dir()

    entries = _read_entries()

    entries.append(entry)

    while len(entries) > max_entries:
        entries.pop(0)

    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            for e in entries:
                f.write(json.dumps(e.to_dict(), ensure_ascii=False) + "\n")
    except Exception as exc:
        logger.warning("Failed to write history to %s: %s", HISTORY_FILE, exc)


def get_history(limit: int = 50, command: str | None = None) -> list[HistoryEntry]:
    """Get history entries.

    Args:
        limit: Maximum number of entries
        command: Filter by command type

    Returns:
        List of history entries (most recent first)
    """
    entries = _read_entries()
    if command is not None:
        entries = [e for e in entries if e.command == command]

    entries.reverse()
    return entries[:limit]


def clear_history() -> None:
    """Clear all history."""
    ensure_config_dir()
    if HISTORY_FILE.exists():
        HISTORY_FILE.unlink()


def search_history(query: str, limit: int = 20) -> list[HistoryEntry]:
    """Search history for matching prompts.

    Args:
        query: Search query (case-insensitive substring match)
        limit: Maximum results

    Returns:
        List of matching entries
    """
    query_lower = query.lower()

    entries = [
        e
        for e in _read_entries()
        if query_lower in e.prompt.lower()
        or query_lower in (e.response or "").lower()
    ]

    entries.reverse()
    return entries[:limit]


def get_history_by_index(index: int) -> HistoryEntry | None:
    """Get history entry by index (0 = most recent).

    Args:
        index: History index

    Returns:
        History entry or None
    """
    entries = get_history(limit=index + 1)
    if index < len(entries):
        return entries[index]
    return None

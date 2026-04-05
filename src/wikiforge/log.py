"""Activity log — append-only chronological record of operations."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from wikiforge.vault import Vault

_LOG_HEADER = "# WikiForge Activity Log\n\n<!-- Append-only. Parseable with: grep \"^## \\[\" _log.md -->\n\n"


def append_log(
    vault: Vault,
    operation: str,
    summary: str,
    details: list[str] | None = None,
) -> None:
    """Append a timestamped entry to the activity log."""
    path = vault.log_path
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")

    # Create log file with header if it doesn't exist
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_LOG_HEADER, encoding="utf-8")

    entry_lines = [f"## [{now}] {operation} | {summary}\n"]
    if details:
        entry_lines.append("")
        for detail in details:
            entry_lines.append(f"- {detail}")
    entry_lines.append("\n")

    with open(path, "a", encoding="utf-8") as f:
        f.write("\n".join(entry_lines))


def render_recent_log(vault: Vault, n: int = 5) -> str:
    """Read the last N log entries for LLM context."""
    path = vault.log_path
    if not path.exists():
        return ""

    text = path.read_text(encoding="utf-8")
    # Split on entry headers
    entries = text.split("\n## [")
    if len(entries) <= 1:
        return ""

    # Take last N entries (first element is the header)
    recent = entries[-n:]
    return "\n## [".join(recent).strip()

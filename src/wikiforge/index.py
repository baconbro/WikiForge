"""Wiki index (_index.md) generation and parsing."""

from __future__ import annotations

from pathlib import Path

import yaml

from wikiforge.models import IndexEntry, WikiIndex


_INDEX_HEADER = "# Wiki Index\n\n<!-- Auto-maintained by WikiForge. Do not edit manually. -->\n"
_YAML_FENCE_START = "```yaml-index"
_YAML_FENCE_END = "```"


def load_index(path: Path) -> WikiIndex:
    if not path.exists():
        return WikiIndex()

    text = path.read_text(encoding="utf-8")

    # Extract YAML block between fences
    start = text.find(_YAML_FENCE_START)
    end = text.find(_YAML_FENCE_END, start + len(_YAML_FENCE_START))
    if start == -1 or end == -1:
        return WikiIndex()

    yaml_text = text[start + len(_YAML_FENCE_START) : end].strip()
    if not yaml_text:
        return WikiIndex()

    data = yaml.safe_load(yaml_text)
    if not isinstance(data, list):
        return WikiIndex()

    entries = [IndexEntry.model_validate(item) for item in data]
    return WikiIndex(entries=entries)


def save_index(path: Path, index: WikiIndex) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    entries_data = [entry.model_dump(mode="json") for entry in index.entries]

    # Build readable markdown
    lines = [_INDEX_HEADER]

    if not index.entries:
        lines.append("No articles yet. Run `wf ingest` and `wf compile` to get started.\n")
    else:
        lines.append(f"**{len(index.entries)} articles** in this wiki.\n\n")

        # Machine-readable YAML block for programmatic access
        lines.append(f"{_YAML_FENCE_START}\n")
        lines.append(yaml.dump(entries_data, default_flow_style=False, sort_keys=False))
        lines.append(f"{_YAML_FENCE_END}\n\n")

        # Human-readable article list grouped by category
        by_category: dict[str, list[IndexEntry]] = {}
        for entry in index.entries:
            by_category.setdefault(entry.category, []).append(entry)

        for category, entries in sorted(by_category.items()):
            lines.append(f"## {category.title()}\n\n")
            for entry in sorted(entries, key=lambda e: e.title):
                lines.append(f"- **[[{entry.title}]]** — {entry.summary}\n")
            lines.append("\n")

    path.write_text("".join(lines), encoding="utf-8")


def render_index_for_llm(index: WikiIndex) -> str:
    """Render the index as a compact string for LLM context."""
    if not index.entries:
        return "The wiki is currently empty. No articles exist yet."

    lines = [f"Wiki contains {len(index.entries)} articles:\n"]
    for entry in index.entries:
        lines.append(f"- [{entry.category}] {entry.title}: {entry.summary}")
    return "\n".join(lines)

"""Schema document loading — per-vault behavioral contract for LLM prompts."""

from __future__ import annotations

from pathlib import Path


DEFAULT_SCHEMA = """\
# Wiki Schema

<!-- This file tells the LLM how to structure and maintain your wiki.
     Edit it to customize conventions for your domain. -->

## Domain

Describe what this knowledge base covers. For example:
- "AI research papers and industry developments"
- "Personal health and fitness tracking"
- "Book notes and literary analysis"

## Page Types

The wiki uses these article categories:
- **concepts** — Ideas, techniques, methodologies
- **entities** — People, organizations, products
- **timelines** — Chronological events and developments
- **comparisons** — Side-by-side analyses of related topics
- **queries** — Filed-back answers from previous questions

## Conventions

- Write in a neutral, encyclopedic tone.
- Each article should cover ONE atomic topic.
- Use [[wikilinks]] liberally to connect related concepts.
- Include a "Related Concepts" section at the end of each article.
- Frontmatter must include: title, summary, sources, tags, category.

## Cross-Referencing

- When a concept is mentioned that has (or should have) its own article, use [[wikilinks]].
- Prefer linking to existing articles over creating redundant content.
- Flag when new information contradicts existing articles.
"""


def load_schema(path: Path) -> str:
    """Load the schema document. Returns empty string if not found."""
    if path.exists():
        content = path.read_text(encoding="utf-8").strip()
        return content
    return ""


def save_default_schema(path: Path) -> None:
    """Write the default schema template."""
    path.write_text(DEFAULT_SCHEMA, encoding="utf-8")

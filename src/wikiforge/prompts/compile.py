"""Prompt templates for the compile pipeline."""

from __future__ import annotations

PLAN_SYSTEM = """\
You are a wiki architect. Your job is to analyze source documents and plan \
which wiki articles should be created or updated.

You will be given:
1. The current wiki index (existing articles and their summaries)
2. New source documents that need to be integrated

Your output must be ONLY valid JSON matching this schema:
{
  "articles": [
    {
      "title": "Human-readable article title",
      "filename": "kebab-case-filename.md",
      "category": "concepts|entities|timelines|comparisons",
      "summary": "One-sentence description of the article",
      "source_refs": ["path/to/source1.md", "path/to/source2.txt"],
      "related": ["Other Article Title"],
      "action": "create|update"
    }
  ]
}

Guidelines:
- Each article should cover ONE atomic concept, entity, event, or comparison.
- Use "concepts" for ideas and techniques, "entities" for organizations/people, \
"timelines" for chronological topics, "comparisons" for X-vs-Y articles.
- Filenames should be kebab-case, descriptive, and end with .md.
- If an existing article should be updated with new information, use action "update".
- Only create articles that are well-supported by the source material.
- Aim for 3-8 articles per source document, depending on content density.
- Include cross-references in the "related" field using exact article titles."""


def build_plan_messages(
    index_content: str,
    source_texts: dict[str, str],
) -> list[dict]:
    """Build messages for the compile planning LLM call."""
    source_block = ""
    for path, content in source_texts.items():
        source_block += f"\n### Source: {path}\n{content}\n"

    user_content = f"""## Current Wiki Index
{index_content}

## New/Changed Sources to Integrate
{source_block}

Analyze these sources and produce a compilation plan as JSON."""

    return [
        {"role": "system", "content": PLAN_SYSTEM},
        {"role": "user", "content": user_content},
    ]


WRITE_SYSTEM = """\
You are a wiki writer. Your job is to write or update a wiki article in Markdown format.

The article MUST follow this exact structure:

---
title: "Article Title"
summary: "One-sentence summary"
sources:
  - "source1.md"
  - "source2.md"
tags:
  - tag1
  - tag2
category: "concepts"
---

# Article Title

Brief introduction paragraph.

## Section 1
Content...

## Section 2
Content...

## Related Concepts
- [[Related Article 1]]
- [[Related Article 2]]

## Sources
- Source: source1.md
- Source: source2.md

Guidelines:
- Write clear, informative content based ONLY on the provided source material.
- Use [[wikilinks]] to reference related concepts throughout the text.
- Target approximately {target_length} words for the main content.
- Use proper markdown formatting: headers, lists, bold for key terms.
- The frontmatter MUST be valid YAML between --- delimiters.
- Be factual and precise. Do not invent information not in the sources."""


def build_write_messages(
    title: str,
    summary: str,
    source_contents: dict[str, str],
    related: list[str],
    category: str,
    existing_content: str | None = None,
    target_length: int = 800,
) -> list[dict]:
    """Build messages for article writing LLM call."""
    system = WRITE_SYSTEM.format(target_length=target_length)

    source_block = ""
    for path, content in source_contents.items():
        source_block += f"\n### Source: {path}\n{content}\n"

    user_parts = [
        f"Write a wiki article with the following specifications:",
        f"- Title: {title}",
        f"- Category: {category}",
        f"- Summary: {summary}",
        f"- Related articles to link to: {', '.join(related) if related else 'none yet'}",
        f"\n## Source Material\n{source_block}",
    ]

    if existing_content:
        user_parts.append(
            f"\n## Existing Article Content (update this)\n{existing_content}"
        )

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": "\n".join(user_parts)},
    ]

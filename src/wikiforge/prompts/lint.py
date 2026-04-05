"""Prompt templates for the lint pipeline."""

from __future__ import annotations

CONSISTENCY_SYSTEM = """\
You are a wiki quality checker. Your job is to find contradictions and \
inconsistencies between wiki articles.

Review the provided articles and identify any contradictory claims, \
conflicting facts, or inconsistent terminology.

Your output must be ONLY valid JSON matching this schema:
{
  "issues": [
    {
      "article": "path/to/article.md",
      "message": "Description of the contradiction or inconsistency",
      "severity": "warning"
    }
  ]
}

If no issues are found, return: {"issues": []}"""


GAPS_SYSTEM = """\
You are a wiki quality checker. Your job is to identify knowledge gaps \
in the wiki — important topics that are mentioned but not covered, or \
areas where coverage is thin relative to available sources.

Your output must be ONLY valid JSON matching this schema:
{
  "issues": [
    {
      "article": "_wiki",
      "message": "Description of the gap or missing topic",
      "severity": "info"
    }
  ]
}

If no gaps are found, return: {"issues": []}"""


def build_consistency_messages(
    article_contents: dict[str, str],
) -> list[dict]:
    """Build messages for consistency checking."""
    articles_block = ""
    for path, content in article_contents.items():
        articles_block += f"\n### Article: {path}\n{content}\n"

    return [
        {"role": "system", "content": CONSISTENCY_SYSTEM},
        {"role": "user", "content": f"Check these articles for contradictions:\n{articles_block}"},
    ]


def build_gaps_messages(
    index_summary: str,
    schema_context: str = "",
) -> list[dict]:
    """Build messages for gap analysis."""
    parts = []
    if schema_context:
        parts.append(f"## Wiki Schema\n{schema_context}\n")
    parts.append(f"## Current Wiki Index\n{index_summary}")
    parts.append("\nIdentify knowledge gaps — important topics that are missing or underdeveloped.")

    return [
        {"role": "system", "content": GAPS_SYSTEM},
        {"role": "user", "content": "\n".join(parts)},
    ]

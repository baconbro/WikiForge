"""Prompt templates for the query pipeline."""

from __future__ import annotations

QUERY_SYSTEM = """\
You are a knowledge base assistant. You answer questions by synthesizing \
information from wiki articles provided to you.

Guidelines:
- Base your answer ONLY on the provided article content.
- Use [[wikilinks]] when referencing concepts that have their own articles.
- If the articles don't contain enough information to answer fully, say so.
- Structure your answer with clear markdown formatting.
- Be concise but thorough. Cite which articles your information comes from.
- If asked for a comparison, use a table format where appropriate."""


def build_query_messages(
    question: str,
    article_contents: dict[str, str],
    index_summary: str,
) -> list[dict]:
    """Build messages for a query against the wiki."""
    articles_block = ""
    for path, content in article_contents.items():
        articles_block += f"\n### Article: {path}\n{content}\n"

    user_content = f"""## Wiki Overview
{index_summary}

## Relevant Articles
{articles_block}

## Question
{question}

Please answer the question based on the wiki articles above."""

    return [
        {"role": "system", "content": QUERY_SYSTEM},
        {"role": "user", "content": user_content},
    ]

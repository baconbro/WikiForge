"""LLM wrapper — unified interface to litellm with retries and structured output."""

from __future__ import annotations

import json
import time
from typing import TypeVar

import litellm
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

# Suppress litellm's verbose logging
litellm.suppress_debug_info = True


def call_llm(
    messages: list[dict],
    model: str = "claude-sonnet-4-20250514",
    temperature: float = 0.3,
    max_retries: int = 3,
) -> str:
    """Call the LLM and return the text response. Retries on transient errors."""
    last_error = None
    for attempt in range(max_retries):
        try:
            response = litellm.completion(
                model=model,
                messages=messages,
                temperature=temperature,
            )
            return response.choices[0].message.content
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"LLM call failed after {max_retries} retries: {last_error}")


def call_llm_json(
    messages: list[dict],
    response_model: type[T],
    model: str = "claude-sonnet-4-20250514",
    temperature: float = 0.2,
) -> T:
    """Call the LLM expecting a JSON response, parse into a pydantic model."""
    raw = call_llm(messages, model=model, temperature=temperature)

    # Extract JSON from the response (may be wrapped in ```json fences)
    json_str = _extract_json(raw)

    try:
        return response_model.model_validate_json(json_str)
    except Exception:
        # Retry once asking the LLM to fix its JSON
        fix_messages = messages + [
            {"role": "assistant", "content": raw},
            {
                "role": "user",
                "content": (
                    "Your response was not valid JSON. Please output ONLY valid JSON "
                    "matching the requested schema, with no markdown fences or extra text."
                ),
            },
        ]
        raw2 = call_llm(fix_messages, model=model, temperature=0.1)
        json_str2 = _extract_json(raw2)
        return response_model.model_validate_json(json_str2)


def _extract_json(text: str) -> str:
    """Extract JSON from text that may be wrapped in markdown code fences."""
    text = text.strip()

    # Try to find ```json ... ``` blocks
    if "```json" in text:
        start = text.index("```json") + len("```json")
        end = text.index("```", start)
        return text[start:end].strip()

    if "```" in text:
        start = text.index("```") + 3
        # Skip optional language tag on same line
        newline = text.index("\n", start)
        start = newline + 1
        end = text.index("```", start)
        return text[start:end].strip()

    return text


def count_tokens(text: str, model: str = "claude-sonnet-4-20250514") -> int:
    """Estimate token count for a string."""
    try:
        return litellm.token_counter(model=model, text=text)
    except Exception:
        # Rough fallback: ~4 chars per token
        return len(text) // 4

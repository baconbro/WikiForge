"""Configuration management for WikiForge."""

from __future__ import annotations

import os
from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class LLMConfig(BaseModel):
    provider: str = "anthropic"
    model: str = "claude-sonnet-4-20250514"
    api_key_env: str = "ANTHROPIC_API_KEY"


class CompileConfig(BaseModel):
    mode: str = "incremental"
    auto_compile_on_ingest: bool = False
    max_articles_per_run: int = 20
    article_target_length: int = 800
    categories: list[str] = Field(
        default_factory=lambda: [
            "concepts",
            "entities",
            "timelines",
            "comparisons",
            "queries",
        ]
    )


class WikiForgeConfig(BaseModel):
    """Top-level configuration for a WikiForge vault."""

    project_name: str = "WikiForge Knowledge Base"
    project_description: str = ""
    llm: LLMConfig = Field(default_factory=LLMConfig)
    compile: CompileConfig = Field(default_factory=CompileConfig)
    chunk_size: int = 4000
    max_context_tokens: int = 100_000

    def get_api_key(self) -> str | None:
        return os.environ.get(self.llm.api_key_env)


def load_config(path: Path) -> WikiForgeConfig:
    if path.exists():
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        return WikiForgeConfig.model_validate(data)
    return WikiForgeConfig()


def save_config(path: Path, config: WikiForgeConfig) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = config.model_dump(mode="json")
    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)

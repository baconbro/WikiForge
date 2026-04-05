"""Pydantic data models for WikiForge."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class SourceStatus(str, Enum):
    pending = "pending"
    compiled = "compiled"
    error = "error"


class ManifestEntry(BaseModel):
    """Tracks a single source file in the manifest."""

    source_path: str
    sha256: str
    last_ingested: datetime
    last_compiled: datetime | None = None
    status: SourceStatus = SourceStatus.pending
    articles: list[str] = Field(default_factory=list)


class Manifest(BaseModel):
    """Registry of all source files and their processing state."""

    version: int = 1
    sources: dict[str, ManifestEntry] = Field(default_factory=dict)


class ArticleFrontmatter(BaseModel):
    """YAML frontmatter for a wiki article."""

    title: str
    summary: str
    sources: list[str] = Field(default_factory=list)
    created: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    tags: list[str] = Field(default_factory=list)
    category: str = "concepts"


class IndexEntry(BaseModel):
    """A single entry in the wiki index."""

    path: str
    title: str
    summary: str
    category: str = "concepts"


class WikiIndex(BaseModel):
    """The wiki's table of contents."""

    entries: list[IndexEntry] = Field(default_factory=list)

    def find_by_path(self, path: str) -> IndexEntry | None:
        for entry in self.entries:
            if entry.path == path:
                return entry
        return None

    def upsert(self, entry: IndexEntry) -> None:
        for i, existing in enumerate(self.entries):
            if existing.path == entry.path:
                self.entries[i] = entry
                return
        self.entries.append(entry)


class ArticlePlan(BaseModel):
    """Plan for a single wiki article to create or update."""

    title: str
    filename: str
    category: str = "concepts"
    summary: str
    source_refs: list[str] = Field(default_factory=list)
    related: list[str] = Field(default_factory=list)
    action: Literal["create", "update"] = "create"


class CompilePlan(BaseModel):
    """LLM-generated plan for a compilation run."""

    articles: list[ArticlePlan] = Field(default_factory=list)

"""Vault directory operations — scaffolding and path resolution."""

from __future__ import annotations

from pathlib import Path

from wikiforge.config import WikiForgeConfig, load_config, save_config
from wikiforge.schema import save_default_schema


class Vault:
    """Represents a WikiForge vault (an Obsidian-compatible directory)."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    @property
    def wikiforge_dir(self) -> Path:
        return self.root / ".wikiforge"

    @property
    def config_path(self) -> Path:
        return self.wikiforge_dir / "config.yaml"

    @property
    def manifest_path(self) -> Path:
        return self.wikiforge_dir / "_manifest.yaml"

    @property
    def raw_dir(self) -> Path:
        return self.root / "raw"

    @property
    def wiki_dir(self) -> Path:
        return self.root / "wiki"

    @property
    def index_path(self) -> Path:
        return self.wiki_dir / "_index.md"

    @property
    def outputs_dir(self) -> Path:
        return self.root / "outputs"

    @property
    def schema_path(self) -> Path:
        return self.root / "schema.md"

    @property
    def log_path(self) -> Path:
        return self.wiki_dir / "_log.md"

    def load_config(self) -> WikiForgeConfig:
        return load_config(self.config_path)

    def is_valid(self) -> bool:
        return self.wikiforge_dir.is_dir()


def init_vault(path: Path, config: WikiForgeConfig | None = None) -> Vault:
    """Scaffold a new WikiForge vault at the given path."""
    vault = Vault(path)

    if vault.wikiforge_dir.exists():
        raise FileExistsError(
            f"Vault already initialized at {vault.root}"
        )

    # Create directory structure
    vault.wikiforge_dir.mkdir(parents=True)
    vault.raw_dir.mkdir(exist_ok=True)
    vault.wiki_dir.mkdir(exist_ok=True)
    vault.outputs_dir.mkdir(exist_ok=True)

    # Create category subdirectories in wiki/
    cfg = config or WikiForgeConfig()
    for category in cfg.compile.categories:
        (vault.wiki_dir / category).mkdir(exist_ok=True)

    # Write default config
    save_config(vault.config_path, cfg)

    # Write empty manifest
    vault.manifest_path.write_text(
        "version: 1\nsources: {}\n", encoding="utf-8"
    )

    # Write default schema
    save_default_schema(vault.schema_path)

    # Write index template
    vault.index_path.write_text(
        "# Wiki Index\n\n"
        "<!-- Auto-maintained by WikiForge. Do not edit manually. -->\n\n"
        "No articles yet. Run `wf ingest` and `wf compile` to get started.\n",
        encoding="utf-8",
    )

    return vault


def resolve_vault(start: Path | None = None) -> Vault:
    """Walk up from start (default: cwd) to find a WikiForge vault."""
    current = (start or Path.cwd()).resolve()
    while True:
        if (current / ".wikiforge").is_dir():
            return Vault(current)
        parent = current.parent
        if parent == current:
            raise FileNotFoundError(
                "No WikiForge vault found. Run `wf init` to create one."
            )
        current = parent

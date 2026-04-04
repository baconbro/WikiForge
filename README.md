# WikiForge

**Raw sources in, living wiki out. Your LLM is the editor.**

WikiForge turns a pile of source documents into a structured, interlinked, LLM-maintained wiki — viewable and navigable in Obsidian.

## Quick Start

```bash
# Install
uv sync

# Initialize a vault
wf init --path my-knowledge-base

# Add sources to raw/
cp my-notes.md my-knowledge-base/raw/

# Ingest and compile
cd my-knowledge-base
wf ingest --all
wf compile

# Query your wiki
wf query "What are the key concepts?"

# Check vault status
wf status
```

## CLI Commands

| Command | Description |
|---|---|
| `wf init [--path PATH]` | Initialize a new vault |
| `wf ingest [--all] [--dry-run]` | Process new sources in `raw/` |
| `wf compile [--plan-only]` | Compile staged sources into wiki articles |
| `wf query QUESTION [-o FILE]` | Ask a question against the wiki |
| `wf search TERM` | Keyword search across wiki articles |
| `wf status` | Show vault statistics |

## How It Works

1. **Ingest** — Drop markdown/text files into `raw/`. WikiForge registers them in a manifest with content hashes.
2. **Compile** — The LLM reads your sources, plans wiki articles, and writes structured markdown with frontmatter, wikilinks, and backlinks into `wiki/`.
3. **Query** — Ask questions against your wiki. The LLM finds relevant articles and synthesizes answers.

The wiki is a *compiled artifact* — entirely LLM-generated. You curate sources and ask questions; the LLM does the writing.

## Configuration

Set your API key:
```bash
export ANTHROPIC_API_KEY=your-key-here
```

Configuration lives in `.wikiforge/config.yaml` inside each vault.

## Development

```bash
uv sync
uv run pytest tests/ -v
```

## License

Apache 2.0

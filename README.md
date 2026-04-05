# WikiForge

**Raw sources in, living wiki out. Your LLM is the editor.**

Most people's experience with LLMs and documents looks like RAG: upload files, the LLM retrieves chunks at query time, generates an answer. The LLM rediscovers knowledge from scratch on every question. Nothing is built up.

WikiForge is different. When you add a source, the LLM doesn't just index it — it *reads* it, extracts the key concepts, and writes structured wiki articles with cross-references, backlinks, and frontmatter. The knowledge is compiled once and kept current. Every source you add and every question you ask makes the wiki richer.

**You never write the wiki yourself.** You curate sources and ask questions. The LLM does the summarizing, cross-referencing, filing, and bookkeeping.

## What's In It For You

- **Knowledge that compounds.** Unlike chat history or RAG, your wiki gets richer over time. Ask a question today, file it back — it's there for tomorrow's questions.
- **Works with Obsidian.** The vault *is* an Obsidian vault. Graph view, wikilinks, Dataview queries, Marp slides — it all just works.
- **No manual maintenance.** The LLM maintains cross-references, updates articles when sources change, and flags contradictions. The maintenance that kills personal wikis is handled for you.
- **Your sources stay yours.** Raw files in `raw/` are never modified. The wiki is a compiled artifact you can rebuild anytime.
- **Domain-adaptable.** Edit `schema.md` to teach the LLM your conventions — whether you're tracking AI research, reading a novel, doing competitive analysis, or building course notes.

## Quick Start

```bash
# Install
pip install uv  # if you don't have uv yet
git clone https://github.com/baconbro/WikiForge.git
cd WikiForge
uv sync

# Set your API key
export ANTHROPIC_API_KEY=sk-ant-...

# Create a vault
wf init --path ~/my-research-wiki --name "AI Research"

# Add some sources
cp paper-summary.md ~/my-research-wiki/raw/
cp lecture-notes.txt ~/my-research-wiki/raw/

# Build the wiki
cd ~/my-research-wiki
wf ingest --all      # Register sources (hashes, metadata)
wf compile           # LLM reads sources → writes wiki articles

# Open in Obsidian and explore the graph view!
```

## Example Workflow

Here's what a real session looks like:

```bash
# 1. You clipped an article about transformer architectures
#    and saved it to raw/transformers-survey.md

# 2. Ingest and compile
$ wf ingest --all
Ingest complete: 1 new, 0 updated, 0 unchanged

$ wf compile
Compiling...

Compilation plan (4 articles):
  + [concepts] Transformer Architecture
  + [concepts] Self-Attention Mechanism
  + [concepts] Positional Encoding
  + [entities] Google Brain

Done: 4 created, 0 updated from 1 sources

# 3. Ask questions
$ wf query "How does self-attention work?"
Self-attention computes relationships between all positions in a
sequence simultaneously. Each token generates query, key, and value
vectors...

---
Based on: Self-Attention Mechanism, Transformer Architecture

# 4. That answer is useful — save it to the wiki for future reference
$ wf query "Compare attention mechanisms across transformer variants" --file-back
...
Filed back to: wiki/queries/compare-attention-mechanisms-across-transformer-variants.md

# 5. Check wiki health
$ wf lint
Running lint checks...

3 issue(s) found across 4 check(s):
  [!] broken_links: Dangling wikilink: [[BERT]] — no matching article
  [i] orphan_pages: 'Positional Encoding' has no inbound links
  [!] stale_sources: Source 'old-notes.md' has changes not yet compiled

Report saved to outputs/_lint_report.md

# 6. Check vault status
$ wf status
WikiForge Vault: AI Research
Path: /home/user/my-research-wiki
LLM: anthropic/claude-sonnet-4-20250514
Schema: yes

Sources: 3 total (1 pending, 2 compiled, 0 errors)
Wiki articles: 5
Index entries: 5

Recent activity:
  [2026-04-05 10:32] lint | 3 issues found
  [2026-04-05 10:30] query | Compare attention mechanisms across transformer variants
  [2026-04-05 10:15] compile | 4 articles from 1 sources
```

## How It Works

```
 You add sources         LLM compiles            You query & explore
┌──────────────┐    ┌──────────────────┐    ┌───────────────────────┐
│   raw/       │───>│   wiki/          │───>│  wf query "..."       │
│  articles    │    │  concepts/       │    │  wf search "..."      │
│  papers      │    │  entities/       │    │  Obsidian graph view  │
│  notes       │    │  timelines/      │    │                       │
│  clippings   │    │  _index.md       │    │  Answers file back ──>│
└──────────────┘    │  _log.md         │    └───────────────────────┘
                    └──────────────────┘               │
                           ^                           │
                           └───────────────────────────┘
                              The compounding flywheel
```

1. **Ingest** (`wf ingest`) — Scans `raw/` for new or changed files. Registers them with SHA-256 hashes in a manifest. No LLM calls yet.

2. **Compile** (`wf compile`) — The LLM reads pending sources, plans which articles to create/update, then writes structured markdown with YAML frontmatter, `[[wikilinks]]`, and cross-references.

3. **Query** (`wf query`) — Finds relevant articles by keyword matching against the index, sends them to the LLM, and synthesizes an answer. With `--file-back`, the answer becomes a new wiki page.

4. **Lint** (`wf lint`) — Health-checks the wiki: broken links, orphan pages, stale sources, contradictions, and knowledge gaps.

## Use Cases

| Use Case | What Goes in `raw/` | What You Get in `wiki/` |
|---|---|---|
| **Research** | Papers, articles, survey notes | Concept pages, entity profiles, comparison tables, evolving thesis |
| **Reading a book** | Chapter summaries, quotes, reactions | Character pages, theme analysis, plot timeline, connections |
| **Personal knowledge** | Journal entries, podcast notes, articles | Goal tracking, insight synthesis, pattern recognition |
| **Business intel** | Meeting transcripts, competitor docs, market reports | Company profiles, market maps, trend analysis |
| **Course notes** | Lecture notes, textbook chapters, problem sets | Topic summaries, concept maps, study guides |
| **Trip planning** | Hotel reviews, blog posts, guides | Destination pages, itinerary options, budget comparisons |

## CLI Reference

| Command | Description |
|---|---|
| `wf init [--path PATH] [--name NAME]` | Initialize a new vault with directory structure and schema |
| `wf ingest [--all] [--dry-run] [FILES...]` | Register new/changed sources in the manifest |
| `wf compile [--plan-only]` | LLM compiles pending sources into wiki articles |
| `wf query QUESTION [-o FILE] [--file-back]` | Ask a question; optionally save answer as wiki page |
| `wf lint [--fix] [--check CHECK]` | Health-check: broken links, orphans, staleness, gaps |
| `wf search TERM` | Fast keyword search across article titles and summaries |
| `wf status` | Vault stats, source counts, recent activity log |

## Vault Structure

```
my-knowledge-base/
├── schema.md              # Wiki conventions — edit to customize the LLM's behavior
├── raw/                   # Your source documents (never modified by the LLM)
│   ├── paper.md
│   └── notes.txt
├── wiki/                  # LLM-compiled wiki (don't edit manually)
│   ├── _index.md          # Auto-maintained table of contents
│   ├── _log.md            # Chronological activity log
│   ├── concepts/
│   │   └── attention-mechanism.md
│   ├── entities/
│   │   └── google-brain.md
│   ├── queries/           # Filed-back query answers
│   │   └── how-does-attention-work.md
│   └── ...
├── outputs/               # Query results, lint reports
│   └── _lint_report.md
└── .wikiforge/
    ├── config.yaml        # LLM provider, model, compile settings
    └── _manifest.yaml     # Source registry with hashes and status
```

## The Schema Document

`schema.md` is what makes WikiForge adaptable to any domain. It's a plain markdown file at the vault root that gets injected into every LLM prompt. Edit it to define:

- **What domain** your wiki covers
- **What page types** to use (concepts, entities, timelines, or your own)
- **Conventions** for tone, structure, and formatting
- **Cross-referencing rules** specific to your domain

The default template works out of the box. Customize it as you learn what works for your use case.

## Configuration

```bash
# Required: set your API key
export ANTHROPIC_API_KEY=sk-ant-...

# The config file is at .wikiforge/config.yaml
# Key settings:
#   llm.model: which model to use (default: claude-sonnet-4-20250514)
#   compile.max_articles_per_run: limit articles per compile (default: 20)
#   compile.article_target_length: target word count (default: 800)
#   compile.categories: article categories (concepts, entities, timelines, comparisons, queries)
```

## Obsidian Integration

WikiForge is Obsidian-native. Open the vault directory in Obsidian and you get:

- **Graph view** — See how concepts connect. Hub nodes are your most cross-referenced ideas.
- **Wikilinks** — `[[links]]` work natively. Click through from concept to concept.
- **Frontmatter** — Every article has YAML metadata. Use Dataview to query across articles.
- **Web Clipper** — Clip articles from the web directly into `raw/`. The LLM handles the rest.

**Recommended plugins**: Dataview, Graph Analysis, Marp Slides, Obsidian Git

## Development

```bash
uv sync
uv run pytest tests/ -v    # 46 tests
```

## License

Apache 2.0

---
name: WikiForge Ingest
description: Ingest files and conversation knowledge into a WikiForge vault
---

# WikiForge Ingest Skill

You have access to WikiForge, an LLM-powered knowledge management system that turns raw documents into interconnected wiki articles. This skill enables you to ingest content directly into a WikiForge vault — from files shared in conversation, from the conversation itself, or from any text the user provides.

## Prerequisites

- The current directory (or a parent) must contain a WikiForge vault (has a `.wikiforge/` directory). If not, initialize one with `wf init`.
- For compilation to work, an API key must be set (e.g. `ANTHROPIC_API_KEY`).

## Available Command

```
wf ingest-text -t "TITLE" [-c "CONTENT"] [-d SUBDIRECTORY] [--compile/--no-compile] [--dry-run]
```

- `-t / --title` (required): Title for the document. Also drives the filename (kebab-case slug).
- `-c / --content`: Text content as a string. If omitted, reads from **stdin**.
- `-d / --subdirectory`: Subdirectory within `raw/` (e.g. `conversations`, `meeting-notes`).
- `--compile / --no-compile`: Auto-compile after ingest (default: compile). Compilation uses the LLM to generate/update wiki articles.
- `--dry-run`: Preview without writing.

## Ingestion Modes

### Mode 1: File Ingestion

When the user shares a file in conversation or asks you to ingest a specific file:

1. Read the file content.
2. Determine a descriptive title from the filename or content.
3. Write it to the vault using a stdin heredoc (preferred for large content):

```bash
cat <<'WFEOF' | wf ingest-text -t "Descriptive Title Here"
<file content here>
WFEOF
```

Or for short content, use the `-c` flag:

```bash
wf ingest-text -t "Title" -c "Short content here"
```

4. Report what was ingested and what wiki articles were created/updated.

### Mode 2: Conversation Ingestion

When the user asks to ingest the conversation (e.g. "save this to the wiki", "ingest our discussion", "capture this knowledge"):

1. **Extract key insights** from the conversation. Do NOT dump the raw transcript. Instead, synthesize:
   - **Summary**: A 2-3 sentence overview of what was discussed
   - **Key Decisions**: Any decisions or conclusions reached
   - **Technical Details**: Important technical information, code patterns, architecture choices, configurations
   - **Action Items**: Any next steps or follow-ups identified
   - **Context**: Why this conversation happened and what prompted it

2. Structure the extracted knowledge as markdown:

```markdown
# <Topic of Conversation>

## Summary
<2-3 sentence overview>

## Key Decisions
- <decision 1>
- <decision 2>

## Technical Details
<relevant technical information, code snippets, architecture notes>

## Action Items
- [ ] <action 1>
- [ ] <action 2>

## Context
<what prompted this discussion, relevant background>

---
*Captured from conversation on <date>*
```

3. Ingest it with a `conversations` subdirectory:

```bash
cat <<'WFEOF' | wf ingest-text -t "Conversation: <Topic>" -d conversations
<structured markdown content>
WFEOF
```

4. Report the result to the user including which wiki articles were created or updated.

### Mode 3: Batch Ingestion

When the user wants to ingest multiple items at once:

1. Ingest each item individually with `--no-compile` to avoid redundant compilation:

```bash
wf ingest-text -t "Item 1" -c "content" --no-compile
wf ingest-text -t "Item 2" -c "content" --no-compile
```

2. Run a single compilation at the end:

```bash
wf compile
```

3. Report the combined results.

## Guidelines

- Always use descriptive titles that reflect the content — these become filenames and help the LLM plan good wiki articles.
- For conversation ingestion, focus on **extractable knowledge**, not play-by-play. Ask yourself: "What would someone searching this wiki need to find?"
- Use subdirectories to organize content by type: `conversations`, `meeting-notes`, `research`, `references`.
- If the vault doesn't exist yet, offer to create one with `wf init`.
- After ingestion with compile, briefly summarize which wiki articles were created or updated.
- If compilation fails due to missing API key, inform the user and explain they can compile later with `wf compile`.

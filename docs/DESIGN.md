# Obsidian LLMHub — Design Document

> **Mirror your AI. Own your knowledge.**

## 1. Vision

**Git for AI conversations.**

AI conversations are valuable, but today they disappear into proprietary chat
histories. Obsidian LLMHub continuously captures your AI conversations, converts
them into structured Markdown, enriches them with metadata, links them into
your knowledge graph, and stores everything in your own repository.

Your conversations remain **searchable**, **version-controlled**, and
**future-proof** — a second brain built from every AI conversation you have.

## 2. Product Principles

1. **Own your data.** Everything lands in plain files (Markdown + YAML + JSONL)
   inside a directory the user controls — ideally a Git repository. No
   proprietary database, no lock-in.
2. **Source-agnostic.** Claude, ChatGPT, Gemini, Codex, Perplexity, Cursor,
   Windsurf, Open WebUI — every source is normalized into one canonical
   conversation schema before anything else happens.
3. **Idempotent sync.** Running the same import twice produces zero diff.
   Re-importing an updated conversation updates exactly that file. This is
   what makes Git history meaningful.
4. **Offline-first, LLM-optional.** The core pipeline (normalize → Markdown →
   chunk → tag → link) works with zero network access. LLM-powered enrichment
   (summaries, embeddings, semantic tags) is a pluggable, optional layer.
5. **Tool-friendly output.** The vault is directly usable by Obsidian, Logseq,
   grep/ripgrep, and any static-site or RAG tooling.

## 3. Architecture

```
 Sources                     Core                          Destinations
┌──────────────┐   ┌───────────────────────────┐   ┌─────────────────────┐
│ Claude       │   │  Conversation Normalizer  │   │ Filesystem vault    │
│ ChatGPT      │──▶│  (canonical schema)       │   │  (Obsidian/Logseq-  │
│ Gemini       │   ├───────────────────────────┤   │   compatible)       │
│ Codex        │   │  Knowledge Pipeline       │──▶│ Git (auto-commit)   │
│ Perplexity   │   │   ├─ Markdown render      │   │ Notion (roadmap)    │
│ Cursor Chat  │   │   ├─ YAML frontmatter     │   └─────────────────────┘
│ Windsurf     │   │   ├─ Chunking             │
│ Open WebUI   │   │   ├─ Tagging              │
└──────────────┘   │   ├─ Linking              │
   importers       │   ├─ Summary   (optional) │
                   │   └─ Embedding (optional) │
                   └───────────────────────────┘
```

### 3.1 Layers

| Layer | Responsibility | Code |
|---|---|---|
| **Importers** | Parse a source's export format into canonical `Conversation` objects; auto-detect format | `obsidianllmhub/importers/` |
| **Model** | Canonical schema: `Conversation`, `Message` | `obsidianllmhub/model.py` |
| **Pipeline** | Stateless enrichment stages operating on the canonical model | `obsidianllmhub/pipeline/` |
| **Sinks** | Write pipeline output to a destination; track state for idempotency | `obsidianllmhub/sinks/` |
| **CLI** | `obsidian-llmhub init / import / status` | `obsidianllmhub/cli.py` |

### 3.2 Canonical data model

Every importer produces this — and nothing downstream ever sees a
source-specific format again:

```yaml
Conversation:
  id: str            # stable id from the source (uuid)
  title: str
  source: str        # claude | chatgpt | generic | ...
  created_at: str    # ISO-8601, UTC
  updated_at: str
  messages:
    - role: user | assistant | system | tool
      text: str      # plain text / markdown
      timestamp: str | null
      model: str | null
  metadata: dict     # source-specific extras, preserved verbatim
```

### 3.3 Vault layout

```
vault/
├── obsidianllmhub.toml                 # vault config
├── conversations/
│   └── <source>/<YYYY>/<MM>/<slug>-<id8>.md
├── index.md                        # auto-generated map of content
└── .obsidianllmhub/
    ├── state.json                  # id → content hash (idempotent sync)
    └── chunks/<id8>.jsonl          # embedding-ready chunks
```

Each conversation file:

```markdown
---
id: 9f1c…
title: Designing a rate limiter
source: claude
created: 2026-07-01T09:12:00+00:00
updated: 2026-07-01T09:48:00+00:00
messages: 14
tags: [rate-limiter, redis, python]
---

# Designing a rate limiter

## 🧑 User
...

## 🤖 Assistant
...

## Related
- [[another-conversation-slug]]
```

### 3.4 Idempotency & Git

The filesystem sink keeps `state.json` mapping conversation id → SHA-256 of
the rendered content. A re-import skips unchanged conversations, rewrites
changed ones, and reports `new / updated / unchanged` counts. The Git sink
then commits only when the working tree actually changed, so history reads
like a changelog of your knowledge.

### 3.5 Enrichment stages

| Stage | MVP implementation | Future |
|---|---|---|
| Markdown | deterministic renderer + YAML frontmatter | templates |
| Chunking | message-boundary-aware, ~2000-char chunks → JSONL | token-aware |
| Tagging | code-fence language detection + keyword frequency | LLM semantic tags |
| Linking | tag-overlap similarity → `[[wiki-links]]` | embedding similarity |
| Summary | — (roadmap) | LLM summary in frontmatter |
| Embedding | chunk JSONL is embedding-ready | local/API embeddings + vector index |

## 4. Roadmap

- **M0 (this repo, done)** — Core pipeline: Claude + ChatGPT + generic
  importers, Markdown/YAML render, chunking, tagging, linking, filesystem
  vault, Git auto-commit, CLI, tests.
- **M1 — More sources.** Gemini Takeout, Perplexity, Cursor/Windsurf local
  chat DBs, Open WebUI export. Watch-mode (`obsidian-llmhub sync --watch`) over a
  downloads folder.
- **M2 — LLM enrichment.** Optional summaries, semantic tags, and titles via
  the Claude API; embeddings + local vector index; `obsidian-llmhub search`.
- **M3 — Continuous capture.** Browser extension / MCP server that streams
  conversations as they happen; Notion & Logseq sinks; scheduled sync
  (cron/Routines).

## 5. Non-goals

- Hosting user data on any server we run.
- Reimplementing a chat client. Obsidian LLMHub mirrors; it doesn't chat.
- Perfect fidelity of rich content (images, artifacts) in M0 — attachments
  are referenced in metadata and preserved verbatim, rendered in later
  milestones.

# 🟣 Obsidian Hub

> **Mirror your AI. Own your knowledge.**

**Git for AI conversations.** AI conversations are valuable, but today they
disappear into proprietary chat histories. Obsidian Hub captures your AI
conversations, converts them into structured Markdown, enriches them with
metadata, links them into your knowledge graph, and stores everything in your
own repository — searchable, version-controlled, and future-proof.

```
Claude · ChatGPT · Gemini · Codex · Perplexity · Cursor · Windsurf · Open WebUI
                                   │
                        Conversation Normalizer
                                   │
                          Knowledge Pipeline
              Markdown · YAML · Chunk · Tag · Link · (Summary · Embedding)
                                   │
                 Obsidian · Logseq · Git · Filesystem · (Notion)
```

See [docs/DESIGN.md](docs/DESIGN.md) for the full architecture and roadmap.

## Quick start

```bash
pip install -e .

# 1. Create a vault (any directory; git init it for version history)
obsidian-hub init ~/ai-vault
git -C ~/ai-vault init

# 2. Import your AI conversation exports (format auto-detected)
obsidian-hub import ~/Downloads/claude-export/conversations.json --vault ~/ai-vault
obsidian-hub import ~/Downloads/chatgpt-export/conversations.json --vault ~/ai-vault

# 3. Inspect
obsidian-hub status --vault ~/ai-vault
```

Re-running an import is **idempotent**: unchanged conversations are skipped,
updated ones are rewritten, and each sync becomes one clean Git commit.

## What you get

- `conversations/<source>/<YYYY>/<MM>/<slug>-<id>.md` — one Markdown note per
  conversation with YAML frontmatter (id, source, dates, tags), role-labeled
  sections, and `[[wiki-links]]` to related conversations.
- `index.md` — an auto-generated map of content, newest first.
- `.obsidianhub/chunks/*.jsonl` — embedding-ready chunks for RAG tooling.

Open the vault in **Obsidian** or **Logseq** and your AI history becomes a
browsable, linked second brain.

## Supported sources

| Source | Status |
|---|---|
| Claude.ai data export | ✅ |
| ChatGPT data export | ✅ |
| Generic JSON (canonical schema — bring any source) | ✅ |
| Gemini / Perplexity / Cursor / Windsurf / Open WebUI | 🚧 roadmap |

## Development

```bash
pip install -e . pytest
pytest
```

## License

MIT

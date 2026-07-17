"""Filesystem vault sink: idempotent, Obsidian/Logseq-compatible.

Layout (see docs/DESIGN.md):
    vault/
      conversations/<source>/<YYYY>/<MM>/<slug>-<id8>.md
      index.md
      .obsidianhub/state.json
      .obsidianhub/chunks/<id8>.jsonl
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

from obsidianhub.model import Conversation
from obsidianhub.pipeline import chunker, linker, markdown, tagger

STATE_DIR = ".obsidianhub"


@dataclass
class SyncReport:
    new: list[str] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)
    unchanged: list[str] = field(default_factory=list)

    @property
    def changed(self) -> bool:
        return bool(self.new or self.updated)

    def summary(self) -> str:
        return (
            f"{len(self.new)} new, {len(self.updated)} updated, "
            f"{len(self.unchanged)} unchanged"
        )


class Vault:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.state_path = self.root / STATE_DIR / "state.json"
        self.chunks_dir = self.root / STATE_DIR / "chunks"

    def init(self) -> None:
        (self.root / "conversations").mkdir(parents=True, exist_ok=True)
        self.chunks_dir.mkdir(parents=True, exist_ok=True)
        if not self.state_path.exists():
            self._save_state({})
        config = self.root / "obsidianhub.toml"
        if not config.exists():
            config.write_text(
                "# Obsidian Hub vault configuration\n"
                '[vault]\nname = "my-ai-knowledge"\n\n'
                "[pipeline]\nchunk_chars = 2000\nmax_tags = 8\n\n"
                "[git]\nauto_commit = true\n",
                encoding="utf-8",
            )

    @property
    def exists(self) -> bool:
        return self.state_path.exists()

    def _load_state(self) -> dict:
        if self.state_path.exists():
            return json.loads(self.state_path.read_text(encoding="utf-8"))
        return {}

    def _save_state(self, state: dict) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(
            json.dumps(state, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    def _note_path(self, conv: Conversation) -> Path:
        created = conv.created_at or "0000-00"
        year, month = created[:4], created[5:7] or "00"
        name = f"{conv.slug}-{conv.short_id}.md"
        return self.root / "conversations" / conv.source / year / month / name

    def sync(self, conversations: list[Conversation]) -> SyncReport:
        """Write conversations into the vault; skip ones whose content is unchanged."""
        state = self._load_state()
        report = SyncReport()

        # Tag everything first so linking sees the whole vault, incl. prior syncs.
        tagged = {entry["note"]: entry.get("tags", []) for entry in state.values()}
        conv_tags: dict[str, list[str]] = {}
        for conv in conversations:
            note_name = self._note_path(conv).stem
            conv_tags[conv.id] = tagger.tags_for(conv)
            tagged[note_name] = conv_tags[conv.id]

        related = linker.related_map(tagged)

        for conv in conversations:
            path = self._note_path(conv)
            note_name = path.stem
            content = markdown.render(
                conv, tags=conv_tags[conv.id], related=related.get(note_name, [])
            )
            digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
            prior = state.get(conv.id)

            if prior and prior.get("hash") == digest:
                report.unchanged.append(note_name)
                continue

            if prior and prior.get("path") and (self.root / prior["path"]) != path:
                stale = self.root / prior["path"]
                if stale.exists():
                    stale.unlink()

            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            self._write_chunks(conv)
            state[conv.id] = {
                "hash": digest,
                "path": str(path.relative_to(self.root)),
                "note": note_name,
                "tags": conv_tags[conv.id],
                "title": conv.title,
                "source": conv.source,
                "updated": conv.updated_at,
            }
            (report.updated if prior else report.new).append(note_name)

        self._save_state(state)
        self._write_index(state)
        return report

    def _write_chunks(self, conv: Conversation) -> None:
        self.chunks_dir.mkdir(parents=True, exist_ok=True)
        chunks = chunker.chunk(conv)
        out = self.chunks_dir / f"{conv.short_id}.jsonl"
        out.write_text(
            "".join(json.dumps(c, ensure_ascii=False) + "\n" for c in chunks),
            encoding="utf-8",
        )

    def _write_index(self, state: dict) -> None:
        entries = sorted(
            state.values(), key=lambda e: e.get("updated") or "", reverse=True
        )
        lines = [
            "---",
            "title: Obsidian Hub Index",
            "type: moc",
            "---",
            "",
            "# 🪞 Obsidian Hub — Conversation Index",
            "",
            f"{len(entries)} conversations mirrored.",
            "",
            "| Updated | Source | Conversation | Tags |",
            "|---|---|---|---|",
        ]
        for e in entries:
            updated = (e.get("updated") or "")[:10]
            tags = " ".join(f"#{t}" for t in e.get("tags", [])[:4])
            lines.append(
                f"| {updated} | {e.get('source', '')} | [[{e['note']}]] | {tags} |"
            )
        (self.root / "index.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

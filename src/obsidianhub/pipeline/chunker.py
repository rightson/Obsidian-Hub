"""Split conversations into embedding-ready chunks.

Chunks respect message boundaries where possible; oversized messages are
split on paragraph boundaries. Output is a list of dicts ready to be
serialized as JSONL and fed to any embedding model.
"""

from __future__ import annotations

from typing import Any

from obsidianhub.model import Conversation

DEFAULT_CHUNK_CHARS = 2000


def _split_long(text: str, limit: int) -> list[str]:
    paragraphs = text.split("\n\n")
    pieces, current = [], ""
    for para in paragraphs:
        candidate = f"{current}\n\n{para}" if current else para
        if len(candidate) <= limit or not current:
            current = candidate
        else:
            pieces.append(current)
            current = para
    if current:
        pieces.append(current)
    # A single paragraph can still exceed the limit; hard-split it.
    final = []
    for piece in pieces:
        while len(piece) > limit:
            final.append(piece[:limit])
            piece = piece[limit:]
        final.append(piece)
    return final


def chunk(conv: Conversation, max_chars: int = DEFAULT_CHUNK_CHARS) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    buffer: list[str] = []
    buffer_len = 0

    def flush() -> None:
        nonlocal buffer, buffer_len
        if buffer:
            chunks.append(
                {
                    "conversation_id": conv.id,
                    "title": conv.title,
                    "source": conv.source,
                    "chunk_index": len(chunks),
                    "text": "\n\n".join(buffer),
                }
            )
            buffer, buffer_len = [], 0

    for msg in conv.messages:
        entry = f"{msg.role}: {msg.text.strip()}"
        if len(entry) > max_chars:
            flush()
            for piece in _split_long(entry, max_chars):
                buffer.append(piece)
                flush()
            continue
        if buffer_len + len(entry) > max_chars:
            flush()
        buffer.append(entry)
        buffer_len += len(entry)
    flush()
    return chunks

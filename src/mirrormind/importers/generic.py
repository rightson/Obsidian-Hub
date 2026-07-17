"""Importer for MirrorMind's own canonical JSON format.

Any tool can emit this format to feed MirrorMind directly — this is the
integration point for sources without a dedicated importer (Open WebUI
plugins, custom scripts, MCP capture, ...). Accepts a single conversation
object or a list of them; the shape matches ``Conversation.to_dict()``.
"""

from __future__ import annotations

from typing import Any

from mirrormind.model import Conversation, Message, iso_utc

SOURCE = "generic"


def matches(data: Any) -> bool:
    items = data if isinstance(data, list) else [data]
    if not items:
        return False
    first = items[0]
    return (
        isinstance(first, dict)
        and "messages" in first
        and isinstance(first.get("messages"), list)
        and all(isinstance(m, dict) and "role" in m for m in first["messages"])
    )


def parse(data: Any) -> list[Conversation]:
    items = data if isinstance(data, list) else [data]
    conversations = []
    for conv in items:
        messages = [
            Message(
                role=m.get("role", "tool"),
                text=m.get("text") or m.get("content") or "",
                timestamp=iso_utc(m.get("timestamp")),
                model=m.get("model"),
                metadata=m.get("metadata") or {},
            )
            for m in conv.get("messages") or []
            if (m.get("text") or m.get("content") or "").strip()
        ]
        conversations.append(
            Conversation(
                id=str(conv.get("id") or conv.get("uuid") or ""),
                title=conv.get("title") or "Untitled",
                source=conv.get("source") or SOURCE,
                created_at=iso_utc(conv.get("created_at")),
                updated_at=iso_utc(conv.get("updated_at")),
                messages=messages,
                metadata=conv.get("metadata") or {},
            )
        )
    return conversations

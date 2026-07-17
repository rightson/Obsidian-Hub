"""Importer for Claude.ai data exports (conversations.json).

Format: a JSON array of conversation objects with ``uuid``, ``name``,
``created_at``, ``updated_at`` and ``chat_messages`` (each with ``sender``
of ``human``/``assistant``, ``text`` and/or a ``content`` block list).
"""

from __future__ import annotations

from typing import Any

from obsidianhub.model import Conversation, Message, iso_utc

SOURCE = "claude"

_ROLE_MAP = {"human": "user", "assistant": "assistant"}


def matches(data: Any) -> bool:
    if not isinstance(data, list) or not data:
        return False
    first = data[0]
    return isinstance(first, dict) and "uuid" in first and "chat_messages" in first


def _message_text(msg: dict[str, Any]) -> str:
    parts: list[str] = []
    for block in msg.get("content") or []:
        if block.get("type") == "text" and block.get("text"):
            parts.append(block["text"])
    if parts:
        return "\n\n".join(parts)
    return msg.get("text") or ""


def parse(data: Any) -> list[Conversation]:
    conversations = []
    for conv in data:
        messages = []
        for msg in conv.get("chat_messages") or []:
            text = _message_text(msg)
            if not text.strip():
                continue
            messages.append(
                Message(
                    role=_ROLE_MAP.get(msg.get("sender", ""), msg.get("sender", "tool")),
                    text=text,
                    timestamp=iso_utc(msg.get("created_at")),
                )
            )
        conversations.append(
            Conversation(
                id=conv["uuid"],
                title=conv.get("name") or "Untitled",
                source=SOURCE,
                created_at=iso_utc(conv.get("created_at")),
                updated_at=iso_utc(conv.get("updated_at")),
                messages=messages,
                metadata={"account": (conv.get("account") or {}).get("uuid")},
            )
        )
    return conversations

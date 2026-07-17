"""Importer for ChatGPT data exports (conversations.json).

Format: a JSON array of conversation objects with ``title``, epoch
``create_time``/``update_time`` and a ``mapping`` of message nodes forming
a tree. The active thread is reconstructed by walking parents up from
``current_node``.
"""

from __future__ import annotations

from typing import Any

from mirrormind.model import Conversation, Message, iso_utc

SOURCE = "chatgpt"


def matches(data: Any) -> bool:
    if not isinstance(data, list) or not data:
        return False
    first = data[0]
    return isinstance(first, dict) and "mapping" in first and "title" in first


def _node_text(message: dict[str, Any]) -> str:
    content = message.get("content") or {}
    ctype = content.get("content_type")
    if ctype == "text":
        return "\n\n".join(p for p in content.get("parts") or [] if isinstance(p, str))
    if ctype == "code":
        lang = content.get("language") or ""
        return f"```{lang}\n{content.get('text', '')}\n```"
    if ctype == "multimodal_text":
        return "\n\n".join(p for p in content.get("parts") or [] if isinstance(p, str))
    return ""


def _active_thread(conv: dict[str, Any]) -> list[dict[str, Any]]:
    """Walk from current_node to the root, returning nodes in order."""
    mapping = conv.get("mapping") or {}
    node_id = conv.get("current_node")
    if node_id is None:  # fall back to any leaf (node that is nobody's parent)
        parents = {n.get("parent") for n in mapping.values()}
        leaves = [nid for nid in mapping if nid not in parents]
        node_id = leaves[0] if leaves else None
    chain = []
    while node_id and node_id in mapping:
        node = mapping[node_id]
        chain.append(node)
        node_id = node.get("parent")
    chain.reverse()
    return chain


def parse(data: Any) -> list[Conversation]:
    conversations = []
    for conv in data:
        messages = []
        for node in _active_thread(conv):
            msg = node.get("message")
            if not msg:
                continue
            if (msg.get("metadata") or {}).get("is_visually_hidden_from_conversation"):
                continue
            text = _node_text(msg)
            if not text.strip():
                continue
            role = (msg.get("author") or {}).get("role", "tool")
            messages.append(
                Message(
                    role=role,
                    text=text,
                    timestamp=iso_utc(msg.get("create_time")),
                    model=(msg.get("metadata") or {}).get("model_slug"),
                )
            )
        conversations.append(
            Conversation(
                id=conv.get("conversation_id") or conv.get("id") or "",
                title=conv.get("title") or "Untitled",
                source=SOURCE,
                created_at=iso_utc(conv.get("create_time")),
                updated_at=iso_utc(conv.get("update_time")),
                messages=messages,
                metadata={"default_model_slug": conv.get("default_model_slug")},
            )
        )
    return conversations

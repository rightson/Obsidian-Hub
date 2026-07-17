"""Canonical conversation schema.

Every importer normalizes its source format into these types; every
pipeline stage and sink consumes only these types.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

ROLES = ("user", "assistant", "system", "tool")


@dataclass
class Message:
    role: str
    text: str
    timestamp: str | None = None
    model: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.role not in ROLES:
            self.metadata.setdefault("original_role", self.role)
            self.role = "tool"

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "text": self.text,
            "timestamp": self.timestamp,
            "model": self.model,
            "metadata": self.metadata,
        }


@dataclass
class Conversation:
    id: str
    title: str
    source: str
    created_at: str | None = None
    updated_at: str | None = None
    messages: list[Message] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def short_id(self) -> str:
        return re.sub(r"[^0-9a-zA-Z]", "", self.id)[:8] or "unknown"

    @property
    def slug(self) -> str:
        return slugify(self.title)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "source": self.source,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "messages": [m.to_dict() for m in self.messages],
            "metadata": self.metadata,
        }


def slugify(text: str, max_length: int = 60) -> str:
    """Filesystem-safe slug. Keeps CJK characters (Obsidian handles them fine)."""
    text = unicodedata.normalize("NFKC", text).strip().lower()
    text = re.sub(r"[\\/:*?\"<>|#^\[\]]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-{2,}", "-", text).strip("-")
    return text[:max_length].strip("-") or "untitled"


def iso_utc(value: Any) -> str | None:
    """Best-effort conversion of epoch seconds or ISO strings to ISO-8601 UTC."""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc).isoformat()
    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return value
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    return None

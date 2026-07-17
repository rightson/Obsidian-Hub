"""Render a canonical Conversation as Markdown with YAML frontmatter."""

from __future__ import annotations

from mirrormind.model import Conversation

_ROLE_HEADINGS = {
    "user": "## 🧑 User",
    "assistant": "## 🤖 Assistant",
    "system": "## ⚙️ System",
    "tool": "## 🔧 Tool",
}


def _yaml_scalar(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value)
    if text == "" or text != text.strip() or any(c in text for c in ":#{}[]&*!|>'\"%@`,"):
        return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return text


def frontmatter(fields: dict[str, object]) -> str:
    lines = ["---"]
    for key, value in fields.items():
        if isinstance(value, (list, tuple)):
            lines.append(f"{key}: [{', '.join(_yaml_scalar(v) for v in value)}]")
        else:
            lines.append(f"{key}: {_yaml_scalar(value)}")
    lines.append("---")
    return "\n".join(lines)


def render(conv: Conversation, tags: list[str] | None = None, related: list[str] | None = None) -> str:
    """Render one conversation to a full Markdown document."""
    fields: dict[str, object] = {
        "id": conv.id,
        "title": conv.title,
        "source": conv.source,
        "created": conv.created_at,
        "updated": conv.updated_at,
        "messages": len(conv.messages),
        "tags": tags or [],
        "type": "ai-conversation",
    }
    parts = [frontmatter(fields), "", f"# {conv.title}", ""]
    for msg in conv.messages:
        heading = _ROLE_HEADINGS.get(msg.role, f"## {msg.role}")
        if msg.timestamp:
            heading += f" — {msg.timestamp}"
        parts.append(heading)
        parts.append("")
        parts.append(msg.text.strip())
        parts.append("")
    if related:
        parts.append("## Related")
        parts.append("")
        parts.extend(f"- [[{name}]]" for name in related)
        parts.append("")
    return "\n".join(parts).rstrip() + "\n"

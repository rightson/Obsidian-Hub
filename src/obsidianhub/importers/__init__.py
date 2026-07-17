"""Importer registry and format auto-detection."""

from __future__ import annotations

import json
from pathlib import Path

from obsidianhub.model import Conversation
from obsidianhub.importers import chatgpt, claude, generic

IMPORTERS = {
    "claude": claude,
    "chatgpt": chatgpt,
    "generic": generic,
}


def detect_source(data: object) -> str | None:
    """Return the importer name whose format matches ``data``, or None."""
    for name, mod in IMPORTERS.items():
        if mod.matches(data):
            return name
    return None


def load_file(path: Path, source: str = "auto") -> list[Conversation]:
    """Parse an export file into canonical conversations."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if source == "auto":
        detected = detect_source(data)
        if detected is None:
            raise ValueError(
                f"Could not detect export format of {path}. "
                f"Pass --source explicitly (one of: {', '.join(IMPORTERS)})."
            )
        source = detected
    if source not in IMPORTERS:
        raise ValueError(f"Unknown source '{source}' (available: {', '.join(IMPORTERS)})")
    return IMPORTERS[source].parse(data)

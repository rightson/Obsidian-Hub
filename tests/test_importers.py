import json
from pathlib import Path

import pytest

from obsidianllmhub import importers

FIXTURES = Path(__file__).parent / "fixtures"


def test_claude_import_and_autodetect():
    convs = importers.load_file(FIXTURES / "claude_export.json")
    assert len(convs) == 2
    conv = convs[0]
    assert conv.source == "claude"
    assert conv.title == "Designing a Redis rate limiter"
    assert conv.id == "a1b2c3d4-1111-2222-3333-444455556666"
    roles = [m.role for m in conv.messages]
    assert roles == ["user", "assistant", "user"]
    assert "sliding window" in conv.messages[1].text
    assert conv.created_at.startswith("2026-07-01T09:12:00")


def test_chatgpt_import_walks_active_thread():
    convs = importers.load_file(FIXTURES / "chatgpt_export.json")
    assert len(convs) == 1
    conv = convs[0]
    assert conv.source == "chatgpt"
    # hidden system node is skipped; order is user then assistant
    assert [m.role for m in conv.messages] == ["user", "assistant"]
    assert conv.messages[1].model == "gpt-4o"
    assert conv.created_at.startswith("2025-07-01")


def test_generic_import(tmp_path):
    payload = {
        "id": "gen-1",
        "title": "Local chat",
        "source": "open-webui",
        "created_at": 1751356800,
        "messages": [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "text": "hello!"},
        ],
    }
    path = tmp_path / "generic.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    convs = importers.load_file(path)
    assert convs[0].source == "open-webui"
    assert [m.text for m in convs[0].messages] == ["hi", "hello!"]


def test_unknown_format_raises(tmp_path):
    path = tmp_path / "junk.json"
    path.write_text('{"foo": 1}', encoding="utf-8")
    with pytest.raises(ValueError, match="detect"):
        importers.load_file(path)

import json
import subprocess
from pathlib import Path

from obsidianllmhub.cli import main

FIXTURES = Path(__file__).parent / "fixtures"


def test_init_import_status_roundtrip(tmp_path, capsys):
    vault = tmp_path / "vault"
    assert main(["init", str(vault)]) == 0
    assert (vault / "obsidianllmhub.toml").exists()

    assert main([
        "import", str(FIXTURES / "claude_export.json"),
        str(FIXTURES / "chatgpt_export.json"),
        "--vault", str(vault), "--no-git",
    ]) == 0
    out = capsys.readouterr().out
    assert "3 new" in out

    notes = list(vault.glob("conversations/**/*.md"))
    assert len(notes) == 3
    claude_note = next(n for n in notes if "rate-limiter" in n.name)
    content = claude_note.read_text(encoding="utf-8")
    assert content.startswith("---\n")
    assert "source: claude" in content
    # the two Redis conversations share tags, so they should link to each other
    assert "## Related" in content

    # index + chunks generated
    assert "Obsidian LLMHub" in (vault / "index.md").read_text(encoding="utf-8")
    assert len(list(vault.glob(".obsidianllmhub/chunks/*.jsonl"))) == 3

    # second import is a no-op (idempotent)
    assert main([
        "import", str(FIXTURES / "claude_export.json"),
        str(FIXTURES / "chatgpt_export.json"),
        "--vault", str(vault), "--no-git",
    ]) == 0
    out = capsys.readouterr().out
    assert "0 new, 0 updated, 3 unchanged" in out

    assert main(["status", "--vault", str(vault)]) == 0
    out = capsys.readouterr().out
    assert "Conversations: 3" in out
    assert "claude: 2" in out


def test_updated_conversation_rewrites_file(tmp_path, capsys):
    vault = tmp_path / "vault"
    main(["init", str(vault)])
    data = json.loads((FIXTURES / "claude_export.json").read_text(encoding="utf-8"))

    export = tmp_path / "conversations.json"
    export.write_text(json.dumps(data), encoding="utf-8")
    main(["import", str(export), "--vault", str(vault), "--no-git"])
    capsys.readouterr()

    data[0]["chat_messages"].append(
        {"sender": "assistant", "text": "Token buckets refill at a fixed rate.", "content": []}
    )
    export.write_text(json.dumps(data), encoding="utf-8")
    main(["import", str(export), "--vault", str(vault), "--no-git"])
    out = capsys.readouterr().out
    assert "1 updated" in out
    note = next(vault.glob("conversations/claude/**/designing*.md"))
    assert "Token buckets" in note.read_text(encoding="utf-8")


def test_git_autocommit(tmp_path, capsys):
    vault = tmp_path / "vault"
    main(["init", str(vault)])
    subprocess.run(["git", "init", "-q", str(vault)], check=True)
    subprocess.run(["git", "-C", str(vault), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(vault), "config", "user.name", "t"], check=True)

    main(["import", str(FIXTURES / "claude_export.json"), "--vault", str(vault)])
    out = capsys.readouterr().out
    assert "Committed as" in out
    log = subprocess.run(
        ["git", "-C", str(vault), "log", "--oneline"], capture_output=True, text=True
    ).stdout
    assert "obsidian-llmhub: sync 2 new" in log

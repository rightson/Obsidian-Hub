"""Git sink: auto-commit vault changes so history reads like a changelog."""

from __future__ import annotations

import subprocess
from pathlib import Path


def _git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, text=True
    )


def is_repo(root: Path) -> bool:
    result = _git(root, "rev-parse", "--is-inside-work-tree")
    return result.returncode == 0 and result.stdout.strip() == "true"


def commit_changes(root: Path, message: str) -> str | None:
    """Stage the vault and commit. Returns the commit hash, or None if no changes."""
    if not is_repo(root):
        return None
    _git(root, "add", "-A", ".")
    if not _git(root, "status", "--porcelain").stdout.strip():
        return None
    result = _git(root, "commit", "-m", message)
    if result.returncode != 0:
        raise RuntimeError(f"git commit failed: {result.stderr.strip()}")
    return _git(root, "rev-parse", "--short", "HEAD").stdout.strip()

"""Obsidian Hub command-line interface.

    obsidian-hub init <vault>
    obsidian-hub import <export.json ...> --vault <vault> [--source auto] [--no-git]
    obsidian-hub status --vault <vault>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from obsidianhub import __version__, importers
from obsidianhub.sinks import git
from obsidianhub.sinks.filesystem import Vault


def _cmd_init(args: argparse.Namespace) -> int:
    vault = Vault(Path(args.vault))
    vault.init()
    print(f"Initialized Obsidian Hub vault at {vault.root}")
    if not git.is_repo(vault.root):
        print("Tip: run `git init` in the vault to get version-controlled history.")
    return 0


def _collect_files(paths: list[str]) -> list[Path]:
    files: list[Path] = []
    for raw in paths:
        p = Path(raw)
        if p.is_dir():
            files.extend(sorted(p.glob("**/conversations.json")))
        elif p.exists():
            files.append(p)
        else:
            print(f"warning: {p} not found, skipping", file=sys.stderr)
    return files


def _cmd_import(args: argparse.Namespace) -> int:
    vault = Vault(Path(args.vault))
    if not vault.exists:
        vault.init()

    files = _collect_files(args.exports)
    if not files:
        print("error: no export files found", file=sys.stderr)
        return 1

    conversations = []
    for path in files:
        try:
            parsed = importers.load_file(path, source=args.source)
        except (ValueError, json.JSONDecodeError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print(f"{path}: {len(parsed)} conversations ({parsed[0].source if parsed else '-'})")
        conversations.extend(parsed)

    report = vault.sync(conversations)
    print(f"Sync complete: {report.summary()}")

    if report.changed and not args.no_git:
        commit = git.commit_changes(
            vault.root,
            f"obsidian-hub: sync {len(report.new)} new, {len(report.updated)} updated",
        )
        if commit:
            print(f"Committed as {commit}")
    return 0


def _cmd_status(args: argparse.Namespace) -> int:
    vault = Vault(Path(args.vault))
    if not vault.exists:
        print(f"No vault at {vault.root} (run `obsidian-hub init` first)", file=sys.stderr)
        return 1
    state = json.loads(vault.state_path.read_text(encoding="utf-8"))
    by_source: dict[str, int] = {}
    for entry in state.values():
        by_source[entry.get("source", "?")] = by_source.get(entry.get("source", "?"), 0) + 1
    print(f"Vault: {vault.root}")
    print(f"Conversations: {len(state)}")
    for source, count in sorted(by_source.items()):
        print(f"  {source}: {count}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="obsidian-hub",
        description="Git for AI conversations - mirror your AI chats into a knowledge vault.",
    )
    parser.add_argument("--version", action="version", version=f"obsidian-hub {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="create a new vault")
    p_init.add_argument("vault", help="path of the vault directory to create")
    p_init.set_defaults(func=_cmd_init)

    p_import = sub.add_parser("import", help="import AI conversation exports into the vault")
    p_import.add_argument("exports", nargs="+", help="export file(s) or directories to scan")
    p_import.add_argument("--vault", default=".", help="vault directory (default: cwd)")
    p_import.add_argument(
        "--source",
        default="auto",
        choices=["auto", *importers.IMPORTERS],
        help="export format (default: auto-detect)",
    )
    p_import.add_argument("--no-git", action="store_true", help="skip git auto-commit")
    p_import.set_defaults(func=_cmd_import)

    p_status = sub.add_parser("status", help="show vault statistics")
    p_status.add_argument("--vault", default=".", help="vault directory (default: cwd)")
    p_status.set_defaults(func=_cmd_status)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

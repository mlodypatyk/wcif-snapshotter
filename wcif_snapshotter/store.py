"""Local git-backed storage of WCIF snapshots.

Each competition gets its own git repository under ``repos/<competition_id>/``.
The latest WCIF is always written to ``wcif.json`` and committed when it changed.
"""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from . import config as config_mod

WCIF_FILENAME = "wcif.json"


def repo_dir(competition_id: str) -> Path:
    return config_mod.repo_dir(competition_id)


def _run_git(competition_id: str, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(repo_dir(competition_id)), *args],
        capture_output=True,
        text=True,
        check=check,
    )


def ensure_repo(competition_id: str) -> Path:
    directory = repo_dir(competition_id)
    directory.mkdir(parents=True, exist_ok=True)
    git_dir = directory / ".git"
    if not git_dir.exists():
        subprocess.run(
            ["git", "init", "-q", str(directory)],
            check=True,
            capture_output=True,
            text=True,
        )
    return directory


def snapshot(competition_id: str, data: dict[str, Any]) -> tuple[bool, Optional[str]]:
    """Write the latest WCIF and commit it. Returns (changed, commit_sha)."""
    directory = ensure_repo(competition_id)
    wcif_path = directory / WCIF_FILENAME

    old_content = wcif_path.read_bytes() if wcif_path.exists() else None
    new_content = json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8")
    new_content += b"\n"

    if old_content == new_content:
        return False, None

    wcif_path.write_bytes(new_content)
    _run_git(competition_id, "add", WCIF_FILENAME)

    name = data.get("name") or competition_id
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    _run_git(competition_id, "commit", "-q", "-m", f"snapshot {timestamp} ({name})")

    sha = _run_git(competition_id, "rev-parse", "--short", "HEAD").stdout.strip()
    return True, sha


def history(competition_id: str) -> list[str]:
    ensure_repo(competition_id)
    proc = _run_git(competition_id, "log", "--oneline", check=False)
    lines = [line for line in proc.stdout.splitlines() if line.strip()]
    return lines


def show(competition_id: str, rev: str) -> str:
    ensure_repo(competition_id)
    proc = _run_git(competition_id, "show", f"{rev}:{WCIF_FILENAME}")
    return proc.stdout


def restore(competition_id: str, rev: str, out: Path) -> None:
    content = show(competition_id, rev)
    out.write_text(content, encoding="utf-8")

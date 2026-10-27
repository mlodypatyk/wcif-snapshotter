"""Configuration and local paths.

Everything is stored under ``~/.wcif-snapshotter/``:

    ~/.wcif-snapshotter/
        config.json                     # OAuth app credentials + tokens
        repos/<competition_id>/         # one git repo per competition
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional

APP_DIR_NAME = ".wcif-snapshotter"

DEFAULT_REDIRECT_URI = "http://127.0.0.1:8080/callback"
DEFAULT_SCOPES = "public manage_competitions"

AUTHORIZE_URL = "https://www.worldcubeassociation.org/oauth/authorize"
TOKEN_URL = "https://www.worldcubeassociation.org/oauth/token"
API_BASE = "https://www.worldcubeassociation.org/api/v0"


def app_dir() -> Path:
    """Return (and lazily create) the app data directory."""
    path = Path.home() / APP_DIR_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def config_path() -> Path:
    return app_dir() / "config.json"


def repos_dir() -> Path:
    path = app_dir() / "repos"
    path.mkdir(parents=True, exist_ok=True)
    return path


def repo_dir(competition_id: str) -> Path:
    return repos_dir() / competition_id


def load_config() -> dict[str, Any]:
    path = config_path()
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def save_config(config: dict[str, Any]) -> None:
    path = config_path()
    with path.open("w", encoding="utf-8") as fh:
        json.dump(config, fh, indent=2, sort_keys=True)


def get_client_id(config: dict[str, Any]) -> str:
    return os.environ.get("WCIF_CLIENT_ID") or config.get("client_id", "")


def get_client_secret(config: dict[str, Any]) -> str:
    return os.environ.get("WCIF_CLIENT_SECRET") or config.get("client_secret", "")


def get_redirect_uri(config: dict[str, Any]) -> str:
    return os.environ.get("WCIF_REDIRECT_URI") or config.get(
        "redirect_uri", DEFAULT_REDIRECT_URI
    )


def get_scopes(config: dict[str, Any]) -> str:
    return os.environ.get("WCIF_SCOPES") or config.get("scopes", DEFAULT_SCOPES)

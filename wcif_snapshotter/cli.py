"""Command-line interface for wcif-snapshotter."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Optional

import typer

from . import api, auth, config as config_mod, diff as diff_mod, store

app = typer.Typer(
    name="wcif-snapshotter",
    help="Snapshot private WCA competition WCIF data locally and browse history.",
    no_args_is_help=True,
)


@app.command()
def configure(
    client_id: str = typer.Option(..., "--client-id", prompt="WCA OAuth client ID"),
    client_secret: str = typer.Option(
        ..., "--client-secret", prompt=True, hide_input=True, prompt_required=True
    ),
    redirect_uri: str = typer.Option(
        config_mod.DEFAULT_REDIRECT_URI, "--redirect-uri"
    ),
    scopes: str = typer.Option(config_mod.DEFAULT_SCOPES, "--scopes"),
) -> None:
    """Store OAuth application credentials in config.json."""
    config = config_mod.load_config()
    config["client_id"] = client_id
    config["client_secret"] = client_secret
    config["redirect_uri"] = redirect_uri
    config["scopes"] = scopes
    config_mod.save_config(config)
    typer.echo(f"Saved configuration to {config_mod.config_path()}")


@app.command()
def login() -> None:
    """Authorize with WCA and store access/refresh tokens."""
    config = config_mod.load_config()
    auth.login(config)


def _snapshot(competition_id: str, public: bool) -> None:
    config = config_mod.load_config()
    access_token = "" if public else auth.get_access_token(config)
    data = api.fetch_wcif(competition_id, access_token, public=public)
    changed, sha = store.snapshot(competition_id, data)
    if changed:
        typer.echo(f"Snapshot committed as {sha}: {data.get('name', competition_id)}")
    else:
        typer.echo("No changes since the previous snapshot.")


@app.command()
def snapshot(competition_id: str, public: bool = typer.Option(False, "--public")) -> None:
    """Fetch the WCIF for a competition and commit a snapshot."""
    _snapshot(competition_id, public)


@app.command()
def watch(
    competition_id: str,
    interval: int = typer.Option(60, "--interval", help="Seconds between snapshots."),
    public: bool = typer.Option(False, "--public"),
) -> None:
    """Snapshot repeatedly every --interval seconds until interrupted (Ctrl-C)."""
    typer.echo(f"Watching '{competition_id}' every {interval}s. Press Ctrl-C to stop.")
    try:
        while True:
            _snapshot(competition_id, public)
            time.sleep(interval)
    except KeyboardInterrupt:
        typer.echo("\nStopped.")


@app.command()
def history(competition_id: str) -> None:
    """List saved snapshots for a competition."""
    entries = store.history(competition_id)
    if not entries:
        typer.echo("No snapshots yet.")
        return
    for entry in entries:
        typer.echo(entry)


@app.command()
def show(
    competition_id: str,
    rev: str = typer.Option("HEAD", "--at", help="Git revision to show."),
) -> None:
    """Print the WCIF JSON at a given revision."""
    content = store.show(competition_id, rev)
    data = json.loads(content)
    typer.echo(json.dumps(data, indent=2, ensure_ascii=False))


@app.command()
def diff(competition_id: str, old_rev: str, new_rev: str) -> None:
    """Diff two snapshots by git revision (e.g. HEAD~1 HEAD)."""
    old_data = json.loads(store.show(competition_id, old_rev))
    new_data = json.loads(store.show(competition_id, new_rev))
    changes = diff_mod.diff(old_data, new_data)
    if not changes:
        typer.echo("No differences.")
        return
    for change in changes:
        typer.echo(change)


@app.command()
def restore(
    competition_id: str,
    rev: str,
    out: Optional[Path] = typer.Option(None, "--out", help="Path to write the WCIF to."),
    patch: bool = typer.Option(False, "--patch", help="PATCH the snapshot back to the WCA server."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip the confirmation prompt."),
) -> None:
    """Write a previous snapshot to a file, or PATCH it back to the server."""
    if patch and out is not None:
        raise typer.BadParameter("Use either --patch or --out, not both.")
    if not patch and out is None:
        raise typer.BadParameter("Provide either --patch or --out.")

    if patch:
        _patch_restore(competition_id, rev, yes)
    else:
        store.restore(competition_id, rev, out)
        typer.echo(f"Wrote WCIF at '{rev}' to {out}")


def _patch_restore(competition_id: str, rev: str, yes: bool) -> None:
    data = json.loads(store.show(competition_id, rev))
    config = config_mod.load_config()
    access_token = auth.get_access_token(config)

    if not yes:
        typer.echo(
            f"PATCH snapshot '{rev}' of '{competition_id}' to "
            f"worldcubeassociation.org? [y/N]",
            nl=False,
        )
        answer = typer.prompt("", default="N", show_default=False).strip().lower()
        if answer not in ("y", "yes"):
            typer.echo("Aborted.")
            raise typer.Exit()

    result = api.patch_wcif(competition_id, access_token, data)
    typer.echo(result.get("status", "PATCH complete."))


if __name__ == "__main__":
    app()

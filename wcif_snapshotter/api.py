"""Fetching WCIF data from the WCA v0 API."""

from __future__ import annotations

from typing import Any

import httpx

from . import config as config_mod


def _wcif_url(competition_id: str, public: bool = False) -> str:
    suffix = "/public" if public else ""
    return f"{config_mod.API_BASE}/competitions/{competition_id}/wcif{suffix}"


def fetch_wcif(competition_id: str, access_token: str, public: bool = False) -> dict[str, Any]:
    headers = {} if public else {"Authorization": f"Bearer {access_token}"}
    resp = httpx.get(_wcif_url(competition_id, public), headers=headers)
    if resp.status_code == 401:
        raise RuntimeError("Authentication failed (401). Try `wcif-snapshotter login` again.")
    if resp.status_code == 403:
        raise RuntimeError(
            "Access forbidden (403). You are likely not a manager (organizer/delegate) "
            f"of competition '{competition_id}'. Try `--public` for the public WCIF instead."
        )
    if resp.status_code == 404:
        raise RuntimeError(f"Competition '{competition_id}' not found (404).")
    resp.raise_for_status()
    return resp.json()


def patch_wcif(competition_id: str, access_token: str, data: dict[str, Any]) -> dict[str, Any]:
    """PATCH a full WCIF document back to the WCA server.

    The endpoint applies the entire document (it is not a JSON merge patch),
    so `data` must be a complete WCIF object as returned by the authorized GET.
    """
    resp = httpx.patch(
        _wcif_url(competition_id),
        headers={"Authorization": f"Bearer {access_token}"},
        json=data,
    )
    if resp.status_code == 401:
        raise RuntimeError("Authentication failed (401). Try `wcif-snapshotter login` again.")
    if resp.status_code == 403:
        raise RuntimeError(
            "Access forbidden (403). You must be a manager (organizer/delegate) of "
            f"'{competition_id}', and if results have been submitted only admins may edit."
        )
    if resp.status_code == 400:
        body = resp.text.strip()
        raise RuntimeError(f"Server rejected the WCIF (400): {body}")
    if resp.status_code == 404:
        raise RuntimeError(f"Competition '{competition_id}' not found (404).")
    resp.raise_for_status()
    return resp.json()

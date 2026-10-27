"""WCA OAuth2 (authorization code) flow and token management.

The WCA token endpoint returns an access token valid for ``expires_in`` seconds
(typically 7200) plus a ``refresh_token``. Both are stored in ``config.json``
alongside the OAuth application credentials.
"""

from __future__ import annotations

import time
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

import httpx

from . import config as config_mod

_TOKEN_EXPIRY_SLACK = 60  # refresh a little before actual expiry


class OAuthError(Exception):
    pass


def _token_data(config: dict[str, Any]) -> dict[str, Any]:
    return config.get("token", {})


def _save_token(config: dict[str, Any], token: dict[str, Any]) -> None:
    config["token"] = token
    config_mod.save_config(config)


def has_token(config: dict[str, Any]) -> bool:
    return bool(_token_data(config).get("access_token"))


def get_access_token(config: dict[str, Any]) -> str:
    """Return a valid access token, refreshing it if necessary."""
    token = _token_data(config)
    access_token = token.get("access_token")
    if not access_token:
        raise OAuthError("Not logged in. Run `wcif-snapshotter login` first.")
    expires_at = token.get("expires_at", 0)
    if expires_at and time.time() >= expires_at - _TOKEN_EXPIRY_SLACK:
        refresh_access_token(config)
        token = _token_data(config)
        access_token = token.get("access_token")
    return access_token


def refresh_access_token(config: dict[str, Any]) -> None:
    """Exchange the stored refresh token for a new access token."""
    token = _token_data(config)
    refresh_token = token.get("refresh_token")
    if not refresh_token:
        raise OAuthError("No refresh token available. Run `wcif-snapshotter login` again.")

    resp = httpx.post(
        config_mod.TOKEN_URL,
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": config_mod.get_client_id(config),
            "client_secret": config_mod.get_client_secret(config),
        },
    )
    _handle_token_response(resp, config)


def _handle_token_response(resp: httpx.Response, config: dict[str, Any]) -> None:
    if resp.status_code != 200:
        raise OAuthError(
            f"Token request failed ({resp.status_code}): {resp.text.strip()}"
        )
    data = resp.json()
    if "access_token" not in data:
        raise OAuthError(f"Unexpected token response: {data}")

    token = _token_data(config)
    token["access_token"] = data["access_token"]
    if "refresh_token" in data:
        token["refresh_token"] = data["refresh_token"]
    token["expires_at"] = time.time() + int(data.get("expires_in", 7200))
    token["scope"] = data.get("scope", token.get("scope"))
    _save_token(config, token)


def build_authorize_url(config: dict[str, Any]) -> str:
    params = {
        "client_id": config_mod.get_client_id(config),
        "redirect_uri": config_mod.get_redirect_uri(config),
        "response_type": "code",
        "scope": config_mod.get_scopes(config),
    }
    return config_mod.AUTHORIZE_URL + "?" + urllib.parse.urlencode(params)


def _parse_redirect_uri(redirect_uri: str) -> tuple[str, int, str]:
    parsed = urllib.parse.urlparse(redirect_uri)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 8080
    path = parsed.path or "/"
    return host, port, path


def login(config: dict[str, Any]) -> None:
    """Run the browser-based authorization code flow and store tokens."""
    client_id = config_mod.get_client_id(config)
    client_secret = config_mod.get_client_secret(config)
    if not client_id or not client_secret:
        raise OAuthError(
            "Missing client_id/client_secret. Set them with "
            "`wcif-snapshotter configure`, or via WCIF_CLIENT_ID/WCIF_CLIENT_SECRET."
        )

    redirect_uri = config_mod.get_redirect_uri(config)
    host, port, path = _parse_redirect_uri(redirect_uri)

    captured: dict[str, str] = {}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            query = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(query)
            if "code" in params:
                captured["code"] = params["code"][0]
            elif "error" in params:
                captured["error"] = params["error"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                b"<html><body><h3>Authorization complete.</h3>"
                b"<p>You can close this window and return to your terminal.</p>"
                b"</body></html>"
            )

        def log_message(self, *args):  # silence request logs
            pass

    server = HTTPServer((host, port), Handler)
    url = build_authorize_url(config)
    print(f"Opening your browser to authorize with WCA:\n{url}\n")
    webbrowser.open(url)

    server.timeout = 1
    while "code" not in captured and "error" not in captured:
        server.handle_request()

    if "error" in captured:
        raise OAuthError(f"Authorization was denied: {captured['error']}")

    code = captured["code"]
    resp = httpx.post(
        config_mod.TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
        },
    )
    _handle_token_response(resp, config)
    print("Logged in and tokens stored in config.json.")

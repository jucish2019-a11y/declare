"""Runtime resolution of the multiplayer server URL.

Players can override the server without rebuilding the client:

  Browser:  https://your.site/declare/?server=wss%3A%2F%2Fother.fly.dev
            (URL-encode the wss:// form)
  Desktop:  $env:DECLARE_ONLINE_URL = "wss://other.fly.dev" ; python main.py

Priority order:
  1. Browser ?server= query param          (overrides everything)
  2. $DECLARE_ONLINE_URL env var           (desktop only)
  3. PRODUCTION_ONLINE_URL constant below  (baked at build time)
  4. ws://127.0.0.1:8765                   (local dev fallback)
"""
from __future__ import annotations

import os
import sys


# ----------------------------------------------------------------- PRODUCTION
# After deploying the server (e.g. `cd server && fly deploy`), set this to your
# production WebSocket URL and rebuild the web client (`pygbag main.py`). Once
# set, players who open the GitHub Pages link don't need to do anything — they
# auto-connect here. Override per-session by appending ?server=... to the URL.
PRODUCTION_ONLINE_URL = ""


_LOCAL_FALLBACK = "ws://127.0.0.1:8765"


def _query_param_server() -> str:
    """Read ?server= from the page's URL when running in pygbag."""
    try:
        from js import window  # type: ignore
        from urllib.parse import unquote
    except Exception:
        return ""
    try:
        search = str(window.location.search or "")
    except Exception:
        return ""
    for part in search.lstrip("?").split("&"):
        if not part:
            continue
        k, _, v = part.partition("=")
        if k == "server" and v:
            try:
                return unquote(v)
            except Exception:
                return v
    return ""


def resolve_url() -> str:
    """Pick the server URL using the documented priority order."""
    if sys.platform == "emscripten":
        url = _query_param_server()
        if url:
            return url
        if PRODUCTION_ONLINE_URL:
            return PRODUCTION_ONLINE_URL
        return _LOCAL_FALLBACK

    # Desktop / native
    env_url = os.environ.get("DECLARE_ONLINE_URL", "").strip()
    if env_url:
        return env_url
    if PRODUCTION_ONLINE_URL:
        return PRODUCTION_ONLINE_URL
    return _LOCAL_FALLBACK


def url_label(url: str) -> str:
    """Short human-friendly tag (host[:port]) for the status line."""
    try:
        if "://" in url:
            host = url.split("://", 1)[1]
        else:
            host = url
        host = host.split("/", 1)[0]
        return host
    except Exception:
        return url

"""Synchronous client API over an asynchronous WebSocket transport.

Pygame's main loop is synchronous. Online messages flow through two thread-safe
queues (outgoing strings, incoming dicts) and a backend worker that owns the
WebSocket. Two backends ship: `desktop_ws` (Python `websockets` package on a
background thread) and `browser_ws` (the browser's native WebSocket via pygbag
JS interop). Selection is deferred to connect time so pygbag's static analyzer
doesn't try to process the desktop-only `threading`/`websockets` imports.
"""
from __future__ import annotations

import json
import queue
import sys
from typing import Optional


STATUS_IDLE = "idle"
STATUS_CONNECTING = "connecting"
STATUS_CONNECTED = "connected"
STATUS_CLOSED = "closed"
STATUS_ERROR = "error"


class OnlineClient:
    """Single shared instance per process. Owns one WebSocket at a time."""

    def __init__(self):
        self._outgoing: "queue.Queue[str]" = queue.Queue()
        self._incoming: "queue.Queue[dict]" = queue.Queue()
        self._status: str = STATUS_IDLE
        self._error: str = ""
        self._backend = None  # backend handle (thread/task)

    # ------------------------------------------------------------- status

    @property
    def status(self) -> str:
        return self._status

    @property
    def error(self) -> str:
        return self._error

    @property
    def is_connected(self) -> bool:
        return self._status == STATUS_CONNECTED

    def _set_status(self, status: str, error: str = "") -> None:
        self._status = status
        if error:
            self._error = error

    # ------------------------------------------------------------- send/recv

    def send(self, msg: dict) -> None:
        if self._status in (STATUS_CLOSED, STATUS_ERROR, STATUS_IDLE):
            return
        try:
            self._outgoing.put_nowait(json.dumps(msg, separators=(",", ":")))
        except queue.Full:
            pass

    def poll(self) -> list[dict]:
        out: list[dict] = []
        try:
            while True:
                out.append(self._incoming.get_nowait())
        except queue.Empty:
            pass
        return out

    # ------------------------------------------------------------- lifecycle

    def connect(self, url: str) -> None:
        if self._status in (STATUS_CONNECTING, STATUS_CONNECTED):
            return
        self._set_status(STATUS_CONNECTING, error="")
        backend_fn = _ensure_backend()
        self._backend = backend_fn(self, url, self._outgoing, self._incoming)

    def close(self) -> None:
        if self._status in (STATUS_CLOSED, STATUS_IDLE):
            return
        try:
            if self._backend is not None and hasattr(self._backend, "close"):
                self._backend.close()
        except Exception:
            pass
        self._set_status(STATUS_CLOSED)


# ----------------------------------------------------------------- backends

def _get_backend():
    if sys.platform == "emscripten":
        from online.browser_ws import _open_ws
        return _open_ws
    else:
        from online.desktop_ws import _open_ws
        return _open_ws

_open_ws_impl = None

def _ensure_backend():
    global _open_ws_impl
    if _open_ws_impl is None:
        _open_ws_impl = _get_backend()
    return _open_ws_impl


# Module-level singleton — pygame code grabs it via online.client.client().
_client_singleton: Optional[OnlineClient] = None


def client() -> OnlineClient:
    global _client_singleton
    if _client_singleton is None:
        _client_singleton = OnlineClient()
    return _client_singleton

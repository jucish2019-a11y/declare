"""Browser WebSocket backend (pygbag / emscripten).

Uses the browser's native `WebSocket` JS object via pygbag's `platform.window`
JS interop. Pygame's main loop on emscripten is already async-friendly, so a
small `asyncio.create_task` keeps the bridge running.

Note: this module is only imported when `sys.platform == "emscripten"`. The
desktop path goes through `desktop_ws.py` and never touches `js`/`platform`.
"""
from __future__ import annotations

import asyncio
import json
import queue


class _BrowserBackend:
    def __init__(self, client, url: str, outgoing: queue.Queue, incoming: queue.Queue):
        self.client = client
        self.url = url
        self.outgoing = outgoing
        self.incoming = incoming
        self._closed = False
        self._ws = None
        # In emscripten, the running pygame loop is already an asyncio task.
        # Schedule our worker on the same loop.
        try:
            asyncio.get_event_loop().create_task(self._main())
        except RuntimeError:
            # Fallback if a loop isn't ready yet.
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.create_task(self._main())

    def close(self) -> None:
        self._closed = True
        try:
            if self._ws is not None:
                self._ws.close()
        except Exception:
            pass

    async def _main(self) -> None:
        try:
            import platform  # pygbag's platform module exposes window/JS
            from js import WebSocket  # type: ignore
        except Exception as e:
            self.client._set_status("error", f"browser ws unavailable: {e}")
            return

        try:
            self._ws = WebSocket.new(self.url)
        except Exception as e:
            self.client._set_status("error", f"new WebSocket failed: {e}")
            return

        # State + queue plumbing through JS event handlers.
        def on_open(_):
            self.client._set_status("connected")

        def on_message(evt):
            try:
                data = evt.data
                obj = json.loads(data if isinstance(data, str) else str(data))
                self.incoming.put(obj)
            except Exception:
                pass

        def on_error(_):
            self.client._set_status("error", "websocket error")

        def on_close(_):
            self.client._set_status("closed")

        # Bind handlers — pygbag exposes JS callable construction via createProxy.
        try:
            from pyodide.ffi import create_proxy  # type: ignore
            self._ws.onopen = create_proxy(on_open)
            self._ws.onmessage = create_proxy(on_message)
            self._ws.onerror = create_proxy(on_error)
            self._ws.onclose = create_proxy(on_close)
        except Exception:
            # Fall back to direct assignment (older pygbag may auto-proxy).
            self._ws.onopen = on_open
            self._ws.onmessage = on_message
            self._ws.onerror = on_error
            self._ws.onclose = on_close

        # Outgoing-queue drain loop.
        while not self._closed:
            try:
                msg = self.outgoing.get_nowait()
            except queue.Empty:
                await asyncio.sleep(0.05)
                continue
            try:
                self._ws.send(msg)
            except Exception as e:
                self.client._set_status("error", f"send failed: {e}")
                return


def _open_ws(client, url: str, outgoing: queue.Queue, incoming: queue.Queue):
    return _BrowserBackend(client, url, outgoing, incoming)

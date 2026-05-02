"""Desktop WebSocket backend.

Runs `websockets.connect` on a background thread, bridging incoming messages to
the OnlineClient's `_incoming` queue and forwarding outgoing messages from
`_outgoing`.
"""
from __future__ import annotations

import asyncio
import json
import logging
import queue
import threading


log = logging.getLogger(__name__)


class _DesktopBackend:
    def __init__(self, client, url: str, outgoing: queue.Queue, incoming: queue.Queue):
        self.client = client
        self.url = url
        self.outgoing = outgoing
        self.incoming = incoming
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name="declare-ws", daemon=True)
        self._thread.start()

    def close(self) -> None:
        self._stop.set()

    def _run(self) -> None:
        try:
            asyncio.run(self._main())
        except Exception as e:
            log.warning("desktop ws thread crashed: %s", e)
            self.client._set_status("error", str(e))

    async def _main(self) -> None:
        try:
            import websockets
        except ImportError:
            self.client._set_status("error", "websockets package not installed")
            return
        try:
            async with websockets.connect(self.url, ping_interval=25,
                                           ping_timeout=20) as ws:
                self.client._set_status("connected")
                send_task = asyncio.create_task(self._sender(ws))
                recv_task = asyncio.create_task(self._receiver(ws))
                stop_task = asyncio.create_task(self._stop_watcher())
                done, pending = await asyncio.wait(
                    {send_task, recv_task, stop_task},
                    return_when=asyncio.FIRST_COMPLETED,
                )
                for t in pending:
                    t.cancel()
        except Exception as e:
            log.warning("desktop ws connect failed: %s", e)
            self.client._set_status("error", str(e))
        else:
            self.client._set_status("closed")

    async def _sender(self, ws) -> None:
        loop = asyncio.get_event_loop()
        while not self._stop.is_set():
            try:
                # Bridge the blocking queue.get to the event loop.
                msg = await loop.run_in_executor(None, _get_with_timeout,
                                                  self.outgoing, 0.1)
            except queue.Empty:
                continue
            if msg is None:
                continue
            await ws.send(msg)

    async def _receiver(self, ws) -> None:
        async for raw in ws:
            try:
                obj = json.loads(raw if isinstance(raw, str) else raw.decode("utf-8"))
            except Exception:
                continue
            self.incoming.put(obj)

    async def _stop_watcher(self) -> None:
        while not self._stop.is_set():
            await asyncio.sleep(0.1)


def _get_with_timeout(q: queue.Queue, timeout: float):
    try:
        return q.get(timeout=timeout)
    except queue.Empty:
        return None


def _open_ws(client, url: str, outgoing: queue.Queue, incoming: queue.Queue):
    return _DesktopBackend(client, url, outgoing, incoming)

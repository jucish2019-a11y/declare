"""Server entrypoint.

Stub `pygame` *before* importing game/* modules — game_manager.py uses
`pygame.time.get_ticks()` on the seen-swap path even though pygame isn't
imported at the top of that file. The shim only provides what game/* touches.
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys
import time
import types


def _install_pygame_shim() -> None:
    if "pygame" in sys.modules:
        return
    fake = types.ModuleType("pygame")
    time_mod = types.ModuleType("pygame.time")
    _start = time.monotonic()

    def get_ticks() -> int:
        return int((time.monotonic() - _start) * 1000)

    time_mod.get_ticks = get_ticks
    fake.time = time_mod
    sys.modules["pygame"] = fake
    sys.modules["pygame.time"] = time_mod


_install_pygame_shim()


# --- now safe to import game-side modules
from server import protocol as proto
from server.lobby import lobby
from server.room import Connection, Room


HOST = os.environ.get("DECLARE_HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8080"))
HELLO_TIMEOUT = 5.0


log = logging.getLogger("declare.server")


# ----------------------------------------------------------------- handler

async def handle_connection(ws):
    conn = Connection(ws=ws)
    try:
        # Hello handshake — first message must identify the client.
        try:
            raw = await asyncio.wait_for(ws.recv(), timeout=HELLO_TIMEOUT)
        except asyncio.TimeoutError:
            await conn.send_error(proto.ERR_BAD_HELLO, "Handshake timeout")
            return
        try:
            msg = proto.decode(raw)
        except Exception:
            await conn.send_error(proto.ERR_BAD_HELLO, "Invalid hello")
            return
        if msg.get("type") != proto.HELLO:
            await conn.send_error(proto.ERR_BAD_HELLO, "Expected hello")
            return
        nickname = (msg.get("nickname") or "Player").strip()[:24] or "Player"
        client_id = (msg.get("client_id") or "").strip()[:64]
        conn.nickname = nickname
        conn.client_id = client_id
        log.info("client connected: %s (%s)", nickname, client_id[:8])

        # Main message loop
        async for raw_msg in ws:
            try:
                msg = proto.decode(raw_msg)
            except Exception:
                await conn.send_error(proto.ERR_BAD_PAYLOAD, "Bad JSON")
                continue
            await dispatch(conn, msg)
    except Exception as e:
        log.exception("connection crashed: %s", e)
    finally:
        await on_disconnect(conn)


async def dispatch(conn: Connection, msg: dict) -> None:
    kind = msg.get("type")
    if kind == proto.PING:
        await conn.send({"type": proto.PONG})
        return
    if kind == proto.CREATE_ROOM:
        await create_room(conn, msg)
        return
    if kind == proto.JOIN_ROOM:
        await join_room(conn, msg)
        return
    if kind == proto.LEAVE_ROOM:
        room = lobby().get(conn.room_code) if conn.room_code else None
        if room:
            await room.leave(conn, lobby())
        conn.room_code = ""
        conn.seat = -1
        return
    if kind == proto.START_GAME:
        room = lobby().get(conn.room_code)
        if room is None:
            await conn.send_error(proto.ERR_NO_ROOM)
            return
        await room.start(conn)
        return
    # All other types are in-game actions; route to the room.
    room = lobby().get(conn.room_code)
    if room is None:
        await conn.send_error(proto.ERR_NO_ROOM, "Not in a room")
        return
    await room.dispatch(conn, msg)


async def on_disconnect(conn: Connection) -> None:
    if not conn.room_code:
        return
    room = lobby().get(conn.room_code)
    if room is None:
        return
    await room.leave(conn, lobby())


# ----------------------------------------------------------------- room ops

async def create_room(conn: Connection, msg: dict) -> None:
    if conn.room_code:
        # auto-leave previous room
        prev = lobby().get(conn.room_code)
        if prev:
            await prev.leave(conn, lobby())
        conn.room_code = ""
        conn.seat = -1
    code = lobby().generate_code()
    room = Room(code, conn, msg)
    lobby().register(room)
    await room.welcome_host(conn)


async def join_room(conn: Connection, msg: dict) -> None:
    if conn.room_code:
        prev = lobby().get(conn.room_code)
        if prev:
            await prev.leave(conn, lobby())
        conn.room_code = ""
        conn.seat = -1
    code = (msg.get("code") or "").strip().upper()
    if not code:
        await conn.send_error(proto.ERR_BAD_PAYLOAD, "Missing code")
        return
    room = lobby().get(code)
    if room is None:
        await conn.send_error(proto.ERR_NO_ROOM, "Room not found")
        return
    await room.join(conn)


# ----------------------------------------------------------------- main

async def serve_forever() -> None:
    import websockets
    log.info("declare server listening on %s:%s", HOST, PORT)
    # Single endpoint at "/" — clients connect to ws://host:port/
    async with websockets.serve(handle_connection, HOST, PORT,
                                 ping_interval=25, ping_timeout=20):
        await asyncio.Future()  # run until cancelled


def main():
    logging.basicConfig(
        level=os.environ.get("DECLARE_LOG", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    asyncio.run(serve_forever())


if __name__ == "__main__":
    main()

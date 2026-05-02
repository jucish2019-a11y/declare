"""Local smoke test: two simulated clients (one host + one joiner) play a
short game against AI-fill on a running server. Run this with the server
already up:

    PORT=8765 python -m server.server &
    PORT=8765 python -m server.smoke_test
"""
from __future__ import annotations

import asyncio
import json
import os
import sys

import websockets


URL = os.environ.get("DECLARE_URL", "ws://127.0.0.1:8765")


class Client:
    def __init__(self, label: str, nickname: str):
        self.label = label
        self.nickname = nickname
        self.ws = None
        self.seat = None
        self.code = None
        self.snapshot = None
        self.game_over_payload = None
        self._inbox: asyncio.Queue = asyncio.Queue()
        self._reader_task = None

    async def connect(self):
        self.ws = await websockets.connect(URL)
        self._reader_task = asyncio.create_task(self._reader())
        await self.send({"type": "hello", "nickname": self.nickname,
                          "client_id": f"smoke-{self.label}"})

    async def close(self):
        if self.ws:
            await self.ws.close()

    async def send(self, msg: dict):
        await self.ws.send(json.dumps(msg))

    async def _reader(self):
        try:
            async for raw in self.ws:
                msg = json.loads(raw)
                await self._inbox.put(msg)
        except Exception:
            pass

    async def expect(self, *types, timeout=5.0) -> dict:
        end = asyncio.get_event_loop().time() + timeout
        while True:
            remaining = end - asyncio.get_event_loop().time()
            if remaining <= 0:
                raise TimeoutError(f"{self.label} expected one of {types}")
            msg = await asyncio.wait_for(self._inbox.get(), timeout=remaining)
            if msg.get("type") == "state_snapshot":
                self.snapshot = msg
            if msg.get("type") == "game_over":
                self.game_over_payload = msg
            if msg.get("type") in types:
                return msg

    async def drain(self, max_seconds: float = 0.5):
        try:
            while True:
                msg = await asyncio.wait_for(self._inbox.get(), timeout=max_seconds)
                if msg.get("type") == "state_snapshot":
                    self.snapshot = msg
                if msg.get("type") == "game_over":
                    self.game_over_payload = msg
        except asyncio.TimeoutError:
            return


async def run() -> int:
    print(f"connecting to {URL}")
    host = Client("host", "Alice")
    joiner = Client("joiner", "Bob")
    await host.connect()
    await joiner.connect()

    # Host creates a 4-player room with AI fill.
    await host.send({
        "type": "create_room",
        "max_players": 4,
        "ai_fill": True,
        "hand_size": 4,
        "peek_count": 2,
        "reaction_window_seconds": 3.0,
    })
    welcome = await host.expect("welcome")
    code = welcome["code"]
    host.code = code
    host.seat = welcome["your_seat"]
    print(f"host welcomed: code={code} seat={host.seat}")
    assert host.seat == 0

    # Joiner joins.
    await joiner.send({"type": "join_room", "code": code})
    j_welcome = await joiner.expect("welcome")
    joiner.seat = j_welcome["your_seat"]
    joiner.code = code
    print(f"joiner welcomed: seat={joiner.seat}")
    assert joiner.seat == 1

    # Host gets a room_update reflecting the joiner.
    await host.expect("room_update")

    # Host starts the game.
    await host.send({"type": "start_game"})
    snap_h = await host.expect("state_snapshot")
    snap_j = await joiner.expect("state_snapshot")
    print(f"first snapshot: state={snap_h['state']}, "
          f"current_player={snap_h['current_player_index']}")
    assert snap_h["state"] in ("TURN_START", "DECIDE", "PEEK_PHASE")

    # Verify hidden info is hidden: each client's your_view should differ.
    h_hand = snap_h["your_view"]["hand"]
    j_hand = snap_j["your_view"]["hand"]
    print(f"host sees their hand: {h_hand}")
    print(f"joiner sees their hand: {j_hand}")
    # Bottom-2 peek means at least 2 cards are visible to each (peek_count=2).
    h_known = sum(1 for c in h_hand if c is not None)
    j_known = sum(1 for c in j_hand if c is not None)
    assert h_known >= 2, f"host known cards = {h_known}"
    assert j_known >= 2, f"joiner known cards = {j_known}"

    # Drive the game by playing as whichever human's turn it is.
    # AI seats 2 and 3 will play themselves on the server side.
    moves = 0
    max_moves = 60  # safety
    end = asyncio.get_event_loop().time() + 30.0
    while asyncio.get_event_loop().time() < end and moves < max_moves:
        # Take the most recent snapshots from both clients.
        for cli in (host, joiner):
            await cli.drain(0.2)
        # Whose turn is it?
        cur = host.snapshot["current_player_index"] if host.snapshot else None
        if cur is None:
            await asyncio.sleep(0.1)
            continue
        # If a reaction window is open and the human is eligible, just pass time.
        reaction = (host.snapshot or {}).get("reaction") or (joiner.snapshot or {}).get("reaction")
        if reaction:
            await asyncio.sleep(0.5)
            continue
        if cur == host.seat:
            await play_step(host)
            moves += 1
        elif cur == joiner.seat:
            await play_step(joiner)
            moves += 1
        else:
            # AI's turn — wait for the server.
            await asyncio.sleep(0.3)
        if (host.game_over_payload or joiner.game_over_payload):
            break

    await host.drain(1.0)
    await joiner.drain(1.0)

    if host.game_over_payload or joiner.game_over_payload:
        payload = host.game_over_payload or joiner.game_over_payload
        print(f"GAME OVER: winner_seat={payload.get('winner_seat')}, "
              f"scores={payload.get('scores')}")
    else:
        print(f"NOTE: game did not finish in time after {moves} human moves")

    await host.close()
    await joiner.close()
    return 0


async def play_step(cli: Client) -> None:
    """Make a simple move: if we haven't drawn, draw; otherwise discard."""
    snap = cli.snapshot
    if snap is None:
        return
    if not snap.get("has_drawn_this_turn"):
        await cli.send({"type": "draw"})
        await asyncio.wait_for(cli.expect("state_snapshot", "event"), timeout=3.0)
        # Drain a couple of follow-up messages.
        await cli.drain(0.2)
        return
    # We have a drawn card — discard it (simplest legal move).
    valid = snap.get("valid_actions", [])
    if "discard" in valid:
        await cli.send({"type": "action", "action": "discard", "details": {}})
    elif "declare" in valid:
        await cli.send({"type": "action", "action": "declare", "details": {}})
    await cli.drain(0.5)


if __name__ == "__main__":
    sys.exit(asyncio.run(run()))

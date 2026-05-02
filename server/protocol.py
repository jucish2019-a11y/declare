"""Wire protocol for the multiplayer server.

JSON over WebSocket. Every message is a dict with a top-level "type" key.
Server-bound types are CLIENT_*, client-bound types are SERVER_*.
"""
from __future__ import annotations

import json


# ---------------------------------------------------------------- client → server
HELLO = "hello"
CREATE_ROOM = "create_room"
JOIN_ROOM = "join_room"
LEAVE_ROOM = "leave_room"
START_GAME = "start_game"
ACTION = "action"
SELF_PAIR = "self_pair"
DRAW = "draw"
REACT_DROP_SELF = "react_drop_self"
REACT_DROP_OPPONENT = "react_drop_opponent"
END_REACTION = "end_reaction"
PING = "ping"

CLIENT_TYPES = {
    HELLO, CREATE_ROOM, JOIN_ROOM, LEAVE_ROOM, START_GAME,
    ACTION, SELF_PAIR, DRAW, REACT_DROP_SELF, REACT_DROP_OPPONENT,
    END_REACTION, PING,
}

# ---------------------------------------------------------------- server → client
WELCOME = "welcome"
ROOM_UPDATE = "room_update"
STATE_SNAPSHOT = "state_snapshot"
EVENT = "event"
GAME_OVER = "game_over"
ERROR = "error"
PONG = "pong"


# ---------------------------------------------------------------- error codes
ERR_BAD_HELLO = "bad_hello"
ERR_NO_ROOM = "no_room"
ERR_ROOM_FULL = "room_full"
ERR_ROOM_STARTED = "room_started"
ERR_NOT_HOST = "not_host"
ERR_NOT_YOUR_TURN = "not_your_turn"
ERR_INVALID_ACTION = "invalid_action"
ERR_BAD_PAYLOAD = "bad_payload"
ERR_INTERNAL = "internal"


def encode(msg: dict) -> str:
    return json.dumps(msg, separators=(",", ":"))


def decode(raw: str | bytes) -> dict:
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    obj = json.loads(raw)
    if not isinstance(obj, dict) or "type" not in obj:
        raise ValueError("malformed message")
    return obj


def make_error(code: str, message: str = "") -> dict:
    return {"type": ERROR, "code": code, "message": message or code}

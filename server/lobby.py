"""In-memory room registry."""
from __future__ import annotations

import random
import string
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from server.room import Room


_ROOM_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no I/O/0/1


class Lobby:
    def __init__(self):
        self.rooms: dict[str, "Room"] = {}

    def generate_code(self) -> str:
        while True:
            code = "".join(random.choices(_ROOM_CODE_ALPHABET, k=4))
            if code not in self.rooms:
                return code

    def register(self, room: "Room") -> None:
        self.rooms[room.code] = room

    def get(self, code: str) -> "Room | None":
        return self.rooms.get(code.upper())

    def remove(self, code: str) -> None:
        self.rooms.pop(code, None)

    def stats(self) -> dict:
        return {
            "rooms": len(self.rooms),
            "players": sum(len(r.connections) for r in self.rooms.values()),
        }


_lobby = Lobby()


def lobby() -> Lobby:
    return _lobby

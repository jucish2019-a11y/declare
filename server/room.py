"""Room: a single online game instance.

Wraps the existing GameManager and brokers all state changes between connected
clients. Entirely asyncio-based; one Room per code, lifetime spans lobby +
gameplay + game-over.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Callable, Optional

from server import protocol as proto
from server.view import (
    state_for_player, game_over_payload, serialize_event,
)


log = logging.getLogger(__name__)


# ----------------------------------------------------------------- Connection

@dataclass
class Connection:
    ws: Any                       # websockets.WebSocketServerProtocol
    nickname: str = ""
    client_id: str = ""
    seat: int = -1
    room_code: str = ""

    async def send(self, msg: dict) -> None:
        try:
            await self.ws.send(proto.encode(msg))
        except Exception as e:
            log.debug("send to %s failed: %s", self.nickname, e)

    async def send_error(self, code: str, message: str = "") -> None:
        await self.send(proto.make_error(code, message))


# --------------------------------------------------------------------- Room

DEFAULT_MAX_PLAYERS = 4
MIN_MAX_PLAYERS = 2
MAX_MAX_PLAYERS = 4


class Room:
    def __init__(self, code: str, host: Connection, settings_dict: dict):
        self.code = code
        self.host_seat = 0
        # connections: seat (0..max-1) → Connection (humans) or None (AI/empty)
        self.max_players = max(MIN_MAX_PLAYERS,
                               min(MAX_MAX_PLAYERS,
                                   int(settings_dict.get("max_players", DEFAULT_MAX_PLAYERS))))
        self.connections: dict[int, Connection] = {0: host}
        host.seat = 0
        host.room_code = code

        self.ai_fill: bool = bool(settings_dict.get("ai_fill", True))
        self.hand_size: int = int(settings_dict.get("hand_size", 4))
        self.peek_count: int = int(settings_dict.get("peek_count", 2))
        self.reaction_window_seconds: float = float(
            settings_dict.get("reaction_window_seconds", 8.0))

        self.gm = None                                  # GameManager once started
        self.player_configs: list[dict] = []
        self.started: bool = False
        self.ended: bool = False
        self._reaction_timer_handle: Optional[asyncio.TimerHandle] = None
        self._ai_task: Optional[asyncio.Task] = None
        self._ai_callback: Optional[Callable] = None
        self._loop = asyncio.get_event_loop()

    # ------------------------------------------------------------- lobby

    def lobby_payload(self) -> dict:
        return {
            "code": self.code,
            "host_seat": self.host_seat,
            "max_players": self.max_players,
            "ai_fill": self.ai_fill,
            "hand_size": self.hand_size,
            "peek_count": self.peek_count,
            "reaction_window_seconds": self.reaction_window_seconds,
            "started": self.started,
            "players": [
                {"seat": s, "nickname": c.nickname}
                for s, c in sorted(self.connections.items())
            ],
        }

    async def broadcast_lobby(self) -> None:
        payload = {"type": proto.ROOM_UPDATE, **self.lobby_payload()}
        await asyncio.gather(*(c.send(payload) for c in self.connections.values()),
                              return_exceptions=True)

    async def join(self, conn: Connection) -> bool:
        if self.started:
            await conn.send_error(proto.ERR_ROOM_STARTED, "Game already started")
            return False
        if len(self.connections) >= self.max_players:
            await conn.send_error(proto.ERR_ROOM_FULL, "Room is full")
            return False
        next_seat = next(s for s in range(self.max_players)
                          if s not in self.connections)
        self.connections[next_seat] = conn
        conn.seat = next_seat
        conn.room_code = self.code
        await conn.send({
            "type": proto.WELCOME,
            "your_seat": next_seat,
            **self.lobby_payload(),
        })
        await self.broadcast_lobby()
        return True

    async def welcome_host(self, host: Connection) -> None:
        await host.send({
            "type": proto.WELCOME,
            "your_seat": 0,
            **self.lobby_payload(),
        })

    async def leave(self, conn: Connection, lobby) -> None:
        if conn.seat in self.connections:
            del self.connections[conn.seat]
        if not self.connections:
            self._cancel_timers()
            lobby.remove(self.code)
            return
        # Re-pick host: lowest remaining seat.
        if conn.seat == self.host_seat:
            self.host_seat = min(self.connections.keys())
        if self.started:
            # Phase 1: any disconnect mid-game ends the room.
            await self._abort_for_peer_left(conn.nickname)
            lobby.remove(self.code)
        else:
            await self.broadcast_lobby()

    async def _abort_for_peer_left(self, who: str) -> None:
        msg = proto.make_error("peer_left", f"{who or 'A player'} left the game")
        await asyncio.gather(*(c.send(msg) for c in self.connections.values()),
                              return_exceptions=True)
        self.ended = True
        self._cancel_timers()

    # ------------------------------------------------------------- start

    async def start(self, conn: Connection) -> None:
        if conn.seat != self.host_seat:
            await conn.send_error(proto.ERR_NOT_HOST, "Only the host can start")
            return
        if self.started:
            await conn.send_error(proto.ERR_ROOM_STARTED)
            return
        if not self.ai_fill and len(self.connections) < MIN_MAX_PLAYERS:
            await conn.send_error(proto.ERR_BAD_PAYLOAD,
                                   "Need at least 2 humans, or enable AI fill")
            return

        # Build player configs in seat order. Empty seats become AI when ai_fill is on.
        configs: list[dict] = []
        for seat in range(self.max_players):
            c = self.connections.get(seat)
            if c is not None:
                configs.append({
                    "name": c.nickname or f"P{seat+1}",
                    "is_human": True,
                    "difficulty": "medium",
                })
            elif self.ai_fill:
                configs.append({
                    "name": f"AI-{seat+1}",
                    "is_human": False,
                    "difficulty": "medium",
                })
        if len(configs) < MIN_MAX_PLAYERS:
            await conn.send_error(proto.ERR_BAD_PAYLOAD, "Not enough players")
            return
        self.player_configs = configs

        # Lazy import so the module can be loaded without pygame
        # (we shim pygame before this in server/__main__.py).
        from game.game_manager import GameManager
        from game.settings import GameSettings

        gs = GameSettings()
        gs.hand_size = self.hand_size
        gs.peek_count = self.peek_count
        gs.reaction_window_seconds = self.reaction_window_seconds
        # Disable client-side AI delay; server runs its own pacing.
        gs.ai_delay = 0.0

        self.gm = GameManager(configs, gs)
        self.gm.setup_game()
        # Skip the "peek phase" timer: reveal each player's bottom-N immediately.
        # Clients render the peek visually based on the snapshot's known_cards.
        self.gm.start_peek_phase()

        self.started = True
        await self.broadcast_state()

        # Kick off AI loop if any seats are AI.
        if any(not c["is_human"] for c in configs):
            self._ai_task = asyncio.create_task(self._ai_loop())

    # ------------------------------------------------------------- snapshots

    async def broadcast_state(self) -> None:
        if self.gm is None:
            return
        # Each connection gets a tailored snapshot.
        snapshots = [
            (c, state_for_player(self.gm, c.seat))
            for c in self.connections.values()
        ]
        await asyncio.gather(*(c.send(snap) for c, snap in snapshots),
                              return_exceptions=True)

    async def broadcast_event(self, action: str, details: dict | None,
                              result: dict | None, actor_seat: int) -> None:
        ev = serialize_event(action, details, result, actor_seat)
        await asyncio.gather(*(c.send(ev) for c in self.connections.values()),
                              return_exceptions=True)

    async def broadcast_game_over(self) -> None:
        payload = game_over_payload(self.gm)
        await asyncio.gather(*(c.send(payload) for c in self.connections.values()),
                              return_exceptions=True)
        self.ended = True

    # ------------------------------------------------------------- dispatch

    async def dispatch(self, conn: Connection, msg: dict) -> None:
        if not self.started or self.gm is None or self.ended:
            await conn.send_error(proto.ERR_INVALID_ACTION, "Game not running")
            return
        try:
            await self._dispatch_inner(conn, msg)
        except Exception as e:
            log.exception("dispatch error: %s", e)
            await conn.send_error(proto.ERR_INTERNAL, str(e))

    async def _dispatch_inner(self, conn: Connection, msg: dict) -> None:
        kind = msg.get("type")
        gm = self.gm

        # During a reaction window, eligible non-source seats may react.
        if kind in (proto.REACT_DROP_SELF, proto.REACT_DROP_OPPONENT, proto.END_REACTION):
            if not gm.reaction_pending:
                await conn.send_error(proto.ERR_INVALID_ACTION, "No reaction window open")
                return
            if conn.seat == gm.reaction_source_player:
                await conn.send_error(proto.ERR_INVALID_ACTION, "You cannot react to your own discard")
                return
            await self._handle_reaction(conn, kind, msg)
            return

        # All other actions require it to be your turn.
        if conn.seat != gm.current_player_index:
            await conn.send_error(proto.ERR_NOT_YOUR_TURN, "Not your turn")
            return

        if kind == proto.DRAW:
            if gm.has_drawn_this_turn:
                await conn.send_error(proto.ERR_INVALID_ACTION, "Already drew")
                return
            gm.draw_card()
            await self.broadcast_event("draw", None, {"drawn_rank": gm.drawn_card.rank}, conn.seat)
            await self.broadcast_state()
            return

        if kind == proto.SELF_PAIR:
            slot_a = int(msg.get("slot_a", -1))
            slot_b = int(msg.get("slot_b", -1))
            result = gm.execute_self_pair_action(slot_a, slot_b)
            if not result.get("success", True) is False:  # success or no explicit failure
                await self.broadcast_event("self_pair", {"slot_a": slot_a, "slot_b": slot_b},
                                           result, conn.seat)
            else:
                await conn.send_error(proto.ERR_INVALID_ACTION, result.get("reason", "bad self_pair"))
                return
            await self._after_action_check(conn.seat)
            return

        if kind == proto.ACTION:
            action = msg.get("action")
            details = self._materialize_details(action, msg.get("details") or {})
            valid_before = action  # for logging
            result = gm.execute_player_action(action, details)
            if isinstance(result, dict) and result.get("success") is False:
                await conn.send_error(proto.ERR_INVALID_ACTION,
                                       result.get("reason", "invalid action"))
                return
            await self.broadcast_event(action, details, result, conn.seat)

            # Discard / pair_own / pair_opponent → maybe open reaction window.
            opened = False
            if action in ("discard", "pair_own", "pair_opponent"):
                discarded = (gm.drawn_card if action == "discard"
                             else (gm._last_action_rank
                                   and self._card_for_rank(gm._last_action_rank)))
                # Use the actual card for the discard pile bookkeeping.
                target_card = gm.drawn_card
                opened = gm.start_reaction_window(
                    gm._last_action_rank or "",
                    conn.seat,
                    discarded_card=target_card,
                )
                if opened:
                    self._schedule_reaction_close()

            await self.broadcast_state()

            # Declaration → resolve immediately.
            if action == "declare":
                gm.resolve_declaration()
                await self.broadcast_state()
                await self.broadcast_game_over()
                return

            # Auto-end-turn for non-power, non-discard actions when not opening a reaction.
            if not opened and action in ("swap", "discard", "pair_own", "pair_opponent"):
                gm.end_turn()
                await self.broadcast_state()
                await self._maybe_end_game()
            elif action == "play_power":
                from game.game_manager import GameState
                power = (gm.drawn_card.power if gm.drawn_card else None)
                # skip / unseen_swap / seen_swap consume the whole turn.
                # peek_* leave the player at DECIDE so they can still
                # swap / discard / pair the drawn card with the new info.
                if power in ("skip", "unseen_swap", "seen_swap") or gm.state == GameState.TURN_END:
                    gm.end_turn()
                    await self.broadcast_state()
                    await self._maybe_end_game()
            return

        await conn.send_error(proto.ERR_INVALID_ACTION, f"Unknown action: {kind}")

    # ------------------------------------------------------------- helpers

    def _materialize_details(self, action: str, details: dict) -> dict:
        """Convert wire JSON details into the shape execute_player_action expects.

        The current player's drawn card lives on the server, so wire payloads
        only need to specify slot indices / target seats.
        """
        gm = self.gm
        out: dict = {"drawn_card": gm.drawn_card}
        if action == "swap":
            out["my_slot"] = int(details.get("my_slot", 0))
        elif action == "discard":
            pass  # only drawn_card needed
        elif action == "pair_own":
            out["player_slot"] = int(details.get("player_slot", 0))
        elif action == "pair_opponent":
            out["opponent_index"] = int(details.get("opponent_index", 0))
            out["opponent_slot"] = int(details.get("opponent_slot", 0))
            out["give_slot"] = int(details.get("give_slot", 0))
        elif action == "play_power":
            out["card"] = gm.drawn_card
            ti = details.get("target_info") or {}
            out["target_info"] = ti
        return out

    def _card_for_rank(self, rank: str):
        # Used only for log fallback; not relied on elsewhere.
        return None

    async def _handle_reaction(self, conn: Connection, kind: str, msg: dict) -> None:
        gm = self.gm
        if kind == proto.REACT_DROP_SELF:
            slot = int(msg.get("slot", -1))
            result = gm.attempt_reactive_drop_self(conn.seat, slot)
            await self.broadcast_event("react_drop_self", {"slot": slot},
                                       result, conn.seat)
        elif kind == proto.REACT_DROP_OPPONENT:
            opp_idx = int(msg.get("opp_idx", -1))
            opp_slot = int(msg.get("opp_slot", -1))
            give_slot = int(msg.get("give_slot", -1))
            result = gm.attempt_reactive_drop_opponent(
                conn.seat, opp_idx, opp_slot, give_slot)
            await self.broadcast_event(
                "react_drop_opponent",
                {"opp_idx": opp_idx, "opp_slot": opp_slot, "give_slot": give_slot},
                result, conn.seat)
        elif kind == proto.END_REACTION:
            # Voluntary pass-through (not strictly needed; server timer also closes).
            pass
        # If the reaction succeeded or someone wrong-dropped, we close the window
        # and proceed.
        await self._close_reaction_and_advance()

    async def _close_reaction_and_advance(self) -> None:
        gm = self.gm
        if not gm.reaction_pending:
            return
        self._cancel_reaction_timer()
        gm.end_reaction_window()
        await self.broadcast_state()
        gm.end_turn()
        await self.broadcast_state()
        await self._maybe_end_game()

    def _schedule_reaction_close(self) -> None:
        self._cancel_reaction_timer()
        delay = max(0.1, float(self.reaction_window_seconds))
        # Drive a server-authoritative countdown for snapshots.
        self.gm.reaction_timer = delay
        self._reaction_started = self._loop.time()
        self._reaction_timer_handle = self._loop.call_later(
            delay, lambda: asyncio.create_task(self._reaction_expired()))

    async def _reaction_expired(self) -> None:
        if not self.started or self.ended or self.gm is None:
            return
        if not self.gm.reaction_pending:
            return
        await self._close_reaction_and_advance()

    def _cancel_reaction_timer(self) -> None:
        if self._reaction_timer_handle is not None:
            self._reaction_timer_handle.cancel()
            self._reaction_timer_handle = None

    def _cancel_timers(self) -> None:
        self._cancel_reaction_timer()
        if self._ai_task is not None:
            self._ai_task.cancel()
            self._ai_task = None

    async def _after_action_check(self, actor_seat: int) -> None:
        await self.broadcast_state()
        await self._maybe_end_game()

    async def _maybe_end_game(self) -> None:
        gm = self.gm
        if gm.check_game_over():
            await self.broadcast_state()
            await self.broadcast_game_over()

    # ------------------------------------------------------------- AI loop

    async def _ai_loop(self) -> None:
        from server.ai_runner import tick_ai
        try:
            while not self.ended and self.started and self.gm is not None:
                acted = await tick_ai(self)
                if not acted:
                    await asyncio.sleep(0.2)
        except asyncio.CancelledError:
            pass
        except Exception:
            log.exception("AI loop crashed")

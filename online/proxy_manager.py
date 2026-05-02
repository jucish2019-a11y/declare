"""Local mirror of the server's GameManager.

The renderer expects a `GameManager` shape: `players[*].hand`, `known_cards`,
`drawn_card`, `state`, `current_player_index`, `deck.remaining`, etc. The
proxy keeps a real (but read-only) GameManager instance and rewrites it from
each `state_snapshot` the server sends. Action methods (`draw`, `discard`,
`swap`, etc.) serialize requests onto the WebSocket — no local state mutation
is allowed; the next snapshot will reflect the change.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from game.card import Card
from game.game_manager import GameManager, GameState
from game.settings import GameSettings


log = logging.getLogger(__name__)


def _faceless_card() -> Card:
    """Placeholder for cards the local player has no info about. The renderer
    paints face-down regardless of rank since face_up=False."""
    c = Card("A", "spade")
    c.face_up = False
    return c


def _card_from_dict(d: Any) -> Optional[Card]:
    if d is None:
        return None
    if isinstance(d, dict) and d.get("unknown"):
        return _faceless_card()
    if isinstance(d, dict) and "r" in d and "s" in d:
        c = Card(d["r"], d["s"])
        c.face_up = bool(d.get("u", False))
        return c
    return None


class ProxyGameManager:
    """Mirrors a server-authoritative GameManager into a renderer-friendly shape."""

    def __init__(self, lobby_payload: dict, your_seat: int):
        # Build player configs from the lobby's seat list, in seat order.
        # Missing seats become AI placeholders so player counts match the
        # server's view.
        max_players = int(lobby_payload.get("max_players", 4))
        seat_to_name: dict[int, str] = {}
        for entry in lobby_payload.get("players", []):
            seat_to_name[int(entry["seat"])] = entry.get("nickname", f"P{entry['seat']+1}")
        configs: list[dict] = []
        for s in range(max_players):
            if s in seat_to_name:
                configs.append({"name": seat_to_name[s], "is_human": True, "difficulty": "medium"})
            else:
                configs.append({"name": f"AI-{s+1}", "is_human": False, "difficulty": "medium"})
        gs = GameSettings()
        gs.hand_size = int(lobby_payload.get("hand_size", 4))
        gs.peek_count = int(lobby_payload.get("peek_count", 2))
        gs.reaction_window_seconds = float(lobby_payload.get("reaction_window_seconds", 8.0))

        self.gm = GameManager(configs, gs)
        # Initialize empty hands so the renderer can iterate.
        for p in self.gm.players:
            p.hand = [None] * gs.hand_size
            p.hand_size = gs.hand_size
        self.gm.deck = _DummyDeck(remaining=0)
        self.gm.discard_pile = []
        self.gm.state = GameState.MENU
        self.gm.current_player_index = 0

        self.your_seat: int = your_seat
        self.last_snapshot: Optional[dict] = None
        self.last_event: Optional[dict] = None
        self.game_over_payload: Optional[dict] = None
        self.online: bool = True

        # Server-driven reaction countdown anchor:
        self.reaction_remaining: float = 0.0

        # Pending action sink: assigned by main.py to the OnlineClient.send.
        self._send = None

    # ----------------------------------------------------- snapshot apply

    def apply_snapshot(self, snap: dict) -> None:
        self.last_snapshot = snap
        gm = self.gm
        # Top-level state
        try:
            gm.state = GameState[snap["state"]]
        except (KeyError, ValueError):
            gm.state = GameState.MENU
        gm.current_player_index = int(snap.get("current_player_index", 0))
        gm.round_number = int(snap.get("round_number", 0))
        gm.deck.remaining = int(snap.get("deck_remaining", 0))
        gm.has_drawn_this_turn = bool(snap.get("has_drawn_this_turn", False))
        gm.drawn_card = _card_from_dict(snap.get("drawn_card"))
        # Discard top
        top = _card_from_dict(snap.get("discard_top"))
        gm.discard_pile = [top] if top is not None else []
        # Game log tail (tail-only — wipe & reload)
        gm.game_log = list(snap.get("log_tail", []))

        # Players
        public = snap.get("players", [])
        for entry in public:
            seat = int(entry["seat"])
            if seat >= len(gm.players):
                continue
            p = gm.players[seat]
            p.name = entry.get("name", p.name)
            p.is_declaring = bool(entry.get("is_declaring", False))
            count = int(entry.get("card_count", 0))
            # Build a placeholder hand so the renderer can iterate.
            new_hand: list[Optional[Card]] = [None] * p.hand_size
            for i in range(min(count, p.hand_size)):
                new_hand[i] = _faceless_card()
            p.hand = new_hand
            p.known_cards = {}
            p.known_opponent_cards = {}

        # My (your_seat) view: replace hand + known with full info.
        me = gm.players[self.your_seat]
        view = snap.get("your_view") or {}
        wire_hand = view.get("hand") or []
        # Reconstruct hand: each entry is null|{"unknown":true}|{"r":...}.
        hand: list[Optional[Card]] = []
        for entry in wire_hand:
            if entry is None:
                hand.append(None)
            elif isinstance(entry, dict) and entry.get("unknown"):
                hand.append(_faceless_card())
            else:
                hand.append(_card_from_dict(entry))
        # Pad to hand_size
        while len(hand) < me.hand_size:
            hand.append(None)
        me.hand = hand[:me.hand_size]
        # Known cards (reconstructed)
        known: dict = {}
        for s_str, card_dict in (view.get("known_cards") or {}).items():
            try:
                slot = int(s_str)
            except (ValueError, TypeError):
                continue
            c = _card_from_dict(card_dict)
            if c is not None:
                known[slot] = c
        me.known_cards = known
        # Known opponents
        opp: dict = {}
        for k, card_dict in (view.get("known_opponents") or {}).items():
            try:
                seat_str, slot_str = k.split(".")
                opp[(int(seat_str), int(slot_str))] = _card_from_dict(card_dict)
            except Exception:
                continue
        me.known_opponent_cards = opp

        # Reaction state
        rxn = snap.get("reaction")
        if rxn:
            gm.reaction_pending = True
            gm.reaction_rank = rxn.get("rank")
            gm.reaction_source_player = rxn.get("source_seat")
            gm.reaction_timer = float(rxn.get("remaining_seconds", 0.0))
            self.reaction_remaining = gm.reaction_timer
            disc = _card_from_dict(rxn.get("discarded_card"))
            gm.reaction_card_discarded = disc
        else:
            gm.reaction_pending = False
            gm.reaction_rank = None
            gm.reaction_source_player = None
            gm.reaction_timer = 0.0
            self.reaction_remaining = 0.0

    def apply_event(self, ev: dict) -> None:
        self.last_event = ev

    def apply_game_over(self, payload: dict) -> None:
        self.game_over_payload = payload
        # Reflect into the underlying game_manager so the existing GameOverScreen
        # can read declaration_result.
        gm = self.gm
        gm.state = GameState.GAME_OVER
        winner_seat = payload.get("winner_seat")
        winner = gm.players[winner_seat] if (winner_seat is not None
                                              and 0 <= winner_seat < len(gm.players)) else None
        gm.declaration_result = {
            "winner": winner,
            "scores": {int(k): int(v) for k, v in (payload.get("scores") or {}).items()},
            "declarer_won": bool(payload.get("declarer_won", False)),
            "auto_win": bool(payload.get("auto_win", False)),
        }
        gm.winner = winner

    # ----------------------------------------------------- send actions

    def attach_send(self, send_fn) -> None:
        """Wire the OnlineClient.send into this proxy."""
        self._send = send_fn

    def _send_safe(self, msg: dict) -> None:
        if self._send is not None:
            self._send(msg)

    # The minimal action surface the main.py dispatch uses.
    def request_draw(self) -> None:
        self._send_safe({"type": "draw"})

    def request_action(self, action: str, details: dict | None = None) -> None:
        self._send_safe({"type": "action", "action": action, "details": details or {}})

    def request_self_pair(self, slot_a: int, slot_b: int) -> None:
        self._send_safe({"type": "self_pair", "slot_a": slot_a, "slot_b": slot_b})

    def request_react_drop_self(self, slot: int) -> None:
        self._send_safe({"type": "react_drop_self", "slot": slot})

    def request_react_drop_opponent(self, opp_idx: int, opp_slot: int, give_slot: int) -> None:
        self._send_safe({
            "type": "react_drop_opponent",
            "opp_idx": opp_idx,
            "opp_slot": opp_slot,
            "give_slot": give_slot,
        })

    # ----------------------------------------------------- proxies

    @property
    def players(self):
        return self.gm.players

    @property
    def state(self):
        return self.gm.state

    @property
    def current_player_index(self):
        return self.gm.current_player_index

    def current_player(self):
        return self.gm.current_player()


class _DummyDeck:
    def __init__(self, remaining: int = 0):
        self.remaining = remaining
        self.is_empty = remaining <= 0
        self.cards: list = []

    def draw(self):
        return None

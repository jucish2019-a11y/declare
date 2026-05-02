"""Per-player game state snapshots.

Each player gets a tailored dict that contains only what they're allowed to know:
their own hand, their own peek dictionaries, and public counts/state for everyone
else. Hidden cards never appear in a snapshot for a player who hasn't learned them.
"""
from __future__ import annotations

from typing import Any

from game.game_manager import GameManager, GameState
from game.rules import (
    can_react_to_discard, can_call_opponent_card, get_valid_actions,
)


def _public_player(p, gm: GameManager) -> dict:
    return {
        "seat": p.seat_index,
        "name": p.name,
        "is_human": p.is_human,
        "card_count": p.card_count,
        "is_declaring": p.is_declaring,
        "is_current": p.seat_index == gm.current_player_index,
    }


def _reaction_dict(gm: GameManager, seat: int) -> dict | None:
    if not gm.reaction_pending or gm.reaction_rank is None:
        return None
    me = gm.players[seat]
    self_slots: list[int] = []
    opp_targets: list[list[int]] = []
    if seat != gm.reaction_source_player:
        self_slots = can_react_to_discard(me, gm.reaction_rank)
        for opp in gm.players:
            if opp.seat_index == seat:
                continue
            slots = can_call_opponent_card(me, opp, gm.reaction_rank)
            for s in slots:
                opp_targets.append([opp.seat_index, s])
    remaining = max(0.0, float(gm.reaction_timer))
    return {
        "rank": gm.reaction_rank,
        "source_seat": gm.reaction_source_player,
        "remaining_seconds": remaining,
        "eligible_self_slots": self_slots,
        "eligible_opponent_slots": opp_targets,
        "discarded_card": (gm.reaction_card_discarded.to_dict()
                            if gm.reaction_card_discarded else None),
    }


def state_for_player(gm: GameManager, seat: int) -> dict:
    me = gm.players[seat]
    is_current = seat == gm.current_player_index
    return {
        "type": "state_snapshot",
        "state": gm.state.name,
        "current_player_index": gm.current_player_index,
        "your_seat": seat,
        "round_number": gm.round_number,
        "deck_remaining": gm.deck.remaining if gm.deck else 0,
        "discard_top": (gm.discard_pile[-1].to_dict()
                        if gm.discard_pile else None),
        "drawn_card": (gm.drawn_card.to_dict()
                       if (is_current and gm.drawn_card and gm.has_drawn_this_turn)
                       else None),
        "has_drawn_this_turn": is_current and gm.has_drawn_this_turn,
        "valid_actions": (get_valid_actions(me, gm.drawn_card, gm.has_drawn_this_turn)
                          if is_current else []),
        "reaction": _reaction_dict(gm, seat),
        "your_view": {
            "hand_size": me.hand_size,
            # null = empty slot, {"unknown": true} = card present but not known to
            # this player, full Card dict = card this player has learned.
            "hand": [
                (me.known_cards[i].to_dict() if i in me.known_cards
                 else {"unknown": True})
                if me.hand[i] is not None else None
                for i in range(me.hand_size)
            ],
            "known_cards": {str(s): c.to_dict()
                            for s, c in me.known_cards.items()},
            "known_opponents": {f"{ks[0]}.{ks[1]}": c.to_dict()
                                for ks, c in me.known_opponent_cards.items()},
        },
        "players": [_public_player(p, gm) for p in gm.players],
        "log_tail": list(gm.game_log[-12:]),
    }


def game_over_payload(gm: GameManager) -> dict:
    result = gm.declaration_result or {}
    winner = result.get("winner")
    return {
        "type": "game_over",
        "winner_seat": winner.seat_index if winner is not None else None,
        "scores": {str(s): v for s, v in (result.get("scores") or {}).items()},
        "declarer_won": bool(result.get("declarer_won", False)),
        "auto_win": bool(result.get("auto_win", False)),
    }


def serialize_event(action: str, details: dict[str, Any] | None,
                    result: dict[str, Any] | None,
                    actor_seat: int) -> dict:
    """Wrap an action result for the wire. Strips Card objects → dicts."""
    safe_result: dict[str, Any] = {}
    for k, v in (result or {}).items():
        if hasattr(v, "to_dict"):
            safe_result[k] = v.to_dict()
        elif isinstance(v, list):
            safe_result[k] = [
                x.to_dict() if hasattr(x, "to_dict") else x for x in v
            ]
        else:
            safe_result[k] = v
    return {
        "type": "event",
        "action": action,
        "actor_seat": actor_seat,
        "result": safe_result,
    }

"""Server-side AI tick.

AIs are first-class players with no Connection. The room's AI loop calls into
this module each tick; if an AI owes the game an action (it's their turn, or a
reaction is open and they can react), this dispatches one action and returns
True. Returning False means "nothing to do — sleep a bit."
"""
from __future__ import annotations

import asyncio
import random


# Per-step pacing — feels human-ish without being slow.
TURN_THINK_DELAY = (0.6, 1.4)
REACT_DELAY = (0.4, 1.2)


def _seat_player(room, seat: int):
    return room.gm.players[seat]


async def _broadcast_action(room, action: str, details: dict | None,
                            result: dict | None, seat: int) -> None:
    await room.broadcast_event(action, details, result, seat)
    await room.broadcast_state()


async def tick_ai(room) -> bool:
    """Run one AI step on the room's GameManager. Returns True if an action fired."""
    gm = room.gm
    if gm is None or room.ended:
        return False

    # 1) Reaction window open: any AI eligible to react?
    if gm.reaction_pending:
        return await _tick_reactions(room)

    # 2) Current player is AI?
    cur = gm.current_player()
    if cur.is_human:
        return False

    # If a connection ever has this seat (shouldn't, but defend), skip.
    if cur.seat_index in {c.seat for c in room.connections.values()}:
        return False

    return await _tick_turn(room, cur)


# ----------------------------------------------------------------- turn

async def _tick_turn(room, ai_player) -> bool:
    from game.ai import AIDecider
    from game.game_manager import GameState

    gm = room.gm
    decider = AIDecider(ai_player, {"players": gm.players})

    # Pre-draw: declare or draw.
    if not gm.has_drawn_this_turn:
        await asyncio.sleep(random.uniform(*TURN_THINK_DELAY))
        if decider.should_declare():
            ai_player.is_declaring = True
            gm.execute_player_action("declare", {})
            await _broadcast_action(room, "declare", None, {}, ai_player.seat_index)
            gm.resolve_declaration()
            await room.broadcast_state()
            await room.broadcast_game_over()
            return True
        gm.draw_card()
        await _broadcast_action(room, "draw",
                                None, {"drawn_rank": gm.drawn_card.rank},
                                ai_player.seat_index)
        return True

    # Post-draw: pick an action.
    await asyncio.sleep(random.uniform(*TURN_THINK_DELAY))
    drawn = gm.drawn_card
    decision = decider.choose_action(drawn)
    action = decision["action"]

    details: dict = {"drawn_card": drawn}
    if action == "pair_own":
        details["player_slot"] = decision["target_slot"]
    elif action == "pair_opponent":
        details["opponent_index"] = decision["target_player"]
        details["opponent_slot"] = _find_opp_slot_for_rank(
            ai_player, decision["target_player"], drawn.rank)
        details["give_slot"] = decision["target_slot"]
    elif action == "swap":
        details["my_slot"] = decision["target_slot"]
    elif action == "play_power":
        details["card"] = drawn
        details["target_info"] = _power_target_info(ai_player, drawn, gm)
    elif action == "discard":
        pass

    result = gm.execute_player_action(action, details)
    if isinstance(result, dict) and result.get("success") is False:
        # AI tried something illegal — fall back to discard.
        result = gm.execute_player_action("discard", {"drawn_card": drawn})
        action = "discard"

    await _broadcast_action(room, action, details, result, ai_player.seat_index)

    # Discard / pair → maybe open reaction window. Server-authoritative.
    opened = False
    if action in ("discard", "pair_own", "pair_opponent"):
        opened = gm.start_reaction_window(
            gm._last_action_rank or "",
            ai_player.seat_index,
            discarded_card=drawn,
        )
        if opened:
            room._schedule_reaction_close()

    if action == "play_power":
        power = drawn.power
        # AI: always end turn after play_power. After a peek, we currently
        # don't capitalize on the new info this turn (cheap & correct).
        if power in ("skip", "unseen_swap", "seen_swap", "peek_self", "peek_opponent"):
            # For peek powers, also drop the drawn card to clear the turn state.
            if power in ("peek_self", "peek_opponent"):
                gm.execute_player_action("discard", {"drawn_card": drawn})
                await _broadcast_action(room, "discard",
                                        {"drawn_card": drawn},
                                        {}, ai_player.seat_index)
                # Discard may open a reaction window.
                opened = gm.start_reaction_window(
                    gm._last_action_rank or "",
                    ai_player.seat_index,
                    discarded_card=drawn,
                )
                if opened:
                    room._schedule_reaction_close()
                    await room.broadcast_state()
                    return True
            gm.end_turn()
            await room.broadcast_state()
            if gm.check_game_over():
                await room.broadcast_state()
                await room.broadcast_game_over()
            return True

    if not opened and action in ("swap", "discard", "pair_own", "pair_opponent"):
        gm.end_turn()
        await room.broadcast_state()
        if gm.check_game_over():
            await room.broadcast_state()
            await room.broadcast_game_over()
    elif opened:
        await room.broadcast_state()

    return True


def _find_opp_slot_for_rank(ai_player, opp_idx: int, rank: str) -> int:
    for (p_idx, slot), card in ai_player.known_opponent_cards.items():
        if p_idx == opp_idx and card.rank == rank:
            return slot
    return 0


def _power_target_info(ai_player, drawn, gm) -> dict:
    power = drawn.power
    if power == "peek_self":
        unknown = [i for i in ai_player.get_active_slots()
                   if i not in ai_player.known_cards]
        slot = random.choice(unknown) if unknown else (ai_player.get_active_slots() or [0])[0]
        return {"slot": slot}
    if power == "peek_opponent":
        opp = _pick_opponent(ai_player, gm)
        opp_slots = opp.get_active_slots()
        unknown = [i for i in opp_slots
                   if (opp.seat_index, i) not in ai_player.known_opponent_cards]
        slot = random.choice(unknown) if unknown else (opp_slots[0] if opp_slots else 0)
        return {"player_index": opp.seat_index, "slot": slot}
    if power == "skip":
        return {}
    if power in ("unseen_swap", "seen_swap"):
        my_slot = _ai_worst_slot(ai_player)
        opp = _pick_opponent(ai_player, gm)
        opp_slots = opp.get_active_slots()
        their_slot = opp_slots[0] if opp_slots else 0
        # Prefer an opponent slot we know is low-value, if any.
        for s in opp_slots:
            card = ai_player.known_opponent_cards.get((opp.seat_index, s))
            if card is not None and card.value <= 3:
                their_slot = s
                break
        return {
            "my_slot": my_slot,
            "target_player": opp.seat_index,
            "their_slot": their_slot,
        }
    return {}


def _pick_opponent(ai_player, gm):
    opponents = [p for p in gm.players if p.seat_index != ai_player.seat_index]
    return random.choice(opponents) if opponents else gm.players[0]


def _ai_worst_slot(ai_player) -> int:
    active = ai_player.get_active_slots()
    if not active:
        return 0
    best_slot = active[0]
    best_value = -1
    for s in active:
        if s in ai_player.known_cards:
            v = ai_player.known_cards[s].value
        else:
            v = 7  # mid estimate for unknown
        if v > best_value:
            best_value = v
            best_slot = s
    return best_slot


# ----------------------------------------------------------------- reaction

async def _tick_reactions(room) -> bool:
    from game.ai import AIDecider

    gm = room.gm
    if gm.reaction_source_player is None:
        return False
    rank = gm.reaction_rank or ""
    if not rank:
        return False

    # Find AIs eligible to react (not the source seat).
    ai_seats = [p.seat_index for p in gm.players
                if not p.is_human
                and p.seat_index != gm.reaction_source_player
                and p.seat_index not in {c.seat for c in room.connections.values()}]
    if not ai_seats:
        return False

    # Tiny delay so the human sees the discard before any AI snaps.
    await asyncio.sleep(random.uniform(*REACT_DELAY))

    for seat in ai_seats:
        if not gm.reaction_pending:
            return True
        ai = gm.players[seat]
        decider = AIDecider(ai, {"players": gm.players})
        decision = decider.should_react_to_discard(rank)
        if not decision:
            continue
        if decision["type"] == "react_drop_self":
            slot = decision["slot"]
            result = gm.attempt_reactive_drop_self(seat, slot)
            await room.broadcast_event("react_drop_self", {"slot": slot}, result, seat)
        else:
            opp_idx = decision["opponent_index"]
            opp_slot = decision["opponent_slot"]
            give_slot = decision["give_slot"]
            result = gm.attempt_reactive_drop_opponent(seat, opp_idx, opp_slot, give_slot)
            await room.broadcast_event("react_drop_opponent",
                                       {"opp_idx": opp_idx, "opp_slot": opp_slot,
                                        "give_slot": give_slot},
                                       result, seat)
        await room._close_reaction_and_advance()
        return True

    return False

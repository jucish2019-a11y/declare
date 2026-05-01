from __future__ import annotations
from enum import Enum
from typing import Callable

from config import (
    HAND_SIZE, MAX_PAIR_STACK, PEEK_REVEAL_SECONDS, POWER_LABELS,
    DEFAULT_REACTION_WINDOW_SECONDS, SWAP_REVEAL_SECONDS, AI_REACTION_DELAY,
)
from game.card import Card, Deck
from game.player import Player, HumanPlayer, AIPlayer
from game.rules import (
    RulesEngine, get_valid_actions, resolve_declare, resolve_power,
    has_zero_cards, calculate_score, can_self_pair, can_react_to_discard,
    can_call_opponent_card, validate_reactive_drop, execute_reactive_drop_self,
    execute_reactive_drop_opponent, execute_wrong_drop_penalty, execute_self_pair,
)


class GameState(Enum):
    MENU = "menu"
    SETUP = "setup"
    PEEK_PHASE = "peek_phase"
    TURN_START = "turn_start"
    DRAW = "draw"
    DECIDE = "decide"
    POWER_RESOLVE = "power_resolve"
    PAIR_CHECK = "pair_check"
    TURN_END = "turn_end"
    RESOLVE_DECLARE = "resolve_declare"
    REACTION_WINDOW = "reaction_window"
    GAME_OVER = "game_over"


class GameManager:
    def __init__(self, player_configs: list[dict], game_settings=None):
        from game.settings import GameSettings
        self.settings = game_settings if game_settings is not None else GameSettings()
        self.players: list[Player] = []
        for config in player_configs:
            if config["is_human"]:
                self.players.append(HumanPlayer(config["name"], len(self.players), self.settings.hand_size))
            else:
                difficulty = config.get("difficulty", "medium")
                p = AIPlayer(config["name"], len(self.players), difficulty, self.settings.hand_size)
                self.players.append(p)
                self.settings.ai_difficulties[p.seat_index] = difficulty
        self.deck: Deck = None
        self.discard_pile: list[Card] = []
        self.rules_engine: RulesEngine = None
        self.state: GameState = GameState.MENU
        self.current_player_index: int = 0
        self.drawn_card: Card | None = None
        self.has_drawn_this_turn: bool = False
        self.drawn_card_resolved: bool = False
        self.skip_next: bool = False
        self.round_number: int = 0
        self.game_log: list[str] = []
        self.winner: Player | None = None
        self.peek_timer: float = 0
        self.peek_reveal: dict | None = None
        self.declaration_result: dict | None = None

        self.reaction_rank: str | None = None
        self.reaction_source_player: int | None = None
        self.reaction_timer: float = 0
        self.reaction_responded: bool = False
        self.reaction_card_discarded: Card | None = None
        self.self_pair_pending: bool = False

        self.reaction_pending: bool = False
        self.reaction_resolved: bool = False
        self.reaction_result_callback: Callable | None = None
        self.reaction_ai_resolved: bool = False
        self._reaction_timer_expired: bool = False
        self.reaction_elapsed: float = 0.0

        self._last_action_rank: str | None = None
        self._last_action_type: str | None = None

    def setup_game(self):
        self.deck = Deck()
        self.discard_pile = []
        self.rules_engine = RulesEngine(self.players, self.deck, self.discard_pile)
        self.drawn_card_resolved = False
        hand_size = self.settings.hand_size
        for player in self.players:
            player.hand = [None] * hand_size
            player.hand_size = hand_size
            player.known_cards = {}
            player.known_opponent_cards = {}
            player.is_declaring = False
            player.received_card_slot = None
            player.received_card_until = 0
            for slot in range(hand_size):
                card = self.deck.draw()
                player.receive_card(card, slot)
        self.state = GameState.PEEK_PHASE
        self.current_player_index = 0
        self.round_number = 1

    def start_peek_phase(self):
        hand_size = self.settings.hand_size
        peek_count = self.settings.peek_count
        peek_slots = list(range(max(0, hand_size - peek_count), hand_size))
        for player in self.players:
            for slot in peek_slots:
                card = player.hand[slot]
                if card is not None:
                    player.known_cards[slot] = card
            player.has_peeked_initial = True
        self.state = GameState.TURN_START

    def current_player(self) -> Player:
        return self.players[self.current_player_index]

    def next_turn(self):
        self.current_player_index = (self.current_player_index + 1) % len(self.players)
        if self.skip_next:
            self.skip_next = False
            self.drawn_card_resolved = False
            self.current_player_index = (self.current_player_index + 1) % len(self.players)
        self.has_drawn_this_turn = False
        self.drawn_card = None
        if self.current_player().is_declaring:
            self.state = GameState.RESOLVE_DECLARE
        else:
            self.state = GameState.TURN_START

    def draw_card(self) -> Card:
        if self.deck.is_empty:
            self.deck.reshuffle(self.discard_pile)
            self.discard_pile.clear()
        self.drawn_card = self.deck.draw()
        self.drawn_card.face_up = True
        self.has_drawn_this_turn = True
        self.drawn_card_resolved = False
        self.state = GameState.DECIDE
        name = "You" if self.current_player().is_human else self.current_player().name
        self.game_log.append(f"{name} drew {self.drawn_card.display_name}")
        return self.drawn_card

    def execute_player_action(self, action: str, details: dict) -> dict:
        valid = get_valid_actions(self.current_player(), self.drawn_card, self.has_drawn_this_turn)
        if action not in valid and action != 'shuffle':
            return {"success": False, "reason": "invalid_action"}
        result = self.rules_engine.execute_action(self.current_player(), action, details)

        if action == "declare":
            self.current_player().is_declaring = True
            self.state = GameState.RESOLVE_DECLARE
        elif action == "play_power":
            card = details.get('card')
            power = card.power if card else None
            if power in ('peek_self', 'peek_opponent'):
                peeked_card = result.get('card')
                if power == 'peek_self':
                    self.peek_reveal = {
                        'card': peeked_card,
                        'slot': result.get('slot'),
                        'timer': PEEK_REVEAL_SECONDS,
                    }
                else:
                    self.peek_reveal = {
                        'card': peeked_card,
                        'player_index': result.get('player_index'),
                        'slot': result.get('slot'),
                        'timer': PEEK_REVEAL_SECONDS,
                    }
                self.state = GameState.DECIDE
            elif power == 'skip':
                self.state = GameState.TURN_END
            elif power in ('unseen_swap', 'seen_swap'):
                if power == 'seen_swap' and result.get('card_received'):
                    slot = result.get('their_slot')
                    target_idx = result.get('target_player')
                    target_player = next((p for p in self.players if p.seat_index == target_idx), None)
                    if target_player and slot is not None:
                        target_player.mark_received_card(slot, SWAP_REVEAL_SECONDS, pygame.time.get_ticks() / 1000.0)
                self.state = GameState.DECIDE
            else:
                self.state = GameState.DECIDE
        elif action in ("swap", "discard", "pair_own", "pair_opponent"):
            self._last_action_type = action
            self._last_action_rank = self.drawn_card.rank if self.drawn_card else None
            self.drawn_card_resolved = True
            self.state = GameState.DECIDE
        elif action == "shuffle":
            pass

        log_entry = self._format_log(action, details, result)
        self.game_log.append(log_entry)
        return result

    def execute_self_pair_action(self, slot_a: int, slot_b: int) -> dict:
        player = self.current_player()
        pairs = can_self_pair(player)
        if (slot_a, slot_b) not in pairs and (slot_b, slot_a) not in pairs:
            return {"success": False, "reason": "invalid_pair"}

        result = self.rules_engine.execute_action(player, 'self_pair', {
            'slot_a': slot_a,
            'slot_b': slot_b,
        })
        self.game_log.append(f"{'You' if player.is_human else player.name} self-paired cards")
        if self.check_game_over():
            return result
        return result

    def start_reaction_window(self, card_rank: str, source_player_index: int, discarded_card: Card = None, result_callback: Callable = None) -> bool:
        has_reactor = False
        for p in self.players:
            if p.seat_index == source_player_index:
                continue
            own_matches = can_react_to_discard(p, card_rank)
            if own_matches:
                has_reactor = True
                break
            for other in self.players:
                if other.seat_index == source_player_index or other.seat_index == p.seat_index:
                    continue
                opp_matches = can_call_opponent_card(p, other, card_rank)
                if opp_matches:
                    has_reactor = True
                    break
            if has_reactor:
                break

        if not has_reactor:
            return False

        self.reaction_rank = card_rank
        self.reaction_source_player = source_player_index
        self.reaction_timer = self.settings.reaction_window_seconds if hasattr(self.settings, 'reaction_window_seconds') else DEFAULT_REACTION_WINDOW_SECONDS
        self.reaction_responded = False
        self.reaction_ai_resolved = False
        self._reaction_timer_expired = False
        self.reaction_elapsed = 0.0
        self.reaction_card_discarded = discarded_card
        self.reaction_pending = True
        self.reaction_resolved = False
        self.reaction_result_callback = result_callback
        self.state = GameState.REACTION_WINDOW
        return True

    def attempt_reactive_drop_self(self, player_index: int, slot: int) -> dict:
        player = self.players[player_index]
        if not validate_reactive_drop(player, slot, self.reaction_rank):
            penalty_result = execute_wrong_drop_penalty(
                player, slot, self.players, self.deck
            )
            penalty_card = penalty_result.get('penalty_card')
            if penalty_card:
                self.game_log.append(f"{'You' if player.is_human else player.name} wrong drop! Drew penalty card")
            else:
                self.game_log.append(f"{'You' if player.is_human else player.name} wrong drop!")
            return {"success": False, "penalty": True, "result": penalty_result}

        result = execute_reactive_drop_self(player, slot)
        self.discard_pile.append(result['card'])
        if self.reaction_card_discarded:
            self.discard_pile.append(self.reaction_card_discarded)
        result['card'].face_up = True
        self.game_log.append(f"{'You' if player.is_human else player.name} dropped {result['card'].display_name} to match!")
        self.reaction_responded = True
        return {"success": True, "result": result}

    def attempt_reactive_drop_opponent(self, reacting_player_index: int, opponent_index: int, opponent_slot: int, give_slot: int) -> dict:
        reacting_player = self.players[reacting_player_index]
        opponent = self.players[opponent_index]

        if not validate_reactive_drop(opponent, opponent_slot, self.reaction_rank):
            penalty_result = execute_wrong_drop_penalty(
                reacting_player, give_slot, self.players, self.deck
            )
            self.game_log.append(f"{'You' if reacting_player.is_human else reacting_player.name} wrong call! Penalty drawn")
            return {"success": False, "penalty": True, "result": penalty_result}

        result = execute_reactive_drop_opponent(reacting_player, opponent, opponent_slot, give_slot)
        self.discard_pile.append(result['opponent_card'])
        if self.reaction_card_discarded:
            self.discard_pile.append(self.reaction_card_discarded)
        if result['opponent_card']:
            result['opponent_card'].face_up = True
        self.game_log.append(f"{'You' if reacting_player.is_human else reacting_player.name} called opponent's matching card")
        self.reaction_responded = True
        return {"success": True, "result": result}

    def end_reaction_window(self):
        self.reaction_rank = None
        self.reaction_source_player = None
        self.reaction_timer = 0
        self.reaction_responded = False
        self.reaction_card_discarded = None
        self.reaction_pending = False
        self.reaction_resolved = True
        self.reaction_ai_resolved = False
        self._reaction_timer_expired = False
        self.reaction_elapsed = 0.0
        if self.reaction_result_callback:
            cb = self.reaction_result_callback
            self.reaction_result_callback = None
            cb()
        self.state = GameState.DECIDE

    def shuffle_player_hand(self, player_index: int):
        player = self.players[player_index]
        player.shuffle_hand(self.players)
        self.game_log.append(f"{'You' if player.is_human else player.name} shuffled their cards")

    def _check_reaction_trigger(self, player_idx: int, action_type: str, card_rank: str):
        if action_type in ('discard', 'pair_own', 'pair_opponent') and card_rank:
            self.start_reaction_window(card_rank, player_idx, discarded_card=self.drawn_card)

    def _log_action(self, player_idx: int, message: str, is_game_event: bool = False):
        prefix = "[EVENT] " if is_game_event else ""
        self.game_log.append(f"{prefix}{message}")

    def _format_log(self, action: str, details: dict, result: dict) -> str:
        player = self.current_player()
        name = "You" if player.is_human else player.name

        if action == "declare":
            return f"{name} declared!"

        if action == "play_power":
            card = details.get('card')
            power = card.power if card else None
            label = POWER_LABELS.get(power, power or 'power')
            if power in ('peek_self', 'peek_opponent'):
                if power == 'peek_self':
                    return f"{name} used {label} on slot {result.get('slot')}"
                else:
                    return f"{name} used {label} on P{result.get('player_index')} slot {result.get('slot')}"
            return f"{name} used {label}"

        if action == "swap":
            slot = details.get('my_slot')
            swapped_card = result.get('swapped_card')
            card_str = swapped_card.display_name if swapped_card else ''
            if player.is_human:
                return f"{name} swapped with slot {slot} (discarded {card_str})"
            return f"{name} swapped card"

        if action == "discard":
            discarded = result.get('discarded_card') or details.get('drawn_card')
            card_str = discarded.display_name if discarded else ''
            return f"{name} discarded {card_str}"

        if action == "pair_own":
            return f"{name} paired own card"

        if action == "pair_opponent":
            return f"{name} paired opponent's card"

        if action == "self_pair":
            return f"{name} self-paired cards"

        if action == "shuffle":
            return f"{name} shuffled their cards"

        return f"{name}: {action}"

    def resolve_power_if_needed(self, power_result: dict):
        if power_result.get('skip'):
            self.skip_next = True
        self.state = GameState.DECIDE

    def end_turn(self):
        self.state = GameState.TURN_END
        self.drawn_card_resolved = False
        if self._last_action_rank:
            self._check_reaction_trigger(self.current_player_index, self._last_action_type, self._last_action_rank)
        self._last_action_rank = None
        self._last_action_type = None
        self.next_turn()

    def resolve_declaration(self) -> dict:
        result = resolve_declare(self.current_player(), self.players)
        self.declaration_result = result
        self.winner = result.get('winner')
        self.state = GameState.GAME_OVER
        return result

    def check_game_over(self) -> bool:
        for player in self.players:
            if has_zero_cards(player):
                scores = {p.seat_index: calculate_score(p) for p in self.players}
                self.declaration_result = {
                    'winner': player,
                    'scores': scores,
                    'declarer_won': True,
                    'auto_win': True,
                }
                self.winner = player
                self.state = GameState.GAME_OVER
                return True
        rules_result = self.rules_engine.check_game_over()
        if rules_result is not None:
            self.declaration_result = rules_result
            self.winner = rules_result.get('winner')
            self.state = GameState.GAME_OVER
            return True
        return False

    def update(self, dt: float):
        if self.peek_reveal is not None:
            self.peek_reveal['timer'] -= dt
            if self.peek_reveal['timer'] <= 0:
                self.peek_reveal = None

        if self.state == GameState.REACTION_WINDOW:
            self.reaction_timer -= dt
            self.reaction_elapsed += dt
            if self.reaction_timer <= 0:
                self._reaction_timer_expired = True

    def can_self_pair_after_draw(self) -> bool:
        if not self.drawn_card_resolved:
            return False
        player = self.current_player()
        pairs = can_self_pair(player)
        return bool(pairs)

    def cancel_targeting(self):
        pass

    def get_game_state_info(self) -> dict:
        valid = get_valid_actions(self.current_player(), self.drawn_card, self.has_drawn_this_turn)
        return {
            "state": self.state,
            "current_player": self.current_player(),
            "current_player_index": self.current_player_index,
            "drawn_card": self.drawn_card,
            "drawn_card_resolved": self.drawn_card_resolved,
            "deck_remaining": self.deck.remaining if self.deck else 0,
            "valid_actions": valid,
            "game_log": self.game_log[-10:],
        }


try:
    import pygame
except ImportError:
    pygame = None
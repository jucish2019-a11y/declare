from __future__ import annotations
import random
from config import HAND_SIZE
from game.card import Card


class Player:
    def __init__(self, name: str, is_human: bool, seat_index: int, hand_size: int = HAND_SIZE):
        self.name = name
        self.is_human = is_human
        self.seat_index = seat_index
        self.hand_size = hand_size
        self.hand: list = [None] * hand_size
        self.known_cards: dict = {}
        self.known_opponent_cards: dict = {}
        self.has_peeked_initial: bool = False
        self.is_declaring: bool = False
        self.layout_mode: str = 'line'
        self.card_positions: dict = {}
        self.received_card_slot: int | None = None
        self.received_card_until: float = 0.0

    @property
    def has_zero_cards(self) -> bool:
        return all(slot is None for slot in self.hand)

    @property
    def card_count(self) -> int:
        return sum(1 for slot in self.hand if slot is not None)

    @property
    def score(self) -> int:
        return sum(slot.value for slot in self.hand if slot is not None)

    def receive_card(self, card: Card, slot: int):
        self.hand[slot] = card

    def remove_card(self, slot: int) -> Card:
        card = self.hand[slot]
        self.hand[slot] = None
        self.known_cards.pop(slot, None)
        return card

    def mark_received_card(self, slot: int, duration: float, current_time: float):
        self.received_card_slot = slot
        self.received_card_until = current_time + duration

    def clear_received_card(self):
        self.received_card_slot = None
        self.received_card_until = 0.0

    def resize_hand(self, new_size: int):
        old_hand = self.hand[:]
        self.hand = [None] * new_size
        for i in range(min(len(old_hand), new_size)):
            self.hand[i] = old_hand[i]
        self.hand_size = new_size

    def swap_cards(self, my_slot: int, other_player, their_slot: int):
        my_card = self.hand[my_slot]
        their_card = other_player.hand[their_slot]
        self.hand[my_slot] = their_card
        other_player.hand[their_slot] = my_card
        self.known_cards.pop(my_slot, None)
        other_player.known_cards.pop(their_slot, None)
        self.known_opponent_cards.pop((other_player.seat_index, their_slot), None)
        other_player.known_opponent_cards.pop((self.seat_index, my_slot), None)

    def get_active_slots(self) -> list:
        return [i for i, slot in enumerate(self.hand) if slot is not None]

    def find_self_pairs(self) -> list:
        pairs = []
        known_slots = {s: c for s, c in self.known_cards.items() if self.hand[s] is not None}
        checked = set()
        for s1, c1 in known_slots.items():
            if s1 in checked:
                continue
            for s2, c2 in known_slots.items():
                if s2 <= s1 or s2 in checked:
                    continue
                if c1.rank == c2.rank:
                    pairs.append((s1, s2))
                    checked.add(s1)
                    checked.add(s2)
                    break
        return pairs

    def shuffle_hand(self, all_players: list):
        active_slots = self.get_active_slots()
        active_cards = [self.hand[s] for s in active_slots]
        random.shuffle(active_cards)
        new_hand = [None] * len(self.hand)
        for i, slot in enumerate(active_slots):
            new_hand[slot] = active_cards[i]
        self.hand = new_hand
        self.known_cards.clear()
        for p in all_players:
            if p.seat_index != self.seat_index:
                p.known_opponent_cards = {
                    k: v for k, v in p.known_opponent_cards.items()
                    if k[0] != self.seat_index
                }

    def swap_hand_slots(self, slot_a: int, slot_b: int, all_players: list):
        card_a = self.hand[slot_a]
        card_b = self.hand[slot_b]
        self.hand[slot_a] = card_b
        self.hand[slot_b] = card_a
        knew_a = slot_a in self.known_cards
        knew_b = slot_b in self.known_cards
        if knew_a and knew_b:
            self.known_cards[slot_a], self.known_cards[slot_b] = self.known_cards[slot_b], self.known_cards[slot_a]
        elif knew_a:
            self.known_cards[slot_b] = self.known_cards.pop(slot_a)
        elif knew_b:
            self.known_cards[slot_a] = self.known_cards.pop(slot_b)
        pos_a = self.card_positions.pop(slot_a, None)
        pos_b = self.card_positions.pop(slot_b, None)
        if pos_b is not None:
            self.card_positions[slot_a] = pos_b
        if pos_a is not None:
            self.card_positions[slot_b] = pos_a
        for p in all_players:
            if p.seat_index != self.seat_index:
                p.known_opponent_cards = {
                    k: v for k, v in p.known_opponent_cards.items()
                    if k[0] != self.seat_index
                }

    def add_penalty_card(self, card: Card) -> int | None:
        for i in range(len(self.hand)):
            if self.hand[i] is None:
                self.hand[i] = card
                self.known_cards[i] = card
                return i
        return None

    def reset_targeting_state(self):
        pass


class HumanPlayer(Player):
    def __init__(self, name: str, seat_index: int, hand_size: int = HAND_SIZE):
        super().__init__(name, is_human=True, seat_index=seat_index, hand_size=hand_size)


class AIPlayer(Player):
    def __init__(self, name: str, seat_index: int, difficulty: str = 'normal', hand_size: int = HAND_SIZE):
        super().__init__(name, is_human=False, seat_index=seat_index, hand_size=hand_size)
        self.difficulty = difficulty
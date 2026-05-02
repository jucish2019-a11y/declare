import random
from config import (
    CARD_VALUES,
    BLACK_KING_VALUE,
    SUITS,
    RANKS,
    POWER_CARDS,
)


class Card:
    def __init__(self, rank: str, suit: str):
        self.rank = rank
        self.suit = suit
        self.face_up = False

    @property
    def value(self):
        if self.rank == 'K' and self.suit in ('spade', 'club'):
            return BLACK_KING_VALUE
        return CARD_VALUES[self.rank]

    @property
    def is_black(self):
        return self.suit in ('spade', 'club')

    @property
    def is_red(self):
        return self.suit in ('heart', 'diamond')

    @property
    def power(self):
        if self.rank in ('J', 'Q', '7', '8', '9', '10'):
            return POWER_CARDS[self.rank]
        if self.rank == 'K':
            return POWER_CARDS.get(('K', self.suit))
        return None

    @property
    def suit_symbol(self):
        symbols = {'spade': '\u2660', 'heart': '\u2665', 'diamond': '\u2666', 'club': '\u2663'}
        return symbols[self.suit]

    @property
    def display_name(self):
        return f"{self.rank}{self.suit_symbol}"

    def __repr__(self):
        return f"Card({self.rank}, {self.suit})"

    def to_dict(self) -> dict:
        return {"r": self.rank, "s": self.suit, "u": self.face_up}

    @classmethod
    def from_dict(cls, data: dict) -> "Card":
        c = cls(data["r"], data["s"])
        c.face_up = bool(data.get("u", False))
        return c


class Deck:
    def __init__(self, seed=None):
        self.cards = [Card(rank, suit) for suit in SUITS for rank in RANKS]
        if seed is not None:
            random.seed(seed)
        random.shuffle(self.cards)

    def draw(self):
        if self.is_empty:
            return None
        return self.cards.pop()

    @property
    def is_empty(self):
        return len(self.cards) == 0

    @property
    def remaining(self):
        return len(self.cards)

    def reshuffle(self, discard_pile):
        for card in discard_pile:
            card.face_up = False
        self.cards.extend(discard_pile)
        random.shuffle(self.cards)
        discard_pile.clear()
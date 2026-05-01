"""TutorialDirector - interactive tutorial with text + hands-on chapters.

Full-page text chapters teach game concepts. Interactive chapters create a
live game scenario that the player must complete to advance.
"""
import math
import random
import pygame

import theme
import audio
from config import (
    SCREEN_WIDTH, SCREEN_HEIGHT, DECK_CENTER, DRAWN_CARD_POS, DISCARD_POS,
    ACTION_BAR_Y, ACTION_BAR_H,
    SWAP_GREEN, SWAP_GREEN_HOVER, PEEK_BLUE, PEEK_BLUE_HOVER,
    DISCARD_ORANGE, DISCARD_ORANGE_HOVER, PAIR_TEAL, PAIR_TEAL_HOVER,
    DECLARE_RED, DECLARE_RED_HOVER, CANCEL_GRAY, CANCEL_GRAY_HOVER,
    SELF_PAIR_COLOR, SELF_PAIR_HOVER,
    UI_FONT_SIZE, POWER_LABELS, FONT_PATHS,
)
import os


def _load_font(role, size, bold=False):
    import pygame
    path = FONT_PATHS.get(role + '_bold' if bold and role + '_bold' in FONT_PATHS else role, '')
    if path and os.path.exists(path):
        try:
            return pygame.font.Font(path, size)
        except Exception:
            pass
    return pygame.font.SysFont("arial", size, bold=bold)
from game.card import Card, Deck
from game.player import HumanPlayer, AIPlayer
from game.rules import RulesEngine, can_declare
from game.ai import AIDecider


def _make_card(rank, suit, face_up=False):
    c = Card(rank, suit)
    c.face_up = face_up
    return c


CHAPTERS = [
    {
        "title": "Welcome to Declare.",
        "body": "A casino-style card game of memory, bluffing, and "
                "lightning-fast reactions. Press SPACE or click "
                "Continue to begin.",
        "mode": "text",
        "advance_on": "continue",
    },
    {
        "title": "Your Hand",
        "body": "Each round you hold a small hand of cards face down. "
                "You can only see cards you have peeked at. The player "
                "with the lowest hand-total wins.",
        "mode": "text",
        "advance_on": "continue",
    },
    {
        "title": "Studying Your Hand",
        "body": "Before the round starts, peek at some cards. "
                "Click the face-down cards to reveal them. "
                "These will be your known cards throughout the round.",
        "mode": "interactive",
        "advance_on": "peek_done",
    },
    {
        "title": "The Draw",
        "body": "On your turn, draw a card from the deck. You can play it, "
                "swap it into your hand, discard it, or use its power. "
                "Click the deck or press 1 to draw.",
        "mode": "interactive",
        "advance_on": "draw",
        "sfx": "draw",
    },
    {
        "title": "Suits & Values",
        "body": "Aces = 1. Number cards = face value. J/Q = 11/12. "
                "Red Kings = 13 (high). Black Kings = 0 - keep these. "
                "Lowest sum wins.",
        "mode": "text",
        "advance_on": "continue",
    },
    {
        "title": "Powers",
        "body": "Cards 7-K carry powers. Peek at your own card, peek at "
                "opponents, swap cards, or skip a turn. The drawn card's "
                "power lights up below the card.",
        "mode": "text",
        "advance_on": "continue",
    },
    {
        "title": "Pairing",
        "body": "If the rank of your drawn card matches a card you've seen, "
                "you can pair them - both go to the discard pile. Pairing "
                "an opponent's card forces them to take one of yours.",
        "mode": "interactive",
        "advance_on": "pair_own",
        "sfx": "pair",
    },
    {
        "title": "Reactive Pairing",
        "body": "When ANY player plays a card, others have a brief window "
                "to drop a matching rank. Wrong card = penalty draw. "
                "Watch the gold banner.",
        "mode": "text",
        "advance_on": "continue",
    },
    {
        "title": "Declare to Win",
        "body": "When your hand-total is 10 or less, click Declare to "
                "end the round. If you have the lowest score, you win. "
                "If not, your score is doubled. Bold but risky.",
        "mode": "interactive",
        "advance_on": "declare",
        "sfx": "achievement",
    },
    {
        "title": "You're Ready.",
        "body": "That's the basics. Click Continue to return to the menu "
                "and start a real match. Good luck at the table.",
        "mode": "text",
        "advance_on": "continue",
        "sfx": "achievement",
    },
]


class TutorialDirector:
    def __init__(self, screen):
        self.screen = screen
        self.active = False
        self.chapter = 0
        self._fade = 0.0
        self._title_font = None
        self._body_font = None
        self._small_font = None
        self._continue_rect = None
        self._skip_rect = None
        self._game_manager = None
        self._renderer = None
        self._chapter_complete = False
        self._peek_card_rects = []

    def _ensure_fonts(self):
        if self._title_font is None:
            import typography as typo
            self._title_font = typo.display_bold(30)
            self._body_font = typo.body(20)
            self._small_font = typo.body(14)

    def start(self):
        self.active = True
        self.chapter = 0
        self._fade = 0.0
        self._chapter_complete = False
        self._game_manager = None
        audio.play("ui_open")

    def stop(self):
        self.active = False
        self._game_manager = None

    def update(self, dt):
        if not self.active:
            return
        self._fade = min(1.0, self._fade + dt * 3.0)
        step = self.current()
        if step and step["mode"] == "interactive" and self._game_manager:
            self._game_manager.update(dt)
            if self._renderer:
                self._renderer.update(dt)

    def current(self):
        if 0 <= self.chapter < len(CHAPTERS):
            return CHAPTERS[self.chapter]
        return None

    def advance(self):
        if not self.active:
            return False
        step = self.current()
        if step and step.get("sfx"):
            audio.play(step["sfx"])
        self.chapter += 1
        self._fade = 0.0
        self._chapter_complete = False
        self._peek_card_rects = []
        self._game_manager = None
        if self.chapter >= len(CHAPTERS):
            self.active = False
            return True
        return False

    def skip_chapter(self):
        return self.advance()

    def notify_action(self, action_name):
        step = self.current()
        if not step:
            return
        if step["advance_on"] == action_name:
            self._chapter_complete = True

    def _trigger_panel_action(self):
        step = self.current()
        if not step or self._chapter_complete:
            return
        from game.game_manager import GameState
        from game.rules import get_valid_actions
        cp = self._game_manager.current_player()
        if not cp or not cp.is_human:
            return

        if self._game_manager.state == GameState.TURN_START:
            if step["advance_on"] == "declare":
                if can_declare(cp, False):
                    self._game_manager.execute_player_action("declare", {})
                    self._game_manager.resolve_declaration()
                    self.notify_action("declare")
                    return
            self._game_manager.draw_card()
            self.notify_action("draw")
            return

        valid = get_valid_actions(cp, self._game_manager.drawn_card, self._game_manager.has_drawn_this_turn)

        if step["advance_on"] == "pair_own" and "pair_own" in valid:
            if self._game_manager.drawn_card:
                drawn_rank = self._game_manager.drawn_card.rank
                for slot in cp.get_active_slots():
                    if slot in cp.known_cards and cp.known_cards[slot].rank == drawn_rank:
                        self._game_manager.execute_player_action("pair_own", {
                            "player_slot": slot,
                            "drawn_card": self._game_manager.drawn_card,
                        })
                        self.notify_action("pair_own")
                        break

        elif step["advance_on"] == "declare" and "declare" in valid:
            self._game_manager.execute_player_action("declare", {})
            self._game_manager.resolve_declaration()
            self.notify_action("declare")

    def _setup_interactive_chapter(self):
        self._chapter_complete = False
        ch = self.chapter

        if ch == 2:
            from game.settings import GameSettings
            from game.game_manager import GameManager, GameState
            configs = [
                {"name": "You", "is_human": True},
                {"name": "Alex", "is_human": False},
            ]
            self._game_manager = GameManager(configs, GameSettings())
            self._game_manager.setup_game()
            self._game_manager.state = GameState.PEEK_PHASE
            self._game_manager.current_player_index = 0
            player = self._game_manager.players[0]
            player.known_cards.clear()
            self._peek_card_rects = []

        elif ch == 3:
            configs = [
                {"name": "You", "is_human": True},
                {"name": "Alex", "is_human": False},
            ]
            from game.settings import GameSettings
            from game.game_manager import GameManager, GameState
            self._game_manager = GameManager(configs, GameSettings())
            self._game_manager.setup_game()
            self._game_manager.start_peek_phase()
            self._game_manager.current_player_index = 0
            self._game_manager.state = GameState.TURN_START

        elif ch == 6:
            from game.settings import GameSettings
            from game.game_manager import GameManager, GameState
            configs = [
                {"name": "You", "is_human": True},
                {"name": "Alex", "is_human": False},
            ]
            self._game_manager = GameManager(configs, GameSettings())
            self._game_manager.setup_game()
            self._game_manager.start_peek_phase()
            self._game_manager.current_player_index = 0
            self._game_manager.state = GameState.TURN_START

            player = self._game_manager.players[0]
            player.hand[0] = _make_card("7", "diamond", face_up=False)
            player.hand[1] = _make_card("7", "heart", face_up=False)
            player.hand[2] = _make_card("2", "spade", face_up=False)
            player.hand[3] = _make_card("3", "club", face_up=False)
            player.known_cards[0] = player.hand[0]
            player.known_cards[1] = player.hand[1]
            player.known_cards.pop(2, None)
            player.known_cards.pop(3, None)

            ai = self._game_manager.players[1]
            ai.hand[0] = _make_card("K", "spade", face_up=False)
            ai.hand[1] = _make_card("Q", "heart", face_up=False)
            ai.hand[2] = _make_card("J", "diamond", face_up=False)
            ai.hand[3] = _make_card("10", "club", face_up=False)

            self._game_manager.deck.cards.clear()
            for suit in ("spade", "club"):
                for rank in ("9", "8", "6", "5", "4", "3", "2"):
                    self._game_manager.deck.cards.append(_make_card(rank, suit))
            self._game_manager.deck.cards.append(_make_card("7", "spade", face_up=True))

        elif ch == 8:
            from game.settings import GameSettings
            from game.game_manager import GameManager, GameState
            configs = [
                {"name": "You", "is_human": True},
                {"name": "Alex", "is_human": False},
            ]
            self._game_manager = GameManager(configs, GameSettings())
            self._game_manager.setup_game()
            self._game_manager.start_peek_phase()
            self._game_manager.current_player_index = 0
            self._game_manager.state = GameState.TURN_START

            player = self._game_manager.players[0]
            player.hand[0] = _make_card("A", "spade", face_up=False)
            player.hand[1] = _make_card("2", "heart", face_up=False)
            player.hand[2] = _make_card("3", "diamond", face_up=False)
            player.hand[3] = _make_card("K", "spade", face_up=False)
            player.known_cards[0] = player.hand[0]
            player.known_cards[1] = player.hand[1]
            player.known_cards[2] = player.hand[2]
            player.known_cards[3] = player.hand[3]

            ai = self._game_manager.players[1]
            ai.hand[0] = _make_card("K", "heart", face_up=False)
            ai.hand[1] = _make_card("Q", "spade", face_up=False)
            ai.hand[2] = _make_card("J", "diamond", face_up=False)
            ai.hand[3] = _make_card("10", "club", face_up=False)

        if self._game_manager:
            from ui.renderer import Renderer
            from game.settings import GameSettings
            self._renderer = Renderer(self.screen)
            gs = GameSettings()
            gs.self_pair_enabled = True
            gs.shuffle_enabled = False
            gs.wrong_drop_penalty = False
            self._renderer.set_game_settings(gs)

    def handle_event(self, event):
        if not self.active:
            return None
        step = self.current()
        if not step:
            return None

        if step["mode"] == "text":
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return "skip"
                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                    return "next"
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self._continue_rect and self._continue_rect.collidepoint(event.pos):
                    return "next"
                if self._skip_rect and self._skip_rect.collidepoint(event.pos):
                    return "skip"
            return None

        else:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return "skip"

            if self._game_manager and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self._continue_rect and self._continue_rect.collidepoint(event.pos):
                    if self._chapter_complete:
                        return "next"
                    self._trigger_panel_action()
                    return None

                if self._skip_rect and self._skip_rect.collidepoint(event.pos):
                    return "skip"

            if self._chapter_complete:
                return None

            if self._game_manager:
                if event.type == pygame.KEYDOWN:
                    NUMBER_TO_ACTION = {
                        pygame.K_1: "draw",
                        pygame.K_2: "declare",
                        pygame.K_5: "pair_own",
                    }
                    if event.key in NUMBER_TO_ACTION:
                        key_action = NUMBER_TO_ACTION[event.key]
                        cp = self._game_manager.current_player()
                        if cp and cp.is_human:
                            from game.rules import get_valid_actions
                            valid = get_valid_actions(cp, self._game_manager.drawn_card, self._game_manager.has_drawn_this_turn)
                            if key_action == "draw" and "draw" in valid and self._game_manager.state == GameState.TURN_START:
                                self._game_manager.draw_card()
                                self.notify_action("draw")
                                return None
                            elif key_action == "declare" and "declare" in valid:
                                self._game_manager.execute_player_action("declare", {})
                                self._game_manager.resolve_declaration()
                                self.notify_action("declare")
                                return None
                            elif key_action == "pair_own" and "pair_own" in valid:
                                if self._game_manager.drawn_card:
                                    drawn_rank = self._game_manager.drawn_card.rank
                                    for slot in cp.get_active_slots():
                                        if slot in cp.known_cards and cp.known_cards[slot].rank == drawn_rank:
                                            self._game_manager.execute_player_action("pair_own", {
                                                "player_slot": slot,
                                                "drawn_card": self._game_manager.drawn_card,
                                            })
                                            self.notify_action("pair_own")
                                            break
                                return None
                if self._game_manager and self._game_manager.state == GameState.PEEK_PHASE:
                    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        if self._handle_peek_click(event.pos):
                            return None
                return self._handle_interactive_event(event)

        return None

    def _handle_interactive_event(self, event):
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return None

        from game.game_manager import GameState

        if self._game_manager.state == GameState.TURN_START:
            deck_rect = pygame.Rect(DECK_CENTER[0] - 40, DECK_CENTER[1] - 60, 80, 120)
            if deck_rect.collidepoint(event.pos):
                self._game_manager.draw_card()
                self.notify_action("draw")
                return None

        elif self._game_manager.state == GameState.DECIDE:
            action = self._detect_action_click(event.pos)
            if not action:
                return None

            cp = self._game_manager.current_player()
            if not cp or not cp.is_human:
                return None

            from game.rules import get_valid_actions
            valid = get_valid_actions(cp, self._game_manager.drawn_card, self._game_manager.has_drawn_this_turn)

            if action == "pair_own" and "pair_own" in valid:
                if self._game_manager.drawn_card:
                    drawn_rank = self._game_manager.drawn_card.rank
                    for slot in cp.get_active_slots():
                        if slot in cp.known_cards and cp.known_cards[slot].rank == drawn_rank:
                            self._game_manager.execute_player_action("pair_own", {
                                "player_slot": slot,
                                "drawn_card": self._game_manager.drawn_card,
                            })
                            self.notify_action("pair_own")
                            break

            elif action == "declare" and "declare" in valid:
                self._game_manager.execute_player_action("declare", {})
                self._game_manager.resolve_declaration()
                self.notify_action("declare")

        return None

    def _detect_action_click(self, pos):
        from game.game_manager import GameState
        btn_h = 44
        btn_y = ACTION_BAR_Y + ACTION_BAR_H // 2 - btn_h // 2

        if self._game_manager.state == GameState.TURN_START:
            deck_rect = pygame.Rect(DECK_CENTER[0] - 40, DECK_CENTER[1] - 60, 80, 120)
            if deck_rect.collidepoint(pos):
                return "draw"

        elif self._game_manager.state == GameState.DECIDE:
            buttons = self._get_tutorial_buttons()
            for name, btn in buttons.items():
                if btn['rect'].collidepoint(pos):
                    return name

        return None

    def _get_tutorial_buttons(self):
        ui_font = _load_font('ui', UI_FONT_SIZE)
        buttons = {}
        cp = self._game_manager.current_player()
        from game.rules import get_valid_actions
        valid = get_valid_actions(cp, self._game_manager.drawn_card, self._game_manager.has_drawn_this_turn)
        if not valid:
            return buttons

        btn_y = ACTION_BAR_Y + ACTION_BAR_H // 2
        btn_h = 44
        spacing = 8

        if self._game_manager.state == GameState.DECIDE:
            from game.rules import can_self_pair
            x = SCREEN_WIDTH // 2 - 400

            if self._game_manager.drawn_card_resolved:
                pairs = can_self_pair(cp)
                if pairs:
                    w = 110
                    rect = pygame.Rect(x, btn_y - btn_h // 2, w, btn_h)
                    buttons['self_pair'] = {'rect': rect, 'text': 'Self-Pair', 'color': SELF_PAIR_COLOR, 'hover_color': SELF_PAIR_HOVER, 'font': ui_font}
                    x += w + spacing

            if 'play_power' in valid and self._game_manager.drawn_card and self._game_manager.drawn_card.power:
                power = self._game_manager.drawn_card.power
                label = POWER_LABELS.get(power, 'Power')
                w = 150
                rect = pygame.Rect(x, btn_y - btn_h // 2, w, btn_h)
                buttons['play_power'] = {'rect': rect, 'text': label, 'color': PEEK_BLUE, 'hover_color': PEEK_BLUE_HOVER, 'font': ui_font}
                x += w + spacing
            if 'swap' in valid:
                w = 110
                rect = pygame.Rect(x, btn_y - btn_h // 2, w, btn_h)
                buttons['swap'] = {'rect': rect, 'text': 'Swap', 'color': SWAP_GREEN, 'hover_color': SWAP_GREEN_HOVER, 'font': ui_font}
                x += w + spacing
            if 'discard' in valid:
                w = 120
                rect = pygame.Rect(x, btn_y - btn_h // 2, w, btn_h)
                buttons['discard'] = {'rect': rect, 'text': 'Discard', 'color': DISCARD_ORANGE, 'hover_color': DISCARD_ORANGE_HOVER, 'font': ui_font}
                x += w + spacing
            if 'pair_own' in valid:
                w = 130
                rect = pygame.Rect(x, btn_y - btn_h // 2, w, btn_h)
                buttons['pair_own'] = {'rect': rect, 'text': 'Pair Own', 'color': PAIR_TEAL, 'hover_color': PAIR_TEAL_HOVER, 'font': ui_font}
                x += w + spacing
            if 'pair_opponent' in valid:
                w = 160
                rect = pygame.Rect(x, btn_y - btn_h // 2, w, btn_h)
                buttons['pair_opponent'] = {'rect': rect, 'text': 'Pair Opponent', 'color': PAIR_TEAL, 'hover_color': PAIR_TEAL_HOVER, 'font': ui_font}
                x += w + spacing
            if 'declare' in valid:
                w = 130
                rect = pygame.Rect(x, btn_y - btn_h // 2, w, btn_h)
                buttons['declare'] = {'rect': rect, 'text': 'Declare', 'color': DECLARE_RED, 'hover_color': DECLARE_RED_HOVER, 'font': ui_font}

        return buttons

    def draw(self, screen):
        if not self.active:
            return
        self._ensure_fonts()
        step = self.current()
        if not step:
            return
        th = theme.active()

        if step["mode"] == "text":
            self._draw_text_chapter(screen, th, step)
        else:
            self._draw_interactive_chapter(screen, th, step)

    def _draw_text_chapter(self, screen, th, step):
        bg = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        for i in range(SCREEN_HEIGHT):
            t = i / max(1, SCREEN_HEIGHT - 1)
            r = int(th.felt_rim[0] * (1 - t * 0.4) + th.felt_deep[0] * t * 0.6)
            g = int(th.felt_rim[1] * (1 - t * 0.4) + th.felt_deep[1] * t * 0.6)
            b = int(th.felt_rim[2] * (1 - t * 0.4) + th.felt_deep[2] * t * 0.6)
            pygame.draw.line(bg, (r, g, b), (0, i), (SCREEN_WIDTH, i))
        screen.blit(bg, (0, 0))

        alpha = int(255 * self._fade)
        total = len(CHAPTERS)

        ch_label = f"Chapter {self.chapter + 1} / {total}"
        ch_surf = self._small_font.render(ch_label, True, th.brass_300)
        ch_surf.set_alpha(alpha)
        screen.blit(ch_surf, ch_surf.get_rect(center=(SCREEN_WIDTH // 2, 200)))

        line_y = 218
        line_w = 180
        cx = SCREEN_WIDTH // 2
        pygame.draw.line(screen, th.brass_500, (cx - line_w, line_y), (cx - 30, line_y), 1)
        pygame.draw.line(screen, th.brass_500, (cx + 30, line_y), (cx + line_w, line_y), 1)
        pygame.draw.polygon(screen, th.brass_500,
                            [(cx, line_y - 5), (cx - 10, line_y), (cx, line_y + 5), (cx + 10, line_y)])

        title_surf = self._title_font.render(step["title"], True, th.brass_300)
        title_surf.set_alpha(alpha)
        screen.blit(title_surf, title_surf.get_rect(center=(SCREEN_WIDTH // 2, 260)))

        body_lines = self._wrap(step["body"], 600)
        for i, line in enumerate(body_lines):
            surf = self._body_font.render(line, True, th.text_white)
            surf.set_alpha(alpha)
            screen.blit(surf, surf.get_rect(center=(SCREEN_WIDTH // 2, 340 + i * 30)))

        bw, bh = 200, 48
        btn_y = SCREEN_HEIGHT - 160
        self._continue_rect = pygame.Rect(SCREEN_WIDTH // 2 + 20, btn_y, bw, bh)
        pygame.draw.rect(screen, th.signal_go, self._continue_rect, border_radius=8)
        pygame.draw.rect(screen, th.brass_500, self._continue_rect, 2, border_radius=8)
        cs = self._body_font.render("Continue", True, th.text_white)
        cs.set_alpha(alpha)
        screen.blit(cs, cs.get_rect(center=self._continue_rect.center))

        sw, sh = 120, 40
        self._skip_rect = pygame.Rect(SCREEN_WIDTH // 2 - 20 - sw, btn_y + 4, sw, sh)
        pygame.draw.rect(screen, (50, 50, 55), self._skip_rect, border_radius=6)
        pygame.draw.rect(screen, th.brass_700, self._skip_rect, 1, border_radius=6)
        sk = self._small_font.render("Skip Chapter", True, th.text_dim)
        sk.set_alpha(alpha)
        screen.blit(sk, sk.get_rect(center=self._skip_rect.center))

        hint = self._small_font.render("Space / Enter to continue  |  Esc to skip chapter",
                                      True, th.text_muted)
        hint.set_alpha(int(alpha * 0.7))
        screen.blit(hint, hint.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 50)))

    def _draw_highlight_ring(self, screen, step):
        if self._chapter_complete:
            return
        pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() / 300)
        th = theme.active()
        ring_color = (*th.brass_300, int(200 * pulse))

        if step["advance_on"] == "peek_done":
            self._draw_peek_rings(screen, pulse)
        elif step["advance_on"] == "draw":
            cx, cy = DECK_CENTER
            radius = 56
            ring_surf = pygame.Surface((radius * 2 + 12, radius * 2 + 12), pygame.SRCALPHA)
            pygame.draw.circle(ring_surf, ring_color, (radius + 6, radius + 6), radius + 4, 4)
            screen.blit(ring_surf, (cx - radius - 6, cy - radius - 6))

        elif step["advance_on"] == "pair_own":
            buttons = self._get_tutorial_buttons()
            if 'pair_own' in buttons:
                rect = buttons['pair_own']['rect']
                inflated = rect.inflate(16, 16)
                ring_surf = pygame.Surface((inflated.width, inflated.height), pygame.SRCALPHA)
                pygame.draw.rect(ring_surf, ring_color, ring_surf.get_rect(), 3, border_radius=6)
                screen.blit(ring_surf, (rect.x - 8, rect.y - 8))

        elif step["advance_on"] == "declare":
            if self._game_manager.state == GameState.TURN_START:
                if self._continue_rect:
                    inflated = self._continue_rect.inflate(16, 16)
                    ring_surf = pygame.Surface((inflated.width, inflated.height), pygame.SRCALPHA)
                    pygame.draw.rect(ring_surf, ring_color, ring_surf.get_rect(), 3, border_radius=6)
                    screen.blit(ring_surf, (self._continue_rect.x - 8, self._continue_rect.y - 8))
            else:
                buttons = self._get_tutorial_buttons()
                if 'declare' in buttons:
                    rect = buttons['declare']['rect']
                    ring_surf = pygame.Surface((rect.width + 16, rect.height + 16), pygame.SRCALPHA)
                    pygame.draw.rect(ring_surf, ring_color, ring_surf.get_rect(), 3, border_radius=6)
                    screen.blit(ring_surf, (rect.x - 8, rect.y - 8))

    def _draw_peek_phase_view(self):
        import card_render
        from config import CARD_WIDTH, CARD_HEIGHT, CARD_SPREAD, PLAYER_BOTTOM, PLAYER_TOP
        th = theme.active()
        player = self._game_manager.players[0]
        hand_size = self._game_manager.settings.hand_size
        peek_count = self._game_manager.settings.peek_count
        total_width = hand_size * CARD_SPREAD + (CARD_WIDTH - CARD_SPREAD)
        start_x = PLAYER_BOTTOM[0] - total_width // 2
        start_y = PLAYER_BOTTOM[1] - CARD_HEIGHT // 2 + 4
        self._peek_card_rects = []
        peek_tag_font = _load_font('ui', 11)
        for slot in range(hand_size):
            x = start_x + slot * CARD_SPREAD
            y = start_y
            card = player.hand[slot]
            is_known = slot in player.known_cards
            rect = pygame.Rect(x, y, CARD_WIDTH, CARD_HEIGHT)
            self._peek_card_rects.append((slot, rect))
            if is_known:
                shadow = pygame.Surface((CARD_WIDTH + 12, CARD_HEIGHT + 14), pygame.SRCALPHA)
                pygame.draw.rect(shadow, (0, 0, 0, 90), shadow.get_rect(), border_radius=10)
                self.screen.blit(shadow, (x - 6, y + 8))
                face = card_render.paint_face(card, CARD_WIDTH, CARD_HEIGHT)
                self.screen.blit(face, (x, y))
                tag_rect = pygame.Rect(x + CARD_WIDTH - 54, y + 4, 50, 18)
                pygame.draw.rect(self.screen, th.brass_300, tag_rect, border_radius=9)
                tag = peek_tag_font.render("PEEKED", True, th.brass_900)
                self.screen.blit(tag, tag.get_rect(center=tag_rect.center))
            else:
                shadow = pygame.Surface((CARD_WIDTH + 12, CARD_HEIGHT + 14), pygame.SRCALPHA)
                pygame.draw.rect(shadow, (0, 0, 0, 90), shadow.get_rect(), border_radius=10)
                self.screen.blit(shadow, (x - 6, y + 8))
                back = card_render.paint_back("classic", CARD_WIDTH, CARD_HEIGHT)
                self.screen.blit(back, (x, y))
        ai = self._game_manager.players[1]
        if ai.hand:
            ai_total_width = 4 * CARD_SPREAD + (CARD_WIDTH - CARD_SPREAD)
            ai_start_x = PLAYER_TOP[0] - ai_total_width // 2
            ai_start_y = PLAYER_TOP[1] - CARD_HEIGHT // 2 + 4
            for slot in range(4):
                x = ai_start_x + slot * CARD_SPREAD
                back = card_render.paint_back("classic", CARD_WIDTH, CARD_HEIGHT)
                self.screen.blit(back, (x, ai_start_y))
        if self._renderer:
            self._renderer.draw_deck(self._game_manager.deck.remaining if self._game_manager.deck else 0)
            if self._game_manager.discard_pile:
                self._renderer.draw_discard(self._game_manager.discard_pile)

    def _draw_peek_rings(self, screen, pulse):
        if not self._game_manager or not hasattr(self, '_peek_card_rects'):
            return
        th = theme.active()
        ring_color = (*th.brass_300, int(180 * pulse))
        player = self._game_manager.players[0]
        hand_size = self._game_manager.settings.hand_size
        peek_count = self._game_manager.settings.peek_count
        for slot, rect in self._peek_card_rects:
            if slot >= hand_size - peek_count and slot not in player.known_cards:
                inflated = rect.inflate(14, 14)
                ring_surf = pygame.Surface((inflated.width, inflated.height), pygame.SRCALPHA)
                pygame.draw.rect(ring_surf, ring_color, ring_surf.get_rect(), 3, border_radius=8)
                screen.blit(ring_surf, (rect.x - 7, rect.y - 7))

    def _handle_peek_click(self, pos):
        if not self._game_manager:
            return False
        player = self._game_manager.players[0]
        hand_size = self._game_manager.settings.hand_size
        peek_count = self._game_manager.settings.peek_count
        for slot, rect in self._peek_card_rects:
            if slot >= hand_size - peek_count and slot not in player.known_cards and rect.collidepoint(pos):
                player.known_cards[slot] = player.hand[slot]
                if slot >= hand_size - peek_count:
                    all_peeked = all(
                        s in player.known_cards
                        for s in range(hand_size - peek_count, hand_size)
                    )
                    if all_peeked:
                        self.notify_action("peek_done")
                return True
        return False

    def _draw_interactive_chapter(self, screen, th, step):
        if self._game_manager is None:
            self._setup_interactive_chapter()

        alpha = int(255 * self._fade)
        total = len(CHAPTERS)

        bg = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        for i in range(SCREEN_HEIGHT):
            t = i / max(1, SCREEN_HEIGHT - 1)
            r = int(th.felt_rim[0] * (1 - t * 0.4) + th.felt_deep[0] * t * 0.6)
            g = int(th.felt_rim[1] * (1 - t * 0.4) + th.felt_deep[1] * t * 0.6)
            b = int(th.felt_rim[2] * (1 - t * 0.4) + th.felt_deep[2] * t * 0.6)
            pygame.draw.line(bg, (r, g, b), (0, i), (SCREEN_WIDTH, i))
        screen.blit(bg, (0, 0))

        if self._renderer and self._game_manager:
            if self._game_manager.state == GameState.PEEK_PHASE:
                self._draw_peek_phase_view()
            else:
                action_buttons = self._get_tutorial_buttons()
                cancel_button = None
                status_message = ""
                awaiting = None
                self._renderer.draw(self._game_manager, pygame.mouse.get_pos(), action_buttons, cancel_button, status_message, awaiting)

        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, int(80 * self._fade)))
        screen.blit(overlay, (0, 0))

        self._draw_highlight_ring(screen, step)

        panel_w, panel_h = 500, 650
        panel_x = 20
        panel_y = 50

        slide = int((1 - self._fade) * 30)
        panel_y += slide

        panel_surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        pygame.draw.rect(panel_surf, (*th.panel_bg, 240), panel_surf.get_rect(), border_radius=14)
        pygame.draw.rect(panel_surf, th.brass_500, panel_surf.get_rect(), 2, border_radius=14)
        screen.blit(panel_surf, (panel_x, panel_y))

        ch_label = f"Chapter {self.chapter + 1} / {total}"
        cl_surf = self._small_font.render(ch_label, True, th.brass_500)
        cl_surf.set_alpha(alpha)
        screen.blit(cl_surf, (panel_x + 15, panel_y + 12))

        title_surf = self._title_font.render(step["title"], True, th.brass_300)
        title_surf.set_alpha(alpha)
        screen.blit(title_surf, (panel_x + 15, panel_y + 44))

        body_lines = self._wrap(step["body"], panel_w - 30)
        for i, line in enumerate(body_lines):
            surf = self._body_font.render(line, True, th.text_white)
            surf.set_alpha(alpha)
            screen.blit(surf, (panel_x + 15, panel_y + 86 + i * 26))

        if self._game_manager.state == GameState.PEEK_PHASE:
            action_label = "Click to Peek"
            action_color = PEEK_BLUE
        elif step["advance_on"] == "declare":
            action_label = "Click to Declare"
            action_color = DECLARE_RED
        elif step["advance_on"] == "pair_own":
            action_label = "Click to Pair"
            action_color = PAIR_TEAL
        elif self._game_manager.state == GameState.TURN_START:
            action_label = "Click to Draw"
            action_color = SWAP_GREEN
        else:
            action_label = step["advance_on"]
            action_color = (130, 130, 130)

        can_continue = self._chapter_complete
        c_color = th.signal_go if can_continue else action_color

        sw, sh = 470, 40
        self._skip_rect = pygame.Rect(panel_x + 15, panel_y + panel_h - 88, sw, sh)
        pygame.draw.rect(screen, (60, 60, 60), self._skip_rect, border_radius=8)
        pygame.draw.rect(screen, th.brass_700, self._skip_rect, 1, border_radius=8)
        sk = self._body_font.render("Skip", True, th.text_dim)
        sk.set_alpha(alpha)
        screen.blit(sk, sk.get_rect(center=self._skip_rect.center))

        bw, bh = 470, 40
        self._continue_rect = pygame.Rect(panel_x + 15, panel_y + panel_h - 42, bw, bh)
        pygame.draw.rect(screen, c_color, self._continue_rect, border_radius=8)
        pygame.draw.rect(screen, th.brass_500, self._continue_rect, 2, border_radius=8)
        cont_label = "Continue" if can_continue else action_label
        cs = self._body_font.render(cont_label, True, th.text_white)
        cs.set_alpha(alpha)
        screen.blit(cs, cs.get_rect(center=self._continue_rect.center))

    def _wrap(self, text, max_w):
        words = text.split()
        lines = []
        current = ""
        for w in words:
            test = current + (" " if current else "") + w
            if self._body_font.size(test)[0] <= max_w:
                current = test
            else:
                if current:
                    lines.append(current)
                current = w
        if current:
            lines.append(current)
        return lines


class FirstLaunchSplash:
    def __init__(self):
        self._fade = 0.0
        self.active = False
        self._title_font = None
        self._body_font = None
        self._btn_font = None
        self._tutorial_rect = None
        self._skip_rect = None

    def show(self):
        self.active = True
        self._fade = 0.0

    def update(self, dt):
        if self.active:
            self._fade = min(1.0, self._fade + dt * 2.5)

    def _ensure(self):
        if self._title_font is None:
            import typography as typo
            self._title_font = typo.display_bold(56)
            self._body_font = typo.header_italic(22)
            self._btn_font = typo.body_bold(22)

    def draw(self, screen):
        if not self.active:
            return
        self._ensure()
        th = theme.active()
        screen.fill(th.felt_rim)

        title = self._title_font.render("Welcome to Declare", True, th.brass_300)
        title.set_alpha(int(255 * self._fade))
        screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 280)))

        body = "First time at the table?"
        body_surf = self._body_font.render(body, True, th.text_white)
        body_surf.set_alpha(int(255 * self._fade))
        screen.blit(body_surf, body_surf.get_rect(center=(SCREEN_WIDTH // 2, 360)))

        body2 = "We can walk you through the rules in five minutes."
        body2_surf = self._body_font.render(body2, True, th.text_dim)
        body2_surf.set_alpha(int(255 * self._fade))
        screen.blit(body2_surf, body2_surf.get_rect(center=(SCREEN_WIDTH // 2, 396)))

        bw, bh = 280, 56
        cx = SCREEN_WIDTH // 2
        self._tutorial_rect = pygame.Rect(cx - bw - 20, 500, bw, bh)
        self._skip_rect = pygame.Rect(cx + 20, 500, bw, bh)

        pygame.draw.rect(screen, th.signal_go, self._tutorial_rect, border_radius=10)
        pygame.draw.rect(screen, th.brass_500, self._tutorial_rect, 2, border_radius=10)
        ts = self._btn_font.render("Start Tutorial", True, th.text_white)
        screen.blit(ts, ts.get_rect(center=self._tutorial_rect.center))

        pygame.draw.rect(screen, (60, 60, 60), self._skip_rect, border_radius=10)
        pygame.draw.rect(screen, th.brass_700, self._skip_rect, 2, border_radius=10)
        ss = self._btn_font.render("Skip - I know how to play", True, th.text_white)
        screen.blit(ss, ss.get_rect(center=self._skip_rect.center))

    def handle_event(self, event):
        if not self.active:
            return None
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._tutorial_rect and self._tutorial_rect.collidepoint(event.pos):
                self.active = False
                return "tutorial"
            if self._skip_rect and self._skip_rect.collidepoint(event.pos):
                self.active = False
                return "skip"
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                self.active = False
                return "tutorial"
            if event.key == pygame.K_ESCAPE:
                self.active = False
                return "skip"
        return None


from game.game_manager import GameManager, GameState
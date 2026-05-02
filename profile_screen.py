"""Profile / Stats / Achievements screen.

Three tabs: Stats, Achievements, Card Backs. All scrollable. Reads from
profile.json. Drawn over a felt background to match the rest of the game.
"""
import pygame

import theme
import audio
import profile as profile_mod
from config import SCREEN_WIDTH, SCREEN_HEIGHT, get_mobile_scale


class ProfileScreen:
    def __init__(self, screen):
        self.screen = screen
        self.tab = "stats"
        self.scroll = 0
        self._title_font = None
        self._tab_font = None
        self._body_font = None
        self._small_font = None
        self._number_font = None
        self.tab_rects = {}
        self.back_rect = None

    def _ensure(self):
        if self._title_font is None:
            import typography as typo
            from config import get_mobile_scale
            m = get_mobile_scale()
            self._title_font = typo.display_bold(int(38 * m))
            self._tab_font = typo.body_bold(int(22 * m))
            self._body_font = typo.body(int(18 * m))
            self._small_font = typo.body(int(14 * m))
            self._number_font = typo.header_bold(int(36 * m))

    def draw(self, prof):
        self._ensure()
        th = theme.active()

        bg = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        for i in range(SCREEN_HEIGHT):
            t = i / max(1, SCREEN_HEIGHT - 1)
            r = int(th.felt_rim[0] + (th.felt_deep[0] - th.felt_rim[0]) * t)
            g = int(th.felt_rim[1] + (th.felt_deep[1] - th.felt_rim[1]) * t)
            b = int(th.felt_rim[2] + (th.felt_deep[2] - th.felt_rim[2]) * t)
            pygame.draw.line(bg, (r, g, b), (0, i), (SCREEN_WIDTH, i))
        self.screen.blit(bg, (0, 0))

        title_surf = self._title_font.render("Profile & Stats", True, th.brass_300)
        self.screen.blit(title_surf, title_surf.get_rect(center=(SCREEN_WIDTH // 2, 60)))

        tabs = [("stats", "Stats"), ("achievements", "Achievements"),
                ("backs", "Card Backs")]
        tab_w = min(220, int(SCREEN_WIDTH * 0.086))
        tab_h = int(44 * get_mobile_scale())
        tab_y = 110
        total_w = tab_w * len(tabs)
        start_x = (SCREEN_WIDTH - total_w) // 2
        self.tab_rects = {}
        for i, (key, label) in enumerate(tabs):
            r = pygame.Rect(start_x + i * tab_w, tab_y, tab_w - 4, tab_h)
            self.tab_rects[key] = r
            active_tab = (key == self.tab)
            color = th.brass_500 if active_tab else (60, 60, 60)
            pygame.draw.rect(self.screen, color, r, border_radius=8)
            border_color = th.brass_300 if active_tab else th.brass_700
            pygame.draw.rect(self.screen, border_color, r, 2, border_radius=8)
            ts = self._tab_font.render(label, True, th.text_white)
            self.screen.blit(ts, ts.get_rect(center=r.center))

        if self.tab == "stats":
            self._draw_stats(prof, th)
        elif self.tab == "achievements":
            self._draw_achievements(prof, th)
        else:
            self._draw_backs(prof, th)

        bw, bh = int(180 * get_mobile_scale()), int(44 * get_mobile_scale())
        self.back_rect = pygame.Rect(40, SCREEN_HEIGHT - bh - 30, bw, bh)
        pygame.draw.rect(self.screen, (60, 60, 60), self.back_rect, border_radius=8)
        pygame.draw.rect(self.screen, th.brass_500, self.back_rect, 2, border_radius=8)
        bs = self._tab_font.render("← Back", True, th.text_white)
        self.screen.blit(bs, bs.get_rect(center=self.back_rect.center))

    def _draw_stats(self, prof, th):
        s = prof.stats
        cards = [
            ("Games Played", s.games_played),
            ("Games Won",    s.games_won),
            ("Win Rate",     f"{(s.games_won / s.games_played * 100):.0f}%" if s.games_played > 0 else "-"),
            ("Current Streak", s.current_win_streak),
            ("Longest Streak", s.longest_win_streak),
            ("Declares Won",   s.declares_won),
            ("Declares Lost",  s.declares_lost),
            ("Auto-Wins",      s.auto_wins),
            ("Pairs Made",     s.pairs_made),
            ("Powers Used",    s.powers_used),
            ("Reactive (right)", s.reactive_pairs_correct),
            ("Reactive (wrong)", s.reactive_pairs_wrong),
        ]
        gx = SCREEN_WIDTH // 2 - min(540, int(SCREEN_WIDTH * 0.21))
        gy = 200
        cw, ch = min(260, int(SCREEN_WIDTH * 0.10)), min(110, int(SCREEN_HEIGHT * 0.076))
        for i, (label, value) in enumerate(cards):
            col = i % 4
            row = i // 4
            rx = gx + col * (cw + 20)
            ry = gy + row * (ch + 20)
            r = pygame.Rect(rx, ry, cw, ch)
            pygame.draw.rect(self.screen, (*th.panel_bg, 220), r, border_radius=10)
            pygame.draw.rect(self.screen, th.brass_700, r, 1, border_radius=10)
            label_surf = self._small_font.render(label.upper(), True, th.brass_300)
            self.screen.blit(label_surf, (rx + 16, ry + 14))
            value_str = str(value)
            val_surf = self._number_font.render(value_str, True, th.text_white)
            self.screen.blit(val_surf, (rx + 16, ry + 40))

        if s.total_play_seconds > 0:
            mins = int(s.total_play_seconds // 60)
            tt = self._body_font.render(f"Total play time: {mins} minutes", True, th.text_dim)
            self.screen.blit(tt, (gx, gy + 280))

    def _draw_achievements(self, prof, th):
        gx = SCREEN_WIDTH // 2 - min(540, int(SCREEN_WIDTH * 0.21))
        gy = 200
        items = list(prof.achievements.values())
        cw, ch = min(350, int(SCREEN_WIDTH * 0.14)), min(70, int(SCREEN_HEIGHT * 0.049))
        cols = 3
        for i, ach in enumerate(items):
            col = i % cols
            row = i // cols
            rx = gx + col * (cw + 20)
            ry = gy + row * (ch + 12)
            r = pygame.Rect(rx, ry, cw, ch)
            unlocked = ach.get("unlocked", False)
            bg_color = (*th.panel_bg, 220) if not unlocked else (*th.panel_bg, 250)
            pygame.draw.rect(self.screen, bg_color, r, border_radius=8)
            border = th.brass_300 if unlocked else (60, 60, 60)
            pygame.draw.rect(self.screen, border, r, 2, border_radius=8)
            badge_x = rx + 16
            badge_y = ry + ch // 2
            badge_color = th.brass_300 if unlocked else (50, 50, 50)
            pygame.draw.circle(self.screen, badge_color, (badge_x, badge_y), 14)
            pygame.draw.circle(self.screen, th.brass_900, (badge_x, badge_y), 14, 2)
            star = self._small_font.render("*" if unlocked else "?", True, th.brass_900)
            self.screen.blit(star, star.get_rect(center=(badge_x, badge_y)))
            title_color = th.text_white if unlocked else th.text_muted
            t_surf = self._body_font.render(ach.get("title", ach["key"]), True, title_color)
            self.screen.blit(t_surf, (rx + 40, ry + 10))
            d_surf = self._small_font.render(ach.get("description", "")[:50],
                                              True, th.text_dim)
            self.screen.blit(d_surf, (rx + 40, ry + 36))

    def _draw_backs(self, prof, th):
        import card_render
        from config import CARD_WIDTH, CARD_HEIGHT
        styles = [
            ("classic",       "Classic",       True),
            ("deco_brass",    "Brass",         "deco_brass" in prof.unlocked_card_backs),
            ("deco_emerald",  "Emerald",       "deco_emerald" in prof.unlocked_card_backs),
            ("deco_obsidian", "Obsidian",      "deco_obsidian" in prof.unlocked_card_backs),
        ]
        gx = SCREEN_WIDTH // 2 - min(540, int(SCREEN_WIDTH * 0.21))
        gy = 200
        for i, (key, label, unlocked) in enumerate(styles):
            rx = gx + i * 280
            ry = gy + 20
            back_surf = card_render.paint_back(key if unlocked else "classic",
                                                CARD_WIDTH * 2, CARD_HEIGHT * 2)
            if not unlocked:
                lock = pygame.Surface((CARD_WIDTH * 2, CARD_HEIGHT * 2), pygame.SRCALPHA)
                lock.fill((0, 0, 0, 180))
                back_surf.blit(lock, (0, 0))
            self.screen.blit(back_surf, (rx, ry))
            label_color = th.brass_300 if unlocked else th.text_muted
            l_surf = self._tab_font.render(label, True, label_color)
            self.screen.blit(l_surf, l_surf.get_rect(midtop=(rx + CARD_WIDTH, ry + CARD_HEIGHT * 2 + 12)))
            if not unlocked:
                hint = self._small_font.render("Locked", True, th.text_muted)
                self.screen.blit(hint, hint.get_rect(midtop=(rx + CARD_WIDTH, ry + CARD_HEIGHT * 2 + 40)))

    def handle_event(self, event, prof):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for key, rect in self.tab_rects.items():
                if rect.collidepoint(event.pos):
                    self.tab = key
                    audio.play("click")
                    return None
            if self.back_rect and self.back_rect.collidepoint(event.pos):
                audio.play("click")
                return "back"
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                return "back"
            if event.key == pygame.K_LEFT:
                tabs = ["stats", "achievements", "backs"]
                idx = tabs.index(self.tab)
                self.tab = tabs[(idx - 1) % 3]
            if event.key == pygame.K_RIGHT:
                tabs = ["stats", "achievements", "backs"]
                idx = tabs.index(self.tab)
                self.tab = tabs[(idx + 1) % 3]
        return None


HOW_TO_SECTIONS = [
    ("Goal",
     "End the round with the lowest sum of card values. Get rid of all "
     "your cards for an automatic win."),
    ("Card Values",
     "Ace = 1.  2-10 = face value.  Jack = 11.  Queen = 12.  "
     "Red King = 13.  Black King = 0 (this is the best card to keep)."),
    ("Each Turn",
     "1. Draw a card from the deck.  2. Choose: play it, swap it into "
     "your hand, discard it, use its power, pair it with a known card, "
     "or declare.  3. Pass the turn."),
    ("Pairing",
     "If your drawn card matches the rank of a card you have seen, "
     "you can pair them - both go to discard. Pairing one of an "
     "opponent's cards forces them to take one of yours in return."),
    ("Reactive Pairing",
     "When ANY player plays a card, every other player has a brief "
     "window to drop a matching rank from their seen cards. Wrong card "
     "= penalty draw. Watch the gold banner."),
    ("Powers",
     "7 / 8: Peek at your own card.  9 / 10: Peek at an opponent's.  "
     "Jack: Skip your next turn.  Queen: Unseen Swap.  "
     "Red King: Seen Swap (you see the card first)."),
    ("Declare",
     "When you think you have the lowest hand-total, click Declare. "
     "If you do, you win. If you don't, your score is doubled. "
     "Use this carefully - you only get one shot."),
    ("Memory is Everything",
     "Cards you peek are marked with a gold dot. Pay attention to which "
     "ranks you've seen, what opponents have drawn, and what's been "
     "discarded. The whole game runs on what you remember."),
]


class HowToPlayScreen:
    def __init__(self, screen):
        self.screen = screen
        self.scroll = 0
        self._title_font = None
        self._head_font = None
        self._body_font = None
        self.back_rect = None

    def _ensure(self):
        if self._title_font is None:
            import typography as typo
            from config import get_mobile_scale
            m = get_mobile_scale()
            self._title_font = typo.display_bold(int(36 * m))
            self._head_font = typo.header_bold(int(22 * m))
            self._body_font = typo.body(int(18 * m))

    def draw(self):
        self._ensure()
        th = theme.active()

        bg = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        for i in range(SCREEN_HEIGHT):
            t = i / max(1, SCREEN_HEIGHT - 1)
            r = int(th.felt_rim[0] + (th.felt_deep[0] - th.felt_rim[0]) * t)
            g = int(th.felt_rim[1] + (th.felt_deep[1] - th.felt_rim[1]) * t)
            b = int(th.felt_rim[2] + (th.felt_deep[2] - th.felt_rim[2]) * t)
            pygame.draw.line(bg, (r, g, b), (0, i), (SCREEN_WIDTH, i))
        self.screen.blit(bg, (0, 0))

        title = self._title_font.render("How To Play", True, th.brass_300)
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 70)))

        col_w = min(720, SCREEN_WIDTH - 80)
        col_x = SCREEN_WIDTH // 2 - col_w // 2
        y = 140 - self.scroll
        for heading, body in HOW_TO_SECTIONS:
            h_surf = self._head_font.render(heading, True, th.brass_300)
            self.screen.blit(h_surf, (col_x, y))
            y += int(32 * get_mobile_scale())
            for line in self._wrap(body, col_w):
                if 0 < y < SCREEN_HEIGHT:
                    bs = self._body_font.render(line, True, th.text_white)
                    self.screen.blit(bs, (col_x, y))
                y += int(26 * get_mobile_scale())
            y += 14

        bw, bh = int(180 * get_mobile_scale()), int(44 * get_mobile_scale())
        self.back_rect = pygame.Rect(40, SCREEN_HEIGHT - bh - 30, bw, bh)
        pygame.draw.rect(self.screen, (60, 60, 60), self.back_rect, border_radius=8)
        pygame.draw.rect(self.screen, th.brass_500, self.back_rect, 2, border_radius=8)
        bs = self._head_font.render("← Back", True, th.text_white)
        self.screen.blit(bs, bs.get_rect(center=self.back_rect.center))

        scroll_hint = self._body_font.render("↑↓ scroll  ·  Esc back",
                                              True, th.text_dim)
        self.screen.blit(scroll_hint, (SCREEN_WIDTH - scroll_hint.get_width() - 30,
                                        SCREEN_HEIGHT - 40))

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                return "back"
            if event.key == pygame.K_DOWN:
                self.scroll = min(self.scroll + 40, 800)
            if event.key == pygame.K_UP:
                self.scroll = max(self.scroll - 40, 0)
        if event.type == pygame.MOUSEWHEEL:
            self.scroll = max(0, min(800, self.scroll - event.y * 30))
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.back_rect and self.back_rect.collidepoint(event.pos):
                return "back"
        return None

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

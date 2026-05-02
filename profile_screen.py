"""Profile / Stats / Achievements screen.

Four tabs: Stats, Achievements, Card Backs, Themes. All scrollable. Reads from
profile.json. Drawn over a felt background to match the rest of the game.
"""
import pygame

import theme
import audio
import profile as profile_mod
from config import SCREEN_WIDTH, SCREEN_HEIGHT


_TAB_KEYS = ["stats", "achievements", "backs", "themes"]


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
        self._theme_rects = {}

    def _ensure(self):
        if self._title_font is None:
            import typography as typo
            self._title_font = typo.display_bold(64)
            self._tab_font = typo.body_bold(36)
            self._body_font = typo.body(28)
            self._small_font = typo.body(22)
            self._number_font = typo.header_bold(56)

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
        self.screen.blit(title_surf, title_surf.get_rect(center=(SCREEN_WIDTH // 2, 96)))

        tabs = [("stats", "Stats"), ("achievements", "Achievements"),
                ("backs", "Card Backs"), ("themes", "Themes")]
        # Tab width tightened slightly so the new fourth tab fits within the
        # same horizontal budget as the previous 3-tab layout.
        tab_w = 296
        tab_y = 184
        tab_h = 70
        total_w = tab_w * len(tabs)
        start_x = (SCREEN_WIDTH - total_w) // 2
        self.tab_rects = {}
        for i, (key, label) in enumerate(tabs):
            r = pygame.Rect(start_x + i * tab_w, tab_y, tab_w - 8, tab_h)
            self.tab_rects[key] = r
            active_tab = (key == self.tab)
            color = th.brass_500 if active_tab else (60, 60, 60)
            pygame.draw.rect(self.screen, color, r, border_radius=12)
            border_color = th.brass_300 if active_tab else th.brass_700
            pygame.draw.rect(self.screen, border_color, r, 2, border_radius=12)
            ts = self._tab_font.render(label, True, th.text_white)
            self.screen.blit(ts, ts.get_rect(center=r.center))

        if self.tab == "stats":
            self._draw_stats(prof, th)
        elif self.tab == "achievements":
            self._draw_achievements(prof, th)
        elif self.tab == "backs":
            self._draw_backs(prof, th)
        else:
            self._draw_themes(prof, th)

        bw, bh = 288, 70
        self.back_rect = pygame.Rect(64, SCREEN_HEIGHT - bh - 48, bw, bh)
        pygame.draw.rect(self.screen, (60, 60, 60), self.back_rect, border_radius=12)
        pygame.draw.rect(self.screen, th.brass_500, self.back_rect, 2, border_radius=12)
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
        cols = 4
        cw, ch = 416, 176
        gap = 32
        grid_w = cols * cw + (cols - 1) * gap
        gx = (SCREEN_WIDTH - grid_w) // 2
        gy = 320
        for i, (label, value) in enumerate(cards):
            col = i % cols
            row = i // cols
            rx = gx + col * (cw + gap)
            ry = gy + row * (ch + gap)
            r = pygame.Rect(rx, ry, cw, ch)
            pygame.draw.rect(self.screen, (*th.panel_bg, 220), r, border_radius=16)
            pygame.draw.rect(self.screen, th.brass_700, r, 2, border_radius=16)
            label_surf = self._small_font.render(label.upper(), True, th.brass_300)
            self.screen.blit(label_surf, (rx + 26, ry + 22))
            value_str = str(value)
            val_surf = self._number_font.render(value_str, True, th.text_white)
            self.screen.blit(val_surf, (rx + 26, ry + 64))

        if s.total_play_seconds > 0:
            mins = int(s.total_play_seconds // 60)
            tt = self._body_font.render(f"Total play time: {mins} minutes", True, th.text_dim)
            self.screen.blit(tt, (gx, gy + 3 * (ch + gap) + 16))

    def _draw_achievements(self, prof, th):
        items = list(prof.achievements.values())
        cols = 3
        cw, ch = 560, 112
        gap_x, gap_y = 32, 20
        grid_w = cols * cw + (cols - 1) * gap_x
        gx = (SCREEN_WIDTH - grid_w) // 2
        gy = 320
        for i, ach in enumerate(items):
            col = i % cols
            row = i // cols
            rx = gx + col * (cw + gap_x)
            ry = gy + row * (ch + gap_y)
            r = pygame.Rect(rx, ry, cw, ch)
            unlocked = ach.get("unlocked", False)
            bg_color = (*th.panel_bg, 220) if not unlocked else (*th.panel_bg, 250)
            pygame.draw.rect(self.screen, bg_color, r, border_radius=12)
            border = th.brass_300 if unlocked else (60, 60, 60)
            pygame.draw.rect(self.screen, border, r, 2, border_radius=12)
            badge_x = rx + 32
            badge_y = ry + ch // 2
            badge_color = th.brass_300 if unlocked else (50, 50, 50)
            pygame.draw.circle(self.screen, badge_color, (badge_x, badge_y), 22)
            pygame.draw.circle(self.screen, th.brass_900, (badge_x, badge_y), 22, 2)
            star = self._body_font.render("*" if unlocked else "?", True, th.brass_900)
            self.screen.blit(star, star.get_rect(center=(badge_x, badge_y)))
            title_color = th.text_white if unlocked else th.text_muted
            t_surf = self._body_font.render(ach.get("title", ach["key"]), True, title_color)
            self.screen.blit(t_surf, (rx + 64, ry + 16))
            d_surf = self._small_font.render(ach.get("description", "")[:50],
                                              True, th.text_dim)
            self.screen.blit(d_surf, (rx + 64, ry + 58))

    def _draw_backs(self, prof, th):
        import card_render
        from config import CARD_WIDTH, CARD_HEIGHT
        styles = [
            ("classic",       "Classic",       0),
            ("deco_brass",    "Brass",         5),
            ("deco_emerald",  "Emerald",       15),
            ("deco_obsidian", "Obsidian",      40),
        ]
        pw, ph = int(CARD_WIDTH * 2.4), int(CARD_HEIGHT * 2.4)
        gap = 96
        total_w = len(styles) * pw + (len(styles) - 1) * gap
        gx = (SCREEN_WIDTH - total_w) // 2
        ry = 360
        wins = prof.stats.games_won
        for i, (key, label, threshold) in enumerate(styles):
            unlocked = key in prof.unlocked_card_backs
            rx = gx + i * (pw + gap)
            cached = card_render.paint_back(key, pw, ph)
            preview = cached if unlocked else cached.copy()
            if not unlocked:
                dim = pygame.Surface((pw, ph), pygame.SRCALPHA)
                pygame.draw.rect(dim, (0, 0, 0, 130), dim.get_rect(),
                                 border_radius=16)
                preview.blit(dim, (0, 0))
                lf = self._number_font.render("LOCKED", True, th.brass_300)
                preview.blit(lf, lf.get_rect(center=(pw // 2, ph // 2)))
            self.screen.blit(preview, (rx, ry))
            label_color = th.brass_300 if unlocked else th.text_muted
            l_surf = self._tab_font.render(label, True, label_color)
            self.screen.blit(l_surf, l_surf.get_rect(midtop=(rx + pw // 2, ry + ph + 26)))
            if not unlocked:
                progress = min(wins, threshold)
                hint_text = f"Win {threshold} games  ({progress}/{threshold})"
                hint = self._small_font.render(hint_text, True, th.brass_300)
                self.screen.blit(hint, hint.get_rect(midtop=(rx + pw // 2, ry + ph + 80)))

    def _draw_themes(self, prof, th):
        """Theme gallery: 4 preview cards horizontally — Parlor + 3 unlockables.
        Locked themes show their unlock condition + progress; unlocked themes
        are click-to-equip and the active one shows an 'Equipped' brass badge."""
        from theme import (
            THEME_LABELS, UNLOCKABLE_THEMES, THEME_UNLOCK_CONDITIONS,
        )

        # Theme keys in display order: Parlor first (always unlocked), then the
        # three unlockables in their canonical order (Saloon → Vegas → Minimal).
        display_keys = ["default"] + list(UNLOCKABLE_THEMES)
        unlocked_set = set(getattr(prof, "unlocked_themes", ["default"]))
        active_key = getattr(prof.settings, "theme", "default")

        # 4-up grid sized to fit within the screen with comfortable gaps.
        n = len(display_keys)
        pw, ph = 432, 320
        gap = 56
        total_w = n * pw + (n - 1) * gap
        gx = (SCREEN_WIDTH - total_w) // 2
        ry = 320

        self._theme_rects = {}
        s = prof.stats
        progress_lookup = {
            "saloon":  ("games_played", s.games_played),
            "vegas":   ("games_won",    s.games_won),
            "minimal": ("declares_won", s.declares_won),
        }

        for i, key in enumerate(display_keys):
            rx = gx + i * (pw + gap)
            unlocked = key in unlocked_set or key == "default"
            is_active = (key == active_key) and unlocked
            card_rect = pygame.Rect(rx, ry, pw, ph)
            self._theme_rects[key] = card_rect

            # Render the mini-felt preview within the card.
            preview_h = 200
            preview = self._render_theme_preview(key, pw - 24, preview_h)
            self.screen.blit(preview, (rx + 12, ry + 14))

            # Card frame.
            border = th.brass_300 if is_active else (th.brass_500 if unlocked else (60, 60, 60))
            pygame.draw.rect(self.screen, (*th.panel_bg, 230), card_rect, border_radius=14)
            pygame.draw.rect(self.screen, border, card_rect, 2, border_radius=14)

            # Re-blit preview over the panel bg so it sits on top of the frame fill.
            self.screen.blit(preview, (rx + 12, ry + 14))

            # Locked overlay: dark wash + condition text + progress.
            if not unlocked:
                veil = pygame.Surface((pw - 24, preview_h), pygame.SRCALPHA)
                pygame.draw.rect(veil, (0, 0, 0, 150), veil.get_rect(),
                                 border_radius=8)
                self.screen.blit(veil, (rx + 12, ry + 14))
                lf = self._number_font.render("LOCKED", True, th.brass_300)
                self.screen.blit(lf, lf.get_rect(
                    center=(rx + pw // 2, ry + 14 + preview_h // 2 - 6)))

            # Theme label.
            label_color = th.brass_300 if unlocked else th.text_muted
            l_surf = self._tab_font.render(
                THEME_LABELS.get(key, key), True, label_color)
            self.screen.blit(l_surf, l_surf.get_rect(
                midtop=(rx + pw // 2, ry + 14 + preview_h + 14)))

            # Status line: equipped badge, click-to-equip hint, or unlock condition.
            status_y = ry + 14 + preview_h + 14 + l_surf.get_height() + 10
            if is_active:
                badge_w, badge_h = 132, 30
                bx = rx + pw // 2 - badge_w // 2
                by = status_y
                pygame.draw.rect(self.screen, th.brass_300,
                                 pygame.Rect(bx, by, badge_w, badge_h),
                                 border_radius=badge_h // 2)
                pygame.draw.rect(self.screen, th.brass_900,
                                 pygame.Rect(bx, by, badge_w, badge_h),
                                 1, border_radius=badge_h // 2)
                bsurf = self._small_font.render("EQUIPPED", True, th.brass_900)
                self.screen.blit(bsurf, bsurf.get_rect(
                    center=(rx + pw // 2, by + badge_h // 2)))
            elif unlocked:
                hint = self._small_font.render("Click to equip", True, th.text_dim)
                self.screen.blit(hint, hint.get_rect(
                    midtop=(rx + pw // 2, status_y)))
            else:
                cond = THEME_UNLOCK_CONDITIONS.get(key, {})
                cond_label = cond.get("label", "")
                stat_key, current = progress_lookup.get(key, (None, 0))
                if stat_key:
                    target = cond.get(stat_key, 0)
                    progress = min(current, target)
                    text = f"{cond_label}  ({progress}/{target})"
                else:
                    text = cond_label
                hint = self._small_font.render(text, True, th.brass_300)
                self.screen.blit(hint, hint.get_rect(
                    midtop=(rx + pw // 2, status_y)))

    def _render_theme_preview(self, key, w, h):
        """Render a self-contained mini-felt + sample card-back for a theme.
        Theme-swap the active theme momentarily so card_render reads the right
        palette, then restore the previous theme so the gallery itself doesn't
        flicker into the previewed theme during paint."""
        import card_render
        prev = theme._active
        try:
            theme.set_active(theme.get_theme(key))
            t = theme.active()
            preview = pygame.Surface((w, h), pygame.SRCALPHA)

            # Mini felt: gradient body + brass border + lamp pool (if atmospheric).
            felt_layer = pygame.Surface((w, h), pygame.SRCALPHA)
            steps = 24
            cx, cy = w // 2, int(h * 0.48)
            rx_ = int(w * 0.46)
            ry_ = int(h * 0.42)
            for layer in range(steps, 0, -1):
                tt = layer / steps
                ease = 1.0 - (1.0 - tt) * (1.0 - tt)
                col = (
                    int(t.felt_rim[0] + (t.felt_mid[0] - t.felt_rim[0]) * (1 - ease)),
                    int(t.felt_rim[1] + (t.felt_mid[1] - t.felt_rim[1]) * (1 - ease)),
                    int(t.felt_rim[2] + (t.felt_mid[2] - t.felt_rim[2]) * (1 - ease)),
                    255,
                )
                sx = int(rx_ * tt)
                sy = int(ry_ * tt)
                pygame.draw.ellipse(
                    felt_layer, col,
                    pygame.Rect(cx - sx, cy - sy, sx * 2, sy * 2),
                )
            preview.fill(getattr(t, "felt_shadow", t.felt_rim))
            preview.blit(felt_layer, (0, 0))

            # Mini lamp pool — only on atmospheric themes (skipped on Minimal/HC).
            if (getattr(t, "is_atmospheric", True)
                    and not getattr(t, "high_contrast", False)):
                lamp = pygame.Surface((w, h), pygame.SRCALPHA)
                for i in range(28, 0, -1):
                    tt = i / 28
                    intensity = (1 - tt) ** 1.7
                    a = int(intensity * 70)
                    if a <= 0:
                        continue
                    pygame.draw.circle(
                        lamp, (*t.lamp_glow, a), (cx, cy - 4),
                        int(rx_ * 0.62 * tt),
                    )
                # Mask to oval shape.
                mask = pygame.Surface((w, h), pygame.SRCALPHA)
                pygame.draw.ellipse(
                    mask, (255, 255, 255, 255),
                    pygame.Rect(cx - rx_, cy - ry_, rx_ * 2, ry_ * 2))
                lamp.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
                preview.blit(lamp, (0, 0))

            # Brass border on the oval.
            pygame.draw.ellipse(preview, t.brass_700,
                                pygame.Rect(cx - rx_, cy - ry_, rx_ * 2, ry_ * 2), 2)
            pygame.draw.ellipse(preview, t.brass_500,
                                pygame.Rect(cx - rx_ - 3, cy - ry_ - 3,
                                            rx_ * 2 + 6, ry_ * 2 + 6), 1)

            # Sample card back centered on the oval — paint_back reads the
            # active theme's card_back palette, so the same "classic" style
            # renders with whatever colors the previewed theme defines.
            back_w = int(w * 0.20)
            back_h = int(back_w * 1.4)
            back = card_render.paint_back("classic", back_w, back_h)
            preview.blit(back, (cx - back_w // 2, cy - back_h // 2))

            # Outer soft frame so the preview sits cleanly on the panel.
            pygame.draw.rect(preview, t.brass_900,
                             preview.get_rect(), 1, border_radius=8)
            return preview
        finally:
            theme._active = prev

    def handle_event(self, event, prof):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for key, rect in self.tab_rects.items():
                if rect.collidepoint(event.pos):
                    self.tab = key
                    audio.play("click")
                    return None
            # Click-to-equip on the Themes tab.
            if self.tab == "themes":
                for key, rect in self._theme_rects.items():
                    if not rect.collidepoint(event.pos):
                        continue
                    unlocked_set = set(getattr(prof, "unlocked_themes", ["default"]))
                    if key != "default" and key not in unlocked_set:
                        return None
                    if prof.settings.theme == key:
                        return None
                    prof.settings.theme = key
                    theme.set_active(theme.get_theme(key))
                    profile_mod.save(prof)
                    audio.play("click")
                    return None
            if self.back_rect and self.back_rect.collidepoint(event.pos):
                audio.play("click")
                return "back"
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                return "back"
            if event.key == pygame.K_LEFT:
                idx = _TAB_KEYS.index(self.tab)
                self.tab = _TAB_KEYS[(idx - 1) % len(_TAB_KEYS)]
            if event.key == pygame.K_RIGHT:
                idx = _TAB_KEYS.index(self.tab)
                self.tab = _TAB_KEYS[(idx + 1) % len(_TAB_KEYS)]
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
            self._title_font = typo.display_bold(58)
            self._head_font = typo.header_bold(36)
            self._body_font = typo.body(28)

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
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 112)))

        col_w = 1280
        col_x = SCREEN_WIDTH // 2 - col_w // 2
        y = 224 - self.scroll
        for heading, body in HOW_TO_SECTIONS:
            h_surf = self._head_font.render(heading, True, th.brass_300)
            self.screen.blit(h_surf, (col_x, y))
            y += 52
            for line in self._wrap(body, col_w):
                if 0 < y < SCREEN_HEIGHT:
                    bs = self._body_font.render(line, True, th.text_white)
                    self.screen.blit(bs, (col_x, y))
                y += 42
            y += 22

        bw, bh = 288, 70
        self.back_rect = pygame.Rect(64, SCREEN_HEIGHT - bh - 48, bw, bh)
        pygame.draw.rect(self.screen, (60, 60, 60), self.back_rect, border_radius=12)
        pygame.draw.rect(self.screen, th.brass_500, self.back_rect, 2, border_radius=12)
        bs = self._head_font.render("← Back", True, th.text_white)
        self.screen.blit(bs, bs.get_rect(center=self.back_rect.center))

        scroll_hint = self._body_font.render("↑↓ scroll  ·  Esc back",
                                              True, th.text_dim)
        self.screen.blit(scroll_hint, (SCREEN_WIDTH - scroll_hint.get_width() - 48,
                                        SCREEN_HEIGHT - 64))

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

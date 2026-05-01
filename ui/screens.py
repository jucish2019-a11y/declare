import pygame
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))))

from config import (
    SCREEN_WIDTH, SCREEN_HEIGHT, BG_GREEN, BG_DARK, CARD_WHITE, CARD_BACK_BLUE,
    CARD_BACK_PATTERN, CARD_SHADOW, BLACK, RED, GOLD, TEXT_WHITE, TEXT_BLACK,
    TEXT_DIM, HIGHLIGHT, DIM, PANEL_BG, PANEL_BORDER, POWER_GLOW, EMPTY_SLOT,
    DECLARE_RED, DECLARE_RED_HOVER, SWAP_GREEN, SWAP_GREEN_HOVER,
    PEEK_BLUE, PEEK_BLUE_HOVER,
    DISCARD_ORANGE, DISCARD_ORANGE_HOVER, PAIR_TEAL, PAIR_TEAL_HOVER,
    CARD_WIDTH, CARD_HEIGHT, CORNER_RADIUS, CARD_SPREAD, HAND_SIZE,
    DECK_CENTER, DRAWN_CARD_POS, DISCARD_POS,
    PLAYER_BOTTOM, PLAYER_TOP, PLAYER_LEFT, PLAYER_RIGHT,
    TITLE_FONT_SIZE, SUBTITLE_FONT_SIZE, UI_FONT_SIZE, LOG_FONT_SIZE,
    SMALL_FONT_SIZE, CARD_FONT_SIZE, CARD_BIG_FONT_SIZE, get_mobile_scale,
)


class Button:
    def __init__(self, x, y, w, h, text, color, hover_color, text_color=TEXT_WHITE):
        self.rect = pygame.Rect(x - w // 2, y - h // 2, w, h)
        self.text = text
        self.color = color
        self.hover_color = hover_color
        self.text_color = text_color
        self.is_hovered = False

    def draw(self, screen, font):
        color = self.hover_color if self.is_hovered else self.color

        shadow_surf = pygame.Surface((self.rect.width + 4, self.rect.height + 4), pygame.SRCALPHA)
        pygame.draw.rect(shadow_surf, (0, 0, 0, 60), (2, 3, self.rect.width, self.rect.height), border_radius=CORNER_RADIUS)
        screen.blit(shadow_surf, (self.rect.x - 2, self.rect.y + 3))

        pygame.draw.rect(screen, color, self.rect, border_radius=CORNER_RADIUS)

        c_r = max(color[0] - 35, 0)
        c_g = max(color[1] - 35, 0)
        c_b = max(color[2] - 35, 0)
        pygame.draw.line(screen, (c_r, c_g, c_b),
                         (self.rect.left + 3, self.rect.bottom - 3),
                         (self.rect.right - 3, self.rect.bottom - 3), 2)
        pygame.draw.line(screen, (c_r, c_g, c_b),
                         (self.rect.right - 3, self.rect.top + 3),
                         (self.rect.right - 3, self.rect.bottom - 3), 2)
        l_r = min(color[0] + 40, 255)
        l_g = min(color[1] + 40, 255)
        l_b = min(color[2] + 40, 255)
        pygame.draw.line(screen, (l_r, l_g, l_b),
                         (self.rect.left + 3, self.rect.top + 3),
                         (self.rect.right - 3, self.rect.top + 3), 2)
        pygame.draw.line(screen, (l_r, l_g, l_b),
                         (self.rect.left + 3, self.rect.top + 3),
                         (self.rect.left + 3, self.rect.bottom - 3), 2)

        pygame.draw.rect(screen, BLACK, self.rect, width=2, border_radius=CORNER_RADIUS)
        text_surf = font.render(self.text, True, self.text_color)
        text_rect = text_surf.get_rect(center=self.rect.center)
        screen.blit(text_surf, text_rect)

    def is_clicked(self, mouse_pos):
        # Polling pygame.mouse.get_pressed() doesn't work for touch
        # Callers should check button-down events against rect instead
        return self.rect.collidepoint(mouse_pos)

    def update_hover(self, mouse_pos):
        self.is_hovered = self.rect.collidepoint(mouse_pos)


import typography as typo


def _get_font(size, bold=False):
    """Legacy helper - defaults to body face. Most screens now call typo
    families directly (display/header/body) for proper typographic hierarchy."""
    return typo.body_bold(size) if bold else typo.body(size)


class MenuScreen:
    def __init__(self, screen):
        self.screen = screen
        scale = get_mobile_scale()
        self.title_font = typo.display_bold(int(TITLE_FONT_SIZE * 1.4))
        self.subtitle_font = typo.header_italic(int(SUBTITLE_FONT_SIZE * 1.1))
        self.button_font = typo.body_bold(int(UI_FONT_SIZE * scale))
        cx = SCREEN_WIDTH // 2
        bw = int(320 * scale)
        bh = int(56 * scale)
        bsp = int(8 * scale)
        base_y = int(SCREEN_HEIGHT * 0.58)
        self.play_button = Button(cx, base_y, bw, bh, "Play", SWAP_GREEN, SWAP_GREEN_HOVER)
        self.tutorial_button = Button(cx, base_y + bh + bsp, bw, int(48 * scale), "Tutorial", PEEK_BLUE, PEEK_BLUE_HOVER)
        self.how_to_button = Button(cx, base_y + bh + int(48 * scale) + bsp * 2, bw, int(44 * scale), "How To Play", PAIR_TEAL, PAIR_TEAL_HOVER)
        self.profile_button = Button(cx, base_y + bh + int(48 * scale) + int(44 * scale) + bsp * 3, bw, int(44 * scale), "Profile & Stats", DISCARD_ORANGE, DISCARD_ORANGE_HOVER)
        self.quit_button = Button(cx, base_y + bh + int(48 * scale) + int(44 * scale) * 2 + bsp * 4, bw, int(44 * scale), "Quit", DECLARE_RED, DECLARE_RED_HOVER)
        self.new_game_button = self.play_button
        self.buttons = [self.play_button, self.tutorial_button, self.how_to_button,
                        self.profile_button, self.quit_button]
        self._t = 0.0

    def _draw_card_back_medallion(self, surface, cx, cy, scale=1.0):
        w, h = int(44 * scale), int(30 * scale)
        hw, hh = w // 2, h // 2
        fill = (50, 85, 155)
        hi = (190, 210, 240)
        lo = (30, 55, 120)
        oval_rect = pygame.Rect(cx - hw, cy - hh, w, h)
        pygame.draw.ellipse(surface, fill, oval_rect)
        pygame.draw.ellipse(surface, hi, oval_rect, 1)
        left_curl = [
            (cx - hw, cy),
            (cx - hw - int(8 * scale), cy - int(4 * scale)),
            (cx - hw - int(6 * scale), cy - int(10 * scale)),
            (cx - hw + int(2 * scale), cy - int(8 * scale)),
        ]
        right_curl = [
            (cx + hw, cy),
            (cx + hw + int(8 * scale), cy - int(4 * scale)),
            (cx + hw + int(6 * scale), cy - int(10 * scale)),
            (cx + hw - int(2 * scale), cy - int(8 * scale)),
        ]
        pygame.draw.lines(surface, fill, False, left_curl, 2)
        pygame.draw.lines(surface, hi, False, left_curl, 1)
        pygame.draw.lines(surface, fill, False, right_curl, 2)
        pygame.draw.lines(surface, hi, False, right_curl, 1)
        inner_diamond = [
            (cx, cy - int(10 * scale)), (cx + int(8 * scale), cy),
            (cx, cy + int(10 * scale)), (cx - int(8 * scale), cy)
        ]
        pygame.draw.polygon(surface, lo, inner_diamond)
        pygame.draw.polygon(surface, hi, inner_diamond, 1)
        dot = pygame.Rect(cx - 2, cy - 2, 4, 4)
        pygame.draw.rect(surface, hi, dot, border_radius=1)

    def _draw_menu_card_back(self, cx, cy, angle=0):
        surf = pygame.Surface((CARD_WIDTH + 20, CARD_HEIGHT + 20), pygame.SRCALPHA)
        rect = pygame.Rect(10, 10, CARD_WIDTH, CARD_HEIGHT)
        pygame.draw.rect(surf, CARD_BACK_BLUE, rect, border_radius=CORNER_RADIUS)
        inner = pygame.Rect(16, 16, CARD_WIDTH - 12, CARD_HEIGHT - 12)
        pygame.draw.rect(surf, CARD_BACK_PATTERN, inner, border_radius=CORNER_RADIUS - 2)
        line_color = (50, 90, 170, 40)
        inner_w, inner_h = CARD_WIDTH - 20, CARD_HEIGHT - 20
        cross_surf = pygame.Surface((inner_w, inner_h), pygame.SRCALPHA)
        for i in range(0, max(inner_w, inner_h), 12):
            if i < inner_w:
                pygame.draw.line(cross_surf, line_color, (i, 0), (i, inner_h))
            if i < inner_h:
                pygame.draw.line(cross_surf, line_color, (0, i), (inner_w, i))
        surf.blit(cross_surf, (10, 10))
        self._draw_card_back_medallion(surf, 10 + CARD_WIDTH // 2, 10 + CARD_HEIGHT // 2)
        pygame.draw.rect(surf, TEXT_WHITE, rect, 1, border_radius=CORNER_RADIUS)
        if angle != 0:
            surf = pygame.transform.rotate(surf, angle)
        self.screen.blit(surf, (cx - (CARD_WIDTH + 20) // 2, cy - (CARD_HEIGHT + 20) // 2))

    def draw(self):
        import theme as theme_mod
        import math as _math
        import card_render
        th = theme_mod.active()
        self._t += 1 / 60
        bg = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        for i in range(SCREEN_HEIGHT):
            t = i / max(1, SCREEN_HEIGHT - 1)
            r = int(th.felt_rim[0] * (1 - t * 0.4) + th.felt_deep[0] * t * 0.6)
            g = int(th.felt_rim[1] * (1 - t * 0.4) + th.felt_deep[1] * t * 0.6)
            b = int(th.felt_rim[2] * (1 - t * 0.4) + th.felt_deep[2] * t * 0.6)
            pygame.draw.line(bg, (r, g, b), (0, i), (SCREEN_WIDTH, i))
        self.screen.blit(bg, (0, 0))

        # lamp glow removed

        card_fan = [(-180, 380, -16), (-90, 370, -8), (0, 365, 0), (90, 370, 8), (180, 380, 16)]
        for dx, cy, angle in card_fan:
            cx = SCREEN_WIDTH // 2 + dx
            back_surf = card_render.paint_back("classic", CARD_WIDTH, CARD_HEIGHT)
            scaled = pygame.transform.smoothscale(back_surf, (int(CARD_WIDTH * 1.4), int(CARD_HEIGHT * 1.4)))
            if angle:
                scaled = pygame.transform.rotate(scaled, angle)
            silhouette = scaled.copy()
            silhouette.fill((0, 0, 0, 255), special_flags=pygame.BLEND_RGBA_MULT)
            sw, sh = silhouette.get_size()
            blur_w = max(1, sw // 5)
            blur_h = max(1, sh // 5)
            soft = pygame.transform.smoothscale(
                pygame.transform.smoothscale(silhouette, (blur_w, blur_h)),
                (sw, sh),
            )
            soft.set_alpha(110)
            self.screen.blit(soft, (cx - sw // 2 + 3, cy - sh // 2 + 6))
            self.screen.blit(scaled, (cx - scaled.get_width() // 2, cy - scaled.get_height() // 2))

        for offset, alpha in ((6, 60), (3, 110), (0, 255)):
            t_color = th.brass_300 if alpha == 255 else th.brass_700
            t_surf = typo.render_with_letter_spacing(
                self.title_font, "DECLARE", t_color, spacing_px=10,
            )
            t_surf.set_alpha(alpha)
            r = t_surf.get_rect(center=(SCREEN_WIDTH // 2 + offset, 160 + offset))
            self.screen.blit(t_surf, r)

        flourish_y = 212
        line_w = 220
        cx = SCREEN_WIDTH // 2
        pygame.draw.line(self.screen, th.brass_500, (cx - line_w, flourish_y),
                         (cx - 30, flourish_y), 1)
        pygame.draw.line(self.screen, th.brass_500, (cx + 30, flourish_y),
                         (cx + line_w, flourish_y), 1)
        pygame.draw.polygon(self.screen, th.brass_500,
                            [(cx, flourish_y - 5), (cx - 12, flourish_y), (cx, flourish_y + 5), (cx + 12, flourish_y)])

        subtitle_surf = self.subtitle_font.render("A Card Game of Memory & Strategy",
                                                   True, th.text_dim)
        self.screen.blit(subtitle_surf, subtitle_surf.get_rect(center=(SCREEN_WIDTH // 2, 240)))

        for button in self.buttons:
            button.draw(self.screen, self.button_font)

        footer_font = self.button_font
        footer = footer_font.render("v1.0 - Built with care", True, th.text_muted)
        self.screen.blit(footer, (16, SCREEN_HEIGHT - 28))

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            for button in self.buttons:
                button.update_hover(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.play_button.is_clicked(event.pos):
                return 'new_game'
            if self.tutorial_button.is_clicked(event.pos):
                return 'tutorial'
            if self.how_to_button.is_clicked(event.pos):
                return 'how_to_play'
            if self.profile_button.is_clicked(event.pos):
                return 'profile'
            if self.quit_button.is_clicked(event.pos):
                return 'quit'
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                return 'new_game'
            if event.key == pygame.K_t:
                return 'tutorial'
            if event.key == pygame.K_h:
                return 'how_to_play'
            if event.key == pygame.K_p:
                return 'profile'
            if event.key == pygame.K_q:
                return 'quit'
        return None


class SetupScreen:
    AI_PERSONAS = [
        {"name": "Marcus",  "diff": "medium", "quip": "Plays the long game."},
        {"name": "Vivian",  "diff": "hard",   "quip": "Counts every card."},
        {"name": "Cassio",  "diff": "easy",   "quip": "All bluff, no plan."},
        {"name": "Reine",   "diff": "hard",   "quip": "Cold and patient."},
        {"name": "Tobias",  "diff": "medium", "quip": "Loves a risky pair."},
        {"name": "Iliana",  "diff": "medium", "quip": "Reads faces like books."},
    ]

    DIFFICULTY_LABEL = {"easy": "Easy", "medium": "Medium", "hard": "Hard"}

    def __init__(self, screen, num_players=2):
        self.screen = screen
        scale = get_mobile_scale()
        self.title_font = typo.display_bold(int(TITLE_FONT_SIZE * 1.1))
        self.subtitle_font = typo.header_italic(SUBTITLE_FONT_SIZE)
        self.label_font = typo.body(int(UI_FONT_SIZE * scale))
        self.button_font = typo.body_bold(int(UI_FONT_SIZE * scale))
        self.input_font = typo.body(SMALL_FONT_SIZE + 2)
        self.small_font = typo.body(13)
        self.section_font = typo.header_bold(14)
        self.num_players = num_players
        self.players_config = []
        import random as _r
        ai_pool = _r.sample(self.AI_PERSONAS, k=min(4, len(self.AI_PERSONAS)))
        for i in range(4):
            if i == 0:
                self.players_config.append({
                    "name": "You", "is_human": True, "difficulty": "medium",
                    "quip": "",
                })
            else:
                persona = ai_pool[i - 1]
                self.players_config.append({
                    "name": persona["name"],
                    "is_human": False,
                    "difficulty": persona["diff"],
                    "quip": persona["quip"],
                })
        self.active_input = None
        self._t = 0.0

        self.player_count_rects = {}
        self._diff_rects = {}
        self._toggle_rects = {}
        self._name_rects = {}

        self.start_button = Button(SCREEN_WIDTH // 2, int(SCREEN_HEIGHT * 0.88), int(320 * scale), int(56 * scale),
                                   "Start Match", SWAP_GREEN, SWAP_GREEN_HOVER)
        self.back_button = Button(120, 60, int(140 * scale), int(40 * scale),
                                  "← Back", DECLARE_RED, DECLARE_RED_HOVER)

    def _draw_background(self):
        import theme as theme_mod
        import math as _math
        th = theme_mod.active()
        self._t += 1 / 60
        bg = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        for i in range(SCREEN_HEIGHT):
            t = i / max(1, SCREEN_HEIGHT - 1)
            r = int(th.felt_rim[0] * (1 - t * 0.4) + th.felt_deep[0] * t * 0.6)
            g = int(th.felt_rim[1] * (1 - t * 0.4) + th.felt_deep[1] * t * 0.6)
            b = int(th.felt_rim[2] * (1 - t * 0.4) + th.felt_deep[2] * t * 0.6)
            pygame.draw.line(bg, (r, g, b), (0, i), (SCREEN_WIDTH, i))
        self.screen.blit(bg, (0, 0))
        # lamp glow removed

    def draw(self):
        import theme as theme_mod
        th = theme_mod.active()
        self._draw_background()

        for offset, alpha in ((4, 70), (2, 130), (0, 255)):
            t_color = th.brass_300 if alpha == 255 else th.brass_700
            t_surf = typo.render_with_letter_spacing(
                self.title_font, "SETUP THE TABLE", t_color, spacing_px=4,
            )
            t_surf.set_alpha(alpha)
            self.screen.blit(t_surf, t_surf.get_rect(center=(SCREEN_WIDTH // 2 + offset, 100 + offset)))

        sub = self.subtitle_font.render("Choose your seats - name yourself, set opponents.",
                                          True, th.text_dim)
        self.screen.blit(sub, sub.get_rect(center=(SCREEN_WIDTH // 2, 154)))

        cy = 210
        sec = self.section_font.render("NUMBER OF PLAYERS", True, th.brass_300)
        self.screen.blit(sec, sec.get_rect(center=(SCREEN_WIDTH // 2, cy)))
        cy += 30
        self.player_count_rects = {}
        bw, bh = 90, 50
        spacing = 14
        total_w = bw * 3 + spacing * 2
        start_x = SCREEN_WIDTH // 2 - total_w // 2
        for idx, count in enumerate([2, 3, 4]):
            r = pygame.Rect(start_x + idx * (bw + spacing), cy, bw, bh)
            self.player_count_rects[count] = r
            active = (count == self.num_players)
            color = th.brass_500 if active else (50, 50, 50)
            border = th.brass_300 if active else (90, 90, 90)
            pygame.draw.rect(self.screen, color, r, border_radius=10)
            pygame.draw.rect(self.screen, border, r, 2, border_radius=10)
            ts = self.title_font.render(str(count), True, th.text_white if active else th.text_dim)
            self.screen.blit(ts, ts.get_rect(center=r.center))

        seat_top = int(SCREEN_HEIGHT * 0.38)
        seat_h = 96
        seat_gap = 12
        seat_w = min(920, SCREEN_WIDTH - 40)
        seat_x = SCREEN_WIDTH // 2 - seat_w // 2
        self._diff_rects = {}
        self._toggle_rects = {}
        self._name_rects = {}
        for i in range(self.num_players):
            y = seat_top + i * (seat_h + seat_gap)
            self._draw_seat_card(i, seat_x, y, seat_w, seat_h, th)

        self.start_button.draw(self.screen, self.button_font)
        self.back_button.draw(self.screen, self.input_font)

    def _draw_seat_card(self, i, x, y, w, h, th):
        config = self.players_config[i]
        is_human = config["is_human"]

        shadow = pygame.Surface((w + 8, h + 8), pygame.SRCALPHA)
        pygame.draw.rect(shadow, (0, 0, 0, 120), (4, 6, w, h), border_radius=12)
        self.screen.blit(shadow, (x - 4, y))

        card = pygame.Surface((w, h), pygame.SRCALPHA)
        bg_color = (28, 38, 32, 240) if is_human else (28, 32, 42, 240)
        pygame.draw.rect(card, bg_color, card.get_rect(), border_radius=12)
        accent_w = 6
        accent_color = th.you_cyan if is_human else th.brass_500
        pygame.draw.rect(card, accent_color, pygame.Rect(0, 0, accent_w, h),
                         border_top_left_radius=12, border_bottom_left_radius=12)
        pygame.draw.rect(card, th.brass_700, card.get_rect(), 1, border_radius=12)
        self.screen.blit(card, (x, y))

        avatar_x = x + 38
        avatar_y = y + h // 2
        if is_human:
            pygame.draw.circle(self.screen, (40, 90, 100), (avatar_x, avatar_y), 26)
            pygame.draw.circle(self.screen, th.you_cyan, (avatar_x, avatar_y), 26, 2)
        else:
            pygame.draw.circle(self.screen, (60, 50, 30), (avatar_x, avatar_y), 26)
            pygame.draw.circle(self.screen, th.brass_300, (avatar_x, avatar_y), 26, 2)
        initial_font = typo.header_bold(26)
        initial = initial_font.render(config["name"][0].upper() if config["name"] else "?",
                                       True, th.text_white)
        self.screen.blit(initial, initial.get_rect(center=(avatar_x, avatar_y)))

        seat_label = self.small_font.render(f"SEAT {i + 1}", True, th.brass_300)
        self.screen.blit(seat_label, (x + 78, y + 16))

        name_x = x + 78
        name_y = y + 32
        name_w = 260
        name_h = 32
        name_rect = pygame.Rect(name_x, name_y, name_w, name_h)
        self._name_rects[i] = name_rect
        focus = (self.active_input == i)
        pygame.draw.rect(self.screen, (244, 236, 216), name_rect, border_radius=6)
        pygame.draw.rect(self.screen, th.brass_300 if focus else (140, 130, 100),
                         name_rect, 2, border_radius=6)
        n_surf = self.input_font.render(config["name"], True, (30, 30, 30))
        self.screen.blit(n_surf, (name_rect.x + 10, name_rect.y + 7))
        if focus:
            cursor_x = name_rect.x + 10 + n_surf.get_width() + 1
            if (pygame.time.get_ticks() // 500) % 2 == 0:
                pygame.draw.line(self.screen, (30, 30, 30),
                                 (cursor_x, name_rect.y + 6),
                                 (cursor_x, name_rect.y + name_rect.height - 6), 2)

        if not is_human and config.get("quip"):
            quip = self.small_font.render(config["quip"], True, th.text_dim)
            self.screen.blit(quip, (name_x, y + h - 22))

        if is_human:
            tip = self.small_font.render("Click name to edit  ·  This is you",
                                          True, th.you_cyan)
            self.screen.blit(tip, (name_x, y + h - 22))

        # Responsive layout: place toggle and difficulty based on seat width
        toggle_w = min(124, max(100, (w - 400) // 3))
        toggle_x = x + min(380, w - 300)
        toggle_y = y + h // 2 - 16
        toggle_h = 32
        toggle_rect = pygame.Rect(toggle_x, toggle_y, toggle_w, toggle_h)
        self._toggle_rects[i] = toggle_rect
        toggle_color = (60, 130, 90) if is_human else (60, 100, 160)
        pygame.draw.rect(self.screen, toggle_color, toggle_rect, border_radius=16)
        pygame.draw.rect(self.screen, th.brass_500, toggle_rect, 1, border_radius=16)
        knob_x = toggle_rect.right - 16 if is_human else toggle_rect.x + 16
        pygame.draw.circle(self.screen, th.text_white, (knob_x, toggle_rect.centery), 12)
        label_txt = "Human" if is_human else "AI"
        ts = self.small_font.render(label_txt, True, th.text_white)
        if is_human:
            self.screen.blit(ts, (toggle_rect.x + 14, toggle_rect.centery - ts.get_height() // 2))
        else:
            self.screen.blit(ts, (toggle_rect.right - 14 - ts.get_width(),
                                   toggle_rect.centery - ts.get_height() // 2))

        if not is_human:
            diff_x = toggle_x + toggle_w + 16
            diff_y = y + h // 2 - 16
            self._diff_rects[i] = {}
            label = self.small_font.render("DIFFICULTY", True, th.brass_300)
            self.screen.blit(label, (diff_x, diff_y - 18))
            for j, diff in enumerate(["easy", "medium", "hard"]):
                bw_btn = min(84, max(60, (w - diff_x - x - 20) // 3 - 4))
                bh_btn = 32
                br = pygame.Rect(diff_x + j * (bw_btn + 4), diff_y, bw_btn, bh_btn)
                self._diff_rects[i][diff] = br
                active = (config["difficulty"] == diff)
                color = th.brass_500 if active else (50, 50, 50)
                border = th.brass_300 if active else (90, 90, 90)
                pygame.draw.rect(self.screen, color, br, border_radius=6)
                pygame.draw.rect(self.screen, border, br, 1, border_radius=6)
                ts2 = self.small_font.render(self.DIFFICULTY_LABEL[diff],
                                              True, th.text_white if active else th.text_dim)
                self.screen.blit(ts2, ts2.get_rect(center=br.center))

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.start_button.update_hover(event.pos)
            self.back_button.update_hover(event.pos)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for count, rect in self.player_count_rects.items():
                if rect.collidepoint(event.pos):
                    self.num_players = count
                    return None

            for i in range(self.num_players):
                if i in self._toggle_rects and self._toggle_rects[i].collidepoint(event.pos):
                    self.players_config[i]["is_human"] = not self.players_config[i]["is_human"]
                    if self.players_config[i]["is_human"]:
                        if self.players_config[i]["name"] in [p["name"] for p in self.AI_PERSONAS]:
                            self.players_config[i]["name"] = "You"
                        self.players_config[i]["quip"] = ""
                    else:
                        used_names = {p["name"] for p in self.players_config if not p["is_human"]}
                        for persona in self.AI_PERSONAS:
                            if persona["name"] not in used_names:
                                self.players_config[i]["name"] = persona["name"]
                                self.players_config[i]["difficulty"] = persona["diff"]
                                self.players_config[i]["quip"] = persona["quip"]
                                break
                    if self.active_input == i:
                        self.active_input = None
                    return None

                if i in self._diff_rects:
                    for diff, dr in self._diff_rects[i].items():
                        if dr.collidepoint(event.pos):
                            self.players_config[i]["difficulty"] = diff
                            return None

                if i in self._name_rects and self._name_rects[i].collidepoint(event.pos):
                    self.active_input = i
                    return None

            if self.active_input is not None:
                self.active_input = None

            if self.start_button.is_clicked(event.pos):
                return 'start_game'
            if self.back_button.is_clicked(event.pos):
                return 'back'

        if event.type == pygame.KEYDOWN and self.active_input is not None:
            i = self.active_input
            if i < self.num_players:
                if event.key == pygame.K_BACKSPACE:
                    self.players_config[i]["name"] = self.players_config[i]["name"][:-1]
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_TAB):
                    self.active_input = None
                elif event.key == pygame.K_ESCAPE:
                    self.active_input = None
                elif (len(self.players_config[i]["name"]) < 20
                      and event.unicode.isprintable() and event.unicode != ''):
                    self.players_config[i]["name"] += event.unicode
        elif event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                return 'start_game'
            if event.key == pygame.K_ESCAPE:
                return 'back'
        return None


class PeekScreen:
    def __init__(self, screen, hand_size: int, peek_count: int, peek_seconds: float):
        self.screen = screen
        scale = get_mobile_scale()
        self.hand_size = hand_size
        self.peek_count = peek_count
        self.peeking = set(range(hand_size - peek_count, hand_size)) if peek_count > 0 else set()
        self.title_font = typo.display_bold(TITLE_FONT_SIZE)
        self.subtitle_font = typo.header_italic(SUBTITLE_FONT_SIZE)
        self.label_font = typo.body(UI_FONT_SIZE)
        self.button_font = typo.body_bold(int(UI_FONT_SIZE * scale))
        self.card_font = typo.header_bold(CARD_FONT_SIZE)
        self.small_font = typo.body(SMALL_FONT_SIZE)
        self.max_time = peek_seconds
        self.elapsed = 0.0
        self.revealed = True
        self.done_button = Button(SCREEN_WIDTH // 2, int(SCREEN_HEIGHT * 0.78), int(320 * scale), int(56 * scale), "I've Memorized - Continue",
                                   SWAP_GREEN, SWAP_GREEN_HOVER)

    def _draw_background(self):
        import theme as theme_mod
        th = theme_mod.active()
        bg = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        for i in range(SCREEN_HEIGHT):
            t = i / max(1, SCREEN_HEIGHT - 1)
            r = int(th.felt_rim[0] * (1 - t * 0.4) + th.felt_deep[0] * t * 0.6)
            g = int(th.felt_rim[1] * (1 - t * 0.4) + th.felt_deep[1] * t * 0.6)
            b = int(th.felt_rim[2] * (1 - t * 0.4) + th.felt_deep[2] * t * 0.6)
            pygame.draw.line(bg, (r, g, b), (0, i), (SCREEN_WIDTH, i))
        self.screen.blit(bg, (0, 0))
        # lamp glow removed

    def draw(self, game_manager):
        import theme as theme_mod
        import card_render
        th = theme_mod.active()
        self._draw_background()

        for offset, alpha in ((4, 70), (2, 130), (0, 255)):
            t_color = th.brass_300 if alpha == 255 else th.brass_700
            t_surf = typo.render_with_letter_spacing(
                self.title_font, "STUDY YOUR HAND", t_color, spacing_px=6,
            )
            t_surf.set_alpha(alpha)
            self.screen.blit(t_surf, t_surf.get_rect(center=(SCREEN_WIDTH // 2 + offset,
                                                               110 + offset)))

        if self.peek_count == 0:
            sub = self.subtitle_font.render(
                "No cards to peek this round - go in blind.", True, th.text_dim)
            self.screen.blit(sub, sub.get_rect(center=(SCREEN_WIDTH // 2, 180)))
        else:
            sub = self.subtitle_font.render(
                f"Memorize your bottom {self.peek_count} card{'s' if self.peek_count > 1 else ''} - "
                "they vanish when the timer runs out.",
                True, th.text_dim,
            )
            self.screen.blit(sub, sub.get_rect(center=(SCREEN_WIDTH // 2, 180)))

        remaining = max(0.0, 1.0 - self.elapsed / max(0.001, self.max_time))
        cx, cy = SCREEN_WIDTH // 2, 290
        radius = 38
        pygame.draw.circle(self.screen, (*th.panel_bg, ), (cx, cy), radius)
        pygame.draw.circle(self.screen, th.brass_700, (cx, cy), radius, 1)
        if remaining > 0:
            arc_color = th.brass_300 if remaining > 0.4 else th.signal_warn
            self._draw_arc(cx, cy, radius - 6, remaining, arc_color)
        secs_left = max(0.0, self.max_time - self.elapsed)
        if self.max_time >= 900:
            time_label = "INF"
        else:
            time_label = f"{secs_left:0.1f}s"
        secs_surf = typo.body_bold(16).render(time_label, True, th.text_white)
        self.screen.blit(secs_surf, secs_surf.get_rect(center=(cx, cy)))

        if game_manager is None:
            self.done_button.draw(self.screen, self.button_font)
            return
        human = next((p for p in game_manager.players if p.is_human), None)
        if human is None:
            self.done_button.draw(self.screen, self.button_font)
            return

        card_w = int(min(CARD_WIDTH * 1.6, (SCREEN_WIDTH - 80) // max(1, self.hand_size) - 20))
        card_h = int(card_w * 1.4)
        gap = 28
        total_width = card_w * self.hand_size + gap * (self.hand_size - 1)
        start_x = (SCREEN_WIDTH - total_width) // 2
        card_y = int(SCREEN_HEIGHT * 0.40)

        slot_label_font = typo.body_bold(14)
        peek_tag_font = typo.body_bold(12)

        for slot_idx in range(self.hand_size):
            x = start_x + slot_idx * (card_w + gap)
            card = human.hand[slot_idx]
            is_peek_slot = slot_idx in self.peeking and self.revealed

            shadow = pygame.Surface((card_w + 14, card_h + 18), pygame.SRCALPHA)
            pygame.draw.rect(shadow, (0, 0, 0, 130),
                             (7, 10, card_w, card_h), border_radius=12)
            self.screen.blit(shadow, (x - 7, card_y))

            if card is None:
                empty = pygame.Rect(x, card_y, card_w, card_h)
                pygame.draw.rect(self.screen, (*th.felt_rim, ), empty, border_radius=12)
                pygame.draw.rect(self.screen, th.brass_700, empty, 2, border_radius=12)
                dash_font = typo.header(28)
                dash = dash_font.render("-", True, th.text_muted)
                self.screen.blit(dash, dash.get_rect(center=empty.center))
            elif is_peek_slot:
                face = card_render.paint_face(card, card_w, card_h)
                glow_size = (card_w + 24, card_h + 24)
                glow = pygame.Surface(glow_size, pygame.SRCALPHA)
                t_phase = pygame.time.get_ticks() / 1000.0
                pulse = 0.6 + 0.4 * abs((t_phase * 1.4) % 2 - 1)
                glow_alpha = int(140 * pulse * (0.5 + 0.5 * remaining))
                pygame.draw.rect(glow, (*th.brass_300, glow_alpha),
                                 glow.get_rect(), border_radius=18)
                self.screen.blit(glow, (x - 12, card_y - 12),
                                 special_flags=pygame.BLEND_RGBA_ADD)
                self.screen.blit(face, (x, card_y))

                tag_w, tag_h = 64, 22
                tag_rect = pygame.Rect(x + card_w - tag_w - 6, card_y + 6,
                                       tag_w, tag_h)
                pygame.draw.rect(self.screen, th.brass_300, tag_rect, border_radius=11)
                tag_text = peek_tag_font.render("PEEKED", True, th.brass_900)
                self.screen.blit(tag_text, tag_text.get_rect(center=tag_rect.center))
            else:
                back = card_render.paint_back("classic", card_w, card_h)
                dim = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
                dim.fill((0, 0, 0, 100))
                self.screen.blit(back, (x, card_y))
                self.screen.blit(dim, (x, card_y))
                hidden_label = peek_tag_font.render("HIDDEN", True, th.text_muted)
                self.screen.blit(hidden_label, hidden_label.get_rect(
                    center=(x + card_w // 2, card_y + card_h // 2)))

            label = slot_label_font.render(f"SEAT SLOT {slot_idx + 1}",
                                            True, th.brass_300)
            self.screen.blit(label, label.get_rect(center=(x + card_w // 2,
                                                             card_y + card_h + 22)))

        tip = self.small_font.render(
            "When the timer ends, your peeked cards flip back. Click anywhere to skip ahead.",
            True, th.text_dim,
        )
        self.screen.blit(tip, tip.get_rect(center=(SCREEN_WIDTH // 2,
                                                     card_y + card_h + 60)))

        self.done_button.draw(self.screen, self.button_font)

    def _draw_arc(self, cx, cy, radius, fraction, color):
        import math
        steps = max(2, int(60 * fraction))
        if steps < 2:
            return
        start_angle = -math.pi / 2
        end_angle = start_angle + 2 * math.pi * fraction
        points = [(cx, cy)]
        for i in range(steps + 1):
            a = start_angle + (end_angle - start_angle) * (i / steps)
            points.append((cx + math.cos(a) * radius, cy + math.sin(a) * radius))
        if len(points) >= 3:
            pygame.draw.polygon(self.screen, color, points)

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.done_button.update_hover(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.done_button.is_clicked(event.pos):
                self.revealed = False
                return 'peek_done'
        return None

    def update(self, dt):
        if self.revealed:
            self.elapsed += dt
            if self.elapsed >= self.max_time:
                self.revealed = False
                return 'peek_done'
        return None


class GameOverScreen:
    def __init__(self, screen):
        self.screen = screen
        scale = get_mobile_scale()
        self.title_font = typo.display_bold(int(TITLE_FONT_SIZE * 1.4))
        self.banner_font = typo.header_italic(int(SUBTITLE_FONT_SIZE * 1.05))
        self.name_font = typo.header_bold(int(UI_FONT_SIZE * 1.1))
        self.label_font = typo.body(UI_FONT_SIZE)
        self.button_font = typo.body_bold(int(UI_FONT_SIZE * scale))
        self.score_font = typo.display_bold(int(UI_FONT_SIZE * 1.4))
        self.small_font = typo.body(SMALL_FONT_SIZE)
        bw = int(280 * scale)
        bh = int(52 * scale)
        by = int(SCREEN_HEIGHT * 0.88)
        self.play_again_button = Button(SCREEN_WIDTH // 2 - bw // 2 - 10, by, bw, bh, "Play Again",
                                        SWAP_GREEN, SWAP_GREEN_HOVER)
        self.menu_button = Button(SCREEN_WIDTH // 2 + bw // 2 + 10, by, bw, bh, "Main Menu",
                                  DECLARE_RED, DECLARE_RED_HOVER)
        self.buttons = [self.play_again_button, self.menu_button]
        self._bg_cache = None

    def _build_background(self):
        import theme as theme_mod
        th = theme_mod.active()
        bg = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        for i in range(SCREEN_HEIGHT):
            t = i / max(1, SCREEN_HEIGHT - 1)
            r = int(th.felt_rim[0] * (1 - t * 0.4) + th.felt_deep[0] * t * 0.6)
            g = int(th.felt_rim[1] * (1 - t * 0.4) + th.felt_deep[1] * t * 0.6)
            b = int(th.felt_rim[2] * (1 - t * 0.4) + th.felt_deep[2] * t * 0.6)
            pygame.draw.line(bg, (r, g, b), (0, i), (SCREEN_WIDTH, i))
        center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
        rx, ry = 760, 420
        pygame.draw.ellipse(bg, th.brass_700,
                            pygame.Rect(center[0] - rx, center[1] - ry, rx * 2, ry * 2), 1)
        pygame.draw.ellipse(bg, th.brass_900,
                            pygame.Rect(center[0] - rx - 6, center[1] - ry - 6,
                                        (rx + 6) * 2, (ry + 6) * 2), 1)
        return bg

    def _draw_title(self, banner_text, banner_color):
        import theme as theme_mod
        th = theme_mod.active()
        for offset, alpha in ((6, 60), (3, 110), (0, 255)):
            t_color = th.brass_300 if alpha == 255 else th.brass_700
            t_surf = typo.render_with_letter_spacing(
                self.title_font, "GAME OVER", t_color, spacing_px=10,
            )
            t_surf.set_alpha(alpha)
            r = t_surf.get_rect(center=(SCREEN_WIDTH // 2 + offset, 90 + offset))
            self.screen.blit(t_surf, r)

        flourish_y = 152
        cx = SCREEN_WIDTH // 2
        line_w = 240
        pygame.draw.line(self.screen, th.brass_500, (cx - line_w, flourish_y),
                         (cx - 30, flourish_y), 1)
        pygame.draw.line(self.screen, th.brass_500, (cx + 30, flourish_y),
                         (cx + line_w, flourish_y), 1)
        pygame.draw.polygon(self.screen, th.brass_500,
                            [(cx, flourish_y - 5), (cx - 12, flourish_y),
                             (cx, flourish_y + 5), (cx + 12, flourish_y)])

        banner_surf = self.banner_font.render(banner_text, True, banner_color)
        banner_rect = banner_surf.get_rect(center=(SCREEN_WIDTH // 2, 188))
        chip_w = banner_rect.width + 56
        chip_h = banner_rect.height + 18
        chip = pygame.Surface((chip_w, chip_h), pygame.SRCALPHA)
        pygame.draw.rect(chip, (15, 15, 15, 200), chip.get_rect(),
                         border_radius=chip_h // 2)
        pygame.draw.rect(chip, (*banner_color, 200), chip.get_rect(), 2,
                         border_radius=chip_h // 2)
        self.screen.blit(chip, (banner_rect.centerx - chip_w // 2,
                                 banner_rect.centery - chip_h // 2))
        self.screen.blit(banner_surf, banner_rect)

    def _draw_player_panel(self, player, x_center, top_y, hand_size,
                            score_val, is_winner, game_manager):
        import card_render
        import theme as theme_mod
        th = theme_mod.active()

        panel_w = max(420, hand_size * (CARD_WIDTH + 16) + 80)
        panel_h = CARD_HEIGHT + 200
        panel_rect = pygame.Rect(x_center - panel_w // 2, top_y, panel_w, panel_h)

        shadow = pygame.Surface((panel_w + 12, panel_h + 12), pygame.SRCALPHA)
        pygame.draw.rect(shadow, (0, 0, 0, 120), (6, 8, panel_w, panel_h),
                         border_radius=14)
        self.screen.blit(shadow, (panel_rect.x - 6, panel_rect.y + 4))

        panel_surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        for i in range(panel_h):
            t = i / max(1, panel_h - 1)
            r = int(th.felt_rim[0] + (th.felt_mid[0] - th.felt_rim[0]) * t * 0.5)
            g = int(th.felt_rim[1] + (th.felt_mid[1] - th.felt_rim[1]) * t * 0.5)
            b = int(th.felt_rim[2] + (th.felt_mid[2] - th.felt_rim[2]) * t * 0.5)
            pygame.draw.line(panel_surf, (r, g, b, 230), (0, i), (panel_w, i))
        mask = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=14)
        panel_surf.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        self.screen.blit(panel_surf, panel_rect.topleft)

        border_color = th.brass_300 if is_winner else th.brass_700
        pygame.draw.rect(self.screen, border_color, panel_rect, 2, border_radius=14)
        pygame.draw.rect(self.screen, th.brass_900, panel_rect.inflate(-8, -8),
                         1, border_radius=12)

        if is_winner:
            crown_y = panel_rect.top - 14
            pts = [
                (x_center - 18, crown_y + 14),
                (x_center - 14, crown_y),
                (x_center - 7, crown_y + 8),
                (x_center, crown_y - 4),
                (x_center + 7, crown_y + 8),
                (x_center + 14, crown_y),
                (x_center + 18, crown_y + 14),
            ]
            pygame.draw.polygon(self.screen, th.brass_300, pts)
            pygame.draw.polygon(self.screen, th.brass_700, pts, 2)

        name_color = th.brass_300 if is_winner else th.text_white
        name_surf = self.name_font.render(player.name, True, name_color)
        self.screen.blit(name_surf, name_surf.get_rect(
            center=(x_center, panel_rect.top + 32)))

        score_label = self.small_font.render("SCORE", True, th.text_dim)
        self.screen.blit(score_label, score_label.get_rect(
            center=(x_center, panel_rect.top + 60)))
        score_color = th.brass_300 if is_winner else th.text_white
        score_surf = self.score_font.render(str(score_val), True, score_color)
        self.screen.blit(score_surf, score_surf.get_rect(
            center=(x_center, panel_rect.top + 90)))

        gap = 12
        total_w = hand_size * CARD_WIDTH + (hand_size - 1) * gap
        cards_x = x_center - total_w // 2
        cards_y = panel_rect.top + 130
        for slot_idx in range(hand_size):
            card = player.hand[slot_idx]
            cx = cards_x + slot_idx * (CARD_WIDTH + gap)
            shadow_card = pygame.Surface((CARD_WIDTH + 8, CARD_HEIGHT + 8),
                                          pygame.SRCALPHA)
            pygame.draw.rect(shadow_card, (0, 0, 0, 120),
                             (4, 6, CARD_WIDTH, CARD_HEIGHT),
                             border_radius=CORNER_RADIUS)
            self.screen.blit(shadow_card, (cx - 4, cards_y - 4))
            if card is not None:
                face = card_render.paint_face(card, CARD_WIDTH, CARD_HEIGHT)
                self.screen.blit(face, (cx, cards_y))
            else:
                empty_rect = pygame.Rect(cx, cards_y, CARD_WIDTH, CARD_HEIGHT)
                pygame.draw.rect(self.screen, (*th.felt_rim, 200), empty_rect,
                                 border_radius=CORNER_RADIUS)
                pygame.draw.rect(self.screen, th.brass_700, empty_rect, 1,
                                 border_radius=CORNER_RADIUS)
                dash = self.label_font.render("-", True, th.text_dim)
                self.screen.blit(dash, dash.get_rect(center=empty_rect.center))

    def draw(self, game_manager, result=None):
        import theme as theme_mod
        th = theme_mod.active()

        if self._bg_cache is None:
            self._bg_cache = self._build_background()
        self.screen.blit(self._bg_cache, (0, 0))

        banner_text = "Game complete"
        banner_color = th.brass_300
        if result:
            if result.get("auto_win"):
                banner_text = "Auto-win - a player ran out of cards"
                banner_color = th.signal_warn
            elif result.get("winner"):
                winner = result["winner"]
                banner_text = f"{winner.name} wins the round"
                banner_color = th.brass_300
            elif result.get("declarer_won") is False:
                banner_text = "The declarer lost!"
                banner_color = th.declare_red
            else:
                banner_text = "It's a draw"
                banner_color = th.text_white

        self._draw_title(banner_text, banner_color)

        if game_manager is None:
            for button in self.buttons:
                button.draw(self.screen, self.button_font)
            return

        num_players = len(game_manager.players)
        scores = result.get("scores", {}) if result else {}
        winner_seat = None
        if result and result.get("winner"):
            winner_seat = result["winner"].seat_index

        hand_size = game_manager.settings.hand_size
        section_width = SCREEN_WIDTH // num_players
        for i, player in enumerate(game_manager.players):
            px = section_width * i + section_width // 2
            score_val = scores.get(player.seat_index,
                                    player.score if hasattr(player, 'score') else 0)
            is_winner = (winner_seat == player.seat_index)
            self._draw_player_panel(player, px, 240, hand_size, score_val,
                                     is_winner, game_manager)

        for button in self.buttons:
            button.draw(self.screen, self.button_font)

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            for button in self.buttons:
                button.update_hover(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.play_again_button.is_clicked(event.pos):
                return 'play_again'
            if self.menu_button.is_clicked(event.pos):
                return 'menu'
        return None
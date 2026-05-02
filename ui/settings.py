"""Settings panel — clean tabbed rebuild.

Six tabs:
  Display      — card layout, animations, log/marker/score toggles
  Gameplay     — hand size, peek count, reaction window, peek phase, confirm
  AI           — difficulty, ai delay, peek reveal speed
  Accessibility— theme, text scale, motion, particles, captions, hints, coach
  Audio        — master, sfx, music, voice
  Profile      — streamer mode, reset

Wide enough to hold every option without clipping. Auto-saves to profile.json
on every change (main.py picks up the 'updated' return and persists).
"""
import pygame

import theme as theme_mod
import typography as typo

from config import (
    SCREEN_WIDTH, SCREEN_HEIGHT, GOLD, TEXT_WHITE, TEXT_DIM, PANEL_BG,
    PANEL_BORDER, UI_FONT_SIZE, SMALL_FONT_SIZE, BG_DARK,
    AI_DELAY_OPTIONS, AI_DELAY_LABELS,
    PEEK_REVEAL_OPTIONS, PEEK_REVEAL_LABELS,
    ANIMATION_OPTIONS, ANIMATION_LABELS,
    LAYOUT_OPTIONS, LAYOUT_LABELS,
    AI_DIFFICULTY_OPTIONS, AI_DIFFICULTY_LABELS,
    PEEK_PHASE_OPTIONS, PEEK_PHASE_LABELS,
    HAND_SIZE_OPTIONS, HAND_SIZE_LABELS,
    REACTION_WINDOW_OPTIONS, REACTION_WINDOW_LABELS,
    PEEK_COUNT_OPTIONS, PEEK_COUNT_LABELS, get_mobile_scale,
)


class SettingsMenu:
    AMBER = (220, 175, 60)
    AMBER_HI = (245, 200, 80)

    @property
    def PANEL_W(self):
        return min(1568, SCREEN_WIDTH - 64)

    @property
    def PANEL_H(self):
        return min(1088, SCREEN_HEIGHT - 64)

    @property
    def PANEL_X(self):
        return (SCREEN_WIDTH - self.PANEL_W) // 2

    @property
    def PANEL_Y(self):
        return (SCREEN_HEIGHT - self.PANEL_H) // 2

    @property
    def GEAR_X(self):
        return SCREEN_WIDTH - int(52 * get_mobile_scale())

    @property
    def GEAR_Y(self):
        return 8

    @property
    def GEAR_W(self):
        return int(40 * get_mobile_scale())

    @property
    def GEAR_H(self):
        return int(34 * get_mobile_scale())

    @property
    def TAB_W(self):
        return min(264, self.PANEL_W // len(self.TABS))

    @property
    def TAB_H(self):
        return int(70 * get_mobile_scale())

    @property
    def TAB_BAR_Y(self):
        return 134

    TABS = [
        ("display",        "Display"),
        ("gameplay",       "Gameplay"),
        ("ai",             "AI"),
        ("access",         "Accessibility"),
        ("audio",          "Audio"),
        ("profile",        "Profile"),
    ]

    def __init__(self, screen):
        self.screen = screen
        self.tab = "display"
        scale = get_mobile_scale()
        self.font = typo.body(int(UI_FONT_SIZE * scale))
        self.small_font = typo.body(int(SMALL_FONT_SIZE * scale))
        self.tab_font = typo.body_bold(int((UI_FONT_SIZE + 4) * scale))
        self.title_font = typo.display_bold(int(56 * scale))
        self.section_font = typo.body_bold(int(22 * scale))
        self.label_font = typo.body(int(26 * scale))

        self._hit = []
        self._tab_rects = {}
        self._done_rect = None
        self._profile_ref = None

    def attach_profile(self, prof):
        """Settings menu can persist its own changes when a profile is bound."""
        self._profile_ref = prof

    def get_gear_rect(self):
        return pygame.Rect(self.GEAR_X, self.GEAR_Y, self.GEAR_W, self.GEAR_H)

    def handle_event(self, event, game_settings, game_manager):
        mouse_pos = pygame.mouse.get_pos()
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for tab_key, rect in self._tab_rects.items():
                if rect.collidepoint(mouse_pos):
                    self.tab = tab_key
                    return None
            if self._done_rect and self._done_rect.collidepoint(mouse_pos):
                return "close"
            for action, rect, payload in self._hit:
                if rect.collidepoint(mouse_pos):
                    self._apply(action, payload, game_settings, game_manager)
                    return "updated"
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_TAB:
                idx = next((i for i, (k, _) in enumerate(self.TABS) if k == self.tab), 0)
                self.tab = self.TABS[(idx + 1) % len(self.TABS)][0]
            if event.key == pygame.K_LEFT:
                idx = next((i for i, (k, _) in enumerate(self.TABS) if k == self.tab), 0)
                self.tab = self.TABS[(idx - 1) % len(self.TABS)][0]
            if event.key == pygame.K_RIGHT:
                idx = next((i for i, (k, _) in enumerate(self.TABS) if k == self.tab), 0)
                self.tab = self.TABS[(idx + 1) % len(self.TABS)][0]
        return None

    def _apply(self, action, payload, gs, gm):
        prof = self._profile_ref

        if action == "layout":
            gs.layout_mode = payload
            if gm and payload == "free":
                hp = next((p for p in gm.players if p.is_human), None)
                if hp is not None:
                    hp.layout_mode = "free"
                    try:
                        from ui.renderer import Renderer
                        r = Renderer(self.screen)
                        r.init_free_positions(hp, gm)
                    except Exception:
                        pass
        elif action == "ai_delay":
            gs.ai_delay = payload
        elif action == "peek_reveal":
            gs.peek_reveal_time = payload
        elif action == "anim":
            gs.animations_enabled = payload
        elif action == "ai_diff":
            if gm:
                for p in gm.players:
                    if not p.is_human:
                        gs.ai_difficulties[p.seat_index] = payload
        elif action == "score":
            gs.show_own_score = payload
        elif action == "marker":
            gs.show_known_marker = payload
        elif action == "log":
            gs.show_game_log = payload
        elif action == "confirm":
            gs.confirm_declare = payload
        elif action == "peek_phase":
            gs.peek_phase_seconds = payload
        elif action == "hand_size":
            gs.hand_size = payload
        elif action == "peek_count":
            gs.peek_count = payload
        elif action == "reaction":
            gs.reaction_window_seconds = payload
        elif action == "self_pair":
            gs.self_pair_enabled = payload
        elif action == "shuffle":
            gs.shuffle_enabled = payload
        elif action == "penalty":
            gs.wrong_drop_penalty = payload
        elif action == "felt":
            gs.felt_style = payload
            theme_mod.apply_felt_style(payload)

        elif action == "theme":
            if prof:
                prof.settings.theme = payload
                theme_mod.set_active(payload)
                try:
                    import card_render
                    card_render.invalidate_cache()
                except ImportError:
                    pass
        elif action == "text_scale":
            if prof:
                prof.settings.text_scale = payload
                theme_mod.apply_text_scale(payload)
        elif action == "motion":
            gs.motion_scale = payload
            if prof:
                prof.settings.motion_scale = payload
                theme_mod.apply_motion_scale(payload)
        elif action == "particles":
            gs.particles_enabled = payload
            if prof:
                prof.settings.particles_enabled = payload
                theme_mod.apply_particles(payload)
        elif action == "atmospheric_lighting":
            gs.atmospheric_lighting = payload
            if prof:
                prof.settings.atmospheric_lighting = payload
            # Invalidate the felt cache so the lamp pool is rebuilt with the
            # new flag honored.
            try:
                from ui.renderer import Renderer  # noqa: F401
            except Exception:
                pass
        elif action == "captions":
            gs.captions = payload
            if prof:
                prof.settings.captions = payload
        elif action == "hint_tier":
            gs.hint_tier = payload
            if prof:
                prof.settings.hint_tier = payload
        elif action == "coach":
            gs.coach_mode = payload
            if prof:
                prof.settings.coach_mode = payload
        elif action == "streamer":
            gs.streamer_mode = payload
            if prof:
                prof.settings.streamer_mode = payload

        elif action == "vol_master":
            if prof:
                prof.settings.sfx_volume = payload
                prof.settings.music_volume = payload * 0.7
                prof.settings.voice_volume = payload * 0.85
                try:
                    import audio
                    audio.set_volume("sfx", prof.settings.sfx_volume)
                    audio.set_volume("music", prof.settings.music_volume)
                    audio.set_volume("voice", prof.settings.voice_volume)
                except ImportError:
                    pass
        elif action == "vol_sfx":
            if prof:
                prof.settings.sfx_volume = payload
                try:
                    import audio
                    audio.set_volume("sfx", payload)
                except ImportError:
                    pass
        elif action == "vol_music":
            if prof:
                prof.settings.music_volume = payload
                try:
                    import audio
                    audio.set_volume("music", payload)
                except ImportError:
                    pass
        elif action == "vol_voice":
            if prof:
                prof.settings.voice_volume = payload
                try:
                    import audio
                    audio.set_volume("voice", payload)
                except ImportError:
                    pass

    def draw(self, game_settings, game_manager, mouse_pos):
        self._hit = []
        self._tab_rects = {}
        th = theme_mod.active()

        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 190))
        self.screen.blit(overlay, (0, 0))

        panel_rect = pygame.Rect(self.PANEL_X, self.PANEL_Y, self.PANEL_W, self.PANEL_H)
        shadow = pygame.Surface((self.PANEL_W + 16, self.PANEL_H + 16), pygame.SRCALPHA)
        pygame.draw.rect(shadow, (0, 0, 0, 160), (8, 10, self.PANEL_W, self.PANEL_H),
                         border_radius=14)
        self.screen.blit(shadow, (self.PANEL_X - 8, self.PANEL_Y + 4))

        panel = pygame.Surface((self.PANEL_W, self.PANEL_H), pygame.SRCALPHA)
        for i in range(self.PANEL_H):
            t = i / max(1, self.PANEL_H - 1)
            r = int(th.felt_rim[0] + (th.felt_mid[0] - th.felt_rim[0]) * t * 0.55)
            g = int(th.felt_rim[1] + (th.felt_mid[1] - th.felt_rim[1]) * t * 0.55)
            b = int(th.felt_rim[2] + (th.felt_mid[2] - th.felt_rim[2]) * t * 0.55)
            pygame.draw.line(panel, (r, g, b, 245), (0, i), (self.PANEL_W, i))
        mask = pygame.Surface((self.PANEL_W, self.PANEL_H), pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=14)
        panel.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        self.screen.blit(panel, panel_rect.topleft)

        pygame.draw.rect(self.screen, th.brass_300, panel_rect, 2, border_radius=14)
        pygame.draw.rect(self.screen, th.brass_900,
                         panel_rect.inflate(-8, -8), 1, border_radius=12)
        pygame.draw.line(self.screen, (255, 255, 255, 60),
                         (panel_rect.left + 6, panel_rect.top + 3),
                         (panel_rect.right - 6, panel_rect.top + 3), 1)

        for offset, alpha, col in ((3, 90, th.brass_900), (0, 255, th.brass_300)):
            title = self.title_font.render("Settings", True, col)
            title.set_alpha(alpha)
            self.screen.blit(title, title.get_rect(
                midtop=(panel_rect.centerx + offset, self.PANEL_Y + 20 + offset)))

        flourish_y = self.PANEL_Y + 20 + self.title_font.get_height() + 6
        cx = panel_rect.centerx
        line_w = 130
        pygame.draw.line(self.screen, th.brass_500,
                         (cx - line_w, flourish_y), (cx - 16, flourish_y), 1)
        pygame.draw.line(self.screen, th.brass_500,
                         (cx + 16, flourish_y), (cx + line_w, flourish_y), 1)
        pygame.draw.polygon(self.screen, th.brass_500,
                            [(cx, flourish_y - 4), (cx - 8, flourish_y),
                             (cx, flourish_y + 4), (cx + 8, flourish_y)])

        self._draw_tab_bar(mouse_pos)

        content_top = self.PANEL_Y + self.TAB_BAR_Y + self.TAB_H + 24
        content_left = self.PANEL_X + 30
        content_right = self.PANEL_X + self.PANEL_W - 30

        if self.tab == "display":
            self._draw_display(content_left, content_top, content_right, game_settings)
        elif self.tab == "gameplay":
            self._draw_gameplay(content_left, content_top, content_right, game_settings)
        elif self.tab == "ai":
            self._draw_ai(content_left, content_top, content_right, game_settings, game_manager)
        elif self.tab == "access":
            self._draw_access(content_left, content_top, content_right, game_settings)
        elif self.tab == "audio":
            self._draw_audio(content_left, content_top, content_right, game_settings)
        elif self.tab == "profile":
            self._draw_profile(content_left, content_top, content_right, game_settings)

        bw, bh = 180, 44
        self._done_rect = pygame.Rect(
            self.PANEL_X + self.PANEL_W // 2 - bw // 2,
            self.PANEL_Y + self.PANEL_H - bh - 18,
            bw, bh,
        )
        hov = self._done_rect.collidepoint(mouse_pos)
        done_top = th.brass_300 if hov else th.brass_500
        done_bot = th.brass_500 if hov else th.brass_700
        plate = pygame.Surface((bw, bh), pygame.SRCALPHA)
        for j in range(bh):
            t = j / max(1, bh - 1)
            rr = int(done_top[0] + (done_bot[0] - done_top[0]) * t)
            gg = int(done_top[1] + (done_bot[1] - done_top[1]) * t)
            bb = int(done_top[2] + (done_bot[2] - done_top[2]) * t)
            pygame.draw.line(plate, (rr, gg, bb, 255), (0, j), (bw, j))
        m = pygame.Surface((bw, bh), pygame.SRCALPHA)
        pygame.draw.rect(m, (255, 255, 255, 255), m.get_rect(), border_radius=10)
        plate.blit(m, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        self.screen.blit(plate, self._done_rect.topleft)
        pygame.draw.rect(self.screen, th.brass_900, self._done_rect, 2,
                         border_radius=10)
        pygame.draw.line(self.screen, (255, 255, 255, 110),
                         (self._done_rect.left + 6, self._done_rect.top + 2),
                         (self._done_rect.right - 6, self._done_rect.top + 2), 1)
        ds = self.tab_font.render("Done", True, th.brass_900)
        self.screen.blit(ds, ds.get_rect(center=self._done_rect.center))

        ai_hint = self.small_font.render("Esc to close  ·  ← → / Tab to switch tabs",
                                          True, TEXT_DIM)
        self.screen.blit(ai_hint, ai_hint.get_rect(midbottom=(panel_rect.centerx,
                                                                self._done_rect.top - 10)))

    def _draw_tab_bar(self, mouse_pos):
        th = theme_mod.active()
        total_w = self.TAB_W * len(self.TABS)
        start_x = self.PANEL_X + (self.PANEL_W - total_w) // 2
        y = self.PANEL_Y + self.TAB_BAR_Y
        for i, (key, label) in enumerate(self.TABS):
            r = pygame.Rect(start_x + i * self.TAB_W, y, self.TAB_W - 4, self.TAB_H)
            self._tab_rects[key] = r
            active = (key == self.tab)
            hover = r.collidepoint(mouse_pos)

            plate = pygame.Surface((r.width, r.height), pygame.SRCALPHA)
            if active:
                top_col = th.brass_300
                bot_col = th.brass_500
                text_color = th.brass_900
            elif hover:
                top_col = (78, 70, 50)
                bot_col = (52, 46, 30)
                text_color = th.text_white
            else:
                top_col = (44, 40, 28)
                bot_col = (28, 26, 18)
                text_color = th.text_dim
            for j in range(r.height):
                t = j / max(1, r.height - 1)
                rr = int(top_col[0] + (bot_col[0] - top_col[0]) * t)
                gg = int(top_col[1] + (bot_col[1] - top_col[1]) * t)
                bb = int(top_col[2] + (bot_col[2] - top_col[2]) * t)
                pygame.draw.line(plate, (rr, gg, bb, 255), (0, j), (r.width, j))
            mask = pygame.Surface((r.width, r.height), pygame.SRCALPHA)
            pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(),
                             border_radius=8)
            plate.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
            self.screen.blit(plate, r.topleft)

            border = th.brass_300 if active else th.brass_700
            pygame.draw.rect(self.screen, border, r, 2 if active else 1,
                             border_radius=8)
            if active:
                pygame.draw.line(self.screen, (255, 255, 255, 90),
                                 (r.left + 4, r.top + 2),
                                 (r.right - 4, r.top + 2), 1)
            ts = self.tab_font.render(label, True, text_color)
            self.screen.blit(ts, ts.get_rect(center=r.center))

    def _section(self, x, y, label):
        s = self.section_font.render(label.upper(), True, GOLD)
        self.screen.blit(s, (x, y))
        line_x = x + s.get_width() + 12
        pygame.draw.line(self.screen, PANEL_BORDER,
                         (line_x, y + s.get_height() // 2 + 1),
                         (self.PANEL_X + self.PANEL_W - 30, y + s.get_height() // 2 + 1), 1)
        return y + s.get_height() + 12

    # Width of the label column (relative to row x). Labels are left-aligned
    # so all rows share the same starting x, and the control strip begins at
    # a fixed offset — keeps the form visually aligned on both sides.
    _LABEL_COL_W = 320
    _LABEL_GAP = 28
    _ROW_H = 38
    _ROW_GAP = 10
    _BTN_H = 34
    _BTN_GAP = 8

    def _row(self, x, y, label, options, current, action, content_right=None):
        """Draw a labeled row of pill-buttons. Returns next y."""
        th = theme_mod.active()
        if content_right is None:
            content_right = self.PANEL_X + self.PANEL_W - 30

        l = self.label_font.render(label + ":", True, th.text_white)
        ctrl_x = x + self._LABEL_COL_W + self._LABEL_GAP
        # Vertically center the label against the button row.
        label_y = y + (self._BTN_H - l.get_height()) // 2
        self.screen.blit(l, (x, label_y))
        avail_w = max(80, content_right - ctrl_x)
        bh = self._BTN_H
        # Per-option width is bounded so 2-option rows don't sprawl across the
        # whole panel — keeps ON/OFF visually similar in size to 3-option rows.
        n = max(1, len(options))
        per_cap = 132 if n <= 2 else 116
        bw = max(72, min(per_cap, (avail_w - (n - 1) * self._BTN_GAP) // n))

        for value, text in options:
            r = pygame.Rect(ctrl_x, y, bw, bh)
            active = self._matches(value, current)
            if active:
                top_col = th.brass_300
                bot_col = th.brass_500
                txt_color = th.brass_900
                border = th.brass_900
            else:
                top_col = (52, 48, 32)
                bot_col = (32, 30, 22)
                txt_color = th.text_white
                border = th.brass_700
            plate = pygame.Surface((bw, bh), pygame.SRCALPHA)
            for j in range(bh):
                t = j / max(1, bh - 1)
                rr = int(top_col[0] + (bot_col[0] - top_col[0]) * t)
                gg = int(top_col[1] + (bot_col[1] - top_col[1]) * t)
                bb = int(top_col[2] + (bot_col[2] - top_col[2]) * t)
                pygame.draw.line(plate, (rr, gg, bb, 255), (0, j), (bw, j))
            m = pygame.Surface((bw, bh), pygame.SRCALPHA)
            pygame.draw.rect(m, (255, 255, 255, 255), m.get_rect(), border_radius=6)
            plate.blit(m, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
            self.screen.blit(plate, r.topleft)
            pygame.draw.rect(self.screen, border, r, 1, border_radius=6)
            if active:
                pygame.draw.line(self.screen, (255, 255, 255, 110),
                                 (r.left + 4, r.top + 2),
                                 (r.right - 4, r.top + 2), 1)
            ts = self.small_font.render(str(text), True, txt_color)
            self.screen.blit(ts, ts.get_rect(center=r.center))
            self._hit.append((action, r, value))
            ctrl_x += bw + self._BTN_GAP
        return y + bh + self._ROW_GAP

    def _matches(self, candidate, current):
        if isinstance(candidate, float) and isinstance(current, float):
            return abs(candidate - current) < 0.05
        return candidate == current

    def _draw_display(self, lx, y, rx, gs):
        y = self._section(lx, y, "Card Layout")
        y = self._row(lx, y, "Layout", list(zip(LAYOUT_OPTIONS, LAYOUT_LABELS)),
                      gs.layout_mode, "layout", rx)

        y += 8
        y = self._section(lx, y, "Animations & Log")
        y = self._row(lx, y, "Animations",
                      list(zip(ANIMATION_OPTIONS, ANIMATION_LABELS)),
                      gs.animations_enabled, "anim", rx)
        y = self._row(lx, y, "Game Log", [(True, "ON"), (False, "OFF")],
                      gs.show_game_log, "log", rx)
        y = self._row(lx, y, "Show Score", [(True, "ON"), (False, "OFF")],
                      gs.show_own_score, "score", rx)
        y = self._row(lx, y, "Known Marker", [(True, "ON"), (False, "OFF")],
                      gs.show_known_marker, "marker", rx)

        y += 8
        y = self._section(lx, y, "Atmosphere")
        y = self._row(lx, y, "Lamp & Vignette", [(True, "ON"), (False, "OFF")],
                      getattr(gs, 'atmospheric_lighting', False),
                      "atmospheric_lighting", rx)

    def _draw_gameplay(self, lx, y, rx, gs):
        y = self._section(lx, y, "Hand")
        y = self._row(lx, y, "Cards Per Hand",
                      list(zip(HAND_SIZE_OPTIONS, HAND_SIZE_LABELS)),
                      gs.hand_size, "hand_size", rx)
        y = self._row(lx, y, "Peek Cards",
                      list(zip(PEEK_COUNT_OPTIONS, PEEK_COUNT_LABELS)),
                      gs.peek_count, "peek_count", rx)
        y = self._row(lx, y, "Peek Phase",
                      list(zip(PEEK_PHASE_OPTIONS, PEEK_PHASE_LABELS)),
                      gs.peek_phase_seconds, "peek_phase", rx)

        y += 8
        y = self._section(lx, y, "Reactions & Declare")
        y = self._row(lx, y, "Reaction Window",
                      list(zip(REACTION_WINDOW_OPTIONS, REACTION_WINDOW_LABELS)),
                      gs.reaction_window_seconds, "reaction", rx)
        y = self._row(lx, y, "Confirm Declare", [(True, "ON"), (False, "OFF")],
                      gs.confirm_declare, "confirm", rx)

        y += 8
        y = self._section(lx, y, "Mechanics")
        y = self._row(lx, y, "Self-Pairing", [(True, "ON"), (False, "OFF")],
                      gs.self_pair_enabled, "self_pair", rx)
        y = self._row(lx, y, "Shuffle Cards", [(True, "ON"), (False, "OFF")],
                      gs.shuffle_enabled, "shuffle", rx)
        y = self._row(lx, y, "Wrong-Drop Penalty", [(True, "ON"), (False, "OFF")],
                      gs.wrong_drop_penalty, "penalty", rx)

        y += 8
        from config import FELT_COLORS, FELT_LABELS
        felt_options = list(zip(list(FELT_COLORS.keys()), FELT_LABELS))
        y = self._row(lx, y, "Table Felt", felt_options,
                      getattr(gs, 'felt_style', 'forest'), "felt", rx)

    def _draw_ai(self, lx, y, rx, gs, gm):
        y = self._section(lx, y, "Difficulty")
        current_diff = "medium"
        if gm and gm.players:
            for p in gm.players:
                if not p.is_human:
                    current_diff = gs.ai_difficulties.get(p.seat_index, "medium")
                    break
        y = self._row(lx, y, "AI Difficulty",
                      list(zip(AI_DIFFICULTY_OPTIONS, AI_DIFFICULTY_LABELS)),
                      current_diff, "ai_diff", rx)
        note = self.small_font.render(
            "Affects declare threshold and reaction probability.",
            True, TEXT_DIM,
        )
        self.screen.blit(note, (lx, y))
        y += 24

        y = self._section(lx, y, "Pacing")
        y = self._row(lx, y, "AI Delay",
                      list(zip(AI_DELAY_OPTIONS, AI_DELAY_LABELS)),
                      gs.ai_delay, "ai_delay", rx)
        y = self._row(lx, y, "Peek Reveal",
                      list(zip(PEEK_REVEAL_OPTIONS, PEEK_REVEAL_LABELS)),
                      gs.peek_reveal_time, "peek_reveal", rx)

    def _draw_access(self, lx, y, rx, gs):
        prof = self._profile_ref
        if prof is None:
            ts = self.label_font.render(
                "Profile not yet loaded - accessibility settings unavailable.",
                True, TEXT_DIM,
            )
            self.screen.blit(ts, (lx, y))
            return

        y = self._section(lx, y, "Theme")
        # Build the theme list: always-available (Parlor + CB modes + HC) plus
        # any unlockables the player has earned. Locked themes are not shown
        # here; they appear with their unlock condition in the Profile screen.
        from theme import (THEME_LABELS, ALWAYS_UNLOCKED, UNLOCKABLE_THEMES,
                           THEME_UNLOCK_CONDITIONS)
        unlocked = list(getattr(prof, 'unlocked_themes', ['default']))
        theme_options = []
        # Parlor first.
        theme_options.append(("default", THEME_LABELS["default"]))
        # Unlockables that the player has earned, in the canonical order.
        for k in UNLOCKABLE_THEMES:
            if k in unlocked:
                theme_options.append((k, THEME_LABELS.get(k, k)))
        # Accessibility themes always available.
        for k in ("deutan", "protan", "tritan", "high_contrast"):
            theme_options.append((k, THEME_LABELS.get(k, k)))
        y = self._row(lx, y, "Theme", theme_options,
                      prof.settings.theme, "theme", rx)
        # Show what's locked + how to unlock, so the player has a clear path.
        locked = [k for k in UNLOCKABLE_THEMES if k not in unlocked]
        if locked:
            from config import TEXT_DIM
            for k in locked:
                cond = THEME_UNLOCK_CONDITIONS.get(k, {})
                hint = self.small_font.render(
                    f"{THEME_LABELS.get(k, k)} — locked: {cond.get('label', '')}",
                    True, TEXT_DIM,
                )
                self.screen.blit(hint, (lx, y))
                y += hint.get_height() + 2
            y += 6
        y = self._row(lx, y, "Text Scale",
                      [(0.8, "80%"), (1.0, "100%"), (1.25, "125%"), (1.5, "150%")],
                      prof.settings.text_scale, "text_scale", rx)

        y += 8
        y = self._section(lx, y, "Motion & Visuals")
        y = self._row(lx, y, "Motion",
                      [(1.0, "Full"), (0.5, "Half"), (0.0, "Off")],
                      prof.settings.motion_scale, "motion", rx)
        y = self._row(lx, y, "Particles", [(True, "ON"), (False, "OFF")],
                      prof.settings.particles_enabled, "particles", rx)
        y = self._row(lx, y, "Captions", [(False, "OFF"), (True, "ON")],
                      prof.settings.captions, "captions", rx)

        y += 8
        y = self._section(lx, y, "Coaching")
        y = self._row(lx, y, "Hints",
                      [(0, "None"), (1, "Subtle"), (2, "Memory"), (3, "All")],
                      prof.settings.hint_tier, "hint_tier", rx)
        y = self._row(lx, y, "Coach Mode", [(False, "OFF"), (True, "ON")],
                      prof.settings.coach_mode, "coach", rx)

    def _draw_audio(self, lx, y, rx, gs):
        prof = self._profile_ref
        if prof is None:
            ts = self.label_font.render(
                "Profile not yet loaded - volume controls unavailable.",
                True, TEXT_DIM,
            )
            self.screen.blit(ts, (lx, y))
            return
        opts = [(0.0, "Off"), (0.25, "Low"), (0.5, "Med"), (0.75, "High"), (1.0, "Max")]
        y = self._section(lx, y, "Volumes")
        y = self._row(lx, y, "Master", opts,
                      max(prof.settings.sfx_volume, prof.settings.music_volume,
                          prof.settings.voice_volume),
                      "vol_master", rx)
        y = self._row(lx, y, "SFX", opts, prof.settings.sfx_volume, "vol_sfx", rx)
        y = self._row(lx, y, "Music", opts, prof.settings.music_volume, "vol_music", rx)
        y = self._row(lx, y, "Voice", opts, prof.settings.voice_volume, "vol_voice", rx)

        y += 8
        note = self.small_font.render(
            "Music is a low-volume ambient bus reserved for future tracks.",
            True, TEXT_DIM,
        )
        self.screen.blit(note, (lx, y))

    def _draw_profile(self, lx, y, rx, gs):
        prof = self._profile_ref
        if prof is None:
            ts = self.label_font.render(
                "Profile not yet loaded.",
                True, TEXT_DIM,
            )
            self.screen.blit(ts, (lx, y))
            return
        y = self._section(lx, y, "Streaming")
        y = self._row(lx, y, "Streamer Mode", [(False, "OFF"), (True, "ON")],
                      prof.settings.streamer_mode, "streamer", rx)
        note = self.small_font.render(
            "Streamer mode hides your hand from the bottom 220px of the screen.",
            True, TEXT_DIM,
        )
        self.screen.blit(note, (lx, y))
        y += 28

        y = self._section(lx, y, "Stats")
        s = prof.stats
        rows = [
            ("Games Played", str(s.games_played)),
            ("Games Won", f"{s.games_won}  ({(s.games_won/s.games_played*100):.0f}% wr)"
                          if s.games_played else "0"),
            ("Current Streak", str(s.current_win_streak)),
            ("Longest Streak", str(s.longest_win_streak)),
            ("Pairs Made", str(s.pairs_made)),
            ("Powers Used", str(s.powers_used)),
        ]
        value_x = lx + self._LABEL_COL_W + self._LABEL_GAP
        line_h = self.label_font.get_height() + 6
        for label, value in rows:
            l = self.label_font.render(label + ":", True, TEXT_DIM)
            self.screen.blit(l, (lx, y))
            v = self.label_font.render(value, True, TEXT_WHITE)
            self.screen.blit(v, (value_x, y))
            y += line_h

        y += 12
        y = self._section(lx, y, "Tutorial")
        complete = "Yes" if prof.tutorial_complete else "No"
        l = self.label_font.render("Tutorial Complete:", True, TEXT_DIM)
        self.screen.blit(l, (lx, y))
        v = self.label_font.render(complete, True, TEXT_WHITE)
        self.screen.blit(v, (value_x, y))

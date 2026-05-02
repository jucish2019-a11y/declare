"""Quick-access accessibility & profile-settings overlay.

Bound to F1 globally. Lets players toggle theme, captions, motion, particles,
streamer mode, hint tier, coach mode without leaving whatever screen they're
on. All changes persist immediately to profile.json.
"""
import pygame

import theme
import audio
from config import SCREEN_WIDTH, SCREEN_HEIGHT


class AccessibilityPanel:
    @property
    def PANEL_W(self):
        return min(720, int(SCREEN_WIDTH * 0.28))

    @property
    def PANEL_H(self):
        return min(600, int(SCREEN_HEIGHT * 0.42))

    def __init__(self):
        self.active = False
        self._fade = 0.0
        self._title_font = None
        self._sec_font = None
        self._body_font = None
        self._small_font = None
        self.controls = []
        self.hovered = -1

    def _ensure(self):
        if self._title_font is None:
            import typography as typo
            from config import get_mobile_scale
            m = get_mobile_scale()
            self._title_font = typo.display_bold(int(32 * m))
            self._sec_font = typo.body_bold(int(16 * m))
            self._body_font = typo.body_bold(int(18 * m))
            self._small_font = typo.body(int(14 * m))

    def open(self):
        self.active = True
        self._fade = 0.0
        audio.play("ui_open")

    def close(self):
        self.active = False
        audio.play("ui_close")

    def update(self, dt):
        if self.active:
            self._fade = min(1.0, self._fade + dt * 3.0)

    def draw(self, screen, prof, game_settings=None):
        if not self.active:
            return
        self._ensure()
        th = theme.active()
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, int(160 * self._fade)))
        screen.blit(overlay, (0, 0))

        px = (SCREEN_WIDTH - self.PANEL_W) // 2
        py = (SCREEN_HEIGHT - self.PANEL_H) // 2 - int((1 - self._fade) * 30)
        panel = pygame.Surface((self.PANEL_W, self.PANEL_H), pygame.SRCALPHA)
        pygame.draw.rect(panel, (*th.panel_bg, 240), panel.get_rect(), border_radius=14)
        pygame.draw.rect(panel, th.brass_500, panel.get_rect(), 2, border_radius=14)
        screen.blit(panel, (px, py))

        title = self._title_font.render("Accessibility & Profile", True, th.brass_300)
        screen.blit(title, (px + 28, py + 22))

        hint = self._small_font.render("F1 to toggle  ·  Auto-saves",
                                        True, th.text_dim)
        screen.blit(hint, (px + self.PANEL_W - hint.get_width() - 28, py + 32))

        self.controls = []
        cy = py + 86

        cy = self._draw_section(screen, px, cy, "Theme", th)
        themes = [("default", "Parlor"), ("deutan", "CB Deutan"),
                  ("protan", "CB Protan"), ("tritan", "CB Tritan"),
                  ("high_contrast", "High Contrast")]
        cy = self._draw_choice_row(
            screen, px, cy, themes, prof.settings.theme,
            lambda v: self._set_theme(prof, v), th,
        )

        cy = self._draw_section(screen, px, cy, "Display", th)
        cy = self._draw_choice_row(
            screen, px, cy,
            [(0.8, "80%"), (1.0, "100%"), (1.25, "125%"), (1.5, "150%")],
            prof.settings.text_scale,
            lambda v: self._set_text_scale(prof, v), th, "Text Scale:",
        )
        cy = self._draw_choice_row(
            screen, px, cy,
            [(1.0, "Full"), (0.5, "Half"), (0.0, "Off")],
            prof.settings.motion_scale,
            lambda v: self._set_motion(prof, game_settings, v), th, "Motion:",
        )
        cy = self._draw_choice_row(
            screen, px, cy,
            [(True, "On"), (False, "Off")],
            prof.settings.particles_enabled,
            lambda v: self._set_particles(prof, game_settings, v), th, "Particles:",
        )

        cy = self._draw_section(screen, px, cy, "Audio", th)
        cy = self._draw_choice_row(
            screen, px, cy,
            [(0.0, "Off"), (0.3, "Low"), (0.7, "Med"), (1.0, "High")],
            prof.settings.sfx_volume,
            lambda v: self._set_volume(prof, "sfx", v), th, "SFX:",
        )
        cy = self._draw_choice_row(
            screen, px, cy,
            [(False, "Off"), (True, "On")],
            prof.settings.captions,
            lambda v: self._set_captions(prof, game_settings, v), th, "Captions:",
        )

        cy = self._draw_section(screen, px, cy, "Coaching", th)
        cy = self._draw_choice_row(
            screen, px, cy,
            [(0, "None"), (1, "Subtle"), (2, "Memory aids"), (3, "All")],
            prof.settings.hint_tier,
            lambda v: self._set_hint_tier(prof, game_settings, v), th, "Hints:",
        )
        cy = self._draw_choice_row(
            screen, px, cy,
            [(False, "Off"), (True, "On")],
            prof.settings.coach_mode,
            lambda v: self._set_coach(prof, game_settings, v), th, "Coach:",
        )
        cy = self._draw_choice_row(
            screen, px, cy,
            [(False, "Off"), (True, "On")],
            prof.settings.streamer_mode,
            lambda v: self._set_streamer(prof, game_settings, v), th, "Streamer:",
        )

        close_w = 130
        close_h = 38
        close_rect = pygame.Rect(px + self.PANEL_W // 2 - close_w // 2,
                                  py + self.PANEL_H - close_h - 20,
                                  close_w, close_h)
        pygame.draw.rect(screen, th.brass_500, close_rect, border_radius=8)
        pygame.draw.rect(screen, th.brass_300, close_rect, 2, border_radius=8)
        cs = self._body_font.render("Close", True, th.text_white)
        screen.blit(cs, cs.get_rect(center=close_rect.center))
        self.controls.append(("close", close_rect, None))

    def _draw_section(self, screen, px, cy, label, th):
        s_surf = self._sec_font.render(label.upper(), True, th.brass_300)
        screen.blit(s_surf, (px + 28, cy))
        pygame.draw.line(screen, th.brass_700,
                         (px + 28 + s_surf.get_width() + 16, cy + s_surf.get_height() // 2),
                         (px + self.PANEL_W - 28, cy + s_surf.get_height() // 2), 1)
        return cy + 26

    def _draw_choice_row(self, screen, px, cy, options, current, on_select, th, label=None):
        x = px + 28
        if label:
            lbl_surf = self._small_font.render(label, True, th.text_dim)
            screen.blit(lbl_surf, (x, cy + 8))
            x = px + 130
        bw = max(80, (self.PANEL_W - 28 - x + px) // max(1, len(options)) - 6)
        bh = 32
        for value, label_text in options:
            r = pygame.Rect(x, cy, bw, bh)
            active = (value == current)
            color = th.signal_go if active else (60, 60, 60)
            border = th.brass_300 if active else th.brass_700
            pygame.draw.rect(screen, color, r, border_radius=6)
            pygame.draw.rect(screen, border, r, 1, border_radius=6)
            ts = self._small_font.render(str(label_text), True, th.text_white)
            screen.blit(ts, ts.get_rect(center=r.center))
            self.controls.append(("select", r, (on_select, value)))
            x += bw + 6
        return cy + bh + 12

    def handle_event(self, event, prof, game_settings=None):
        if not self.active:
            return None
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_F1):
                self.close()
                return "close"
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for kind, rect, payload in self.controls:
                if rect.collidepoint(event.pos):
                    if kind == "close":
                        self.close()
                        return "close"
                    if kind == "select":
                        on_select, value = payload
                        on_select(value)
                        audio.play("click")
                        import profile as profile_mod
                        profile_mod.save(prof)
                        return "updated"
        return None

    def _set_theme(self, prof, key):
        prof.settings.theme = key
        theme.set_active(key)
        if key in ("deutan", "protan", "tritan"):
            import profile as profile_mod
            profile_mod.unlock(prof, "colorblind_friend")
        try:
            import card_render
            card_render.invalidate_cache()
        except ImportError:
            pass

    def _set_text_scale(self, prof, scale):
        prof.settings.text_scale = scale
        theme.apply_text_scale(scale)

    def _set_motion(self, prof, gs, scale):
        prof.settings.motion_scale = scale
        theme.apply_motion_scale(scale)
        if gs:
            gs.motion_scale = scale

    def _set_particles(self, prof, gs, enabled):
        prof.settings.particles_enabled = enabled
        theme.apply_particles(enabled)
        if gs:
            gs.particles_enabled = enabled

    def _set_volume(self, prof, bus, value):
        if bus == "sfx":
            prof.settings.sfx_volume = value
        elif bus == "music":
            prof.settings.music_volume = value
        elif bus == "voice":
            prof.settings.voice_volume = value
        audio.set_volume(bus, value)

    def _set_captions(self, prof, gs, enabled):
        prof.settings.captions = enabled
        if gs:
            gs.captions = enabled

    def _set_hint_tier(self, prof, gs, tier):
        prof.settings.hint_tier = tier
        if gs:
            gs.hint_tier = tier

    def _set_coach(self, prof, gs, enabled):
        prof.settings.coach_mode = enabled
        if gs:
            gs.coach_mode = enabled

    def _set_streamer(self, prof, gs, enabled):
        prof.settings.streamer_mode = enabled
        if gs:
            gs.streamer_mode = enabled

"""Pause overlay: opens on Esc, freezes the game underneath."""
import pygame

import theme
from config import SCREEN_WIDTH, SCREEN_HEIGHT, get_mobile_scale


class PauseOverlay:
    @property
    def _panel_w(self):
        return min(768, int(SCREEN_WIDTH * 0.30))

    @property
    def _panel_h(self):
        return min(736, int(SCREEN_HEIGHT * 0.51))

    def __init__(self):
        self._title_font = None
        self._option_font = None
        self._small_font = None
        self.options = [
            ("resume",      "Resume"),
            ("restart",     "Restart Match"),
            ("settings",    "Settings"),
            ("quit_menu",   "Quit to Menu"),
        ]
        self.selected = 0
        self.hovered_index = -1
        self._fade_t = 0.0

    def _ensure_fonts(self):
        if self._title_font is None:
            import typography as typo
            m = get_mobile_scale()
            self._title_font = typo.display_bold(int(68 * m))
            self._option_font = typo.body_bold(int(42 * m))
            self._small_font = typo.body(int(26 * m))

    def reset(self):
        self.selected = 0
        self.hovered_index = -1
        self._fade_t = 0.0

    def update(self, dt):
        self._fade_t = min(1.0, self._fade_t + dt * 4.0)

    def draw(self, screen):
        self._ensure_fonts()
        t = theme.active()
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, int(160 * self._fade_t)))
        screen.blit(overlay, (0, 0))

        panel_w = self._panel_w
        panel_h = self._panel_h
        panel_x = SCREEN_WIDTH // 2 - panel_w // 2
        panel_y = SCREEN_HEIGHT // 2 - panel_h // 2
        slide_y = int((1.0 - self._fade_t) * 48)
        panel_y -= slide_y

        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        pygame.draw.rect(panel, (*t.panel_bg, 230), panel.get_rect(), border_radius=22)
        pygame.draw.rect(panel, t.brass_500, panel.get_rect(), 3, border_radius=22)
        inner = pygame.Rect(13, 13, panel_w - 26, panel_h - 26)
        pygame.draw.rect(panel, t.brass_700, inner, 1, border_radius=16)
        screen.blit(panel, (panel_x, panel_y))

        title_surf = self._title_font.render("PAUSED", True, t.brass_300)
        title_rect = title_surf.get_rect(center=(SCREEN_WIDTH // 2, panel_y + int(panel_h * 0.13)))
        screen.blit(title_surf, title_rect)

        rule_y = panel_y + int(panel_h * 0.22)
        pygame.draw.line(
            screen, t.brass_700,
            (panel_x + 96, rule_y), (panel_x + panel_w - 96, rule_y), 2,
        )

        start_y = panel_y + int(panel_h * 0.30)
        spacing = int(panel_h * 0.11)
        self._option_rects = []
        for i, (key, label) in enumerate(self.options):
            y = start_y + i * spacing
            is_focus = (i == self.selected) or (i == self.hovered_index)
            color = t.brass_300 if is_focus else t.text_white
            label_surf = self._option_font.render(label, True, color)
            rect = label_surf.get_rect(center=(SCREEN_WIDTH // 2, y))
            self._option_rects.append((rect, key))
            if is_focus:
                bar = pygame.Rect(rect.x - 28, rect.y, 6, rect.height)
                pygame.draw.rect(screen, t.brass_300, bar, border_radius=3)
                bar2 = pygame.Rect(rect.right + 22, rect.y, 6, rect.height)
                pygame.draw.rect(screen, t.brass_300, bar2, border_radius=3)
            screen.blit(label_surf, rect)

        hint_surf = self._small_font.render(
             "Esc - Resume    Up/Down - Navigate    Enter - Select",
            True, t.text_dim,
        )
        screen.blit(hint_surf, hint_surf.get_rect(center=(SCREEN_WIDTH // 2, panel_y + panel_h - int(panel_h * 0.06))))

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self.selected = (self.selected - 1) % len(self.options)
                return ("nav", None)
            if event.key in (pygame.K_DOWN, pygame.K_s):
                self.selected = (self.selected + 1) % len(self.options)
                return ("nav", None)
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                return ("select", self.options[self.selected][0])
            if event.key == pygame.K_ESCAPE:
                return ("select", "resume")
        if event.type == pygame.MOUSEMOTION:
            self.hovered_index = -1
            for i, (rect, _key) in enumerate(getattr(self, "_option_rects", [])):
                if rect.collidepoint(event.pos):
                    self.hovered_index = i
                    self.selected = i
                    return ("nav", None)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, (rect, key) in enumerate(getattr(self, "_option_rects", [])):
                if rect.collidepoint(event.pos):
                    return ("select", key)
        return (None, None)

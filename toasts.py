"""Toast notification queue: short slide-in messages, top-right of the screen.

Layered above gameplay, never blocks input, never blocks AI. Three lanes,
oldest auto-dismissed first. Each toast has a 2-second life by default.
"""
import math
import pygame
from collections import deque

import theme
from config import SCREEN_WIDTH


class Toast:
    __slots__ = ("text", "kind", "icon", "life", "max_life", "y_offset", "_age")

    def __init__(self, text, kind="info", icon=None, life=2.4):
        self.text = text
        self.kind = kind
        self.icon = icon
        self.life = life
        self.max_life = life
        self.y_offset = 0.0
        self._age = 0.0

    def update(self, dt):
        self.life -= dt
        self._age += dt

    def alpha(self):
        if self._age < 0.18:
            return self._age / 0.18
        if self.life < 0.4:
            return max(0.0, self.life / 0.4)
        return 1.0

    def slide_in(self):
        if self._age >= 0.25:
            return 0.0
        t = max(0.0, 1.0 - self._age / 0.25)
        return 200.0 * (t ** 2)

    @property
    def expired(self):
        return self.life <= 0


class ToastManager:
    def __init__(self, max_visible=4):
        self.toasts = deque()
        self.max_visible = max_visible
        self._font = None
        self._small_font = None

    def _ensure_fonts(self):
        if self._font is None:
            import typography as typo
            from config import get_mobile_scale
            m = get_mobile_scale()
            self._font = typo.body_bold(int(18 * m))
            self._small_font = typo.body(int(14 * m))

    def push(self, text, kind="info", icon=None, life=2.4):
        toast = Toast(text=text, kind=kind, icon=icon, life=life)
        self.toasts.append(toast)
        while len(self.toasts) > self.max_visible:
            self.toasts.popleft()

    def update(self, dt):
        for t in list(self.toasts):
            t.update(dt)
        while self.toasts and self.toasts[0].expired:
            self.toasts.popleft()

    def draw(self, screen):
        if not self.toasts:
            return
        self._ensure_fonts()
        t = theme.active()
        margin = 18
        spacing = 8
        x_right = SCREEN_WIDTH - margin
        y_cursor = margin + 50

        for toast in list(self.toasts):
            text_surf = self._font.render(toast.text, True, t.text_white)
            tw = text_surf.get_width()
            box_w = tw + 56
            box_h = 44
            slide = toast.slide_in()
            box_x = x_right - box_w + int(slide)
            box_y = y_cursor

            box_alpha = int(220 * toast.alpha())
            if box_alpha <= 0:
                y_cursor += box_h + spacing
                continue

            box_surf = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
            kind_color = self._kind_color(toast.kind, t)
            pygame.draw.rect(
                box_surf, (*t.panel_bg, box_alpha),
                box_surf.get_rect(), border_radius=8,
            )
            stripe = pygame.Rect(0, 0, 4, box_h)
            pygame.draw.rect(
                box_surf, (*kind_color, box_alpha),
                stripe, border_radius=2,
            )
            pygame.draw.rect(
                box_surf, (*t.panel_border, box_alpha),
                box_surf.get_rect(), 1, border_radius=8,
            )
            screen.blit(box_surf, (box_x, box_y))

            if toast.icon:
                icon_color = (*kind_color, int(255 * toast.alpha()))
                icon_surf = self._font.render(toast.icon, True, kind_color)
                icon_surf.set_alpha(int(255 * toast.alpha()))
                screen.blit(icon_surf, (box_x + 16, box_y + 12))

            text_surf.set_alpha(int(255 * toast.alpha()))
            screen.blit(text_surf, (box_x + 40, box_y + 12))

            y_cursor += box_h + spacing

    def _kind_color(self, kind, t):
        return {
            "info":    t.signal_info,
            "success": t.signal_go,
            "warn":    t.signal_warn,
            "error":   t.signal_stop,
            "achievement": t.brass_300,
        }.get(kind, t.signal_info)

    def clear(self):
        self.toasts.clear()

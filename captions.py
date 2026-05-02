"""Caption strip: time-coded text glosses of audio events for accessibility."""
import pygame
import time
from collections import deque

import theme
from config import SCREEN_WIDTH, SCREEN_HEIGHT


class CaptionStream:
    def __init__(self, max_visible=4, life=2.5):
        self.lines = deque()
        self.max_visible = max_visible
        self.life = life
        self._font = None

    def push(self, text):
        if not text:
            return
        self.lines.append((text, time.monotonic()))
        while len(self.lines) > self.max_visible:
            self.lines.popleft()

    def update(self):
        now = time.monotonic()
        while self.lines and (now - self.lines[0][1]) > self.life:
            self.lines.popleft()

    def draw(self, screen):
        if not self.lines:
            return
        if self._font is None:
            import typography as typo
            from config import get_mobile_scale
            m = get_mobile_scale()
            self._font = typo.body_bold(int(18 * m))
        th = theme.active()
        now = time.monotonic()
        x = 24
        y = SCREEN_HEIGHT - 220
        for text, t in self.lines:
            age = now - t
            alpha = max(0, min(255, int(255 * (1.0 - age / self.life))))
            surf = self._font.render(text, True, th.text_white)
            bg_w = surf.get_width() + 16
            bg_h = surf.get_height() + 6
            bg = pygame.Surface((bg_w, bg_h), pygame.SRCALPHA)
            pygame.draw.rect(bg, (0, 0, 0, int(180 * alpha / 255)),
                             bg.get_rect(), border_radius=4)
            screen.blit(bg, (x, y))
            surf.set_alpha(alpha)
            screen.blit(surf, (x + 8, y + 3))
            y += bg_h + 4

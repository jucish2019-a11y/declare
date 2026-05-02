import math
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


# Cached parlor backdrop, keyed on theme name + atmospheric/HC flags.
# Built once per theme — every supporting screen (menu / setup / peek /
# game-over) shares the same composition for a unified visual language.
_BACKDROP_CACHE = {}


def _draw_screens_brass_ornament(surface, cx, cy, th):
    """Small inlaid brass diamond + compass pips. Mirrors the in-game
    `_draw_brass_ornament` helper — duplicated here so screens.py doesn't
    depend on the in-game Renderer's lifecycle."""
    outer_pts = [(cx, cy - 14), (cx + 10, cy), (cx, cy + 14), (cx - 10, cy)]
    pygame.draw.polygon(surface, th.brass_500, outer_pts)
    pygame.draw.polygon(surface, th.brass_900, outer_pts, 1)
    inner_pts = [(cx, cy - 8), (cx + 5, cy), (cx, cy + 8), (cx - 5, cy)]
    pygame.draw.polygon(surface, th.brass_300, inner_pts)
    pygame.draw.circle(surface, th.brass_900, (cx, cy), 2)
    for dx, dy in ((0, -20), (0, 20), (-18, 0), (18, 0)):
        pygame.draw.circle(surface, th.brass_500, (cx + dx, cy + dy), 2)


_MENU_BG_CACHE = {'surface': None, 'mtime': None}
_MENU_BG_WINDOW_CACHE = {'key': None, 'surface': None}


def _screen_background():
    """Load and cache the shared backdrop image at `assets/menu_bg.png`.

    Used by every supporting screen (menu / setup / peek / game-over) so
    they share a consistent visual base. Scaled with a "cover" fit so it
    fills the full screen at the correct aspect ratio (cropping the longer
    dimension as needed). Re-loads automatically if the file's mtime
    changes so a designer can drop in a new image without restarting the
    game. Falls back to the procedural parlor backdrop if the file is
    missing."""
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, '..', 'assets', 'menu_bg.png')
    path = os.path.normpath(path)
    if not os.path.exists(path):
        # Fallback: use the moody parlor backdrop on the active theme.
        import theme as theme_mod
        return parlor_backdrop(theme_mod.active())

    try:
        mtime = os.path.getmtime(path)
    except OSError:
        mtime = None
    if (_MENU_BG_CACHE['surface'] is not None
            and _MENU_BG_CACHE['mtime'] == mtime):
        return _MENU_BG_CACHE['surface']

    raw = pygame.image.load(path).convert()
    rw, rh = raw.get_size()
    # Cover-fit: scale so the smaller dimension just covers the screen,
    # then center-crop the overflow.
    scale = max(SCREEN_WIDTH / rw, SCREEN_HEIGHT / rh)
    sw = max(SCREEN_WIDTH, int(rw * scale))
    sh = max(SCREEN_HEIGHT, int(rh * scale))
    scaled = pygame.transform.smoothscale(raw, (sw, sh))
    out = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    out.blit(scaled, ((SCREEN_WIDTH - sw) // 2, (SCREEN_HEIGHT - sh) // 2))
    _MENU_BG_CACHE['surface'] = out
    _MENU_BG_CACHE['mtime'] = mtime
    return out


def get_menu_bg_texture(size):
    """Return a window-sized cover-fit of the shared menu backdrop.

    Used by the Display layer to fill letterbox bars on non-design-aspect
    windows so menus, setup, peek, and game-over share a continuous
    backdrop at any window size. Falls back to a cover-fit of the
    procedural parlor backdrop when `assets/menu_bg.png` is missing."""
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, '..', 'assets', 'menu_bg.png')
    path = os.path.normpath(path)
    try:
        mtime = os.path.getmtime(path) if os.path.exists(path) else None
    except OSError:
        mtime = None

    if mtime is None:
        import theme as theme_mod
        th = theme_mod.active()
        theme_key = (th.name,
                     getattr(th, 'is_atmospheric', True),
                     getattr(th, 'high_contrast', False))
        cache_key = ('parlor', theme_key, size)
    else:
        cache_key = ('image', mtime, size)

    if _MENU_BG_WINDOW_CACHE['key'] == cache_key:
        return _MENU_BG_WINDOW_CACHE['surface']

    if mtime is None:
        import theme as theme_mod
        base = parlor_backdrop(theme_mod.active())
    else:
        base = pygame.image.load(path).convert()
    bw, bh = base.get_size()
    scale = max(size[0] / bw, size[1] / bh)
    sw = max(size[0], int(bw * scale))
    sh = max(size[1], int(bh * scale))
    scaled = pygame.transform.smoothscale(base, (sw, sh))
    out = pygame.Surface(size)
    out.blit(scaled, ((size[0] - sw) // 2, (size[1] - sh) // 2))
    _MENU_BG_WINDOW_CACHE['key'] = cache_key
    _MENU_BG_WINDOW_CACHE['surface'] = out
    return out


def _draw_brass_pill(surface, cx, cy, w, h, text, font, th,
                      text_color=None, body_a=240):
    """Brass-edged pill: brass_900 → brass_700 vertical gradient body,
    brass_300 top highlight, brass_500 outline. Text centered in `font`.
    Used for section headers and small status badges throughout the
    supporting screens."""
    pill_x = cx - w // 2
    pill_y = cy - h // 2
    pill = pygame.Surface((w, h), pygame.SRCALPHA)
    for i in range(h):
        t = i / max(1, h - 1)
        r = int(th.brass_900[0] + (th.brass_700[0] - th.brass_900[0]) * t)
        g = int(th.brass_900[1] + (th.brass_700[1] - th.brass_900[1]) * t)
        b = int(th.brass_900[2] + (th.brass_700[2] - th.brass_900[2]) * t)
        pygame.draw.line(pill, (r, g, b, body_a), (0, i), (w, i))
    mask = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(),
                     border_radius=h // 2)
    pill.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    surface.blit(pill, (pill_x, pill_y))
    pygame.draw.line(surface, th.brass_300,
                     (pill_x + 8, pill_y + 1),
                     (pill_x + w - 8, pill_y + 1), 1)
    pygame.draw.rect(surface, th.brass_500,
                     pygame.Rect(pill_x, pill_y, w, h),
                     1, border_radius=h // 2)
    if text:
        text_surf = font.render(text, True, text_color or th.text_white)
        surface.blit(text_surf, text_surf.get_rect(center=(cx, cy)))


def _draw_brass_plate(surface, rect, th, accent_color=None,
                       body_a=240, radius=12):
    """Brass-trimmed plate: brass_900 → brass_700 gradient body,
    brass_300 top highlight, brass_500 outline at given radius. Optional
    accent_color paints a 10 px stripe along the left edge (used by
    Setup's seat plates to encode human/AI)."""
    x, y, w, h = rect.x, rect.y, rect.width, rect.height
    plate = pygame.Surface((w, h), pygame.SRCALPHA)
    for i in range(h):
        t = i / max(1, h - 1)
        r = int(th.brass_900[0] + (th.brass_700[0] - th.brass_900[0]) * t)
        g = int(th.brass_900[1] + (th.brass_700[1] - th.brass_900[1]) * t)
        b = int(th.brass_900[2] + (th.brass_700[2] - th.brass_900[2]) * t)
        pygame.draw.line(plate, (r, g, b, body_a), (0, i), (w, i))
    mask = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(),
                     border_radius=radius)
    plate.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    if accent_color is not None:
        pygame.draw.rect(plate, accent_color, pygame.Rect(0, 0, 10, h),
                         border_top_left_radius=radius,
                         border_bottom_left_radius=radius)
    surface.blit(plate, (x, y))
    pygame.draw.line(surface, th.brass_300,
                     (x + 8, y + 1),
                     (x + w - 8, y + 1), 1)
    pygame.draw.rect(surface, th.brass_500, rect, 1, border_radius=radius)


def parlor_backdrop(theme_obj, bright=False):
    """Return a cached backdrop surface for the supporting screens.

    Two variants:
    - **default** (Setup / Peek / Game-Over): moody late-night parlor — felt
      shadow base, modest lamp glow, strong vignette.
    - **bright** (Menu): inviting daytime parlor — brighter felt base, a
      larger and warmer lamp glow, and almost no vignette so the menu reads
      welcoming rather than ominous.

    Composition (bottom up): base fill → soft elliptical felt patch → warm
    lamp glow (skipped on HC + non-atmospheric themes) → optional vignette →
    brass corner ornaments."""
    key = (theme_obj.name,
           getattr(theme_obj, 'is_atmospheric', True),
           getattr(theme_obj, 'high_contrast', False),
           bool(bright))
    cached = _BACKDROP_CACHE.get(key)
    if cached is not None:
        return cached

    out = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    if bright:
        # Bright menu base: blend felt_mid 35 % toward white so the room
        # implies "lit" rather than "shadowed."
        base = (
            min(255, int(theme_obj.felt_mid[0] * 0.65 + 90)),
            min(255, int(theme_obj.felt_mid[1] * 0.65 + 90)),
            min(255, int(theme_obj.felt_mid[2] * 0.65 + 80)),
        )
    else:
        base = getattr(theme_obj, 'felt_shadow', theme_obj.felt_rim)
    out.fill(base)

    # Soft elliptical felt patch. Bright variant uses a much larger ellipse
    # so the lit zone fills almost the whole screen.
    cx, cy = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2
    if bright:
        rx = int(SCREEN_WIDTH * 0.55)
        ry = int(SCREEN_HEIGHT * 0.55)
    else:
        rx = int(SCREEN_WIDTH * 0.40)
        ry = int(SCREEN_HEIGHT * 0.35)
    felt_layer = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    steps = 36
    # Bright variant blends from felt_mid (edge) toward a felt_mid-lifted
    # center, so the entire felt reads brighter.
    if bright:
        edge = theme_obj.felt_mid
        center = (
            min(255, int(theme_obj.felt_mid[0] * 0.85 + 70)),
            min(255, int(theme_obj.felt_mid[1] * 0.85 + 70)),
            min(255, int(theme_obj.felt_mid[2] * 0.85 + 60)),
        )
    else:
        edge = theme_obj.felt_rim
        center = theme_obj.felt_mid
    for layer in range(steps, 0, -1):
        t = layer / steps
        ease = 1.0 - (1.0 - t) * (1.0 - t)
        col = (
            int(edge[0] + (center[0] - edge[0]) * (1 - ease)),
            int(edge[1] + (center[1] - edge[1]) * (1 - ease)),
            int(edge[2] + (center[2] - edge[2]) * (1 - ease)),
            255,
        )
        sx = int(rx * t)
        sy = int(ry * t)
        pygame.draw.ellipse(
            felt_layer, col,
            pygame.Rect(cx - sx, cy - sy, sx * 2, sy * 2),
        )
    out.blit(felt_layer, (0, 0))

    # Lamp glow.
    if (getattr(theme_obj, 'is_atmospheric', True)
            and not getattr(theme_obj, 'high_contrast', False)):
        lamp = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        lamp_cx, lamp_cy = cx, cy - int(ry * 0.15)
        if bright:
            pool_radius = int(rx * 0.85)
            peak_alpha = 70
        else:
            pool_radius = int(rx * 0.55)
            peak_alpha = 38
        for i in range(48, 0, -1):
            t = i / 48
            intensity = (1 - t) ** 1.6
            a = int(intensity * peak_alpha)
            if a <= 0:
                continue
            pygame.draw.circle(lamp, (*theme_obj.lamp_glow, a),
                               (lamp_cx, lamp_cy), int(pool_radius * t))
        out.blit(lamp, (0, 0))

    # Vignette — strong on the moody backdrop, almost absent on the bright one.
    vig = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    max_d = math.hypot(cx, cy)
    tint = (8, 5, 2)
    vignette_strength = 0.18 if bright else 0.55
    for i in range(28):
        t = i / 27
        r_v = int(max_d * (1.0 - t * 0.4))
        a = int(255 * vignette_strength * (t ** 2.2))
        pygame.draw.circle(vig, (*tint, a), (cx, cy), r_v)
    out.blit(vig, (0, 0))

    # Brass corner ornaments.
    inset = 96
    for ox, oy in ((inset, inset),
                   (SCREEN_WIDTH - inset, inset),
                   (inset, SCREEN_HEIGHT - inset),
                   (SCREEN_WIDTH - inset, SCREEN_HEIGHT - inset)):
        _draw_screens_brass_ornament(out, ox, oy, theme_obj)

    _BACKDROP_CACHE[key] = out
    return out


class Button:
    def __init__(self, x, y, w, h, text, color, hover_color,
                 text_color=TEXT_WHITE, icon=None):
        self.rect = pygame.Rect(x - w // 2, y - h // 2, w, h)
        self.text = text
        self.color = color
        self.hover_color = hover_color
        self.text_color = text_color
        self.is_hovered = False
        # Optional procedural icon kind: 'play', 'tutorial', 'how_to',
        # 'profile', 'settings', 'quit', 'start', 'back', 'continue'.
        self.icon = icon

    def draw(self, screen, font):
        import theme as theme_mod
        th = theme_mod.active()
        color = self.hover_color if self.is_hovered else self.color
        rect = self.rect

        # Hover lift — visual press-up by 2 px with the shadow staying put.
        lift = -2 if self.is_hovered else 0
        draw_rect = rect.move(0, lift)

        # Drop shadow anchored to the un-lifted rect for depth.
        shadow_surf = pygame.Surface((rect.width + 8, rect.height + 12), pygame.SRCALPHA)
        pygame.draw.rect(shadow_surf, (0, 0, 0, 110),
                         (4, 6, rect.width, rect.height), border_radius=12)
        screen.blit(shadow_surf, (rect.x - 4, rect.y))

        # Body plate — vertical gradient at 82 %–100 % shade of the body color.
        plate = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        for i in range(rect.height):
            t = i / max(1, rect.height - 1)
            shade = 0.82 + 0.20 * (1 - abs(t - 0.35) * 2)
            cc = (
                max(0, min(255, int(color[0] * shade))),
                max(0, min(255, int(color[1] * shade))),
                max(0, min(255, int(color[2] * shade))),
                255,
            )
            pygame.draw.line(plate, cc, (0, i), (rect.width, i))
        mask = pygame.Surface(plate.get_size(), pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=12)
        plate.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        screen.blit(plate, draw_rect)

        # Top highlight + brass border.
        pygame.draw.line(screen, th.brass_300,
                         (draw_rect.left + 6, draw_rect.top + 2),
                         (draw_rect.right - 6, draw_rect.top + 2), 1)
        pygame.draw.rect(screen, th.brass_500, draw_rect, 2, border_radius=12)

        # Icon + label, centered as a single block.
        text_surf = font.render(self.text, True, self.text_color)
        icon_size = int(rect.height * 0.5) if self.icon else 0
        icon_gap = 12 if self.icon else 0
        block_w = icon_size + icon_gap + text_surf.get_width()
        block_x = draw_rect.centerx - block_w // 2
        block_y = draw_rect.centery
        if self.icon:
            self._draw_icon(screen, block_x + icon_size // 2, block_y,
                            icon_size, self.icon, self.text_color)
        text_rect = text_surf.get_rect(
            midleft=(block_x + icon_size + icon_gap, block_y),
        )
        screen.blit(text_surf, text_rect)

    @staticmethod
    def _draw_icon(surface, cx, cy, size, kind, color):
        """Procedural button icon. `(cx, cy)` is the icon center. Drawn in
        the button's text color so it tracks visual hierarchy."""
        s = size
        thick = max(2, s // 10)

        if kind in ('play', 'start'):
            # Right-pointing triangle.
            pts = [
                (cx - s // 3, cy - s // 2),
                (cx + s // 2, cy),
                (cx - s // 3, cy + s // 2),
            ]
            pygame.draw.polygon(surface, color, pts)
        elif kind == 'tutorial':
            # Open-book glyph: two trapezoids meeting at a spine.
            book_w = s // 2
            book_h = int(s * 0.42)
            left = [
                (cx - book_w, cy - book_h),
                (cx - 2,       cy - book_h + 4),
                (cx - 2,       cy + book_h),
                (cx - book_w, cy + book_h - 4),
            ]
            right = [
                (cx + book_w, cy - book_h),
                (cx + 2,       cy - book_h + 4),
                (cx + 2,       cy + book_h),
                (cx + book_w, cy + book_h - 4),
            ]
            pygame.draw.polygon(surface, color, left, thick)
            pygame.draw.polygon(surface, color, right, thick)
            pygame.draw.line(surface, color,
                             (cx, cy - book_h + 2), (cx, cy + book_h - 2), thick)
        elif kind == 'how_to':
            # Card outline with a question mark inside.
            r = pygame.Rect(cx - s // 3, cy - s // 2, (s * 2) // 3, s)
            pygame.draw.rect(surface, color, r, thick, border_radius=4)
            # Question mark: simple two-stroke approximation.
            pygame.draw.arc(surface, color,
                            pygame.Rect(cx - s // 6, cy - s // 4, s // 3, s // 4),
                            0.3, 3.4, thick)
            pygame.draw.line(surface, color,
                             (cx, cy), (cx, cy + s // 8), thick)
            pygame.draw.circle(surface, color, (cx, cy + s // 4), max(1, thick - 1))
        elif kind == 'profile':
            # Head + shoulders silhouette.
            pygame.draw.circle(surface, color, (cx, cy - s // 6), s // 5, thick)
            pygame.draw.arc(surface, color,
                            pygame.Rect(cx - s // 3, cy, (s * 2) // 3, s // 2),
                            math.pi, 2 * math.pi, thick)
        elif kind == 'settings':
            # 8-tooth gear — two rotated squares + center hole.
            r_outer = s // 2
            r_inner = int(s * 0.30)
            for k in range(8):
                a = k * math.pi / 4
                x1 = cx + math.cos(a) * (r_inner + 1)
                y1 = cy + math.sin(a) * (r_inner + 1)
                x2 = cx + math.cos(a) * r_outer
                y2 = cy + math.sin(a) * r_outer
                pygame.draw.line(surface, color, (x1, y1), (x2, y2), thick + 1)
            pygame.draw.circle(surface, color, (cx, cy), r_inner, thick)
            pygame.draw.circle(surface, color, (cx, cy), max(1, s // 10))
        elif kind == 'quit':
            # Door with arrow exiting right.
            door = pygame.Rect(cx - s // 2, cy - s // 2, s // 3, s)
            pygame.draw.rect(surface, color, door, thick, border_radius=2)
            arrow_y = cy
            pygame.draw.line(surface, color,
                             (cx - s // 8, arrow_y), (cx + s // 2, arrow_y), thick)
            pygame.draw.polygon(surface, color, [
                (cx + s // 2, arrow_y),
                (cx + s // 4, arrow_y - s // 5),
                (cx + s // 4, arrow_y + s // 5),
            ])
        elif kind == 'back':
            # Left-pointing chevron.
            pygame.draw.lines(surface, color, False, [
                (cx + s // 4, cy - s // 2),
                (cx - s // 4, cy),
                (cx + s // 4, cy + s // 2),
            ], thick + 1)
        elif kind == 'continue':
            # Right-pointing chevron.
            pygame.draw.lines(surface, color, False, [
                (cx - s // 4, cy - s // 2),
                (cx + s // 4, cy),
                (cx - s // 4, cy + s // 2),
            ], thick + 1)

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
        h44 = int(44 * scale)
        h48 = int(48 * scale)
        base_y = int(SCREEN_HEIGHT * 0.65)
        SETTINGS_OLIVE = (110, 95, 50)
        SETTINGS_OLIVE_HOVER = (140, 122, 68)
        # Simplified menu: 3 primary actions only.
        # Help combines Tutorial + How To Play.
        # Settings and Profile are accessed in-game via the menu button.
        self.play_button = Button(cx, base_y, bw, int(bh * 1.15), "Play",
                                   SWAP_GREEN, SWAP_GREEN_HOVER, icon='play')
        self.help_button = Button(cx, base_y + int(bh * 1.15) + bsp * 2, bw, h48,
                                   PEEK_BLUE, PEEK_BLUE_HOVER, icon='tutorial')
        self.quit_button = Button(cx, base_y + int(bh * 1.15) + h48 + bsp * 4, bw, h44,
                                   DECLARE_RED, DECLARE_RED_HOVER, icon='quit')
        self.new_game_button = self.play_button
        self.buttons = [self.play_button, self.help_button, self.quit_button]
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

    def _compute_card_fan(self, t):
        """Return [(dx, cy, angle), ...] for the 5 fanned menu cards.

        Plays a one-shot shuffle on menu open (collapse to stack, riffle,
        fan back out, ~2.1s total) then settles into idle breathing forever."""
        import math as _math
        BASE = [(-288, 712, -16), (-144, 696, -8), (0, 688, 0),
                (144, 696, 8), (288, 712, 16)]
        STACK_X, STACK_Y = 0.0, 688.0
        INTRO_END = 0.3
        COLLAPSE_END = 0.8
        RIFFLE_END = 1.5
        FAN_END = 2.1

        out = []
        for i, (bx, by, ba) in enumerate(BASE):
            breath = t * 1.2 + i * 0.6
            sway_x = _math.sin(breath) * 2.5
            sway_y = _math.cos(breath * 0.85) * 1.8
            sway_a = _math.sin(breath * 0.7) * 0.6

            if t < INTRO_END:
                cx, cy, ang = bx, by, ba
            elif t < COLLAPSE_END:
                k = (t - INTRO_END) / (COLLAPSE_END - INTRO_END)
                ke = k * k * (3 - 2 * k)
                cx = bx * (1 - ke) + STACK_X * ke
                cy = by * (1 - ke) + STACK_Y * ke
                ang = ba * (1 - ke)
            elif t < RIFFLE_END:
                k = (t - COLLAPSE_END) / (RIFFLE_END - COLLAPSE_END)
                SIDE = (-1, -1, 0, 1, 1)
                SPREAD = (115, 55, 0, 55, 115)
                HEIGHT = (60, 78, 70, 78, 60)
                PHASE = (0.00, 0.10, 0.05, 0.10, 0.00)
                k_p = max(0.0, min(1.0, (k - PHASE[i]) / max(0.01, 1.0 - PHASE[i])))
                arc = _math.sin(k_p * _math.pi)
                cx = STACK_X + SIDE[i] * SPREAD[i] * arc
                cy = STACK_Y - HEIGHT[i] * arc
                ang = SIDE[i] * 14 * arc
            elif t < FAN_END:
                k = (t - RIFFLE_END) / (FAN_END - RIFFLE_END)
                ke = k * k * (3 - 2 * k)
                cx = STACK_X * (1 - ke) + bx * ke
                cy = STACK_Y * (1 - ke) + by * ke
                ang = ba * ke
            else:
                cx, cy, ang = bx + sway_x, by + sway_y, ba + sway_a
            out.append((cx, cy, ang))
        return out

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
        self.screen.blit(_screen_background(), (0, 0))

        back_surf = card_render.paint_back("classic", CARD_WIDTH, CARD_HEIGHT)
        target_w = int(CARD_WIDTH * 1.4)
        target_h = int(CARD_HEIGHT * 1.4)
        if getattr(self, '_card_back_src', None) is not back_surf:
            self._card_back_src = back_surf
            self._card_back_scaled = pygame.transform.smoothscale(back_surf, (target_w, target_h))
            silhouette = self._card_back_scaled.copy()
            silhouette.fill((0, 0, 0, 255), special_flags=pygame.BLEND_RGBA_MULT)
            blur = pygame.transform.smoothscale(
                pygame.transform.smoothscale(
                    silhouette, (max(1, target_w // 5), max(1, target_h // 5))
                ),
                (target_w, target_h),
            )
            blur.set_alpha(110)
            self._card_back_shadow = blur
        base = self._card_back_scaled
        shadow_src = self._card_back_shadow

        # Soft brass-tinted ground glow under the card fan so the cards
        # read as resting on a surface, not floating.
        if (getattr(th, 'is_atmospheric', True)
                and not getattr(th, 'high_contrast', False)):
            if not hasattr(self, '_fan_glow_cache'):
                self._fan_glow_cache = {}
            glow_key = th.name
            if glow_key not in self._fan_glow_cache:
                fan_glow = pygame.Surface((900, 280), pygame.SRCALPHA)
                for i in range(10, 0, -1):
                    t = i / 10
                    a = int(28 * (1 - t) ** 1.4)
                    if a <= 0:
                        continue
                    ew = int(900 * t)
                    eh = int(280 * t)
                    pygame.draw.ellipse(
                        fan_glow, (*th.brass_500, a),
                        pygame.Rect((900 - ew) // 2, (280 - eh) // 2, ew, eh),
                    )
                self._fan_glow_cache[glow_key] = fan_glow
            self.screen.blit(self._fan_glow_cache[glow_key],
                             (SCREEN_WIDTH // 2 - 450, 720 - 140))

        # Cache rotated card images to avoid per-frame rotate transforms.
        if not hasattr(self, '_fan_rot_cache'):
            self._fan_rot_cache = {}
        for dx, cy_f, angle in self._compute_card_fan(self._t):
            cx = SCREEN_WIDTH // 2 + int(dx)
            cy = int(cy_f)
            if abs(angle) > 0.05:
                # Round angle to nearest 0.5 degree for cache hits.
                angle_key = round(angle * 2) / 2
                cache_key = (angle_key, base)
                if cache_key not in self._fan_rot_cache:
                    self._fan_rot_cache[cache_key] = (
                        pygame.transform.rotate(base, angle_key),
                        pygame.transform.rotate(shadow_src, angle_key),
                    )
                scaled, shadow = self._fan_rot_cache[cache_key]
            else:
                scaled = base
                shadow = shadow_src
            sw, sh = shadow.get_size()
            self.screen.blit(shadow, (cx - sw // 2 + 3, cy - sh // 2 + 6))
            sw2, sh2 = scaled.get_size()
            self.screen.blit(scaled, (cx - sw2 // 2, cy - sh2 // 2))

        # Title with 3-pass brass shadow.
        title_surf = None
        for offset, alpha in ((6, 60), (3, 110), (0, 255)):
            t_color = th.brass_300 if alpha == 255 else th.brass_700
            t_surf = typo.render_with_letter_spacing(
                self.title_font, "DECLARE", t_color, spacing_px=10,
            )
            t_surf.set_alpha(alpha)
            r = t_surf.get_rect(center=(SCREEN_WIDTH // 2 + offset, 160 + offset))
            self.screen.blit(t_surf, r)
            if alpha == 255:
                title_surf = t_surf
                title_rect = r

        # Brass diamond ornaments flanking the title — east & west.
        if title_surf is not None:
            orn_y = title_rect.centery
            _draw_screens_brass_ornament(
                self.screen, title_rect.left - 56, orn_y, th)
            _draw_screens_brass_ornament(
                self.screen, title_rect.right + 56, orn_y, th)

        flourish_y = 339
        line_w = 352
        cx = SCREEN_WIDTH // 2
        pygame.draw.line(self.screen, th.brass_500, (cx - line_w, flourish_y),
                         (cx - 48, flourish_y), 1)
        pygame.draw.line(self.screen, th.brass_500, (cx + 48, flourish_y),
                         (cx + line_w, flourish_y), 1)
        pygame.draw.polygon(self.screen, th.brass_500,
                            [(cx, flourish_y - 8), (cx - 19, flourish_y), (cx, flourish_y + 8), (cx + 19, flourish_y)])

        subtitle_surf = self.subtitle_font.render("A Card Game of Memory & Strategy",
                                                   True, th.text_dim)
        self.screen.blit(subtitle_surf, subtitle_surf.get_rect(center=(SCREEN_WIDTH // 2, 400)))

        for button in self.buttons:
            button.draw(self.screen, self.button_font)

        # Footer separator line + version label.
        footer_y = SCREEN_HEIGHT - 60
        pygame.draw.line(self.screen, th.brass_700,
                         (96, footer_y),
                         (SCREEN_WIDTH - 96, footer_y), 1)
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
            if self.help_button.is_clicked(event.pos):
                return 'help'
            if self.quit_button.is_clicked(event.pos):
                return 'quit'
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                return 'new_game'
            if event.key == pygame.K_h:
                return 'help'
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
        self.small_font = typo.body(22)
        self.section_font = typo.header_bold(24)
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
                                  "Back", DECLARE_RED, DECLARE_RED_HOVER, icon='back')

    def _draw_background(self):
        self._t += 1 / 60
        self.screen.blit(_screen_background(), (0, 0))

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
        self.screen.blit(sub, sub.get_rect(center=(SCREEN_WIDTH // 2, 246)))

        # Subtle brass underline beneath the subtitle.
        underline_y = 282
        cx_screen = SCREEN_WIDTH // 2
        pygame.draw.line(self.screen, th.brass_500,
                         (cx_screen - 300, underline_y),
                         (cx_screen + 300, underline_y), 1)

        # Section header: brass-edged pill instead of plain text.
        cy = 336
        _draw_brass_pill(
            self.screen, SCREEN_WIDTH // 2, cy, 380, 46,
            "NUMBER OF PLAYERS", self.section_font, th,
            text_color=th.brass_300,
        )
        cy += 60

        # Player-count buttons: brass-plate body with active-state pulsing
        # inner glow so the choice reads at a glance.
        self.player_count_rects = {}
        bw, bh = 144, 80
        spacing = 22
        total_w = bw * 3 + spacing * 2
        start_x = SCREEN_WIDTH // 2 - total_w // 2
        pulse_t = (math.sin(self._t * 2 * math.pi * 1.0) + 1) * 0.5
        for idx, count in enumerate([2, 3, 4]):
            r = pygame.Rect(start_x + idx * (bw + spacing), cy, bw, bh)
            self.player_count_rects[count] = r
            active = (count == self.num_players)
            # Body gradient.
            body_top = th.brass_500 if active else (44, 40, 32)
            body_bot = th.brass_700 if active else (28, 26, 22)
            body = pygame.Surface((bw, bh), pygame.SRCALPHA)
            for i in range(bh):
                tt = i / max(1, bh - 1)
                rr = int(body_top[0] + (body_bot[0] - body_top[0]) * tt)
                gg = int(body_top[1] + (body_bot[1] - body_top[1]) * tt)
                bb = int(body_top[2] + (body_bot[2] - body_top[2]) * tt)
                pygame.draw.line(body, (rr, gg, bb, 250), (0, i), (bw, i))
            mask = pygame.Surface((bw, bh), pygame.SRCALPHA)
            pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(),
                             border_radius=10)
            body.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
            self.screen.blit(body, r.topleft)
            # Top highlight.
            pygame.draw.line(self.screen, th.brass_300 if active else th.brass_700,
                             (r.left + 6, r.top + 2),
                             (r.right - 6, r.top + 2), 1)
            border = th.brass_300 if active else th.brass_700
            pygame.draw.rect(self.screen, border, r, 2, border_radius=10)
            ts = self.title_font.render(str(count), True,
                                          th.text_white if active else th.text_dim)
            self.screen.blit(ts, ts.get_rect(center=r.center))
            # Soft pulsing inner glow on the active option.
            if active:
                glow_alpha = int(40 + 30 * pulse_t)
                glow = pygame.Surface((bw, bh), pygame.SRCALPHA)
                pygame.draw.rect(glow, (*th.brass_300, glow_alpha),
                                 glow.get_rect(), 3, border_radius=10)
                self.screen.blit(glow, r.topleft)

        seat_top = int(SCREEN_HEIGHT * 0.38)
        seat_h = 154
        seat_gap = 19
        seat_w = min(1472, SCREEN_WIDTH - 64)
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

        # Drop shadow.
        shadow = pygame.Surface((w + 13, h + 13), pygame.SRCALPHA)
        pygame.draw.rect(shadow, (0, 0, 0, 120), (6, 10, w, h), border_radius=12)
        self.screen.blit(shadow, (x - 6, y))

        # Brass-trimmed plate body with seat-identity accent stripe.
        accent_color = th.you_cyan if is_human else th.brass_500
        plate_rect = pygame.Rect(x, y, w, h)
        _draw_brass_plate(self.screen, plate_rect, th,
                          accent_color=accent_color, body_a=240, radius=12)

        # 3-tier avatar ring matching the in-game nameplate avatars.
        avatar_x = x + 61
        avatar_y = y + h // 2
        ring_outer = th.brass_900
        ring_fill = (40, 90, 100) if is_human else (60, 50, 30)
        ring_inner = th.you_cyan if is_human else th.brass_300
        pygame.draw.circle(self.screen, ring_outer, (avatar_x, avatar_y), 44)
        pygame.draw.circle(self.screen, ring_fill, (avatar_x, avatar_y), 41)
        pygame.draw.circle(self.screen, ring_inner, (avatar_x, avatar_y), 41, 2)
        initial_font = typo.display_bold(42)
        initial = initial_font.render(config["name"][0].upper() if config["name"] else "?",
                                       True, th.text_white)
        self.screen.blit(initial, initial.get_rect(center=(avatar_x, avatar_y)))

        seat_label = self.small_font.render(f"SEAT {i + 1}", True, th.brass_300)
        self.screen.blit(seat_label, (x + 125, y + 18))

        name_x = x + 125
        name_y = y + 51
        name_w = 416
        name_h = 51
        name_rect = pygame.Rect(name_x, name_y, name_w, name_h)
        self._name_rects[i] = name_rect
        focus = (self.active_input == i)
        pygame.draw.rect(self.screen, (244, 236, 216), name_rect, border_radius=6)
        pygame.draw.rect(self.screen, th.brass_300 if focus else (140, 130, 100),
                         name_rect, 2, border_radius=6)
        n_surf = self.input_font.render(config["name"], True, (30, 30, 30))
        self.screen.blit(n_surf, (name_rect.x + 16, name_rect.y + 11))
        if focus:
            cursor_x = name_rect.x + 16 + n_surf.get_width() + 1
            if (pygame.time.get_ticks() // 500) % 2 == 0:
                pygame.draw.line(self.screen, (30, 30, 30),
                                 (cursor_x, name_rect.y + 10),
                                 (cursor_x, name_rect.y + name_rect.height - 10), 2)

        if not is_human and config.get("quip"):
            quip = self.small_font.render(config["quip"], True, th.text_dim)
            self.screen.blit(quip, (name_x, y + h - 35))

        if is_human:
            tip = self.small_font.render("Click name to edit  ·  This is you",
                                          True, th.you_cyan)
            self.screen.blit(tip, (name_x, y + h - 35))

        # Human / AI toggle: brass-plate body with a colored "active side" glow
        # so the state reads at a glance.
        toggle_w = min(198, max(160, (w - 640) // 3))
        toggle_x = x + min(608, w - 480)
        toggle_y = y + h // 2 - 26
        toggle_h = 51
        toggle_rect = pygame.Rect(toggle_x, toggle_y, toggle_w, toggle_h)
        self._toggle_rects[i] = toggle_rect
        # Brass-plate body.
        toggle_body = pygame.Surface((toggle_w, toggle_h), pygame.SRCALPHA)
        for j_row in range(toggle_h):
            tt = j_row / max(1, toggle_h - 1)
            rr = int(th.brass_900[0] + (th.brass_700[0] - th.brass_900[0]) * tt)
            gg = int(th.brass_900[1] + (th.brass_700[1] - th.brass_900[1]) * tt)
            bb = int(th.brass_900[2] + (th.brass_700[2] - th.brass_900[2]) * tt)
            pygame.draw.line(toggle_body, (rr, gg, bb, 245), (0, j_row), (toggle_w, j_row))
        body_mask = pygame.Surface((toggle_w, toggle_h), pygame.SRCALPHA)
        pygame.draw.rect(body_mask, (255, 255, 255, 255), body_mask.get_rect(),
                         border_radius=toggle_h // 2)
        toggle_body.blit(body_mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        self.screen.blit(toggle_body, toggle_rect.topleft)
        # Active side highlight wash — half the capsule glows in the seat color.
        active_color = th.you_cyan if is_human else th.signal_warn
        half_w = toggle_w // 2
        wash = pygame.Surface((half_w, toggle_h), pygame.SRCALPHA)
        pygame.draw.rect(wash, (*active_color, 90), wash.get_rect(),
                         border_radius=toggle_h // 2)
        if is_human:
            self.screen.blit(wash, (toggle_rect.x, toggle_rect.y))
        else:
            self.screen.blit(wash, (toggle_rect.x + half_w, toggle_rect.y))
        # Outline.
        pygame.draw.rect(self.screen, th.brass_500, toggle_rect, 1,
                         border_radius=toggle_h // 2)
        # Knob.
        knob_x = toggle_rect.right - 26 if is_human else toggle_rect.x + 26
        pygame.draw.circle(self.screen, th.brass_900, (knob_x, toggle_rect.centery), 20)
        pygame.draw.circle(self.screen, th.brass_300, (knob_x, toggle_rect.centery), 18)
        # Label sits on the active side.
        label_txt = "Human" if is_human else "AI"
        ts = self.small_font.render(label_txt, True, th.text_white)
        if is_human:
            self.screen.blit(ts, (toggle_rect.x + 22, toggle_rect.centery - ts.get_height() // 2))
        else:
            self.screen.blit(ts, (toggle_rect.right - 22 - ts.get_width(),
                                   toggle_rect.centery - ts.get_height() // 2))

        # Difficulty pills (AI seats only) — brass-edged, active = brass_300 fill.
        if not is_human:
            diff_x = toggle_x + toggle_w + 26
            diff_y = y + h // 2 - 26
            self._diff_rects[i] = {}
            label = self.small_font.render("DIFFICULTY", True, th.brass_300)
            self.screen.blit(label, (diff_x, diff_y - 34))
            for j, diff in enumerate(["easy", "medium", "hard"]):
                bw_btn = min(134, max(96, (w - diff_x - x - 32) // 3 - 6))
                bh_btn = 51
                br = pygame.Rect(diff_x + j * (bw_btn + 6), diff_y, bw_btn, bh_btn)
                self._diff_rects[i][diff] = br
                active = (config["difficulty"] == diff)
                if active:
                    pygame.draw.rect(self.screen, th.brass_300, br, border_radius=8)
                    pygame.draw.rect(self.screen, th.brass_500, br, 2, border_radius=8)
                    pygame.draw.line(self.screen, th.brass_100,
                                     (br.left + 4, br.top + 1),
                                     (br.right - 4, br.top + 1), 1)
                    txt_color = th.brass_900
                else:
                    diff_body = pygame.Surface((bw_btn, bh_btn), pygame.SRCALPHA)
                    for j_row in range(bh_btn):
                        tt = j_row / max(1, bh_btn - 1)
                        rr = int(th.brass_900[0] + (th.brass_700[0] - th.brass_900[0]) * tt)
                        gg = int(th.brass_900[1] + (th.brass_700[1] - th.brass_900[1]) * tt)
                        bb = int(th.brass_900[2] + (th.brass_700[2] - th.brass_900[2]) * tt)
                        pygame.draw.line(diff_body, (rr, gg, bb, 235),
                                         (0, j_row), (bw_btn, j_row))
                    dm = pygame.Surface((bw_btn, bh_btn), pygame.SRCALPHA)
                    pygame.draw.rect(dm, (255, 255, 255, 255), dm.get_rect(),
                                     border_radius=8)
                    diff_body.blit(dm, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
                    self.screen.blit(diff_body, br.topleft)
                    pygame.draw.rect(self.screen, th.brass_700, br, 1,
                                     border_radius=8)
                    txt_color = th.text_dim
                ts2 = self.small_font.render(self.DIFFICULTY_LABEL[diff],
                                              True, txt_color)
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
        self.done_button = Button(SCREEN_WIDTH // 2, int(SCREEN_HEIGHT * 0.78), int(520 * scale), int(56 * scale), "I've Memorized — Continue",
                                   SWAP_GREEN, SWAP_GREEN_HOVER)

    def _draw_background(self):
        self.screen.blit(_screen_background(), (0, 0))

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
                                                                176 + offset)))

        if self.peek_count == 0:
            sub = self.subtitle_font.render(
                "No cards to peek this round - go in blind.", True, th.text_dim)
            self.screen.blit(sub, sub.get_rect(center=(SCREEN_WIDTH // 2, 288)))
        else:
            sub = self.subtitle_font.render(
                f"Memorize your bottom {self.peek_count} card{'s' if self.peek_count > 1 else ''} - "
                "they vanish when the timer runs out.",
                True, th.text_dim,
            )
            self.screen.blit(sub, sub.get_rect(center=(SCREEN_WIDTH // 2, 288)))

        remaining = max(0.0, 1.0 - self.elapsed / max(0.001, self.max_time))
        cx, cy = SCREEN_WIDTH // 2, 464
        radius = 64
        # Brass medallion timer: outer brass ring (3 layers) + radial brass
        # body, with a clean filled arc in `arc_color` over the inner area.
        pygame.draw.circle(self.screen, th.brass_700, (cx, cy), radius)
        pygame.draw.circle(self.screen, th.brass_500, (cx, cy), radius - 2)
        pygame.draw.circle(self.screen, th.brass_300, (cx, cy), radius - 4)
        # Inner radial fill brass_900 → brass_700.
        for i in range(radius - 6, 0, -1):
            t = 1 - (i / max(1, radius - 6))
            rr = int(th.brass_900[0] + (th.brass_700[0] - th.brass_900[0]) * t)
            gg = int(th.brass_900[1] + (th.brass_700[1] - th.brass_900[1]) * t)
            bb = int(th.brass_900[2] + (th.brass_700[2] - th.brass_900[2]) * t)
            pygame.draw.circle(self.screen, (rr, gg, bb), (cx, cy), i)
        # Specular highlight (top-left).
        hl = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(hl, (*th.brass_300, 70),
                           (radius - 12, radius - 12), max(2, radius // 3))
        self.screen.blit(hl, (cx - radius, cy - radius))
        # Filled remaining-time arc, color-coded.
        if remaining > 0:
            if remaining > 0.4:
                arc_color = th.brass_300
            elif remaining > 0.1:
                arc_color = th.signal_warn
            else:
                arc_color = th.signal_stop
            self._draw_arc(cx, cy, radius - 14, remaining, arc_color)
        secs_left = max(0.0, self.max_time - self.elapsed)
        if self.max_time >= 900:
            time_label = "INF"
        else:
            time_label = f"{secs_left:0.1f}s"
        secs_surf = typo.display_bold(28).render(time_label, True, th.text_white)
        self.screen.blit(secs_surf, secs_surf.get_rect(center=(cx, cy)))

        if game_manager is None:
            self.done_button.draw(self.screen, self.button_font)
            return
        human = next((p for p in game_manager.players if p.is_human), None)
        if human is None:
            self.done_button.draw(self.screen, self.button_font)
            return

        card_w = int(min(CARD_WIDTH * 1.6, (SCREEN_WIDTH - 128) // max(1, self.hand_size) - 32))
        card_h = int(card_w * 1.4)
        gap = 45
        total_width = card_w * self.hand_size + gap * (self.hand_size - 1)
        start_x = (SCREEN_WIDTH - total_width) // 2
        card_y = int(SCREEN_HEIGHT * 0.40)

        slot_label_font = typo.display_bold(20)
        peek_tag_font = typo.display_bold(18)

        for slot_idx in range(self.hand_size):
            x = start_x + slot_idx * (card_w + gap)
            card = human.hand[slot_idx]
            is_peek_slot = slot_idx in self.peeking and self.revealed

            shadow = pygame.Surface((card_w + 22, card_h + 29), pygame.SRCALPHA)
            pygame.draw.rect(shadow, (0, 0, 0, 130),
                             (11, 16, card_w, card_h), border_radius=12)
            self.screen.blit(shadow, (x - 11, card_y))

            # Brass-edged frame around every card so they read as inlaid into
            # the table rather than floating.
            frame_rect = pygame.Rect(x - 4, card_y - 4, card_w + 8, card_h + 8)
            pygame.draw.rect(self.screen, th.brass_700, frame_rect,
                             border_radius=14)
            pygame.draw.rect(self.screen, th.brass_500, frame_rect, 2,
                             border_radius=14)

            if card is None:
                empty = pygame.Rect(x, card_y, card_w, card_h)
                pygame.draw.rect(self.screen, (*th.felt_rim, ), empty, border_radius=12)
                pygame.draw.rect(self.screen, th.brass_700, empty, 2, border_radius=12)
                dash_font = typo.header(45)
                dash = dash_font.render("-", True, th.text_muted)
                self.screen.blit(dash, dash.get_rect(center=empty.center))
            elif is_peek_slot:
                face = card_render.paint_face(card, card_w, card_h)
                glow_size = (card_w + 38, card_h + 38)
                glow = pygame.Surface(glow_size, pygame.SRCALPHA)
                t_phase = pygame.time.get_ticks() / 1000.0
                pulse = 0.6 + 0.4 * abs((t_phase * 1.4) % 2 - 1)
                glow_alpha = int(140 * pulse * (0.5 + 0.5 * remaining))
                pygame.draw.rect(glow, (*th.brass_300, glow_alpha),
                                 glow.get_rect(), border_radius=18)
                self.screen.blit(glow, (x - 19, card_y - 19),
                                 special_flags=pygame.BLEND_RGBA_ADD)
                self.screen.blit(face, (x, card_y))

                tag_w, tag_h = 110, 32
                tag_rect = pygame.Rect(x + card_w - tag_w - 10, card_y + 10,
                                       tag_w, tag_h)
                _draw_brass_pill(
                    self.screen, tag_rect.centerx, tag_rect.centery,
                    tag_w, tag_h, "PEEKED", peek_tag_font, th,
                    text_color=th.brass_300,
                )
            else:
                back = card_render.paint_back("classic", card_w, card_h)
                dim = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
                dim.fill((0, 0, 0, 100))
                self.screen.blit(back, (x, card_y))
                self.screen.blit(dim, (x, card_y))
                hidden_label = peek_tag_font.render("HIDDEN", True, th.brass_300)
                self.screen.blit(hidden_label, hidden_label.get_rect(
                    center=(x + card_w // 2, card_y + card_h // 2)))

            # Slot label pill — brass-edged, Cinzel-Bold inside.
            slot_pill_w = 200
            slot_pill_h = 32
            _draw_brass_pill(
                self.screen, x + card_w // 2, card_y + card_h + 38,
                slot_pill_w, slot_pill_h,
                f"SLOT {slot_idx + 1}", slot_label_font, th,
                text_color=th.brass_300,
            )

        tip = self.small_font.render(
            "When the timer ends, your peeked cards flip back. Click anywhere to skip ahead.",
            True, th.text_dim,
        )
        self.screen.blit(tip, tip.get_rect(center=(SCREEN_WIDTH // 2,
                                                     card_y + card_h + 96)))

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
        bw = int(440 * scale)
        bh = int(80 * scale)
        by = int(SCREEN_HEIGHT * 0.88)
        self.play_again_button = Button(SCREEN_WIDTH // 2 - bw // 2 - 16, by, bw, bh, "Play Again",
                                        SWAP_GREEN, SWAP_GREEN_HOVER)
        self.menu_button = Button(SCREEN_WIDTH // 2 + bw // 2 + 16, by, bw, bh, "Main Menu",
                                  DECLARE_RED, DECLARE_RED_HOVER, icon='back')
        self.buttons = [self.play_again_button, self.menu_button]
        self._bg_cache = None

    def _build_background(self):
        import theme as theme_mod
        th = theme_mod.active()
        bg = _screen_background().copy()
        # Game-over keeps the brass oval flourish for theatrical framing.
        center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
        rx, ry = 1216, 672
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

        flourish_y = 243
        cx = SCREEN_WIDTH // 2
        line_w = 384
        pygame.draw.line(self.screen, th.brass_500, (cx - line_w, flourish_y),
                         (cx - 48, flourish_y), 1)
        pygame.draw.line(self.screen, th.brass_500, (cx + 48, flourish_y),
                         (cx + line_w, flourish_y), 1)
        pygame.draw.polygon(self.screen, th.brass_500,
                            [(cx, flourish_y - 8), (cx - 19, flourish_y),
                             (cx, flourish_y + 8), (cx + 19, flourish_y)])

        banner_surf = self.banner_font.render(banner_text, True, banner_color)
        banner_rect = banner_surf.get_rect(center=(SCREEN_WIDTH // 2, 301))
        chip_w = banner_rect.width + 90
        chip_h = banner_rect.height + 29
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
        panel_h = CARD_HEIGHT + 320
        panel_rect = pygame.Rect(x_center - panel_w // 2, top_y, panel_w, panel_h)

        shadow = pygame.Surface((panel_w + 19, panel_h + 19), pygame.SRCALPHA)
        pygame.draw.rect(shadow, (0, 0, 0, 120), (10, 13, panel_w, panel_h),
                         border_radius=14)
        self.screen.blit(shadow, (panel_rect.x - 10, panel_rect.y + 6))

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
            crown_y = panel_rect.top - 22
            pts = [
                (x_center - 29, crown_y + 22),
                (x_center - 22, crown_y),
                (x_center - 11, crown_y + 13),
                (x_center, crown_y - 6),
                (x_center + 11, crown_y + 13),
                (x_center + 22, crown_y),
                (x_center + 29, crown_y + 22),
            ]
            pygame.draw.polygon(self.screen, th.brass_300, pts)
            pygame.draw.polygon(self.screen, th.brass_700, pts, 2)

        name_color = th.brass_300 if is_winner else th.text_white
        name_surf = self.name_font.render(player.name, True, name_color)
        self.screen.blit(name_surf, name_surf.get_rect(
            center=(x_center, panel_rect.top + 51)))

        score_label = self.small_font.render("SCORE", True, th.text_dim)
        self.screen.blit(score_label, score_label.get_rect(
            center=(x_center, panel_rect.top + 96)))
        score_color = th.brass_300 if is_winner else th.text_white
        score_surf = self.score_font.render(str(score_val), True, score_color)
        self.screen.blit(score_surf, score_surf.get_rect(
            center=(x_center, panel_rect.top + 144)))

        gap = 19
        total_w = hand_size * CARD_WIDTH + (hand_size - 1) * gap
        cards_x = x_center - total_w // 2
        cards_y = panel_rect.top + 208
        for slot_idx in range(hand_size):
            card = player.hand[slot_idx]
            cx = cards_x + slot_idx * (CARD_WIDTH + gap)
            shadow_card = pygame.Surface((CARD_WIDTH + 13, CARD_HEIGHT + 13),
                                          pygame.SRCALPHA)
            pygame.draw.rect(shadow_card, (0, 0, 0, 120),
                             (6, 10, CARD_WIDTH, CARD_HEIGHT),
                             border_radius=CORNER_RADIUS)
            self.screen.blit(shadow_card, (cx - 6, cards_y - 6))
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
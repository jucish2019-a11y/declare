"""High-quality card painter.

Loads real public-domain PNG cards from assets/cards/ when available, falls
back to procedural rendering when not. Procedural fallback is still high
quality (paper texture, pip layouts, deco face cards) so the game looks
right whether or not the asset pack was downloaded.
"""
import math
import os
import pygame
import random

import theme
from config import CARD_WIDTH, CARD_HEIGHT, CORNER_RADIUS


_FACE_CACHE = {}
_BACK_CACHE = {}
_RAW_PNG_CACHE = {}


def _assets_dir():
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(here, "assets", "cards")


def _load_png_face(card):
    key = (card.rank, card.suit)
    if key in _RAW_PNG_CACHE:
        return _RAW_PNG_CACHE[key]
    path = os.path.join(_assets_dir(), f"{card.rank}_{card.suit}.png")
    if not os.path.exists(path):
        _RAW_PNG_CACHE[key] = None
        return None
    try:
        surf = pygame.image.load(path).convert_alpha()
    except (pygame.error, FileNotFoundError):
        _RAW_PNG_CACHE[key] = None
        return None
    _RAW_PNG_CACHE[key] = surf
    return surf


def _load_png_back(style):
    key = ("back", style)
    if key in _RAW_PNG_CACHE:
        return _RAW_PNG_CACHE[key]
    style_filename = {
        "classic": "back_red.png",
        "deco_brass": "back_red.png",
        "deco_emerald": "back_red.png",
        "deco_obsidian": "back_red.png",
    }.get(style, "back_red.png")
    path = os.path.join(_assets_dir(), style_filename)
    if not os.path.exists(path):
        _RAW_PNG_CACHE[key] = None
        return None
    try:
        surf = pygame.image.load(path).convert_alpha()
    except (pygame.error, FileNotFoundError):
        _RAW_PNG_CACHE[key] = None
        return None
    _RAW_PNG_CACHE[key] = surf
    return surf


def _scaled_to_card(src, w, h):
    if src.get_size() == (w, h):
        return src
    return pygame.transform.smoothscale(src, (w, h))


def invalidate_cache():
    _FACE_CACHE.clear()
    _BACK_CACHE.clear()


def _font(size, bold=True):
    import typography as typo
    return typo.body_bold(size) if bold else typo.body(size)


def _serif_font(size, bold=True):
    import typography as typo
    return typo.header_bold(size) if bold else typo.header(size)


SUIT_GLYPH = {"spade": "♠", "heart": "♥", "diamond": "♦", "club": "♣"}


def _draw_corner_chip(surf, card, w, h):
    """Paint a small high-contrast rank+suit indicator in the top-left corner.

    Suit drawn as a polygon (not a font glyph) so missing-Unicode fonts can't
    break it. Subtle paper-color background so it doesn't fight the card art."""
    color = (178, 34, 34) if card.is_red else (26, 26, 26)
    rank_size = max(13, int(h * 0.16))
    rank_font = _serif_font(rank_size, bold=True)
    rank_surf = rank_font.render(card.rank, True, color)
    suit_pip_size = max(7, int(h * 0.09))

    chip_w = max(rank_surf.get_width(), suit_pip_size * 2) + 10
    chip_h = rank_surf.get_height() + suit_pip_size * 2 + 6
    chip = pygame.Surface((chip_w, chip_h), pygame.SRCALPHA)
    pygame.draw.rect(chip, (244, 236, 216, 240), chip.get_rect(), border_radius=4)
    pygame.draw.rect(chip, (*color, 110), chip.get_rect(), 1, border_radius=4)
    chip.blit(rank_surf, ((chip_w - rank_surf.get_width()) // 2, 1))
    suit_cy = rank_surf.get_height() + suit_pip_size + 2
    _draw_pip(chip, chip_w // 2, suit_cy, card.suit, color, size=suit_pip_size)
    surf.blit(chip, (3, 3))

    chip_rot = pygame.transform.rotate(chip, 180)
    surf.blit(chip_rot, (w - chip_rot.get_width() - 3, h - chip_rot.get_height() - 3))


def _ink(card):
    th = theme.active()
    return th.ink_red if card.is_red else th.ink_black


def _paper(width=CARD_WIDTH, height=CARD_HEIGHT):
    th = theme.active()
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    base = th.paper_warm
    pygame.draw.rect(surf, base, surf.get_rect(), border_radius=CORNER_RADIUS)
    rng = random.Random((width << 8) ^ height ^ sum(base))
    grain = pygame.Surface((width, height), pygame.SRCALPHA)
    for _ in range(60):
        x = rng.randint(0, width - 1)
        y = rng.randint(0, height - 1)
        a = rng.randint(8, 18)
        pygame.draw.circle(grain, (200, 188, 160, a), (x, y), 1)
    surf.blit(grain, (0, 0))

    bevel = pygame.Surface((width, height), pygame.SRCALPHA)
    pygame.draw.line(bevel, (255, 250, 235, 70), (4, 3), (width - 5, 3), 1)
    pygame.draw.line(bevel, (255, 250, 235, 50), (3, 4), (3, height - 5), 1)
    pygame.draw.line(bevel, (60, 40, 20, 50), (4, height - 4), (width - 5, height - 4), 1)
    pygame.draw.line(bevel, (60, 40, 20, 50), (width - 4, 4), (width - 4, height - 5), 1)
    surf.blit(bevel, (0, 0))

    edge_color = (*th.paper_edge, 200)
    pygame.draw.rect(surf, edge_color, surf.get_rect(), 1, border_radius=CORNER_RADIUS)
    return surf


def _draw_pip(surf, cx, cy, suit, color, size=8, flipped=False):
    if suit == "spade":
        pts = [(cx, cy - size), (cx + size * 0.85, cy + size * 0.5),
               (cx, cy + size * 0.85), (cx - size * 0.85, cy + size * 0.5)]
        pygame.draw.polygon(surf, color, pts)
        stem_top = cy + size * 0.4
        pygame.draw.polygon(surf, color, [
            (cx - size * 0.3, stem_top),
            (cx + size * 0.3, stem_top),
            (cx, stem_top + size * 0.55),
        ])
    elif suit == "heart":
        r = size * 0.55
        pygame.draw.circle(surf, color, (int(cx - r * 0.85), int(cy - r * 0.4)), int(r))
        pygame.draw.circle(surf, color, (int(cx + r * 0.85), int(cy - r * 0.4)), int(r))
        pts = [(cx - size * 1.2, cy - r * 0.1),
               (cx, cy + size * 0.95),
               (cx + size * 1.2, cy - r * 0.1)]
        pygame.draw.polygon(surf, color, pts)
        if flipped:
            pass
    elif suit == "diamond":
        pts = [(cx, cy - size * 1.05), (cx + size * 0.78, cy),
               (cx, cy + size * 1.05), (cx - size * 0.78, cy)]
        pygame.draw.polygon(surf, color, pts)
    elif suit == "club":
        r = size * 0.55
        pygame.draw.circle(surf, color, (int(cx), int(cy - size * 0.6)), int(r))
        pygame.draw.circle(surf, color, (int(cx - size * 0.65), int(cy + size * 0.05)), int(r))
        pygame.draw.circle(surf, color, (int(cx + size * 0.65), int(cy + size * 0.05)), int(r))
        pygame.draw.polygon(surf, color, [
            (cx - size * 0.3, cy + size * 0.4),
            (cx + size * 0.3, cy + size * 0.4),
            (cx, cy + size * 1.1),
        ])


def _pip_layout(rank):
    """Return list of (x_norm, y_norm, flipped) in [0..1] coords for a rank's pips."""
    L = 0.5
    cols = (0.32, 0.5, 0.68)
    rows7 = (0.18, 0.30, 0.42, 0.5, 0.58, 0.70, 0.82)
    if rank == "A":
        return [(L, 0.5, False)]
    if rank == "2":
        return [(L, 0.22, False), (L, 0.78, True)]
    if rank == "3":
        return [(L, 0.22, False), (L, 0.5, False), (L, 0.78, True)]
    if rank == "4":
        return [(cols[0], 0.22, False), (cols[2], 0.22, False),
                (cols[0], 0.78, True), (cols[2], 0.78, True)]
    if rank == "5":
        return [(cols[0], 0.22, False), (cols[2], 0.22, False),
                (L, 0.5, False),
                (cols[0], 0.78, True), (cols[2], 0.78, True)]
    if rank == "6":
        return [(cols[0], 0.22, False), (cols[2], 0.22, False),
                (cols[0], 0.5, False), (cols[2], 0.5, False),
                (cols[0], 0.78, True), (cols[2], 0.78, True)]
    if rank == "7":
        return [(cols[0], 0.22, False), (cols[2], 0.22, False),
                (L, 0.36, False),
                (cols[0], 0.5, False), (cols[2], 0.5, False),
                (cols[0], 0.78, True), (cols[2], 0.78, True)]
    if rank == "8":
        return [(cols[0], 0.22, False), (cols[2], 0.22, False),
                (L, 0.36, False),
                (cols[0], 0.5, False), (cols[2], 0.5, False),
                (L, 0.64, True),
                (cols[0], 0.78, True), (cols[2], 0.78, True)]
    if rank == "9":
        return [(cols[0], 0.22, False), (cols[2], 0.22, False),
                (cols[0], 0.4, False), (cols[2], 0.4, False),
                (L, 0.5, False),
                (cols[0], 0.6, True), (cols[2], 0.6, True),
                (cols[0], 0.78, True), (cols[2], 0.78, True)]
    if rank == "10":
        return [(cols[0], 0.18, False), (cols[2], 0.18, False),
                (L, 0.30, False),
                (cols[0], 0.40, False), (cols[2], 0.40, False),
                (cols[0], 0.60, True), (cols[2], 0.60, True),
                (L, 0.70, True),
                (cols[0], 0.82, True), (cols[2], 0.82, True)]
    return []


def _draw_corner_index(surf, x, y, rank, suit, color, w, h, mirrored=False):
    rank_font = _font(max(11, int(15 * w / CARD_WIDTH)), bold=True)
    suit_font = _font(max(9, int(13 * w / CARD_WIDTH)), bold=True)
    rs = rank_font.render(rank, True, color)
    sg = suit_font.render(SUIT_GLYPH.get(suit, "?"), True, color)
    if mirrored:
        rs = pygame.transform.rotate(rs, 180)
        sg = pygame.transform.rotate(sg, 180)
        surf.blit(rs, (x - rs.get_width(), y - rs.get_height() - sg.get_height() + 2))
        surf.blit(sg, (x - sg.get_width(), y - sg.get_height() + 2))
    else:
        surf.blit(rs, (x, y))
        surf.blit(sg, (x, y + rs.get_height() - 2))


def _draw_face_card(surf, rank, suit, color, w, h):
    """Procedural face cards: silhouette portrait with deco motifs."""
    cx, cy = w // 2, h // 2

    panel = pygame.Surface((int(w * 0.62), int(h * 0.62)), pygame.SRCALPHA)
    pr = panel.get_rect()
    panel_color = (*color[:3], 30)
    pygame.draw.rect(panel, panel_color, pr, border_radius=6)
    pygame.draw.rect(panel, (*color[:3], 110), pr, 1, border_radius=6)
    surf.blit(panel, (cx - pr.width // 2, cy - pr.height // 2))

    def line(x1, y1, x2, y2, width=1):
        pygame.draw.line(surf, color, (cx + x1, cy + y1), (cx + x2, cy + y2), width)

    if rank == "J":
        head_r = int(h * 0.10)
        pygame.draw.circle(surf, color, (cx, cy - int(h * 0.18)), head_r, 2)
        line(-head_r * 0.7, -h * 0.18 + head_r * 0.3, head_r * 0.7, -h * 0.18 + head_r * 0.3, 2)
        line(0, -h * 0.18 + head_r, 0, h * 0.10, 2)
        line(-int(w * 0.18), 0, int(w * 0.18), 0, 2)
        line(-int(w * 0.18), 0, -int(w * 0.10), int(h * 0.18), 2)
        line(int(w * 0.18), 0, int(w * 0.10), int(h * 0.18), 2)
        line(0, h * 0.10, -int(w * 0.10), int(h * 0.22), 2)
        line(0, h * 0.10, int(w * 0.10), int(h * 0.22), 2)
        for i in range(3):
            t = -head_r + i * head_r * 0.6
            line(t, -h * 0.30, t + head_r * 0.3, -h * 0.36, 2)
    elif rank == "Q":
        head_r = int(h * 0.10)
        pygame.draw.circle(surf, color, (cx, cy - int(h * 0.18)), head_r, 2)
        crown_pts = [
            (cx - head_r, cy - int(h * 0.20) - head_r * 0.4),
            (cx - head_r * 0.7, cy - int(h * 0.20) - head_r * 1.2),
            (cx - head_r * 0.3, cy - int(h * 0.20) - head_r * 0.7),
            (cx, cy - int(h * 0.20) - head_r * 1.4),
            (cx + head_r * 0.3, cy - int(h * 0.20) - head_r * 0.7),
            (cx + head_r * 0.7, cy - int(h * 0.20) - head_r * 1.2),
            (cx + head_r, cy - int(h * 0.20) - head_r * 0.4),
        ]
        pygame.draw.lines(surf, color, False, crown_pts, 2)
        line(-int(w * 0.20), -h * 0.05, int(w * 0.20), -h * 0.05, 2)
        line(-int(w * 0.20), -h * 0.05, -int(w * 0.22), int(h * 0.20), 2)
        line(int(w * 0.20), -h * 0.05, int(w * 0.22), int(h * 0.20), 2)
        line(0, -h * 0.05, 0, int(h * 0.18), 2)
        line(-head_r * 0.7, -h * 0.18 + head_r * 0.3, head_r * 0.7, -h * 0.18 + head_r * 0.3, 1)
    elif rank == "K":
        head_r = int(h * 0.11)
        pygame.draw.circle(surf, color, (cx, cy - int(h * 0.16)), head_r, 2)
        cy_crown = cy - int(h * 0.18) - head_r
        crown_pts = [
            (cx - head_r * 1.1, cy_crown),
            (cx - head_r * 0.7, cy_crown - head_r * 0.9),
            (cx - head_r * 0.2, cy_crown - head_r * 0.4),
            (cx, cy_crown - head_r * 1.3),
            (cx + head_r * 0.2, cy_crown - head_r * 0.4),
            (cx + head_r * 0.7, cy_crown - head_r * 0.9),
            (cx + head_r * 1.1, cy_crown),
        ]
        pygame.draw.lines(surf, color, False, crown_pts, 2)
        cross_y = cy_crown - head_r * 1.6
        line(0, cy_crown - h * 0 - cy + cross_y, 0, cy_crown - h * 0 - cy + cross_y - head_r * 0.7, 2)
        line(-head_r * 0.3, cy_crown - h * 0 - cy + cross_y - head_r * 0.4,
             head_r * 0.3, cy_crown - h * 0 - cy + cross_y - head_r * 0.4, 2)
        beard_pts = [
            (cx - head_r * 0.7, cy - int(h * 0.16) + head_r * 0.5),
            (cx - head_r * 0.4, cy - int(h * 0.16) + head_r * 1.2),
            (cx, cy - int(h * 0.16) + head_r * 0.9),
            (cx + head_r * 0.4, cy - int(h * 0.16) + head_r * 1.2),
            (cx + head_r * 0.7, cy - int(h * 0.16) + head_r * 0.5),
        ]
        pygame.draw.lines(surf, color, False, beard_pts, 2)
        line(-int(w * 0.22), -h * 0.02, int(w * 0.22), -h * 0.02, 3)
        line(-int(w * 0.22), -h * 0.02, -int(w * 0.24), int(h * 0.20), 2)
        line(int(w * 0.22), -h * 0.02, int(w * 0.24), int(h * 0.20), 2)

        if suit in ("heart", "diamond"):
            arr_color = (*color[:3], 180)
            sx, sy = cx - int(w * 0.30), cy + int(h * 0.05)
            ex, ey = cx + int(w * 0.30), cy + int(h * 0.05)
            arrow_surf = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
            pygame.draw.line(arrow_surf, arr_color, (sx, sy + int(h * 0.05)), (ex, ey - int(h * 0.05)), 2)
            pygame.draw.line(arrow_surf, arr_color, (sx, sy - int(h * 0.05)), (ex, ey + int(h * 0.05)), 2)
            head1 = [(ex, ey - int(h * 0.05)), (ex - int(w * 0.06), ey - int(h * 0.10)), (ex - int(w * 0.06), ey)]
            head2 = [(ex, ey + int(h * 0.05)), (ex - int(w * 0.06), ey + int(h * 0.10)), (ex - int(w * 0.06), ey)]
            pygame.draw.polygon(arrow_surf, arr_color, head1)
            pygame.draw.polygon(arrow_surf, arr_color, head2)
            surf.blit(arrow_surf, (0, 0), special_flags=pygame.BLEND_PREMULTIPLIED)


def _draw_black_king_zero(surf, w, h, color):
    cx, cy = w // 2, h // 2
    th = theme.active()
    badge_r = int(h * 0.13)
    pygame.draw.circle(surf, (*color[:3], 50), (cx, cy + int(h * 0.30)), badge_r)
    pygame.draw.circle(surf, color, (cx, cy + int(h * 0.30)), badge_r, 2)
    z_font = _serif_font(max(14, int(20 * w / CARD_WIDTH)), bold=True)
    z = z_font.render("0", True, color)
    surf.blit(z, z.get_rect(center=(cx, cy + int(h * 0.30))))


def paint_face(card, w=CARD_WIDTH, h=CARD_HEIGHT):
    th = theme.active()
    cache_key = (card.rank, card.suit, w, h, th.name, th.high_contrast,
                 tuple(th.ink_red), tuple(th.ink_black), tuple(th.paper_warm))
    if cache_key in _FACE_CACHE:
        return _FACE_CACHE[cache_key]

    real = _load_png_face(card)
    if real is not None:
        scaled = _scaled_to_card(real, w, h)
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        mask = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(),
                         border_radius=CORNER_RADIUS)
        surf.blit(scaled, (0, 0))
        surf.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)

        if card.rank == "K" and not card.is_red:
            badge_r = max(7, int(h * 0.10))
            cx, cy = int(w * 0.82), int(h * 0.18)
            pygame.draw.circle(surf, (20, 20, 20), (cx, cy), badge_r)
            pygame.draw.circle(surf, (220, 195, 110), (cx, cy), badge_r, 2)
            zfont = _serif_font(max(10, int(badge_r * 1.4)), bold=True)
            z = zfont.render("0", True, (220, 195, 110))
            surf.blit(z, z.get_rect(center=(cx, cy)))
        if getattr(card, "power", None):
            from config import POWER_COLORS
            glow_color = POWER_COLORS.get(card.power, (180, 180, 180))
            pygame.draw.rect(surf, (*glow_color, 90), surf.get_rect(),
                             2, border_radius=CORNER_RADIUS)
        pygame.draw.rect(surf, (40, 40, 40, 200), surf.get_rect(), 1,
                         border_radius=CORNER_RADIUS)
        _FACE_CACHE[cache_key] = surf
        return surf

    surf = _paper(w, h)
    color = th.ink_red if card.is_red else th.ink_black

    bar = pygame.Surface((6, h - 8), pygame.SRCALPHA)
    pygame.draw.rect(bar, (*color[:3], 200), bar.get_rect(), border_radius=2)
    surf.blit(bar, (3, 4))

    pad = 5
    _draw_corner_index(surf, pad, pad, card.rank, card.suit, color, w, h, mirrored=False)
    _draw_corner_index(surf, w - pad, h - pad, card.rank, card.suit, color, w, h, mirrored=True)

    if card.rank in ("A", "2", "3", "4", "5", "6", "7", "8", "9", "10"):
        if card.rank == "A":
            big_pip_size = int(min(w, h) * 0.25)
            _draw_pip(surf, w // 2, h // 2, card.suit, color, size=big_pip_size)
        else:
            for nx, ny, flipped in _pip_layout(card.rank):
                px = int(w * (0.18 + (nx - 0.18) * 1.0))
                py = int(h * ny)
                _draw_pip(surf, px, py, card.suit, color, size=int(min(w, h) * 0.075), flipped=flipped)
    elif card.rank in ("J", "Q", "K"):
        _draw_face_card(surf, card.rank, card.suit, color, w, h)
        if card.rank == "K" and not card.is_red:
            _draw_black_king_zero(surf, w, h, color)

    if getattr(card, "power", None):
        from config import POWER_COLORS
        glow_color = POWER_COLORS.get(card.power, (180, 180, 180))
        flourish = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(flourish, (*glow_color, 70), pygame.Rect(0, 0, w, h),
                         2, border_radius=CORNER_RADIUS)
        surf.blit(flourish, (0, 0))

    pygame.draw.rect(surf, (*th.paper_edge, 220), surf.get_rect(), 1,
                     border_radius=CORNER_RADIUS)

    _FACE_CACHE[cache_key] = surf
    return surf


BRASS_MOTIF = (240, 200, 110)


def _back_palette(style, th):
    if style == "deco_emerald":
        return ((10, 60, 40), (30, 110, 70), (220, 200, 130))
    if style == "deco_obsidian":
        return ((18, 18, 22), (40, 40, 50), (220, 200, 130))
    if style == "deco_brass":
        return ((40, 30, 18), (90, 65, 30), (240, 200, 110))
    return (th.card_back_a, th.card_back_b, th.card_back_motif)


def _vertical_gradient(w, h, a, b):
    grad = pygame.Surface((w, h), pygame.SRCALPHA)
    for y in range(h):
        t = y / max(1, h - 1)
        r = int(a[0] + (b[0] - a[0]) * t)
        g = int(a[1] + (b[1] - a[1]) * t)
        bl = int(a[2] + (b[2] - a[2]) * t)
        pygame.draw.line(grad, (r, g, bl, 255), (0, y), (w, y))
    return grad


def _radial_gradient(w, h, center_color, edge_color):
    grad = pygame.Surface((w, h), pygame.SRCALPHA)
    grad.fill((*edge_color, 255))
    cx, cy = w / 2, h / 2
    max_r = int(math.hypot(cx, cy)) + 2
    for r in range(max_r, 0, -1):
        t = r / max_r
        rr = int(center_color[0] + (edge_color[0] - center_color[0]) * t)
        gg = int(center_color[1] + (edge_color[1] - center_color[1]) * t)
        bb = int(center_color[2] + (edge_color[2] - center_color[2]) * t)
        pygame.draw.circle(grad, (rr, gg, bb, 255), (int(cx), int(cy)), r)
    return grad


def _octagon_points(rect, chamfer):
    x, y, ww, hh = rect.x, rect.y, rect.width, rect.height
    c = min(chamfer, ww // 2, hh // 2)
    return [
        (x + c, y), (x + ww - c, y),
        (x + ww, y + c), (x + ww, y + hh - c),
        (x + ww - c, y + hh), (x + c, y + hh),
        (x, y + hh - c), (x, y + c),
    ]


def _draw_classic(surf, w, h, motif, mask):
    """Theme-driven: cross-hatch + oval medallion + 4-point diamond."""
    overlay = pygame.Surface((w, h), pygame.SRCALPHA)
    spacing = 12
    for x in range(-h, w + h, spacing):
        pygame.draw.line(overlay, (*motif[:3], 22), (x, 0), (x + h, h), 1)
        pygame.draw.line(overlay, (*motif[:3], 22), (x, h), (x + h, 0), 1)
    overlay.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    surf.blit(overlay, (0, 0))

    cx, cy = w // 2, h // 2
    med_w, med_h = int(w * 0.55), int(h * 0.4)
    medallion = pygame.Rect(cx - med_w // 2, cy - med_h // 2, med_w, med_h)
    pygame.draw.ellipse(surf, (*motif[:3], 90), medallion)
    pygame.draw.ellipse(surf, motif, medallion, 2)

    d = max(6, int(min(w, h) * 0.05))
    pygame.draw.polygon(surf, motif, [
        (cx, cy - d * 1.2), (cx + d * 0.8, cy),
        (cx, cy + d * 1.2), (cx - d * 0.8, cy),
    ])


def _draw_brass(surf, w, h, motif, mask):
    """Sunburst + octagonal medallion + diamond+bars + corner ornaments."""
    overlay = pygame.Surface((w, h), pygame.SRCALPHA)
    apex = (w // 2, h // 8)
    rays = 19
    spread = math.pi * 1.05
    base_y = h + 10
    for i in range(rays):
        t = (i / (rays - 1) - 0.5) * spread
        ex = apex[0] + math.tan(t) * (base_y - apex[1])
        pygame.draw.line(overlay, (*BRASS_MOTIF, 14), apex, (int(ex), base_y), 1)
    overlay.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    surf.blit(overlay, (0, 0))

    cx, cy = w // 2, h // 2
    med_w, med_h = int(w * 0.62), int(h * 0.46)
    med_rect = pygame.Rect(cx - med_w // 2, cy - med_h // 2, med_w, med_h)
    chamfer = max(8, min(med_w, med_h) // 5)
    outer_pts = _octagon_points(med_rect, chamfer)
    pygame.draw.polygon(surf, (*motif[:3], 100), outer_pts)
    pygame.draw.polygon(surf, motif, outer_pts, 2)

    inset = max(6, min(med_w, med_h) // 10)
    inner_rect = pygame.Rect(med_rect.x + inset, med_rect.y + inset,
                             med_w - inset * 2, med_h - inset * 2)
    inner_pts = _octagon_points(inner_rect, max(4, chamfer - inset))
    pygame.draw.polygon(surf, (*motif[:3], 80), inner_pts, 1)

    dh = max(10, int(h * 0.09))
    dw = max(6, int(w * 0.045))
    pygame.draw.polygon(surf, motif, [
        (cx, cy - dh), (cx + dw, cy), (cx, cy + dh), (cx - dw, cy),
    ])
    bar_off = dw + max(6, int(w * 0.04))
    bar_h = int(dh * 1.4)
    pygame.draw.rect(surf, motif, (cx - bar_off - 1, cy - bar_h // 2, 2, bar_h))
    pygame.draw.rect(surf, motif, (cx + bar_off - 1, cy - bar_h // 2, 2, bar_h))

    pad = max(6, int(min(w, h) * 0.05))
    pip_r = max(2, int(min(w, h) * 0.018))
    arm = max(6, int(min(w, h) * 0.06))
    corners = [
        (pad, pad, 1, 1),
        (w - pad, pad, -1, 1),
        (pad, h - pad, 1, -1),
        (w - pad, h - pad, -1, -1),
    ]
    for cxp, cyp, sx, sy in corners:
        pygame.draw.circle(surf, motif, (cxp, cyp), pip_r)
        pygame.draw.line(surf, motif, (cxp, cyp + sy * pip_r * 2),
                         (cxp, cyp + sy * (pip_r * 2 + arm)), 1)
        pygame.draw.line(surf, motif, (cxp + sx * pip_r * 2, cyp),
                         (cxp + sx * (pip_r * 2 + arm), cyp), 1)


def _draw_emerald(surf, w, h, motif, mask):
    """Diamond lattice + concentric ovals + facet lines + sparkle + corner pips."""
    overlay = pygame.Surface((w, h), pygame.SRCALPHA)
    cell = max(10, w // 12)
    half = cell // 2
    rows = h // half + 2
    cols = w // cell + 2
    for r in range(rows):
        for c in range(cols):
            ox = c * cell + (half if r % 2 else 0)
            oy = r * half
            pygame.draw.polygon(overlay, (*motif[:3], 18), [
                (ox, oy - half), (ox + half, oy),
                (ox, oy + half), (ox - half, oy),
            ], 1)
    overlay.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    surf.blit(overlay, (0, 0))

    cx, cy = w // 2, h // 2
    med_w, med_h = int(w * 0.6), int(h * 0.45)
    medallion = pygame.Rect(cx - med_w // 2, cy - med_h // 2, med_w, med_h)
    pygame.draw.ellipse(surf, (*motif[:3], 90), medallion)
    pygame.draw.ellipse(surf, motif, medallion, 2)
    for i in range(1, 5):
        inset_w = int(med_w * 0.08 * i)
        inset_h = int(med_h * 0.08 * i)
        rect = pygame.Rect(medallion.x + inset_w, medallion.y + inset_h,
                           med_w - inset_w * 2, med_h - inset_h * 2)
        pygame.draw.ellipse(surf, (*motif[:3], 110), rect, 1)

    facet_r = min(med_w, med_h) // 2
    for k in range(8):
        angle = math.pi * 2 * k / 8 + math.pi / 8
        x2 = cx + int(math.cos(angle) * facet_r * 0.95)
        y2 = cy + int(math.sin(angle) * facet_r * 0.7)
        pygame.draw.line(surf, (*motif[:3], 110), (cx, cy), (x2, y2), 1)

    sx, sy = cx + max(2, w // 80), cy - max(2, h // 80)
    pygame.draw.circle(surf, (255, 255, 255, 230), (sx, sy), 2)

    pip_off = max(8, int(min(w, h) * 0.06))
    pip_d = max(3, int(min(w, h) * 0.025))
    for cxp, cyp in [(pip_off, pip_off), (w - pip_off, pip_off),
                     (pip_off, h - pip_off), (w - pip_off, h - pip_off)]:
        pygame.draw.polygon(surf, motif, [
            (cxp, cyp - pip_d), (cxp + pip_d, cyp),
            (cxp, cyp + pip_d), (cxp - pip_d, cyp),
        ])


def _draw_obsidian(surf, w, h, motif, mask):
    """Honeycomb + starfield + 16-ray rosette + concentric rings + pearl + corner pips."""
    overlay = pygame.Surface((w, h), pygame.SRCALPHA)
    hex_r = max(6, w // 14)
    hex_w = math.sqrt(3) * hex_r
    hex_h = 1.5 * hex_r
    rows = int(h / hex_h) + 2
    cols = int(w / hex_w) + 2
    for r in range(rows):
        for c in range(cols):
            cxh = c * hex_w + (hex_w / 2 if r % 2 else 0)
            cyh = r * hex_h
            pts = [(cxh + math.cos(math.pi / 6 + math.pi / 3 * k) * hex_r,
                    cyh + math.sin(math.pi / 6 + math.pi / 3 * k) * hex_r)
                   for k in range(6)]
            pygame.draw.polygon(overlay, (*motif[:3], 16), pts, 1)

    rng = random.Random((w << 16) ^ (h << 4) ^ 0xB175)
    n_stars = max(8, (w * h) // 600)
    for _ in range(n_stars):
        sx = rng.randint(0, w - 1)
        sy = rng.randint(0, h - 1)
        a = rng.randint(40, 120)
        pygame.draw.circle(overlay, (255, 255, 255, a), (sx, sy), 1)

    overlay.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    surf.blit(overlay, (0, 0))

    cx, cy = w // 2, h // 2
    med_w, med_h = int(w * 0.6), int(h * 0.45)
    medallion = pygame.Rect(cx - med_w // 2, cy - med_h // 2, med_w, med_h)
    pygame.draw.ellipse(surf, motif, medallion, 2)

    base_r = min(med_w, med_h) // 4
    for k in range(16):
        angle = math.pi * 2 * k / 16
        x1 = cx + math.cos(angle) * base_r
        y1 = cy + math.sin(angle) * base_r
        x2 = cx + math.cos(angle) * base_r * 1.9
        y2 = cy + math.sin(angle) * base_r * 1.9
        width = 2 if k % 2 == 0 else 1
        pygame.draw.line(surf, motif, (int(x1), int(y1)), (int(x2), int(y2)), width)

    pygame.draw.circle(surf, (*motif[:3], 160), (cx, cy), int(base_r * 0.65), 1)
    pygame.draw.circle(surf, motif, (cx, cy), max(2, int(base_r * 0.30)))

    pearl_x = cx - max(2, w // 90)
    pearl_y = cy - max(2, h // 90)
    pygame.draw.circle(surf, (255, 255, 255, 230), (pearl_x, pearl_y), 2)

    pad = max(7, int(min(w, h) * 0.05))
    ring_r = max(3, int(min(w, h) * 0.022))
    for cxp, cyp in [(pad, pad), (w - pad, pad), (pad, h - pad), (w - pad, h - pad)]:
        pygame.draw.circle(surf, motif, (cxp, cyp), ring_r, 1)
        pygame.draw.circle(surf, motif, (cxp, cyp), max(1, ring_r // 2))


def paint_back(style="classic", w=CARD_WIDTH, h=CARD_HEIGHT):
    th = theme.active()
    a, b, motif = _back_palette(style, th)
    cache_key = (style, w, h, th.name, th.high_contrast, tuple(a), tuple(b))
    if cache_key in _BACK_CACHE:
        return _BACK_CACHE[cache_key]

    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    mask = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=CORNER_RADIUS)

    if style == "deco_obsidian":
        grad = _radial_gradient(w, h, (40, 40, 50), (18, 18, 22))
    else:
        grad = _vertical_gradient(w, h, a, b)
    grad.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    surf.blit(grad, (0, 0))

    if style == "deco_brass":
        _draw_brass(surf, w, h, motif, mask)
    elif style == "deco_emerald":
        _draw_emerald(surf, w, h, motif, mask)
    elif style == "deco_obsidian":
        _draw_obsidian(surf, w, h, motif, mask)
    else:
        _draw_classic(surf, w, h, motif, mask)

    inner1 = pygame.Rect(4, 4, w - 8, h - 8)
    pygame.draw.rect(surf, (*motif[:3], 80), inner1, 2, border_radius=max(2, CORNER_RADIUS - 4))
    inner2 = pygame.Rect(8, 8, w - 16, h - 16)
    pygame.draw.rect(surf, (*motif[:3], 40), inner2, 1, border_radius=max(2, CORNER_RADIUS - 8))

    pygame.draw.rect(surf, (*BRASS_MOTIF, 220), surf.get_rect(), 1, border_radius=CORNER_RADIUS)
    pygame.draw.line(surf, (255, 255, 255, 70), (4, 3), (w - 5, 3), 1)
    pygame.draw.line(surf, (255, 255, 255, 35), (3, 4), (3, h - 5), 1)

    surf.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)

    _BACK_CACHE[cache_key] = surf
    return surf


def paint_back_glow(style="classic", w=CARD_WIDTH, h=CARD_HEIGHT, t=0.0):
    """Animated card-back shimmer overlay; called per-frame for the active deck."""
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    band_y = int(h * (0.5 + 0.5 * math.sin(t * 0.6)))
    for offs in range(-12, 13):
        a = max(0, 30 - abs(offs) * 2)
        if a <= 0:
            continue
        pygame.draw.line(surf, (255, 230, 170, a),
                         (0, band_y + offs), (w, band_y + offs), 1)
    mask = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=CORNER_RADIUS)
    surf.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    return surf

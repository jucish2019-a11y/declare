"""Theme tokens for Declare.

Replaces flat literal RGB tuples scattered across config.py / renderer.py.
A single Theme instance is held by main.py and read by every rendering call.
Swapping themes (default / colorblind / high-contrast) reskins the whole game.
"""
from dataclasses import dataclass, field, replace


@dataclass(frozen=True)
class Theme:
    name: str = "Parlor"

    felt_deep: tuple = (26, 58, 46)
    felt_mid: tuple = (58, 118, 86)
    felt_rim: tuple = (16, 38, 28)
    felt_shadow: tuple = (8, 22, 16)
    lamp_glow: tuple = (255, 215, 130)

    paper_warm: tuple = (244, 236, 216)
    paper_edge: tuple = (190, 178, 150)
    ink_red: tuple = (178, 34, 34)
    ink_black: tuple = (26, 26, 26)
    card_back_a: tuple = (24, 36, 78)
    card_back_b: tuple = (54, 78, 140)
    card_back_motif: tuple = (220, 175, 90)

    brass_100: tuple = (255, 231, 168)
    brass_300: tuple = (232, 195, 110)
    brass_500: tuple = (188, 145, 64)
    brass_700: tuple = (124, 92, 38)
    brass_900: tuple = (60, 42, 18)

    signal_go: tuple = (79, 180, 119)
    signal_stop: tuple = (212, 72, 72)
    signal_warn: tuple = (224, 165, 38)
    signal_info: tuple = (111, 207, 227)
    you_cyan: tuple = (111, 207, 227)

    text_white: tuple = (244, 244, 240)
    text_dim: tuple = (170, 170, 170)
    text_muted: tuple = (130, 130, 130)
    panel_bg: tuple = (15, 15, 15)
    panel_bg_alpha: int = 220
    panel_border: tuple = (60, 60, 60)
    overlay: tuple = (0, 0, 0)

    declare_red: tuple = (212, 72, 72)
    declare_red_hi: tuple = (240, 102, 102)
    swap_green: tuple = (40, 130, 60)
    swap_green_hi: tuple = (60, 170, 80)
    peek_blue: tuple = (70, 140, 220)
    peek_blue_hi: tuple = (100, 170, 250)
    discard_orange: tuple = (200, 120, 30)
    discard_orange_hi: tuple = (230, 150, 50)
    pair_teal: tuple = (40, 140, 160)
    pair_teal_hi: tuple = (60, 170, 190)
    cancel_gray: tuple = (100, 100, 100)
    cancel_gray_hi: tuple = (140, 140, 140)

    text_scale: float = 1.0
    motion_scale: float = 1.0
    particles_enabled: bool = True
    high_contrast: bool = False
    # When False, the renderer suppresses the lamp pool, vignette, dust motes,
    # and other atmospheric flourishes — used by the Minimal theme to deliver
    # a flat, modern, low-ornament look.
    is_atmospheric: bool = True

    @property
    def gold(self):
        return self.brass_300

    @property
    def empty_slot(self):
        return (60, 90, 60)

    @property
    def known_tint(self):
        return (*self.brass_300, 40)


THEME_DEFAULT = Theme()

THEME_DEUTAN = replace(
    THEME_DEFAULT,
    name="Color-blind (Deutan)",
    ink_red=(0, 90, 200),
    declare_red=(0, 90, 200),
    declare_red_hi=(40, 130, 240),
    signal_stop=(0, 90, 200),
    signal_go=(220, 165, 40),
    swap_green=(220, 165, 40),
    swap_green_hi=(245, 195, 70),
)

THEME_PROTAN = replace(
    THEME_DEFAULT,
    name="Color-blind (Protan)",
    ink_red=(70, 110, 220),
    declare_red=(70, 110, 220),
    declare_red_hi=(110, 150, 245),
    signal_stop=(70, 110, 220),
    signal_go=(220, 175, 60),
    swap_green=(220, 175, 60),
    swap_green_hi=(240, 200, 90),
)

THEME_TRITAN = replace(
    THEME_DEFAULT,
    name="Color-blind (Tritan)",
    ink_red=(220, 60, 80),
    declare_red=(220, 60, 80),
    signal_stop=(220, 60, 80),
    signal_go=(50, 170, 170),
    swap_green=(50, 170, 170),
    swap_green_hi=(80, 200, 200),
    peek_blue=(190, 130, 220),
    peek_blue_hi=(220, 160, 245),
)

THEME_HIGH_CONTRAST = replace(
    THEME_DEFAULT,
    name="High Contrast",
    felt_deep=(0, 0, 0),
    felt_mid=(20, 20, 20),
    felt_rim=(0, 0, 0),
    felt_shadow=(0, 0, 0),
    lamp_glow=(255, 255, 255),
    paper_warm=(255, 255, 255),
    paper_edge=(0, 0, 0),
    ink_red=(255, 0, 0),
    ink_black=(0, 0, 0),
    card_back_a=(0, 0, 80),
    card_back_b=(0, 0, 160),
    card_back_motif=(255, 255, 0),
    brass_300=(255, 255, 0),
    brass_500=(255, 230, 0),
    text_white=(255, 255, 255),
    text_dim=(220, 220, 220),
    panel_bg=(0, 0, 0),
    panel_border=(255, 255, 255),
    high_contrast=True,
)

THEME_SALOON = replace(
    THEME_DEFAULT,
    name="Saloon",
    felt_deep=(38, 70, 48),
    felt_mid=(54, 100, 70),
    felt_rim=(12, 24, 18),
    felt_shadow=(4, 12, 8),
    lamp_glow=(255, 195, 110),
    paper_warm=(238, 224, 196),
    paper_edge=(176, 160, 130),
    card_back_a=(52, 18, 22),
    card_back_b=(90, 35, 38),
    card_back_motif=(200, 155, 75),
    brass_100=(245, 218, 152),
    brass_300=(216, 178, 100),
    brass_500=(172, 130, 58),
    brass_700=(108, 80, 32),
    brass_900=(52, 38, 16),
)

THEME_VEGAS = replace(
    THEME_DEFAULT,
    name="Vegas Premium",
    felt_deep=(10, 70, 48),
    felt_mid=(28, 130, 92),
    felt_rim=(4, 32, 22),
    felt_shadow=(0, 14, 10),
    lamp_glow=(245, 240, 230),
    paper_warm=(252, 250, 246),
    paper_edge=(212, 210, 205),
    card_back_a=(12, 25, 70),
    card_back_b=(45, 80, 175),
    card_back_motif=(220, 220, 220),
    brass_100=(245, 245, 240),
    brass_300=(215, 215, 220),
    brass_500=(175, 175, 180),
    brass_700=(110, 110, 120),
    brass_900=(50, 50, 60),
    declare_red=(235, 60, 60),
    declare_red_hi=(255, 90, 90),
    swap_green=(60, 180, 90),
    swap_green_hi=(90, 220, 120),
)

THEME_MINIMAL = replace(
    THEME_DEFAULT,
    name="Minimal",
    felt_deep=(32, 60, 70),
    felt_mid=(32, 60, 70),
    felt_rim=(20, 40, 48),
    felt_shadow=(12, 24, 28),
    lamp_glow=(200, 210, 220),
    paper_warm=(248, 248, 248),
    paper_edge=(210, 210, 210),
    card_back_a=(28, 60, 80),
    card_back_b=(50, 90, 120),
    card_back_motif=(180, 195, 200),
    brass_100=(240, 240, 240),
    brass_300=(210, 210, 215),
    brass_500=(170, 170, 175),
    brass_700=(110, 110, 115),
    brass_900=(50, 50, 55),
    is_atmospheric=False,
)

THEMES = {
    "default": THEME_DEFAULT,
    "saloon": THEME_SALOON,
    "vegas": THEME_VEGAS,
    "minimal": THEME_MINIMAL,
    "deutan": THEME_DEUTAN,
    "protan": THEME_PROTAN,
    "tritan": THEME_TRITAN,
    "high_contrast": THEME_HIGH_CONTRAST,
}

THEME_LABELS = {
    "default": "Parlor",
    "saloon": "Saloon",
    "vegas": "Vegas Premium",
    "minimal": "Minimal",
    "deutan": "CB - Deutan",
    "protan": "CB - Protan",
    "tritan": "CB - Tritan",
    "high_contrast": "High Contrast",
}

# Themes that must be unlocked through play. The colorblind/HC accessibility
# themes are always available regardless of unlock state.
UNLOCKABLE_THEMES = ("saloon", "vegas", "minimal")
ALWAYS_UNLOCKED = ("default", "deutan", "protan", "tritan", "high_contrast")

THEME_UNLOCK_CONDITIONS = {
    "saloon":  {"games_played": 10, "label": "Play 10 games"},
    "vegas":   {"games_won": 25,    "label": "Win 25 games"},
    "minimal": {"declares_won": 5,  "label": "Win 5 declares"},
}


def get_theme(key: str) -> Theme:
    return THEMES.get(key, THEME_DEFAULT)


_active = THEME_DEFAULT


def set_active(theme_or_key):
    global _active
    if isinstance(theme_or_key, Theme):
        _active = theme_or_key
    else:
        _active = get_theme(theme_or_key)


def active() -> Theme:
    return _active


def with_text_scale(scale: float) -> Theme:
    return replace(_active, text_scale=scale)


def apply_text_scale(scale: float):
    global _active
    _active = replace(_active, text_scale=scale)


def apply_motion_scale(scale: float):
    global _active
    _active = replace(_active, motion_scale=scale)


def apply_particles(enabled: bool):
    global _active
    _active = replace(_active, particles_enabled=enabled)


def apply_felt_style(felt_key: str):
    global _active
    try:
        from config import FELT_COLORS, FELT_COLORS_LIGHT
        deep = FELT_COLORS.get(felt_key, FELT_COLORS['forest'])
        mid = tuple(min(255, int(v * 1.45)) for v in deep)
        rim = tuple(int(v * 0.45) for v in deep)
        shadow = tuple(int(v * 0.20) for v in deep)
        _active = replace(_active, felt_deep=deep, felt_mid=mid, felt_rim=rim, felt_shadow=shadow)
    except Exception:
        pass

import os
import sys

SCREEN_WIDTH = 1600
SCREEN_HEIGHT = 900
FPS = 60


def is_mobile():
    """Detect mobile/touch-first environments."""
    if sys.platform == "emscripten":
        try:
            import platform as wasm_platform
            ua = getattr(wasm_platform.window.navigator, 'userAgent', '')
            ua = str(ua).lower()
            return any(k in ua for k in ('android', 'iphone', 'ipad', 'mobile'))
        except Exception:
            return False
    return False


def get_mobile_scale():
    """Return a scaling factor for UI elements on mobile devices."""
    return 1.15 if is_mobile() else 1.0
AI_DELAY = 0.8
PEEK_REVEAL_SECONDS = 2.5

BG_GREEN = (39, 119, 62)
BG_DARK = (20, 20, 20)
BG_GRADIENT_TOP = (18, 22, 30)
BG_GRADIENT_BOTTOM = (10, 12, 16)

CARD_WHITE = (255, 255, 255)
CARD_BACK_BLUE = (30, 60, 120)
CARD_BACK_PATTERN = (40, 80, 150)
CARD_SHADOW = (15, 15, 15)
BLACK = (0, 0, 0)
RED = (200, 30, 30)
GOLD = (255, 215, 0)
GOLD_HOVER = (255, 235, 130)
GOLD_DIM = (180, 155, 50)
TEXT_WHITE = (255, 255, 255)
TEXT_BLACK = (0, 0, 0)
TEXT_DIM = (180, 180, 180)
TEXT_DIMMER = (120, 120, 120)
HIGHLIGHT = (255, 255, 100)
DIM = (100, 100, 100)
PANEL_BG = (15, 15, 15)
PANEL_BORDER = (60, 60, 60)
PANEL_BORDER_GOLD = (180, 150, 50)
POWER_GLOW = (80, 180, 255)
EMPTY_SLOT = (60, 90, 60)
KNOWN_TINT = (255, 215, 0, 40)
DECLARE_RED = (220, 40, 40)
DECLARE_RED_HOVER = (255, 70, 70)
CANCEL_GRAY = (100, 100, 100)
CANCEL_GRAY_HOVER = (140, 140, 140)
PEEK_BLUE = (70, 140, 220)
PEEK_BLUE_HOVER = (100, 170, 250)
SWAP_GREEN = (40, 130, 60)
SWAP_GREEN_HOVER = (60, 170, 80)
DISCARD_ORANGE = (200, 120, 30)
DISCARD_ORANGE_HOVER = (230, 150, 50)
PAIR_TEAL = (40, 140, 160)
PAIR_TEAL_HOVER = (60, 170, 190)

STATUS_BAR_H = 44
ACTION_BAR_Y = 830
ACTION_BAR_H = 70

CARD_WIDTH = 100
CARD_HEIGHT = 140
CORNER_RADIUS = 10

CARD_SPREAD = 116

DECK_CENTER = (640, 400)
DRAWN_CARD_POS = (860, 400)
DISCARD_POS = (750, 400)

PLAYER_BOTTOM = (800, 700)
PLAYER_TOP = (800, 200)
PLAYER_LEFT = (260, 450)
PLAYER_RIGHT = (1340, 450)

PLAYER_AREA_2 = {
    0: (20, 480, 1580, 820),
    1: (40, 80, 1560, 380),
}
PLAYER_AREA_3 = {
    0: (20, 480, 1580, 820),
    1: (40, 80, 780, 380),
    2: (820, 80, 1560, 380),
}
PLAYER_AREA_4 = {
    0: (20, 480, 1580, 820),
    1: (40, 80, 1560, 380),
    2: (20, 140, 480, 820),
    3: (1120, 140, 1580, 820),
}

LOG_PANEL_X = 1300
LOG_PANEL_Y = 520
LOG_PANEL_W = 280
LOG_PANEL_H = 280

CARD_VALUES = {
    'A': 1,
    '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, '10': 10,
    'J': 11, 'Q': 12, 'K': 13,
}

BLACK_KING_VALUE = 0

RANKS = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']
SUITS = ['spade', 'heart', 'diamond', 'club']

HAND_SIZE = 4
MAX_PAIR_STACK = 2

DEFAULT_HAND_SIZE = 4
DEFAULT_PEEK_COUNT = 2
HAND_SIZE_OPTIONS = [2, 3, 4, 5, 6]
HAND_SIZE_LABELS = ['2', '3', '4', '5', '6']
PEEK_COUNT_OPTIONS = [0, 1, 2, 3, 4, 5]
PEEK_COUNT_LABELS = ['0', '1', '2', '3', '4', '5']

POWER_CARDS = {
    '7': 'peek_self',
    '8': 'peek_self',
    '9': 'peek_opponent',
    '10': 'peek_opponent',
    'J': 'skip',
    'Q': 'unseen_swap',
    ('K', 'heart'): 'seen_swap',
    ('K', 'diamond'): 'seen_swap',
    ('K', 'spade'): None,
    ('K', 'club'): None,
}

POWER_LABELS = {
    'peek_self': 'Peek Self',
    'peek_opponent': 'Peek Opponent',
    'skip': 'Skip Next',
    'unseen_swap': 'Unseen Swap',
    'seen_swap': 'Seen Swap',
}

POWER_COLORS = {
    'peek_self': PEEK_BLUE,
    'peek_opponent': PEEK_BLUE,
    'skip': DECLARE_RED,
    'unseen_swap': SWAP_GREEN,
    'seen_swap': SWAP_GREEN,
}

CARD_GRID_SPACING_X = 100
CARD_GRID_SPACING_Y = 130
PLAYER_AREA_PADDING = 20

DEFAULT_AI_DELAY = 0.8
DEFAULT_PEEK_REVEAL_TIME = 2.5
DEFAULT_PEEK_PHASE_SECONDS = 5.0
DEFAULT_ANIMATIONS_ENABLED = True
DEFAULT_SHOW_OWN_SCORE = False
DEFAULT_SHOW_KNOWN_MARKER = True
DEFAULT_SHOW_GAME_LOG = True
DEFAULT_CONFIRM_DECLARE = True
DEFAULT_AI_DIFFICULTY = 'medium'
DEFAULT_LAYOUT_MODE = 'line'
DEFAULT_FELT = 'forest'
DEFAULT_SELF_PAIR_ENABLED = True
DEFAULT_SHUFFLE_ENABLED = True
DEFAULT_WRONG_DROP_PENALTY = True
DEFAULT_REACTION_WINDOW_SECONDS = 8.0
DEFAULT_REACTION_WINDOW = 8.0

SWAP_REVEAL_SECONDS = 2.0

REACTION_WINDOW_OPTIONS = [3.0, 8.0, 13.0]
REACTION_WINDOW_LABELS = ['3s', '8s', '13s']

AI_REACTION_DELAY = 1.0

SHUFFLE_COLOR = (130, 100, 190)
SHUFFLE_HOVER = (160, 130, 220)
SELF_PAIR_COLOR = (50, 170, 150)
SELF_PAIR_HOVER = (70, 200, 175)
DROP_MATCH_COLOR = (230, 150, 50)
DROP_MATCH_HOVER = (250, 175, 70)

AI_DELAY_OPTIONS = [0.3, 0.8, 1.5]
AI_DELAY_LABELS = ['Fast', 'Normal', 'Slow']
PEEK_REVEAL_OPTIONS = [1.5, 2.5, 4.0]
PEEK_REVEAL_LABELS = ['Short', 'Normal', 'Long']
ANIMATION_OPTIONS = [True, False]
ANIMATION_LABELS = ['ON', 'OFF']
LAYOUT_OPTIONS = ['line', 'square', 'free']
LAYOUT_LABELS = ['Line', 'Square', 'Free']
AI_DIFFICULTY_OPTIONS = ['easy', 'medium', 'hard']
AI_DIFFICULTY_LABELS = ['Easy', 'Medium', 'Hard']
PEEK_PHASE_OPTIONS = [3.0, 5.0, 10.0, 999.0]
PEEK_PHASE_LABELS = ['3s', '5s', '10s', '\u221e']

ANIM_SHUFFLE_DURATION = 0.4
ANIM_REACTIVE_DROP_DURATION = 0.3
ANIM_PENALTY_DRAW_DURATION = 0.3

FELT_COLORS = {
    'forest':   (39, 119, 62),
    'burgundy': (92, 26, 27),
    'navy':     (26, 39, 68),
    'charcoal': (50, 50, 50),
    'emerald':  (18, 80, 60),
}
FELT_LABELS = ['Forest', 'Burgundy', 'Navy', 'Charcoal', 'Emerald']

FELT_COLORS_LIGHT = {
    'forest':   (50, 140, 80),
    'burgundy': (120, 35, 36),
    'navy':     (35, 52, 88),
    'charcoal': (65, 65, 65),
    'emerald':  (25, 100, 75),
}

ANIM_DRAW_DURATION = 0.3
ANIM_SWAP_DURATION = 0.4
ANIM_UNSEEN_SWAP_DURATION = 0.5
ANIM_SEEN_SWAP_DURATION = 0.6
ANIM_PEEK_LIFT_DURATION = 0.25
ANIM_PAIR_FLY_DURATION = 0.4
ANIM_DISCARD_DURATION = 0.3
ANIM_NOTIFICATION_DURATION = 2.0
ANIM_FLASH_DURATION = 0.3

CARD_FONT_SIZE = 18
CARD_BIG_FONT_SIZE = 28
TITLE_FONT_SIZE = 56
SUBTITLE_FONT_SIZE = 22
UI_FONT_SIZE = 20
LOG_FONT_SIZE = 15
SMALL_FONT_SIZE = 14

FONTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'fonts')
FONT_PATHS = {
    'title': os.path.join(FONTS_DIR, 'Cinzel-Bold.ttf'),
    'subtitle': os.path.join(FONTS_DIR, 'Cinzel-Regular.ttf'),
    'ui': os.path.join(FONTS_DIR, 'Inter-Regular.ttf'),
    'ui_bold': os.path.join(FONTS_DIR, 'Inter-SemiBold.ttf'),
    'card': os.path.join(FONTS_DIR, 'Roboto-Regular.ttf'),
    'card_bold': os.path.join(FONTS_DIR, 'Roboto-Bold.ttf'),
    'small': os.path.join(FONTS_DIR, 'Inter-Regular.ttf'),
    'log': os.path.join(FONTS_DIR, 'Inter-Regular.ttf'),
}
FONT_FALLBACKS = {
    'title': 'georgia',
    'subtitle': 'georgia',
    'ui': 'segoeui',
    'ui_bold': 'segoeui',
    'card': 'arial',
    'card_bold': 'arial',
    'small': 'segoeui',
    'log': 'segoeui',
}
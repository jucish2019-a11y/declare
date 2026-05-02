import math
import pygame
from config import (SCREEN_WIDTH, SCREEN_HEIGHT, BG_GREEN, BG_DARK, CARD_WHITE, CARD_BACK_BLUE,
    CARD_BACK_PATTERN, CARD_SHADOW, BLACK, RED, GOLD, TEXT_WHITE, TEXT_BLACK, TEXT_DIM,
    HIGHLIGHT, DIM, PANEL_BG, PANEL_BORDER, POWER_GLOW, EMPTY_SLOT, KNOWN_TINT,
    DECLARE_RED, DECLARE_RED_HOVER, CANCEL_GRAY, CANCEL_GRAY_HOVER,
    PEEK_BLUE, PEEK_BLUE_HOVER, SWAP_GREEN, SWAP_GREEN_HOVER,
    DISCARD_ORANGE, DISCARD_ORANGE_HOVER, PAIR_TEAL, PAIR_TEAL_HOVER,
    STATUS_BAR_H, ACTION_BAR_Y, ACTION_BAR_H,
    CARD_WIDTH, CARD_HEIGHT, CORNER_RADIUS, CARD_SPREAD,
    DECK_CENTER, DRAWN_CARD_POS, DISCARD_POS,
    PLAYER_BOTTOM, PLAYER_TOP, PLAYER_LEFT, PLAYER_RIGHT,
    LOG_PANEL_X, LOG_PANEL_Y, LOG_PANEL_W, LOG_PANEL_H,
    CARD_FONT_SIZE, CARD_BIG_FONT_SIZE, TITLE_FONT_SIZE, SUBTITLE_FONT_SIZE,
    UI_FONT_SIZE, LOG_FONT_SIZE, SMALL_FONT_SIZE,
    STATUS_LABEL_FONT_SIZE, STATUS_NAME_FONT_SIZE,
    NAMEPLATE_FONT_SIZE, NAMEPLATE_SUB_FONT_SIZE,
    STACK_LABEL_FONT_SIZE, LOG_HEADER_FONT_SIZE, LOG_SUB_FONT_SIZE,
    POWER_LABELS, POWER_COLORS, HAND_SIZE,
    CARD_GRID_SPACING_X, CARD_GRID_SPACING_Y, PLAYER_AREA_PADDING,
    ANIM_DRAW_DURATION, ANIM_SWAP_DURATION, ANIM_UNSEEN_SWAP_DURATION,
    ANIM_SEEN_SWAP_DURATION, ANIM_PEEK_LIFT_DURATION, ANIM_PAIR_FLY_DURATION,
    ANIM_DISCARD_DURATION, ANIM_NOTIFICATION_DURATION, ANIM_FLASH_DURATION,
    PLAYER_AREA_2, PLAYER_AREA_3, PLAYER_AREA_4, get_mobile_scale)
from game.card import Card
from game.player import Player
from game.game_manager import GameManager, GameState
from ui.animations import (VisualEvent, VisualEventType, AnimationQueue,
    ease_out_cubic, ease_out_back)
import card_render
import theme as theme_mod
import typography as typo

SEAT_POSITIONS_2 = {0: PLAYER_BOTTOM, 1: PLAYER_TOP}
SEAT_POSITIONS_3 = {0: PLAYER_BOTTOM, 1: (672, 320), 2: (1888, 320)}
SEAT_POSITIONS_4 = {0: PLAYER_BOTTOM, 1: PLAYER_LEFT, 2: PLAYER_TOP, 3: PLAYER_RIGHT}


_FELT_WINDOW_CACHE = {'key': None, 'surface': None}


def get_felt_texture(size):
    """Return a window-sized surface filled with the theme's room-shadow color.

    Used by the Display layer to fill letterbox bars during gameplay so the
    bars read as the dim room around the felt oval rather than as a stretched
    or distorted felt copy. Mirrors the base fill in `_build_felt_cache`
    (which begins with `out.fill(felt_shadow)` before painting the oval)."""
    th = theme_mod.active()
    shadow_col = getattr(th, 'felt_shadow', th.felt_rim)
    cache_key = (th.name, tuple(shadow_col), size)
    if _FELT_WINDOW_CACHE['key'] == cache_key:
        return _FELT_WINDOW_CACHE['surface']
    out = pygame.Surface(size)
    out.fill(shadow_col)
    _FELT_WINDOW_CACHE['key'] = cache_key
    _FELT_WINDOW_CACHE['surface'] = out
    return out


def _player_area_bounds(seat_index, num_players):
    if num_players == 2:
        return PLAYER_AREA_2.get(seat_index, PLAYER_AREA_2[0])
    elif num_players == 3:
        return PLAYER_AREA_3.get(seat_index, PLAYER_AREA_3[0])
    else:
        return PLAYER_AREA_4.get(seat_index, PLAYER_AREA_4[0])


STATE_LABELS = {
    GameState.MENU: "Menu",
    GameState.SETUP: "Setup",
    GameState.PEEK_PHASE: "Peek Phase",
    GameState.TURN_START: "Turn Start",
    GameState.DRAW: "Draw",
    GameState.DECIDE: "Decide",
    GameState.POWER_RESOLVE: "Resolve Power",
    GameState.PAIR_CHECK: "Pair Check",
    GameState.TURN_END: "Turn End",
    GameState.RESOLVE_DECLARE: "Resolve Declare",
    GameState.GAME_OVER: "Game Over",
}

LAYOUT_ICONS = {'line': '\u2500\u2500\u2500', 'square': '\u2588\u2588', 'free': '\u2726'}
LAYOUT_NAMES = ['line', 'square', 'free']


def _get_seat_position(seat_index, num_players):
    if num_players == 2:
        return SEAT_POSITIONS_2.get(seat_index, PLAYER_BOTTOM)
    elif num_players == 3:
        return SEAT_POSITIONS_3.get(seat_index, PLAYER_BOTTOM)
    else:
        return SEAT_POSITIONS_4.get(seat_index, PLAYER_BOTTOM)


def _get_font(size, bold=False):
    import typography as typo
    return typo.body_bold(size) if bold else typo.body(size)


class Renderer:
    def __init__(self, screen):
        self.screen = screen
        self.card_font = typo.body_bold(CARD_FONT_SIZE)
        self.card_big_font = typo.header_bold(CARD_BIG_FONT_SIZE)
        self.title_font = typo.display_bold(TITLE_FONT_SIZE)
        self.subtitle_font = typo.header(SUBTITLE_FONT_SIZE)
        self.ui_font = typo.body_bold(UI_FONT_SIZE)
        self.log_font = typo.body(LOG_FONT_SIZE)
        self.log_sub_font = typo.body(LOG_SUB_FONT_SIZE)
        self.small_font = typo.body(SMALL_FONT_SIZE)
        # Display-family roles (Cinzel) for headers, nameplates, and stack labels.
        # These are the "hero" type slots — used where the player should feel weight.
        self.display_label_font = typo.display_bold(STATUS_LABEL_FONT_SIZE)
        self.display_name_font = typo.display(STATUS_NAME_FONT_SIZE)
        self.nameplate_font = typo.display_bold(NAMEPLATE_FONT_SIZE)
        self.nameplate_sub_font = typo.body(NAMEPLATE_SUB_FONT_SIZE)
        self.stack_label_font = typo.display_bold(STACK_LABEL_FONT_SIZE)
        self.hovered_card = None
        self.hovered_button = None
        self.hovered_slot = None
        self.peek_reveal = None
        self._pulse_time = 0.0
        # Per-button hover-start timestamps (ms). Cleared the moment the mouse
        # leaves the button. After ~400 ms we show a tooltip describing the action.
        self._action_hover_start = {}
        self.animation_queue = AnimationQueue()
        self.dragging_card = None
        self.drag_pos = None
        self.game_settings = None
        # Surface cache for expensive procedural gradients. Invalidated on theme change.
        self._surface_cache = {}
        self._cache_theme_name = None

    def _ensure_cache(self):
        """Invalidate surface cache when theme changes."""
        th_name = theme_mod.active().name
        if self._cache_theme_name != th_name:
            self._surface_cache.clear()
            self._cache_theme_name = th_name

    def _cached(self, key, builder):
        """Return a cached surface, building it if necessary."""
        self._ensure_cache()
        if key not in self._surface_cache:
            self._surface_cache[key] = builder()
        return self._surface_cache[key]

    def draw(self, game_manager, mouse_pos=(0, 0), action_buttons=None,
             cancel_button=None, status_message="", awaiting_target=None):
        self.screen.fill(BG_GREEN)
        self._draw_table_felt()
        self._draw_status_bar(game_manager)
        self._draw_center_stack_groundplate()
        self._draw_pile_halo(game_manager)
        self.draw_discard(game_manager.discard_pile)
        self.draw_deck(game_manager.deck.remaining if game_manager.deck else 0)
        if game_manager.drawn_card:
            self.draw_drawn_card(game_manager.drawn_card)
        num_players = len(game_manager.players)
        current_player_index = game_manager.current_player_index
        for player in game_manager.players:
            pos = _get_seat_position(player.seat_index, num_players)
            is_current = player.seat_index == current_player_index
            is_human = player.is_human
            self.draw_player_area(player, pos, is_current, is_human, game_manager, mouse_pos)
        self.draw_peek_reveal()
        if game_settings := self.game_settings:
            if game_settings.show_game_log:
                self.draw_game_log(game_manager.game_log,
                                   round_number=game_manager.round_number)
        if action_buttons:
            self._draw_action_bar_container()
            self.draw_action_buttons(action_buttons)
        if cancel_button:
            self._draw_cancel_button(cancel_button, mouse_pos)
        if status_message:
            self.draw_status_message(status_message)
        self._draw_reaction_banner(game_manager, self.screen)
        self.animation_queue.draw(self.screen, self)

    def _draw_action_bar_container(self):
        th = theme_mod.active()
        container_rect = pygame.Rect(0, ACTION_BAR_Y - 8, SCREEN_WIDTH, ACTION_BAR_H + 16)

        def _build_container():
            surf = pygame.Surface((container_rect.width, container_rect.height), pygame.SRCALPHA)
            h = container_rect.height
            for i in range(h):
                t = i / max(1, h - 1)
                r = int(th.brass_900[0] * (0.40 + 0.30 * t))
                g = int(th.brass_900[1] * (0.40 + 0.30 * t))
                b = int(th.brass_900[2] * (0.40 + 0.30 * t))
                pygame.draw.line(surf, (r, g, b, 240), (0, i), (container_rect.width, i))
            mask = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
            pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=10)
            surf.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
            return surf

        container_surf = self._cached("action_bar_container", _build_container)
        self.screen.blit(container_surf, container_rect.topleft)

        # Top edge: thicker brass highlight band so the action rail visually
        # "attaches" to the felt above instead of floating.
        pygame.draw.line(self.screen, th.brass_300,
                         (0, container_rect.top),
                         (SCREEN_WIDTH, container_rect.top), 2)
        pygame.draw.line(self.screen, th.brass_500,
                         (0, container_rect.top + 2),
                         (SCREEN_WIDTH, container_rect.top + 2), 1)

        # Decorative brass studs every 200 px along the top edge.
        stud_y = container_rect.top + 6
        for sx in range(120, SCREEN_WIDTH, 200):
            pygame.draw.circle(self.screen, th.brass_500, (sx, stud_y), 4)
            pygame.draw.circle(self.screen, th.brass_900, (sx, stud_y), 4, 1)
            pygame.draw.circle(self.screen, th.brass_300, (sx - 1, stud_y - 1), 1)

        pygame.draw.rect(self.screen, th.brass_700, container_rect, 1, border_radius=10)

    def _draw_table_felt(self):
        th = theme_mod.active()
        gs = self.game_settings
        atmo = bool(getattr(gs, 'atmospheric_lighting', False)) if gs else False
        # The felt color tuples are part of the cache key so that picking a new
        # Table Felt in settings (which mutates the active theme's felt_*
        # tuples but not its name) actually rebuilds the cached surface.
        cache_key = (th.name, atmo, th.felt_deep, th.felt_mid,
                     th.felt_rim, th.felt_shadow)
        if not hasattr(self, "_felt_cache") or self._felt_theme_key != cache_key:
            self._felt_cache = self._build_felt_cache()
            self._felt_theme_key = cache_key
        self.screen.blit(self._felt_cache, (0, 0))

    def _build_felt_cache(self):
        import random as _r
        th = theme_mod.active()
        out = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        # Outside-oval room shadow (darker than the felt rim itself).
        shadow_col = getattr(th, "felt_shadow", th.felt_rim)
        out.fill(shadow_col)

        center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
        rx, ry = 1120, 608
        # The pendant lamp hangs slightly above the geometric center of the table —
        # the brightest pool of light is offset upward by ~3% of ry.
        lamp_cx, lamp_cy = center[0], center[1] - int(ry * 0.03)

        # Pass 1 — felt body: rim-to-mid radial gradient, properly alpha-composited.
        # We draw progressively smaller filled ellipses from edge color to center color,
        # which avoids the BLEND_MAX trick (which couldn't truly darken the rim).
        felt_layer = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        steps = 24
        for layer in range(steps, 0, -1):
            t = layer / steps  # 1.0 → ~0
            # Ease-out so the bright center occupies more area than a linear ramp.
            ease = 1.0 - (1.0 - t) * (1.0 - t)
            col = (
                int(th.felt_rim[0] + (th.felt_mid[0] - th.felt_rim[0]) * (1 - ease)),
                int(th.felt_rim[1] + (th.felt_mid[1] - th.felt_rim[1]) * (1 - ease)),
                int(th.felt_rim[2] + (th.felt_mid[2] - th.felt_rim[2]) * (1 - ease)),
                255,
            )
            sx = int(rx * t)
            sy = int(ry * t)
            pygame.draw.ellipse(
                felt_layer, col,
                pygame.Rect(center[0] - sx, center[1] - sy, sx * 2, sy * 2),
            )
        out.blit(felt_layer, (0, 0))

        # Pass 2 — warm lamp pool: bright pendant glow centered on (lamp_cx, lamp_cy),
        # masked to the oval so it never spills onto the room shadow.
        # Skipped when:
        #   - high contrast mode is on,
        #   - the active theme is non-atmospheric (e.g. Minimal), or
        #   - the player has turned off the atmospheric lighting setting.
        gs = self.game_settings
        atmo_setting = bool(getattr(gs, 'atmospheric_lighting', False)) if gs else False
        theme_atmo = getattr(th, "is_atmospheric", True)
        if not getattr(th, "high_contrast", False) and atmo_setting and theme_atmo:
            lamp_layer = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            pool_radius = int(rx * 0.62)
            pool_steps = 20
            for i in range(pool_steps, 0, -1):
                t = i / pool_steps  # 1.0 outer → ~0 inner
                # Quadratic falloff so the pool has a soft edge but a hot core.
                intensity = (1 - t) ** 1.7
                a = int(intensity * 78)
                if a <= 0:
                    continue
                r_pool = int(pool_radius * t)
                pygame.draw.circle(lamp_layer, (*th.lamp_glow, a),
                                   (lamp_cx, lamp_cy), r_pool)
            # Clip the lamp pool to the felt oval.
            mask = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            pygame.draw.ellipse(mask, (255, 255, 255, 255),
                                pygame.Rect(center[0] - rx, center[1] - ry, rx * 2, ry * 2))
            lamp_layer.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
            out.blit(lamp_layer, (0, 0))

        # Pass 3 — wear speckles, denser at the rim and sparser in the lit pool
        # (the lamp washes out fine texture in the bright zone).
        rng = _r.Random(42)
        wear = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        for _ in range(900):
            px = rng.randint(0, SCREEN_WIDTH)
            py = rng.randint(0, SCREEN_HEIGHT)
            dx = (px - center[0]) / rx
            dy = (py - center[1]) / ry
            d2 = dx * dx + dy * dy
            if d2 > 1:
                continue
            # Distance from lamp center (normalized to oval scale).
            ldx = (px - lamp_cx) / (rx * 0.62)
            ldy = (py - lamp_cy) / (ry * 0.62)
            ld2 = ldx * ldx + ldy * ldy
            if ld2 < 1.0 and rng.random() < (1.0 - ld2) * 0.55:
                # In the bright pool, drop ~half the speckles for cleaner highlights.
                continue
            a = rng.randint(6, 18)
            sz = rng.choice((1, 1, 1, 2))
            tone = rng.randint(-12, 12)
            cc = (max(0, min(255, th.felt_mid[0] + tone)),
                  max(0, min(255, th.felt_mid[1] + tone)),
                  max(0, min(255, th.felt_mid[2] + tone)), a)
            pygame.draw.circle(wear, cc, (px, py), sz)
        out.blit(wear, (0, 0))

        # Pass 4 — concentric inner guide rings (very subtle felt seam lines).
        for i in range(8):
            t = i / 8
            inset = int(80 * t)
            pygame.draw.ellipse(out, th.felt_rim,
                                pygame.Rect(center[0] - rx - inset, center[1] - ry - inset,
                                            (rx + inset) * 2, (ry + inset) * 2),
                                1)

        # Pass 5 — heavier brass border. Outer dark band, mid bright band, inner highlight.
        pygame.draw.ellipse(out, th.brass_700,
                            pygame.Rect(center[0] - rx, center[1] - ry, rx * 2, ry * 2), 3)
        pygame.draw.ellipse(out, th.brass_500,
                            pygame.Rect(center[0] - rx - 5, center[1] - ry - 5,
                                        rx * 2 + 10, ry * 2 + 10), 2)
        pygame.draw.ellipse(out, th.brass_300,
                            pygame.Rect(center[0] - rx + 3, center[1] - ry + 3,
                                        rx * 2 - 6, ry * 2 - 6), 1)

        for ring in (rx + 14, rx + 22):
            pygame.draw.ellipse(out, th.brass_900,
                                pygame.Rect(center[0] - ring, center[1] - int(ry * ring / rx),
                                            ring * 2, int(ry * ring / rx) * 2), 1)

        # Pass 6 — brass cardinal ornaments. East/West sit cleanly on the rim;
        # we skip North/South because the status bar (top) and action bar (bottom)
        # overlap them, and North-East would collide with the game-log panel.
        # Two ornaments + the center seal forms a visual axis line across the table.
        for sx in (-1, 1):
            ox = center[0] + int(sx * rx * 0.985)
            oy = center[1]
            self._draw_brass_ornament(out, ox, oy, th)

        # Pass 7 — large center "D" seal: a watermark, not a label. Cinzel Bold, alpha 55.
        seal_font = typo.display_bold(96)
        seal = seal_font.render("D", True, th.brass_900)
        seal.set_alpha(55)
        out.blit(seal, seal.get_rect(center=center))

        return out

    def _draw_hand_pool(self, cx, cy):
        """Faint elliptical lamp pool under a player's hand area."""
        th = theme_mod.active()
        pool_w = 820
        pool_h = 260

        def _build_hand_pool():
            pool = pygame.Surface((pool_w, pool_h), pygame.SRCALPHA)
            layers = 10
            for i in range(layers, 0, -1):
                t = i / layers
                a = int(26 * (1 - t) ** 1.4)
                if a <= 0:
                    continue
                ew = int(pool_w * t)
                eh = int(pool_h * t)
                pygame.draw.ellipse(
                    pool, (*th.lamp_glow, a),
                    pygame.Rect((pool_w - ew) // 2, (pool_h - eh) // 2, ew, eh),
                )
            return pool

        pool = self._cached("hand_pool", _build_hand_pool)
        self.screen.blit(pool, (cx - pool_w // 2, cy - pool_h // 2))

    def _draw_center_stack_groundplate(self):
        """Faint elliptical brass-tinted glow under the deck/discard/drawn cluster.
        Reads as 'the felt is worn here from play.' Drawn between the felt and the cards
        so it tints the felt rather than overlaying the piles."""
        th = theme_mod.active()
        deck_x, _ = DECK_CENTER
        drawn_x, _ = DRAWN_CARD_POS
        center_x = (deck_x + drawn_x) // 2
        center_y = DECK_CENTER[1] + 8
        ellipse_w = 880
        ellipse_h = 280

        def _build_groundplate():
            plate = pygame.Surface((ellipse_w, ellipse_h), pygame.SRCALPHA)
            layers = 12
            for i in range(layers, 0, -1):
                t = i / layers
                a = int(38 * (1 - t) ** 1.4)
                if a <= 0:
                    continue
                ew = int(ellipse_w * t)
                eh = int(ellipse_h * t)
                pygame.draw.ellipse(
                    plate, (*th.brass_500, a),
                    pygame.Rect((ellipse_w - ew) // 2, (ellipse_h - eh) // 2, ew, eh),
                )
            return plate

        plate = self._cached("center_stack_groundplate", _build_groundplate)
        self.screen.blit(plate, (center_x - ellipse_w // 2, center_y - ellipse_h // 2))

    def _draw_pile_halo(self, game_manager):
        """Sine-pulsed halo around whichever pile the player can act on right now.
        - TURN_START: deck halo (you need to draw)
        - DECIDE with drawn card: drawn-card halo (you need to decide)
        - REACTION_WINDOW: discard halo (you might need to react)"""
        th = theme_mod.active()
        active_pos = None
        if game_manager.state == GameState.TURN_START:
            active_pos = DECK_CENTER
        elif game_manager.state == GameState.DECIDE and game_manager.drawn_card is not None:
            active_pos = DRAWN_CARD_POS
        elif game_manager.state == GameState.REACTION_WINDOW:
            active_pos = DISCARD_POS
        if active_pos is None:
            return
        cx, cy = active_pos
        # Sine pulse 1Hz.
        t = (math.sin(self._pulse_time * 2 * math.pi) + 1) * 0.5
        base_alpha = int(50 + 60 * t)
        halo_w = CARD_WIDTH + 48
        halo_h = CARD_HEIGHT + 48

        def _build_halo_base():
            surf = pygame.Surface((halo_w, halo_h), pygame.SRCALPHA)
            for i in range(12, 0, -1):
                a = int(255 * (i / 12) ** 1.6)
                if a <= 0:
                    continue
                inset = 24 - int(i * 2)
                if inset < 0:
                    inset = 0
                pygame.draw.rect(
                    surf, (*th.brass_300, a),
                    pygame.Rect(inset, inset, halo_w - inset * 2, halo_h - inset * 2),
                    1, border_radius=CORNER_RADIUS + 4,
                )
            return surf

        halo_key = ("pile_halo", halo_w, halo_h)
        halo = self._cached(halo_key, _build_halo_base)
        halo.set_alpha(int(base_alpha * 255 / 110))  # scale to pulse alpha
        self.screen.blit(halo, (cx - halo_w // 2, cy - halo_h // 2))

    def _draw_stack_label(self, cx, cy, label, value):
        """Brass-edged pill showing 'LABEL · VALUE' (e.g. 'DECK · 43')."""
        th = theme_mod.active()
        label_text = f"{label} · {value}"
        font = self.stack_label_font
        text = font.render(label_text, True, th.text_white)
        pad_x = 14
        pad_y = 6
        pill_w = text.get_width() + pad_x * 2
        pill_h = text.get_height() + pad_y * 2
        pill_x = cx - pill_w // 2
        pill_y = cy - pill_h // 2

        # Body: brass_900 → brass_700 vertical gradient, semi-translucent.
        def _build_pill(pw, ph):
            pill = pygame.Surface((pw, ph), pygame.SRCALPHA)
            for i in range(ph):
                t = i / max(1, ph - 1)
                r = int(th.brass_900[0] + (th.brass_700[0] - th.brass_900[0]) * t)
                g = int(th.brass_900[1] + (th.brass_700[1] - th.brass_900[1]) * t)
                b = int(th.brass_900[2] + (th.brass_700[2] - th.brass_900[2]) * t)
                pygame.draw.line(pill, (r, g, b, 220), (0, i), (pw, i))
            mask = pygame.Surface((pw, ph), pygame.SRCALPHA)
            pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(),
                             border_radius=ph // 2)
            pill.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
            return pill

        pill_key = ("stack_label_pill", pill_w, pill_h)
        pill = self._cached(pill_key, lambda: _build_pill(pill_w, pill_h))
        self.screen.blit(pill, (pill_x, pill_y))

        # Top highlight + outline.
        pygame.draw.line(self.screen, th.brass_300,
                         (pill_x + 8, pill_y + 1),
                         (pill_x + pill_w - 8, pill_y + 1), 1)
        pygame.draw.rect(self.screen, th.brass_500,
                         pygame.Rect(pill_x, pill_y, pill_w, pill_h),
                         1, border_radius=pill_h // 2)
        self.screen.blit(text, (pill_x + pad_x, pill_y + pad_y))

    def _draw_ribbon(self, cx, top_y, label, accent_color=None):
        """Bunting-shaped ribbon banner. Used above the drawn card.
        Slight vertical bob (sine ±2px) when motion is enabled."""
        th = theme_mod.active()
        body_color = accent_color if accent_color is not None else th.brass_500
        font = typo.display_bold(28)
        text = font.render(label, True, th.text_white)

        pad_x = 22
        pad_y = 8
        notch = 12
        body_w = text.get_width() + pad_x * 2
        body_h = text.get_height() + pad_y * 2

        # Vertical bob — only if motion is enabled.
        bob = 0
        ms = th.motion_scale
        if ms > 0.1:
            bob = int(math.sin(self._pulse_time * 2.4) * 2 * ms)

        ribbon_x = cx - body_w // 2
        ribbon_y = top_y - body_h + bob

        # Bunting shape: rectangle with notched bottom corners, plus two side tails.
        ribbon = pygame.Surface((body_w + notch * 2, body_h + notch), pygame.SRCALPHA)
        # Side tails — flagging outward and downward at each end.
        left_tail = [
            (0, body_h // 2),
            (notch + 4, 2),
            (notch + 4, body_h - 2),
        ]
        right_tail = [
            (body_w + notch * 2, body_h // 2),
            (body_w + notch - 4, 2),
            (body_w + notch - 4, body_h - 2),
        ]
        pygame.draw.polygon(ribbon, body_color, left_tail)
        pygame.draw.polygon(ribbon, body_color, right_tail)

        # Main body with notched bottom.
        body_pts = [
            (notch, 0),
            (notch + body_w, 0),
            (notch + body_w, body_h - notch),
            (notch + body_w - notch, body_h),
            (notch + notch, body_h),
            (notch, body_h - notch),
        ]
        pygame.draw.polygon(ribbon, body_color, body_pts)

        # Top highlight band.
        pygame.draw.line(ribbon, th.brass_300,
                         (notch + 4, 2), (notch + body_w - 4, 2), 1)
        # Dark outline trace.
        pygame.draw.lines(ribbon, th.brass_900, True, body_pts, 1)

        self.screen.blit(ribbon, (ribbon_x - notch, ribbon_y))
        self.screen.blit(text, (ribbon_x + pad_x, ribbon_y + pad_y))

    def _draw_state_medallion(self, state, state_label):
        """Right-side circular state token. Outer ring color encodes state category:
            - red:  declare resolution (the moment of truth)
            - cyan: reaction window (you might need to act fast)
            - blue: power resolution
            - green: pair check
            - brass: everything else
        Label sits to the left of the token in Cinzel."""
        th = theme_mod.active()

        # State category → outer ring color.
        ring_color_map = {
            GameState.RESOLVE_DECLARE: th.signal_stop,
            GameState.REACTION_WINDOW: th.signal_info,
            GameState.POWER_RESOLVE: th.peek_blue,
            GameState.PAIR_CHECK: th.signal_go,
            GameState.GAME_OVER: th.brass_700,
        }
        ring_col = ring_color_map.get(state, th.brass_300)

        diameter = 50
        radius = diameter // 2
        right_pad = 14
        cx = SCREEN_WIDTH - right_pad - radius
        cy = STATUS_BAR_H // 2

        # Outer state-color ring (3px).
        pygame.draw.circle(self.screen, ring_col, (cx, cy), radius)
        # Mid brass band (2px in).
        pygame.draw.circle(self.screen, th.brass_500, (cx, cy), radius - 3)
        # Inner radial fill: brass_900 → brass_700 from center out.
        def _build_medallion_fill(d, rad):
            surf = pygame.Surface((d, d), pygame.SRCALPHA)
            for i in range(rad - 5, 0, -1):
                t = 1 - (i / max(1, rad - 5))
                r = int(th.brass_900[0] + (th.brass_700[0] - th.brass_900[0]) * t)
                g = int(th.brass_900[1] + (th.brass_700[1] - th.brass_900[1]) * t)
                b = int(th.brass_900[2] + (th.brass_700[2] - th.brass_900[2]) * t)
                pygame.draw.circle(surf, (r, g, b), (rad, rad), i)
            # Inner highlight (top-left).
            pygame.draw.circle(surf, (*th.brass_300, 60),
                               (rad - 5, rad - 5), max(2, rad // 3))
            return surf

        fill_key = ("state_medallion_fill", diameter)
        fill_surf = self._cached(fill_key, lambda: _build_medallion_fill(diameter, radius))
        self.screen.blit(fill_surf, (cx - radius, cy - radius))

        # Center glyph — first letter of the state in Cinzel.
        glyph_letter = state_label.split(" ")[0][:1].upper() if state_label else "?"
        glyph_font = typo.display_bold(24)
        glyph_surf = glyph_font.render(glyph_letter, True, th.brass_300)
        self.screen.blit(glyph_surf, glyph_surf.get_rect(center=(cx, cy)))

        # Label to the left of the medallion, in Cinzel-Bold, color-matched.
        label_font = typo.display_bold(22)
        label_surf = label_font.render(state_label.upper(), True, ring_col)
        label_x = cx - radius - 12 - label_surf.get_width()
        label_y = (STATUS_BAR_H - label_surf.get_height()) // 2
        self.screen.blit(label_surf, (label_x, label_y))

    def _draw_nameplate(self, cx, cy, player, is_current, is_human):
        """Brass-trimmed plate showing avatar + name + card count.
        Active player gets a pulsing brass glow ring.
        Human player gets a small cyan 'YOU' chip on the right edge."""
        th = theme_mod.active()

        name_text = player.name
        sub_text = f"Cards: {player.card_count}"

        plate_h = 72
        avatar_d = 56
        pad_l = 14
        gap = 14
        pad_r = 14

        name_font = typo.display_bold(28)
        sub_font = typo.body(NAMEPLATE_SUB_FONT_SIZE)
        you_font = typo.body_bold(18)

        name_surf = name_font.render(name_text, True, th.text_white)
        sub_surf = sub_font.render(sub_text, True, th.text_dim)

        you_chip_w = 0
        you_chip_h = 26
        you_surf = None
        if is_human:
            you_surf = you_font.render("YOU", True, th.brass_900)
            you_chip_w = you_surf.get_width() + 18

        text_block_w = max(name_surf.get_width(), sub_surf.get_width())
        plate_w = pad_l + avatar_d + gap + text_block_w + pad_r + (you_chip_w + 8 if you_chip_w else 0)
        # Clamp so very long names don't blow out the layout.
        plate_w = max(240, min(plate_w, 420))

        plate_x = cx - plate_w // 2
        plate_y = cy - plate_h // 2

        # Outer pulsing brass glow ring for the active player.
        if is_current:
            t = (math.sin(self._pulse_time * 1.6) + 1) * 0.5
            ring_alpha = int(70 + 50 * t)
            ring_pad = 14
            ring = pygame.Surface(
                (plate_w + ring_pad * 2, plate_h + ring_pad * 2), pygame.SRCALPHA
            )
            for i in range(ring_pad, 0, -2):
                a = int(ring_alpha * (i / ring_pad) ** 1.6)
                pygame.draw.rect(
                    ring, (*th.brass_300, a),
                    pygame.Rect(ring_pad - i, ring_pad - i,
                                plate_w + i * 2, plate_h + i * 2),
                    1, border_radius=12 + i,
                )
            self.screen.blit(ring, (plate_x - ring_pad, plate_y - ring_pad))

        # Plate body — brass_900→brass_700 vertical gradient, 8px corners.
        def _build_nameplate_plate(pw, ph):
            plate = pygame.Surface((pw, ph), pygame.SRCALPHA)
            for i in range(ph):
                t = i / max(1, ph - 1)
                r = int(th.brass_900[0] + (th.brass_700[0] - th.brass_900[0]) * t)
                g = int(th.brass_900[1] + (th.brass_700[1] - th.brass_900[1]) * t)
                b = int(th.brass_900[2] + (th.brass_700[2] - th.brass_900[2]) * t)
                pygame.draw.line(plate, (r, g, b, 240), (0, i), (pw, i))
            mask = pygame.Surface((pw, ph), pygame.SRCALPHA)
            pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=8)
            plate.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
            return plate

        plate_key = ("nameplate_plate", plate_w, plate_h)
        plate = self._cached(plate_key, lambda: _build_nameplate_plate(plate_w, plate_h))
        self.screen.blit(plate, (plate_x, plate_y))

        # Top highlight + outline.
        pygame.draw.line(self.screen, th.brass_300,
                         (plate_x + 6, plate_y + 1),
                         (plate_x + plate_w - 6, plate_y + 1), 1)
        pygame.draw.rect(self.screen, th.brass_500,
                         pygame.Rect(plate_x, plate_y, plate_w, plate_h),
                         1, border_radius=8)

        # Avatar circle.
        ax = plate_x + pad_l + avatar_d // 2
        ay = plate_y + plate_h // 2
        pygame.draw.circle(self.screen, th.brass_900, (ax, ay), avatar_d // 2)
        pygame.draw.circle(self.screen, (40, 70, 50), (ax, ay), avatar_d // 2 - 3)
        pygame.draw.circle(self.screen, th.brass_300, (ax, ay), avatar_d // 2, 2)
        initial_font = typo.display_bold(28)
        initial_letter = (name_text[:1] or "?").upper()
        initial_surf = initial_font.render(initial_letter, True, th.brass_300)
        self.screen.blit(initial_surf, initial_surf.get_rect(center=(ax, ay)))

        # Text block — name on top, "Cards: N" below.
        text_x = plate_x + pad_l + avatar_d + gap
        text_block_h = name_surf.get_height() + 2 + sub_surf.get_height()
        text_top = plate_y + (plate_h - text_block_h) // 2
        # Truncate name with an ellipsis if it would overflow.
        max_text_w = plate_w - (text_x - plate_x) - pad_r - (you_chip_w + 8 if you_chip_w else 0)
        if name_surf.get_width() > max_text_w:
            text = name_text
            while text and name_font.size(text + "…")[0] > max_text_w:
                text = text[:-1]
            name_surf = name_font.render(text + "…" if text else "…", True, th.text_white)
        self.screen.blit(name_surf, (text_x, text_top))
        self.screen.blit(sub_surf, (text_x, text_top + name_surf.get_height() + 2))

        # "YOU" chip on the right edge for the human seat.
        if you_surf is not None:
            chip_x = plate_x + plate_w - pad_r - you_chip_w
            chip_y = plate_y + (plate_h - you_chip_h) // 2
            chip_bg = pygame.Surface((you_chip_w, you_chip_h), pygame.SRCALPHA)
            pygame.draw.rect(chip_bg, th.you_cyan, chip_bg.get_rect(),
                             border_radius=you_chip_h // 2)
            pygame.draw.rect(chip_bg, th.brass_900, chip_bg.get_rect(),
                             1, border_radius=you_chip_h // 2)
            self.screen.blit(chip_bg, (chip_x, chip_y))
            self.screen.blit(you_surf,
                             you_surf.get_rect(center=(chip_x + you_chip_w // 2,
                                                       chip_y + you_chip_h // 2)))

    def _draw_brass_ornament(self, surface, cx, cy, th):
        """Small inlaid brass diamond + compass pips. Reads as a period table fitting."""
        # Outer diamond plate.
        outer_pts = [(cx, cy - 16), (cx + 12, cy), (cx, cy + 16), (cx - 12, cy)]
        pygame.draw.polygon(surface, th.brass_500, outer_pts)
        pygame.draw.polygon(surface, th.brass_900, outer_pts, 1)
        # Inner brighter diamond.
        inner_pts = [(cx, cy - 9), (cx + 6, cy), (cx, cy + 9), (cx - 6, cy)]
        pygame.draw.polygon(surface, th.brass_300, inner_pts)
        # Center pip.
        pygame.draw.circle(surface, th.brass_900, (cx, cy), 2)
        # Compass pips at N/S/E/W of the ornament.
        for dx, dy in ((0, -24), (0, 24), (-22, 0), (22, 0)):
            pygame.draw.circle(surface, th.brass_500, (cx + dx, cy + dy), 2)
            pygame.draw.circle(surface, th.brass_700, (cx + dx, cy + dy), 2, 1)

    def _draw_status_bar(self, game_manager):
        th = theme_mod.active()
        bar_rect = pygame.Rect(0, 0, SCREEN_WIDTH, STATUS_BAR_H)

        def _build_status_bar():
            plate = pygame.Surface((SCREEN_WIDTH, STATUS_BAR_H))
            for i in range(STATUS_BAR_H):
                t = i / max(1, STATUS_BAR_H - 1)
                r = int(th.brass_900[0] + (th.brass_700[0] - th.brass_900[0]) * (1 - abs(t - 0.5) * 2))
                g = int(th.brass_900[1] + (th.brass_700[1] - th.brass_900[1]) * (1 - abs(t - 0.5) * 2))
                b = int(th.brass_900[2] + (th.brass_700[2] - th.brass_900[2]) * (1 - abs(t - 0.5) * 2))
                pygame.draw.line(plate, (r, g, b), (0, i), (SCREEN_WIDTH, i))
            return plate

        plate = self._cached("status_bar", _build_status_bar)
        self.screen.blit(plate, (0, 0))

        pygame.draw.line(self.screen, th.brass_300, (0, 0), (SCREEN_WIDTH, 0), 1)
        pygame.draw.line(self.screen, th.brass_500, (0, 1), (SCREEN_WIDTH, 1), 1)
        pygame.draw.line(self.screen, th.brass_900, (0, STATUS_BAR_H - 1), (SCREEN_WIDTH, STATUS_BAR_H - 1), 1)
        for k in range(0, SCREEN_WIDTH, 80):
            pygame.draw.circle(self.screen, th.brass_500, (k + 10, STATUS_BAR_H // 2), 1)

        state_label = STATE_LABELS.get(game_manager.state, str(game_manager.state.value))
        current_player = game_manager.current_player()

        avatar_rect = pygame.Rect(14, (STATUS_BAR_H - 28) // 2, 28, 28)
        pygame.draw.circle(self.screen, (40, 70, 50), avatar_rect.center, 14)
        pygame.draw.circle(self.screen, th.brass_300, avatar_rect.center, 14, 2)
        initial_surf = self.small_font.render(current_player.name[0].upper(), True, th.brass_300)
        self.screen.blit(initial_surf, initial_surf.get_rect(center=avatar_rect.center))

        round_surf = self.display_label_font.render(
            f"Round {game_manager.round_number}", True, th.text_white)
        text_x = avatar_rect.right + 16
        self.screen.blit(round_surf, (text_x, (STATUS_BAR_H - round_surf.get_height()) // 2))

        name_surf = self.display_name_font.render(current_player.name, True, th.brass_300)
        name_x = text_x + round_surf.get_width() + 20
        self.screen.blit(name_surf, (name_x, (STATUS_BAR_H - name_surf.get_height()) // 2))

        # State medallion (right side) — circular brass token + Cinzel label.
        # The outer ring color signals state category at a glance.
        self._draw_state_medallion(game_manager.state, state_label)

    def draw_card_face(self, x, y, card, selected=False, hovered=False, show_power_label=False, show_pips=True):
        rect = pygame.Rect(x, y, CARD_WIDTH, CARD_HEIGHT)
        lift_y = -3 if hovered else 0
        self._draw_shadow(x + 1, y + 5 + lift_y)

        face = card_render.paint_face(card, CARD_WIDTH, CARD_HEIGHT)
        self.screen.blit(face, (x, y + lift_y))

        if show_power_label and card.power is not None:
            power_color = POWER_COLORS.get(card.power, TEXT_WHITE)
            power_label = POWER_LABELS.get(card.power, card.power)
            p_surf = self.small_font.render(power_label, True, power_color)
            p_rect = p_surf.get_rect(center=(x + CARD_WIDTH // 2, y + CARD_HEIGHT + 12))
            self.screen.blit(p_surf, p_rect)
        if selected:
            sel_rect = pygame.Rect(x - 2, y - 2 + lift_y, CARD_WIDTH + 4, CARD_HEIGHT + 4)
            pygame.draw.rect(self.screen, GOLD, sel_rect, 3, border_radius=CORNER_RADIUS + 2)
        return rect

    def _draw_suit_pips(self, x, y, card):
        color = RED if card.is_red else BLACK
        cx = x + CARD_WIDTH // 2
        cy = y + CARD_HEIGHT // 2
        w, h = CARD_WIDTH, CARD_HEIGHT

        def pip(px, py, size=8):
            pts = [(px, py - size), (px + size * 0.65, py + size * 0.5),
                   (px - size * 0.65, py + size * 0.5)]
            pygame.draw.polygon(self.screen, color, pts)

        def diam(px, py, size=8):
            pts = [(px, py - size), (px + size, py), (px, py + size), (px - size, py)]
            pygame.draw.polygon(self.screen, color, pts)

        rank = card.rank
        if rank == 'A':
            pip(cx, cy)
        elif rank == '2':
            pip(cx, cy - 26)
            pip(cx, cy + 26)
        elif rank == '3':
            pip(cx, cy - 26)
            pip(cx, cy + 26)
            pip(cx, cy)
        elif rank == '4':
            pip(cx - 20, cy - 18)
            pip(cx + 20, cy - 18)
            pip(cx - 20, cy + 18)
            pip(cx + 20, cy + 18)
        elif rank == '5':
            pip(cx - 20, cy - 18)
            pip(cx + 20, cy - 18)
            pip(cx - 20, cy + 18)
            pip(cx + 20, cy + 18)
            pip(cx, cy)
        elif rank == '6':
            pip(cx - 20, cy - 22)
            pip(cx + 20, cy - 22)
            pip(cx - 20, cy)
            pip(cx + 20, cy)
            pip(cx - 20, cy + 22)
            pip(cx + 20, cy + 22)
        elif rank == '7':
            pip(cx - 20, cy - 22)
            pip(cx + 20, cy - 22)
            pip(cx - 20, cy)
            pip(cx + 20, cy)
            pip(cx - 20, cy + 22)
            pip(cx + 20, cy + 22)
            pip(cx, cy - 32)
        elif rank == '8':
            pip(cx - 20, cy - 22)
            pip(cx + 20, cy - 22)
            pip(cx - 20, cy)
            pip(cx + 20, cy)
            pip(cx - 20, cy + 22)
            pip(cx + 20, cy + 22)
            pip(cx, cy - 32)
            pip(cx, cy + 32)
        elif rank == '9':
            pip(cx - 22, cy - 26)
            pip(cx + 22, cy - 26)
            pip(cx - 22, cy)
            pip(cx + 22, cy)
            pip(cx - 22, cy + 26)
            pip(cx + 22, cy + 26)
            pip(cx, cy)
        elif rank == '10':
            pip(cx - 22, cy - 30)
            pip(cx + 22, cy - 30)
            pip(cx - 22, cy - 4)
            pip(cx + 22, cy - 4)
            pip(cx - 22, cy + 22)
            pip(cx + 22, cy + 22)
            pip(cx, cy - 30)
            pip(cx, cy - 4)
            pip(cx, cy + 22)
        elif rank in ('J', 'Q', 'K'):
            pass
        else:
            pass

    def _draw_crown(self, x, y, card):
        color = RED if card.is_red else BLACK
        cx = x + CARD_WIDTH // 2 + 8
        cy = y + CARD_HEIGHT // 2 + 6
        base_w = 22
        base_h = 10
        crown_pts = [
            (cx - base_w // 2, cy + base_h // 2),
            (cx - base_w // 2, cy - base_h // 4),
            (cx - base_w // 4, cy - base_h // 2),
            (cx, cy - base_h // 4),
            (cx + base_w // 4, cy - base_h // 2),
            (cx + base_w // 2, cy - base_h // 4),
            (cx + base_w // 2, cy + base_h // 2),
        ]
        crown_fill = (220, 170, 30) if card.is_red else (80, 80, 80)
        pygame.draw.polygon(self.screen, crown_fill, crown_pts)
        pygame.draw.polygon(self.screen, (255, 220, 80), crown_pts, 1)
        if card.rank == 'K':
            if not card.is_red:
                k_surf = self.small_font.render("0", True, (180, 180, 180))
                k_rect = k_surf.get_rect(center=(cx, cy + base_h + 5))
                self.screen.blit(k_surf, k_rect)
            else:
                k_surf = self.small_font.render("13", True, (150, 20, 20))
                k_rect = k_surf.get_rect(center=(cx, cy + base_h + 5))
                self.screen.blit(k_surf, k_rect)

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

    def draw_card_back(self, x, y, has_known_marker=False, hovered=False,
                      player=None, slot_index=None, game_manager=None):
        rect = pygame.Rect(x, y, CARD_WIDTH, CARD_HEIGHT)
        lift_y = -4 if hovered else 0
        self._draw_shadow(x, y + 5 + lift_y)

        style = self._active_back_style()
        back = card_render.paint_back(style=style, w=CARD_WIDTH, h=CARD_HEIGHT)
        self.screen.blit(back, (x, y + lift_y))

        # Static specular highlight band — a soft warm gleam in the top-left
        # corner of the card back, sells "lit by overhead lamp." Subtle.
        th = theme_mod.active()
        if not getattr(th, "high_contrast", False):
            def _build_card_highlight():
                spec = pygame.Surface((CARD_WIDTH, CARD_HEIGHT), pygame.SRCALPHA)
                for i in range(8, 0, -1):
                    a = int(i * 5.5)
                    if a <= 0:
                        continue
                    pygame.draw.circle(
                        spec, (*th.lamp_glow, a),
                        (int(CARD_WIDTH * 0.28), int(CARD_HEIGHT * 0.18)),
                        int(CARD_WIDTH * 0.28 * (i / 8)),
                    )
                # Mask to card rounded shape so the gleam doesn't bleed past edges.
                shape = pygame.Surface((CARD_WIDTH, CARD_HEIGHT), pygame.SRCALPHA)
                pygame.draw.rect(shape, (255, 255, 255, 255), shape.get_rect(),
                                 border_radius=CORNER_RADIUS)
                spec.blit(shape, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
                return spec

            highlight_key = ("card_back_highlight", CARD_WIDTH, CARD_HEIGHT)
            spec = self._cached(highlight_key, _build_card_highlight)
            self.screen.blit(spec, (x, y + lift_y))

        if hovered:
            t = pygame.time.get_ticks() / 1000.0
            shimmer = card_render.paint_back_glow(style, CARD_WIDTH, CARD_HEIGHT, t)
            self.screen.blit(shimmer, (x, y + lift_y), special_flags=pygame.BLEND_RGBA_ADD)

        if has_known_marker:
            # Memory pin: outer brass disc + inner pearl + tiny vertical drop —
            # reads as a small inlaid brass pin holding the card "remembered."
            pin_x = x + CARD_WIDTH - 14
            pin_y = y + 12 + lift_y
            pygame.draw.circle(self.screen, th.brass_900, (pin_x, pin_y), 8)
            pygame.draw.circle(self.screen, th.brass_500, (pin_x, pin_y), 7)
            pygame.draw.circle(self.screen, th.brass_300, (pin_x, pin_y), 5)
            pygame.draw.circle(self.screen, th.brass_100,
                               (pin_x - 1, pin_y - 1), 2)
            # Small vertical drop below the pin head — the "stem".
            pygame.draw.line(self.screen, th.brass_700,
                             (pin_x, pin_y + 7), (pin_x, pin_y + 13), 2)
            pygame.draw.circle(self.screen, th.brass_700, (pin_x, pin_y + 13), 1)

        received_highlight = False
        if player is not None and slot_index is not None and game_manager is not None:
            if player.received_card_slot == slot_index and player.received_card_until > 0:
                received_highlight = True

        if received_highlight:
            pulse = abs(math.sin(pygame.time.get_ticks() * 0.008)) * 0.4 + 0.6
            glow_col = (*GOLD, int(180 * pulse))
            glow_rect = rect.inflate(8, 8)
            glow_surf = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
            pygame.draw.rect(glow_surf, glow_col, glow_surf.get_rect(), border_radius=10)
            self.screen.blit(glow_surf, (glow_rect.x, glow_rect.y))

        return rect

    def _active_back_style(self):
        return getattr(self, "_card_back_style", "classic")

    def set_back_style(self, style):
        if getattr(self, "_card_back_style", None) == style:
            return
        self._card_back_style = style
        card_render.invalidate_cache()

    def _draw_card_back_crosshatch(self, x, y):
        inner_x = x + 10
        inner_y = y + 10
        inner_w = CARD_WIDTH - 20
        inner_h = CARD_HEIGHT - 20
        line_color = (50, 90, 170, 40)
        spacing = 12
        surface = pygame.Surface((inner_w, inner_h), pygame.SRCALPHA)
        for i in range(-inner_h, inner_w, spacing):
            pts = []
            for j in range(0, inner_w + inner_h, 4):
                px = i + j
                py = j
                if 0 <= px < inner_w and 0 <= py < inner_h:
                    pass
                px2 = i + j
                py2 = -j + inner_h if (i + j) >= inner_h else inner_h
                if 0 <= px2 < inner_w and 0 <= py2 < inner_h:
                    pass
        cross_surf = pygame.Surface((inner_w, inner_h), pygame.SRCALPHA)
        step = spacing
        for i in range(0, max(inner_w, inner_h), step):
            if i < inner_w:
                pygame.draw.line(cross_surf, line_color, (i, 0), (i, inner_h))
            if i < inner_h:
                pygame.draw.line(cross_surf, line_color, (0, i), (inner_w, i))
        self.screen.blit(cross_surf, (inner_x, inner_y))

    def draw_empty_slot(self, x, y):
        rect = pygame.Rect(x, y, CARD_WIDTH, CARD_HEIGHT)
        self._draw_dashed_rect(self.screen, EMPTY_SLOT, rect, CORNER_RADIUS)
        return rect

    def draw_deck(self, remaining):
        cx, cy = DECK_CENTER
        dx = cx - CARD_WIDTH // 2
        dy = cy - CARD_HEIGHT // 2
        if remaining > 0:
            stack_count = min(remaining, 4)
            style = self._active_back_style()
            back = card_render.paint_back(style, CARD_WIDTH, CARD_HEIGHT)
            for i in range(stack_count, 0, -1):
                self._draw_shadow(dx - i * 2, dy - i * 2 + 5)
                self.screen.blit(back, (dx - i * 2, dy - i * 2))
            self._draw_shadow(dx, dy + 5)
            self.screen.blit(back, (dx, dy))
            self._draw_stack_label(cx, cy + CARD_HEIGHT // 2 + 26,
                                   "DECK", str(remaining))
        else:
            self.draw_empty_slot(dx, dy)
            empty_surf = self.small_font.render("Empty", True, DIM)
            empty_rect = empty_surf.get_rect(center=(cx, cy))
            self.screen.blit(empty_surf, empty_rect)
            self._draw_stack_label(cx, cy + CARD_HEIGHT // 2 + 26,
                                   "DECK", "0")

    def draw_discard(self, discard_pile):
        if not discard_pile:
            return
        cx, cy = DISCARD_POS
        dx = cx - CARD_WIDTH // 2
        dy = cy - CARD_HEIGHT // 2
        top_card = discard_pile[-1]
        top_card.face_up = True
        self.draw_card_face(dx, dy, top_card)
        self._draw_stack_label(cx, cy + CARD_HEIGHT // 2 + 26,
                               "DISCARD", str(len(discard_pile)))

    def draw_player_area(self, player, position, is_current, is_human, game_manager, mouse_pos):
        px, py = position
        layout = getattr(player, 'layout_mode', 'line')
        num_players = len(game_manager.players)
        card_positions = self._compute_card_positions(player, position, game_manager)
        self.hovered_slot = None
        if is_human:
            for slot_index in range(player.hand_size):
                if slot_index < len(card_positions):
                    cx, cy = card_positions[slot_index]
                    card_rect = pygame.Rect(cx, cy, CARD_WIDTH, CARD_HEIGHT)
                    if card_rect.collidepoint(mouse_pos) and player.hand[slot_index] is not None:
                        self.hovered_slot = slot_index
                        break

        bounds = _player_area_bounds(player.seat_index, num_players)
        if layout == 'free':
            self._draw_area_outline(bounds)

        # Hand-area light pool — soft elliptical lamp glow under the player's
        # cards. Anchors the cards to the felt and silently signals "this zone
        # is yours." Skipped on high-contrast and non-atmospheric themes.
        _th_active = theme_mod.active()
        if (not getattr(_th_active, "high_contrast", False)
                and getattr(_th_active, "is_atmospheric", True)):
            self._draw_hand_pool(px, py)

        # Brass-trimmed nameplate (replaces the old floating-text + dark pill).
        # We anchor the plate to whichever side of the cards is "outside" — for
        # the human (bottom seat) that's *above* the cards toward center; for
        # opponents at the top it's also above. The plate must clear the cards
        # by a comfortable gap (no overlap) and must clear the status bar.
        _, y_min, _, y_max = bounds
        plate_h = 72
        gap_above_cards = 26
        if card_positions:
            card_top = card_positions[0][1]
            raw_plate_y = card_top - gap_above_cards - plate_h // 2
        else:
            raw_plate_y = py - 80
        # Lower clamp keeps the plate clear of the status bar; we deliberately
        # let it sit *above* the player-area `y_min` if needed because the gap
        # between status bar and player area is metadata real estate, not card
        # real estate.
        min_y = STATUS_BAR_H + 8 + plate_h // 2
        max_y = y_max - CARD_HEIGHT - 110
        plate_y = max(min_y, min(raw_plate_y, max_y))
        self._draw_nameplate(px, plate_y, player, is_current, is_human)

        for slot_index in range(player.hand_size):
            card = player.hand[slot_index]
            if slot_index < len(card_positions):
                cx, cy = card_positions[slot_index]
            else:
                cx, cy = 0, 0

            if self.dragging_card is not None and self.dragging_card == slot_index and is_human:
                continue

            hovered = is_human and self.hovered_slot == slot_index
            if card is None:
                self.draw_empty_slot(cx, cy)
            elif is_human:
                has_marker = slot_index in player.known_cards
                self.draw_card_back(cx, cy, has_known_marker=has_marker, hovered=hovered,
                                    player=player, slot_index=slot_index, game_manager=game_manager)
            else:
                self.draw_card_back(cx, cy, has_known_marker=False,
                                    player=player, slot_index=slot_index, game_manager=game_manager)

        if self.dragging_card is not None and is_human and self.drag_pos is not None:
            slot_index = self.dragging_card
            card = player.hand[slot_index]
            if card is not None:
                dx, dy = self.drag_pos
                drag_surf = pygame.Surface((CARD_WIDTH, CARD_HEIGHT), pygame.SRCALPHA)
                if slot_index in player.known_cards:
                    self._render_card_face_on_surface(drag_surf, card, show_pips=False)
                else:
                    self._render_card_back_on_surface(drag_surf)
                drag_surf.set_alpha(200)
                self.screen.blit(drag_surf, (dx - CARD_WIDTH // 2, dy - CARD_HEIGHT // 2))

    def _draw_area_outline(self, bounds):
        x_min, y_min, x_max, y_max = bounds
        outline_rect = pygame.Rect(x_min, y_min, x_max - x_min, y_max - y_min)
        outline_surf = pygame.Surface((outline_rect.width, outline_rect.height), pygame.SRCALPHA)
        pygame.draw.rect(outline_surf, (255, 255, 255, 25), outline_surf.get_rect(), 2, border_radius=8)
        self.screen.blit(outline_surf, outline_rect.topleft)

    def _compute_card_positions(self, player, position, game_manager):
        px, py = position
        layout = getattr(player, 'layout_mode', 'line')
        num_players = len(game_manager.players)
        positions = []

        if layout == 'line':
            total_width = player.hand_size * CARD_SPREAD + (CARD_WIDTH - CARD_SPREAD)
            start_x = px - total_width // 2
            start_y = py - CARD_HEIGHT // 2 + 4
            for i in range(player.hand_size):
                positions.append((start_x + i * CARD_SPREAD, start_y))

        elif layout == 'square':
            if player.hand_size != 4:
                total_width = player.hand_size * CARD_SPREAD + (CARD_WIDTH - CARD_SPREAD)
                start_x = px - total_width // 2
                start_y = py - CARD_HEIGHT // 2 + 4
                for i in range(player.hand_size):
                    positions.append((start_x + i * CARD_SPREAD, start_y))
            else:
                grid_w = 2 * CARD_GRID_SPACING_X
                grid_h = 2 * CARD_GRID_SPACING_Y
                start_x = px - grid_w // 2
                start_y = py - grid_h // 2 + 4
                grid_positions = [
                    (start_x, start_y),
                    (start_x + CARD_GRID_SPACING_X, start_y),
                    (start_x, start_y + CARD_GRID_SPACING_Y),
                    (start_x + CARD_GRID_SPACING_X, start_y + CARD_GRID_SPACING_Y),
                ]
                for i in range(player.hand_size):
                    if i < len(grid_positions):
                        positions.append(grid_positions[i])
                    else:
                        positions.append((px, py))

        elif layout == 'free':
            default_positions = self._default_line_positions(px, py, player.hand_size)
            stored = getattr(player, 'card_positions', {})
            for i in range(player.hand_size):
                if i in stored and stored[i] is not None:
                    positions.append(stored[i])
                elif i < len(default_positions):
                    positions.append(default_positions[i])
                    if i not in stored:
                        stored[i] = default_positions[i]
                else:
                    positions.append((px, py))
            player.card_positions = stored

        return positions

    def _default_line_positions(self, px, py, hand_size):
        total_width = hand_size * CARD_SPREAD + (CARD_WIDTH - CARD_SPREAD)
        start_x = px - total_width // 2
        start_y = py - CARD_HEIGHT // 2 + 4
        positions = []
        for i in range(hand_size):
            positions.append((start_x + i * CARD_SPREAD, start_y))
        return positions

    def _draw_layout_buttons(self, player, cx, y, mouse_pos):
        layout = getattr(player, 'layout_mode', 'line')
        btn_w = 36
        btn_h = 22
        spacing = 4
        total_w = len(LAYOUT_NAMES) * btn_w + (len(LAYOUT_NAMES) - 1) * spacing
        start_x = cx - total_w // 2

        for i, mode in enumerate(LAYOUT_NAMES):
            bx = start_x + i * (btn_w + spacing)
            rect = pygame.Rect(bx, y, btn_w, btn_h)
            is_active = (layout == mode)
            is_hovered = rect.collidepoint(mouse_pos) and not is_active
            if is_active:
                color = GOLD
                text_color = BG_DARK
            elif is_hovered:
                color = (100, 100, 100)
                text_color = TEXT_WHITE
            else:
                color = (60, 60, 60)
                text_color = TEXT_DIM
            self._draw_rounded_rect(self.screen, color, rect, 4)
            icon = LAYOUT_ICONS[mode]
            icon_surf = self.small_font.render(icon, True, text_color)
            icon_rect = icon_surf.get_rect(center=rect.center)
            self.screen.blit(icon_surf, icon_rect)

    def get_layout_button_rects(self, player, cx, y):
        btn_w = 36
        btn_h = 22
        spacing = 4
        total_w = len(LAYOUT_NAMES) * btn_w + (len(LAYOUT_NAMES) - 1) * spacing
        start_x = cx - total_w // 2
        rects = {}
        for i, mode in enumerate(LAYOUT_NAMES):
            bx = start_x + i * (btn_w + spacing)
            rects[mode] = pygame.Rect(bx, y, btn_w, btn_h)
        return rects

    def get_layout_button_y(self, player, game_manager):
        pos = _get_seat_position(player.seat_index, len(game_manager.players))
        card_positions = self._compute_card_positions(player, pos, game_manager)
        if card_positions:
            return int(card_positions[0][1]) - 28 - 18
        return pos[1] - 50

    def init_free_positions(self, player, game_manager):
        pos = _get_seat_position(player.seat_index, len(game_manager.players))
        defaults = self._default_line_positions(pos[0], pos[1], player.hand_size)
        for i, p in enumerate(defaults):
            if i not in player.card_positions:
                player.card_positions[i] = p

    def _render_card_face_on_surface(self, surface, card, show_pips=True):
        rect = surface.get_rect()
        face = card_render.paint_face(card, rect.width, rect.height)
        surface.blit(face, (0, 0))

    def _render_card_back_on_surface(self, surface):
        rect = surface.get_rect()
        gradient_surf = pygame.Surface((CARD_WIDTH, CARD_HEIGHT), pygame.SRCALPHA)
        for i in range(CARD_WIDTH):
            t = i / CARD_WIDTH
            alpha = int(20 + 25 * t)
            pygame.draw.line(gradient_surf, (20, 45, 95, alpha), (i, 0), (i, CARD_HEIGHT))
        surface.blit(gradient_surf, (0, 0))
        pygame.draw.rect(surface, CARD_BACK_BLUE, rect, border_radius=CORNER_RADIUS)
        inner = pygame.Rect(6, 6, rect.width - 12, rect.height - 12)
        pygame.draw.rect(surface, CARD_BACK_PATTERN, inner, border_radius=CORNER_RADIUS - 2)
        inner_x, inner_y = 10, 10
        inner_w, inner_h = CARD_WIDTH - 20, CARD_HEIGHT - 20
        line_color = (50, 90, 170, 40)
        cross_surf = pygame.Surface((inner_w, inner_h), pygame.SRCALPHA)
        for i in range(0, max(inner_w, inner_h), 12):
            if i < inner_w:
                pygame.draw.line(cross_surf, line_color, (i, 0), (i, inner_h))
            if i < inner_h:
                pygame.draw.line(cross_surf, line_color, (0, i), (inner_w, i))
        surface.blit(cross_surf, (inner_x, inner_y))
        dcx = rect.width // 2
        dcy = rect.height // 2
        self._draw_card_back_medallion(surface, dcx, dcy)
        pygame.draw.rect(surface, TEXT_WHITE, rect, 1, border_radius=CORNER_RADIUS)

    def draw_drawn_card(self, card):
        cx, cy = DRAWN_CARD_POS
        dx = cx - CARD_WIDTH // 2
        dy = cy - CARD_HEIGHT // 2
        # Gold ribbon banner above the drawn card. If the card has a power, the
        # ribbon switches to that power's color and shows the power label so the
        # player sees the strategic option without scanning text.
        ribbon_text = "DREW"
        ribbon_color = None
        if card.power is not None:
            ribbon_text = POWER_LABELS.get(card.power, ribbon_text).upper()
            ribbon_color = POWER_COLORS.get(card.power)
        self._draw_ribbon(cx, dy - 22, ribbon_text, accent_color=ribbon_color)
        rect = self.draw_card_face(dx, dy, card, show_power_label=False, show_pips=False)
        return rect

    def draw_peek_reveal(self):
        if self.peek_reveal is None or self.peek_reveal['timer'] <= 0:
            return
        card = self.peek_reveal['card']
        rx = self.peek_reveal['x']
        ry = self.peek_reveal['y']
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        self.screen.blit(overlay, (0, 0))
        label_surf = self.ui_font.render("You saw:", True, GOLD)
        label_rect = label_surf.get_rect(center=(rx + CARD_WIDTH // 2, ry - 24))
        self.screen.blit(label_surf, label_rect)
        self.draw_card_face(rx, ry, card)
        fade_pct = min(self.peek_reveal['timer'] / 0.5, 1.0)
        border_alpha = int(255 * fade_pct)
        border_surf = pygame.Surface((CARD_WIDTH + 8, CARD_HEIGHT + 8), pygame.SRCALPHA)
        pygame.draw.rect(border_surf, (*POWER_GLOW, border_alpha), border_surf.get_rect(), 3, border_radius=CORNER_RADIUS + 2)
        self.screen.blit(border_surf, (rx - 4, ry - 4))

    # Lookup tables for type-coded log entries. The keyword test runs against
    # the lower-cased log line; the first keyword to match wins. Order matters
    # — declare/penalty come before pair/draw because "declared a pair" should
    # read as a declare event, not a pair event.
    _LOG_KIND_RULES = (
        ("declare",   ("declar", "penalt", "won", "wins", "winner", "lost")),
        ("power",     ("peek", "power", "skipp", "swap power")),
        ("pair",      ("pair", "matched", "paired")),
        ("system",    ("round ", "shuffl", "start", "deal")),
        ("react",     ("dropped", "drop ", "reaction", "called")),
        ("swap",      ("swap", "swapped")),
        ("discard",   ("discard",)),
        ("draw",      ("drew", "draw")),
    )

    def _classify_log_entry(self, text):
        low = text.lower()
        for kind, kws in self._LOG_KIND_RULES:
            if any(kw in low for kw in kws):
                return kind
        return "default"

    def _log_entry_style(self, kind):
        """Returns (bullet_glyph, color) for a classified log kind."""
        th = theme_mod.active()
        return {
            "declare":  ("⚡", th.signal_stop),   # ⚡
            "power":    ("✦", th.peek_blue),     # ✦
            "pair":     ("◆", th.signal_go),     # ◆
            "system":   ("—", th.brass_500),     # —
            "react":    ("◆", th.signal_warn),   # ◆ amber
            "swap":     ("⇄", th.brass_300),     # ⇄
            "discard":  ("◻", th.brass_300),     # ◻
            "draw":     ("♠", th.brass_300),     # ♠
        }.get(kind, ("◆", th.brass_500))

    def draw_game_log(self, log_entries, round_number=None):
        th = theme_mod.active()
        panel_rect = pygame.Rect(LOG_PANEL_X, LOG_PANEL_Y, LOG_PANEL_W, LOG_PANEL_H)

        # Outer brass panel — slightly more opaque than before so the felt
        # doesn't bleed through and wash out the ledger paper inside.
        def _build_log_panel():
            surf = pygame.Surface((LOG_PANEL_W, LOG_PANEL_H), pygame.SRCALPHA)
            for i in range(LOG_PANEL_H):
                t = i / max(1, LOG_PANEL_H - 1)
                r = int(th.brass_900[0] * (0.40 + 0.22 * (1 - t)))
                g = int(th.brass_900[1] * (0.40 + 0.22 * (1 - t)))
                b = int(th.brass_900[2] * (0.40 + 0.22 * (1 - t)))
                pygame.draw.line(surf, (r, g, b, 245), (0, i), (LOG_PANEL_W, i))
            mask = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
            pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=10)
            surf.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
            return surf

        panel_key = ("log_panel", LOG_PANEL_W, LOG_PANEL_H)
        panel_surf = self._cached(panel_key, _build_log_panel)
        self.screen.blit(panel_surf, (LOG_PANEL_X, LOG_PANEL_Y))

        # Aged-paper inner panel — a warm dark tone behind the entries so log
        # text reads as a ledger page rather than a translucent overlay.
        header_font = typo.header_italic(LOG_HEADER_FONT_SIZE)
        # We compute the header height up here so the paper inset can start
        # below the brass-top header strip.
        header_h_est = header_font.get_height()
        paper_inset = 12
        paper_top = LOG_PANEL_Y + header_h_est + 28 + 18  # header + sub line + sep
        paper_rect = pygame.Rect(
            LOG_PANEL_X + paper_inset, paper_top,
            LOG_PANEL_W - paper_inset * 2, LOG_PANEL_Y + LOG_PANEL_H - paper_top - paper_inset,
        )

        def _build_paper(pw, ph):
            surf = pygame.Surface((pw, ph), pygame.SRCALPHA)
            for i in range(ph):
                t = i / max(1, ph - 1)
                r = int(40 + (52 - 40) * (1 - t))
                g = int(32 + (42 - 32) * (1 - t))
                b = int(18 + (26 - 18) * (1 - t))
                pygame.draw.line(surf, (r, g, b, 230), (0, i), (pw, i))
            paper_mask = pygame.Surface((pw, ph), pygame.SRCALPHA)
            pygame.draw.rect(paper_mask, (255, 255, 255, 255), paper_mask.get_rect(), border_radius=6)
            surf.blit(paper_mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
            return surf

        paper_key = ("log_paper", paper_rect.width, paper_rect.height)
        paper = self._cached(paper_key, lambda: _build_paper(paper_rect.width, paper_rect.height))
        self.screen.blit(paper, paper_rect.topleft)
        pygame.draw.rect(self.screen, th.brass_900, paper_rect, 1, border_radius=6)

        # Brass border lines on the outer panel.
        pygame.draw.line(self.screen, th.brass_300,
                         (LOG_PANEL_X + 12, LOG_PANEL_Y + 1),
                         (LOG_PANEL_X + LOG_PANEL_W - 12, LOG_PANEL_Y + 1), 1)
        pygame.draw.line(self.screen, th.brass_500,
                         (LOG_PANEL_X + 12, LOG_PANEL_Y + 2),
                         (LOG_PANEL_X + LOG_PANEL_W - 12, LOG_PANEL_Y + 2), 1)
        pygame.draw.rect(self.screen, th.brass_700, panel_rect, 2, border_radius=10)

        # Header — Playfair Italic for the deco "Game Log" title, plus a
        # subtle Round X subline beneath in Inter so the player can orient.
        header_surf = header_font.render("Game Log", True, th.brass_300)
        header_pos = (LOG_PANEL_X + 22, LOG_PANEL_Y + 10)
        self.screen.blit(header_surf, header_pos)

        if round_number is not None:
            sub_font = typo.body(LOG_SUB_FONT_SIZE)
            sub_surf = sub_font.render(f"ROUND {round_number}", True, th.text_dim)
            sub_pos = (LOG_PANEL_X + 26, header_pos[1] + header_surf.get_height() + 2)
            self.screen.blit(sub_surf, sub_pos)

        ornament = self.small_font.render("❖", True, th.brass_500)
        ornament_x = LOG_PANEL_X + LOG_PANEL_W - 22 - ornament.get_width()
        ornament_y = LOG_PANEL_Y + 10 + (header_surf.get_height() - ornament.get_height()) // 2
        self.screen.blit(ornament, (ornament_x, ornament_y))

        # Header → content separator: thin dark, bright accent.
        sep_y = paper_rect.top - 8
        pygame.draw.line(self.screen, th.brass_700,
                         (LOG_PANEL_X + 18, sep_y),
                         (LOG_PANEL_X + LOG_PANEL_W - 18, sep_y), 1)
        pygame.draw.line(self.screen, th.brass_500,
                         (LOG_PANEL_X + 18, sep_y + 3),
                         (LOG_PANEL_X + LOG_PANEL_W - 18, sep_y + 3), 1)

        content_top = paper_rect.top + 8
        bullet_x = paper_rect.left + 14
        stripe_x = paper_rect.left + 4
        text_x = paper_rect.left + 38
        line_h = 38

        if not log_entries:
            empty_font = typo.body_italic(22)
            empty = empty_font.render("Awaiting the first move...", True, th.text_muted)
            er = empty.get_rect(midtop=(LOG_PANEL_X + LOG_PANEL_W // 2, content_top + 14))
            self.screen.blit(empty, er)
            return

        visible = log_entries[-8:]
        n = len(visible)
        max_text_w = paper_rect.right - text_x - 12

        for i, entry in enumerate(visible):
            text = str(entry.get('text', entry)) if isinstance(entry, dict) else str(entry)
            kind = self._classify_log_entry(text)
            bullet_glyph, kind_color = self._log_entry_style(kind)
            if self.log_font.size(text)[0] > max_text_w:
                while text and self.log_font.size(text + "…")[0] > max_text_w:
                    text = text[:-1]
                text = text + "…"

            age = (n - 1 - i)
            alpha = max(140, 255 - age * 13)
            y = content_top + i * line_h

            # 3 px color stripe on the left margin matching the entry kind.
            stripe = pygame.Surface((3, line_h - 6), pygame.SRCALPHA)
            stripe.fill((*kind_color, alpha))
            self.screen.blit(stripe, (stripe_x, y + 2))

            bullet_surf = self.log_font.render(bullet_glyph, True, kind_color)
            bullet_surf.set_alpha(alpha)
            self.screen.blit(bullet_surf, (bullet_x, y))

            line_surf = self.log_font.render(text, True, th.text_white)
            line_surf.set_alpha(alpha)
            self.screen.blit(line_surf, (text_x, y))

    _ACTION_TOOLTIPS = {
        'declare':       "Declare your hand for victory",
        'draw':          "Draw a card from the deck",
        'swap':          "Trade the drawn card for one of yours",
        'discard':       "Discard the drawn card",
        'pair_own':      "Match the drawn card to one of yours",
        'pair_opponent': "Match the drawn card to an opponent's",
        'self_pair':     "Pair two of your own known cards",
        'shuffle':       "Re-shuffle your face-down cards",
        'play_power':    "Use this card's special power",
        'drop_self':     "Match this rank from your hand",
        'drop_opponent': "Force an opponent to play this rank",
        'pass_reaction': "Skip this reaction window",
    }

    def draw_action_buttons(self, action_buttons):
        th = theme_mod.active()
        focus_key = getattr(self, "_focused_action", None)
        dim_keys = getattr(self, "_dim_actions", set())
        pulse_keys = getattr(self, "_pulse_actions", set())
        keybind_hints = getattr(self, "_action_keybinds", {})

        now_ms = pygame.time.get_ticks()
        # Clear hover-start records for buttons no longer visible.
        for stale in [k for k in self._action_hover_start if k not in action_buttons]:
            del self._action_hover_start[stale]
        # We collect tooltip jobs while iterating and draw them after the loop
        # so the tooltip is never occluded by an adjacent button's plate.
        tooltip_jobs = []

        for name, btn in action_buttons.items():
            rect = btn['rect']
            hovered = rect.collidepoint(pygame.mouse.get_pos())
            focused = (name == focus_key)
            dim = (name in dim_keys)
            pulse = (name in pulse_keys)
            icon_kind = btn.get('icon')
            color = btn.get('hover_color', btn['color']) if (hovered or focused) else btn['color']

            # Hover lift: visually press the button "up" by 2 px, with the shadow
            # staying in place so the eye reads it as physical depth.
            lift = -2 if (hovered or focused) and not dim else 0
            draw_rect = rect.move(0, lift)

            # Drop shadow (anchored to the un-lifted rect so lift creates depth).
            shadow_surf = pygame.Surface((rect.width + 8, rect.height + 12), pygame.SRCALPHA)
            pygame.draw.rect(shadow_surf, (0, 0, 0, 110),
                             (4, 6, rect.width, rect.height), border_radius=12)
            self.screen.blit(shadow_surf, (rect.x - 4, rect.y))

            # Body plate gradient. For disabled buttons we desaturate toward
            # neutral brass so the dim state reads at a glance.
            if dim:
                lum = int(0.30 * color[0] + 0.59 * color[1] + 0.11 * color[2])
                plate_col = (
                    int(lum * 0.55 + th.brass_700[0] * 0.45),
                    int(lum * 0.55 + th.brass_700[1] * 0.45),
                    int(lum * 0.55 + th.brass_700[2] * 0.45),
                )
            else:
                plate_col = color
            plate = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            for i in range(rect.height):
                t = i / max(1, rect.height - 1)
                shade = 0.82 + 0.20 * (1 - abs(t - 0.35) * 2)
                cc = (
                    max(0, min(255, int(plate_col[0] * shade))),
                    max(0, min(255, int(plate_col[1] * shade))),
                    max(0, min(255, int(plate_col[2] * shade))),
                    255,
                )
                pygame.draw.line(plate, cc, (0, i), (rect.width, i))
            mask = pygame.Surface(plate.get_size(), pygame.SRCALPHA)
            pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=12)
            plate.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
            if dim:
                plate.set_alpha(95)
            self.screen.blit(plate, draw_rect)

            # Top highlight + outline.
            pygame.draw.line(self.screen, th.brass_300,
                             (draw_rect.left + 6, draw_rect.top + 2),
                             (draw_rect.right - 6, draw_rect.top + 2), 1)
            pygame.draw.rect(self.screen, th.brass_500, draw_rect, 2, border_radius=12)

            # Icon glyph + label, centered within the full button width.
            # The keyboard-shortcut chip is now drawn *below* the button, so
            # the label gets the entire button width with no right-side reserve.
            label_color = th.text_white if not dim else th.text_dim
            text_surf = self.ui_font.render(btn['text'], True, label_color)
            icon_size = int(rect.height * 0.42)
            icon_gap = 10 if icon_kind else 0
            block_w = (icon_size if icon_kind else 0) + icon_gap + text_surf.get_width()
            block_x = draw_rect.left + max(8, (rect.width - block_w) // 2)
            block_y = draw_rect.centery
            if icon_kind:
                self._draw_button_icon(
                    self.screen, block_x, block_y, icon_size, icon_kind, label_color,
                )
            text_rect = text_surf.get_rect(
                midleft=(block_x + (icon_size + icon_gap if icon_kind else 0), block_y),
            )
            self.screen.blit(text_surf, text_rect)

            # Keyboard-shortcut chip — sits *under* the button, horizontally
            # centered, so the label has full button width to breathe.
            kb = keybind_hints.get(name)
            if kb:
                chip_surf = self.small_font.render(kb.upper(), True, th.brass_900)
                chip_w = chip_surf.get_width() + 12
                chip_h = chip_surf.get_height() + 4
                cx = draw_rect.centerx - chip_w // 2
                cy = draw_rect.bottom + 6
                chip_bg = pygame.Surface((chip_w, chip_h), pygame.SRCALPHA)
                pygame.draw.rect(chip_bg, th.brass_300, chip_bg.get_rect(),
                                 border_radius=chip_h // 2)
                pygame.draw.rect(chip_bg, th.brass_700, chip_bg.get_rect(),
                                 1, border_radius=chip_h // 2)
                self.screen.blit(chip_bg, (cx, cy))
                self.screen.blit(chip_surf, (cx + 6, cy + 2))

            # Recommended-action shimmer (kept from existing code).
            if pulse:
                t = pygame.time.get_ticks() / 1000.0
                pulse_a = int(140 * (0.5 + 0.5 * math.sin(t * 5.0)))
                glow = pygame.Surface((rect.width + 18, rect.height + 18), pygame.SRCALPHA)
                pygame.draw.rect(glow, (*th.brass_300, pulse_a),
                                 glow.get_rect(), 4, border_radius=14)
                self.screen.blit(glow, (rect.x - 9, rect.y - 9 + lift))

            if focused:
                pygame.draw.rect(self.screen, th.brass_300,
                                 draw_rect.inflate(6, 6), 2, border_radius=14)

            # Track hover for tooltips. Tooltip appears 400 ms after the mouse
            # first lands on the button and stays until the mouse leaves.
            tip_text = self._ACTION_TOOLTIPS.get(name)
            if hovered and not dim and tip_text:
                start = self._action_hover_start.get(name)
                if start is None:
                    self._action_hover_start[name] = now_ms
                elif now_ms - start >= 400:
                    tooltip_jobs.append((draw_rect, tip_text))
            else:
                self._action_hover_start.pop(name, None)

        for rect, text in tooltip_jobs:
            self._draw_tooltip(rect, text)

    def _draw_tooltip(self, anchor_rect, text):
        """Brass-trimmed tooltip plate centered above the anchor rect."""
        th = theme_mod.active()
        font = typo.body(20)
        text_surf = font.render(text, True, th.text_white)
        pad_x = 14
        pad_y = 8
        tip_w = text_surf.get_width() + pad_x * 2
        tip_h = text_surf.get_height() + pad_y * 2
        tip_x = anchor_rect.centerx - tip_w // 2
        tip_y = anchor_rect.top - tip_h - 10
        # Keep within the screen.
        tip_x = max(8, min(tip_x, SCREEN_WIDTH - tip_w - 8))

        bg = pygame.Surface((tip_w, tip_h), pygame.SRCALPHA)
        for i in range(tip_h):
            t = i / max(1, tip_h - 1)
            r = int(th.brass_900[0] * (0.38 + 0.20 * (1 - t)))
            g = int(th.brass_900[1] * (0.38 + 0.20 * (1 - t)))
            b = int(th.brass_900[2] * (0.38 + 0.20 * (1 - t)))
            pygame.draw.line(bg, (r, g, b, 245), (0, i), (tip_w, i))
        mask = pygame.Surface((tip_w, tip_h), pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=6)
        bg.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        self.screen.blit(bg, (tip_x, tip_y))
        pygame.draw.rect(self.screen, th.brass_500,
                         pygame.Rect(tip_x, tip_y, tip_w, tip_h), 1, border_radius=6)
        # Small downward triangle pointing at the button.
        tri = [
            (anchor_rect.centerx - 6, tip_y + tip_h - 1),
            (anchor_rect.centerx + 6, tip_y + tip_h - 1),
            (anchor_rect.centerx, tip_y + tip_h + 6),
        ]
        pygame.draw.polygon(self.screen, th.brass_500, tri)
        pygame.draw.polygon(self.screen, th.brass_900, tri, 1)
        self.screen.blit(text_surf, (tip_x + pad_x, tip_y + pad_y))

    def _draw_button_icon(self, surface, x, y, size, kind, color):
        """Procedural glyph drawn inside an action button. `(x, y)` is the
        top-center anchor — the glyph is centered horizontally on x within `size`,
        vertically on y."""
        s = size
        cx = x + s // 2
        cy = y
        col = color
        thick = max(2, s // 10)

        if kind == 'swap':
            # Two crossed arrows — top arrow points right, bottom points left.
            top_y = cy - s // 4
            bot_y = cy + s // 4
            pygame.draw.line(surface, col, (cx - s // 2, top_y),
                             (cx + s // 2, top_y), thick)
            pygame.draw.polygon(surface, col, [
                (cx + s // 2, top_y),
                (cx + s // 2 - s // 5, top_y - s // 6),
                (cx + s // 2 - s // 5, top_y + s // 6),
            ])
            pygame.draw.line(surface, col, (cx - s // 2, bot_y),
                             (cx + s // 2, bot_y), thick)
            pygame.draw.polygon(surface, col, [
                (cx - s // 2, bot_y),
                (cx - s // 2 + s // 5, bot_y - s // 6),
                (cx - s // 2 + s // 5, bot_y + s // 6),
            ])
        elif kind == 'discard':
            # Card outline with a downward arrow inside it.
            r = pygame.Rect(cx - s // 3, cy - s // 2, (s * 2) // 3, s)
            pygame.draw.rect(surface, col, r, thick, border_radius=3)
            pygame.draw.line(surface, col, (cx, cy - s // 4),
                             (cx, cy + s // 4), thick)
            pygame.draw.polygon(surface, col, [
                (cx, cy + s // 3),
                (cx - s // 6, cy + s // 8),
                (cx + s // 6, cy + s // 8),
            ])
        elif kind == 'pair':
            # Two overlapping card rectangles.
            r1 = pygame.Rect(cx - s // 2, cy - s // 3, (s * 2) // 5, (s * 2) // 3)
            r2 = pygame.Rect(cx - s // 12, cy - s // 2, (s * 2) // 5, (s * 2) // 3)
            pygame.draw.rect(surface, col, r1, thick, border_radius=3)
            pygame.draw.rect(surface, col, r2, thick, border_radius=3)
        elif kind == 'declare':
            # Small crown silhouette: 3-peak shape.
            base_y = cy + s // 3
            top_y = cy - s // 3
            pts = [
                (cx - s // 2, base_y),
                (cx - s // 2, cy - s // 6),
                (cx - s // 4, top_y + s // 6),
                (cx - s // 8, cy - s // 6),
                (cx, top_y),
                (cx + s // 8, cy - s // 6),
                (cx + s // 4, top_y + s // 6),
                (cx + s // 2, cy - s // 6),
                (cx + s // 2, base_y),
            ]
            pygame.draw.polygon(surface, col, pts, thick)
            # Crown band dots.
            for px in (cx - s // 4, cx, cx + s // 4):
                pygame.draw.circle(surface, col, (px, base_y - thick), max(1, thick - 1))
        elif kind == 'draw':
            # Card stack with up-arrow above (drawing one off the deck).
            r = pygame.Rect(cx - s // 3, cy - s // 8, (s * 2) // 3, s // 2)
            pygame.draw.rect(surface, col, r, thick, border_radius=3)
            pygame.draw.rect(surface, col,
                             pygame.Rect(cx - s // 3 + 4, cy - s // 8 - 4,
                                         (s * 2) // 3, s // 2),
                             thick, border_radius=3)
            pygame.draw.line(surface, col,
                             (cx, cy - s // 2), (cx, cy - s // 6), thick)
            pygame.draw.polygon(surface, col, [
                (cx, cy - s // 2),
                (cx - s // 6, cy - s // 3),
                (cx + s // 6, cy - s // 3),
            ])
        elif kind == 'shuffle':
            # Two looping arrows — one curving over the other.
            pygame.draw.arc(surface, col,
                            pygame.Rect(cx - s // 2, cy - s // 2, s, s),
                            0.4, 2.6, thick)
            pygame.draw.arc(surface, col,
                            pygame.Rect(cx - s // 2, cy - s // 2 + 2, s, s),
                            3.5, 5.7, thick)
            # Arrowheads.
            pygame.draw.polygon(surface, col, [
                (cx + s // 2 - 2, cy + s // 8),
                (cx + s // 3, cy - s // 12),
                (cx + s // 3, cy + s // 4),
            ])
            pygame.draw.polygon(surface, col, [
                (cx - s // 2 + 2, cy - s // 8),
                (cx - s // 3, cy - s // 4),
                (cx - s // 3, cy + s // 12),
            ])
        elif kind == 'drop':
            # Card with a down arrow + check, signaling 'react and drop'.
            r = pygame.Rect(cx - s // 3, cy - s // 2, (s * 2) // 3, s)
            pygame.draw.rect(surface, col, r, thick, border_radius=3)
            pygame.draw.line(surface, col,
                             (cx - s // 8, cy), (cx, cy + s // 6), thick)
            pygame.draw.line(surface, col,
                             (cx, cy + s // 6), (cx + s // 4, cy - s // 5), thick)
        elif kind == 'pass':
            # An X to signal "no thanks".
            pygame.draw.line(surface, col,
                             (cx - s // 3, cy - s // 3), (cx + s // 3, cy + s // 3), thick)
            pygame.draw.line(surface, col,
                             (cx - s // 3, cy + s // 3), (cx + s // 3, cy - s // 3), thick)
        elif kind == 'power':
            # Lightning bolt — generic power glyph.
            pygame.draw.polygon(surface, col, [
                (cx - s // 6, cy - s // 2),
                (cx + s // 4, cy - s // 8),
                (cx, cy - s // 12),
                (cx + s // 6, cy + s // 2),
                (cx - s // 4, cy + s // 8),
                (cx, cy + s // 12),
            ])

    def _draw_cancel_button(self, cancel_button, mouse_pos):
        rect = cancel_button['rect']
        hovered = rect.collidepoint(mouse_pos)
        color = CANCEL_GRAY_HOVER if hovered else CANCEL_GRAY

        shadow_surf = pygame.Surface((rect.width + 4, rect.height + 4), pygame.SRCALPHA)
        pygame.draw.rect(shadow_surf, (0, 0, 0, 60), (2, 3, rect.width, rect.height), border_radius=8)
        self.screen.blit(shadow_surf, (rect.x - 2, rect.y + 2))

        self._draw_rounded_rect(self.screen, color, rect, 8)

        c_r = max(color[0] - 30, 0)
        c_g = max(color[1] - 30, 0)
        c_b = max(color[2] - 30, 0)
        pygame.draw.line(self.screen, (c_r, c_g, c_b),
                        (rect.left + 3, rect.bottom - 3), (rect.right - 3, rect.bottom - 3), 2)
        pygame.draw.line(self.screen, (c_r, c_g, c_b),
                        (rect.right - 3, rect.top + 3), (rect.right - 3, rect.bottom - 3), 2)

        l_r = min(color[0] + 40, 255)
        l_g = min(color[1] + 40, 255)
        l_b = min(color[2] + 40, 255)
        pygame.draw.line(self.screen, (l_r, l_g, l_b),
                        (rect.left + 3, rect.top + 3), (rect.right - 3, rect.top + 3), 2)
        pygame.draw.line(self.screen, (l_r, l_g, l_b),
                        (rect.left + 3, rect.top + 3), (rect.left + 3, rect.bottom - 3), 2)
        pygame.draw.rect(self.screen, TEXT_WHITE, rect, 1, border_radius=8)
        text_surf = self.ui_font.render(cancel_button.get('text', 'Cancel'), True, TEXT_WHITE)
        text_rect = text_surf.get_rect(center=rect.center)
        self.screen.blit(text_surf, text_rect)

    def _draw_reaction_banner(self, game_manager, screen):
        """Draw the reaction window banner when active."""
        if game_manager.state != GameState.REACTION_WINDOW:
            return
        if not game_manager.reaction_pending:
            return

        rank = game_manager.reaction_rank or "?"
        timer = max(0, game_manager.reaction_timer)

        scale = get_mobile_scale()
        banner_h = int(70 * scale)
        banner_w = min(600, SCREEN_WIDTH - 40)
        banner_y = SCREEN_HEIGHT // 2 - banner_h // 2
        banner_x = SCREEN_WIDTH // 2
        banner_rect = pygame.Rect(banner_x - banner_w // 2, banner_y, banner_w, banner_h)

        pulse = abs(math.sin(pygame.time.get_ticks() * 0.005)) * 0.3 + 0.7
        glow_color = (*GOLD, int(200 * pulse))

        glow_surf = pygame.Surface((banner_w + 20, banner_h + 20), pygame.SRCALPHA)
        pygame.draw.rect(glow_surf, glow_color, glow_surf.get_rect(), border_radius=12)
        screen.blit(glow_surf, (banner_x - banner_w // 2 - 10, banner_y - 10))

        pygame.draw.rect(screen, (30, 80, 40), banner_rect, border_radius=10)
        pygame.draw.rect(screen, GOLD, banner_rect, 2, border_radius=10)

        title_font = typo.display_bold(int(28 * scale))
        body_font = typo.body(int(20 * scale))

        title_surf = title_font.render(f"REACT! {rank} was played!", True, GOLD)
        timer_surf = body_font.render(f"{timer:.1f}s remaining", True, TEXT_WHITE)

        screen.blit(title_surf, (banner_rect.centerx - title_surf.get_width() // 2, banner_rect.y + int(12 * scale)))
        screen.blit(timer_surf, (banner_rect.centerx - timer_surf.get_width() // 2, banner_rect.y + int(42 * scale)))

        bar_width = banner_w - 40
        bar_x = banner_rect.x + 20
        bar_y = banner_rect.y + banner_h - int(15 * scale)
        remaining = timer / game_manager.settings.reaction_window_seconds
        pygame.draw.rect(screen, (60, 60, 60), (bar_x, bar_y, bar_width, max(4, int(6 * scale))), border_radius=3)
        pygame.draw.rect(screen, GOLD, (bar_x, bar_y, int(bar_width * remaining), max(4, int(6 * scale))), border_radius=3)

    def draw_reaction_result(self, notification_text: str, screen) -> None:
        """Flash a notification for reaction results (wrong card penalty, etc)."""
        if not notification_text:
            return
        
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        screen.blit(overlay, (0, 0))

        box_w = min(800, SCREEN_WIDTH - 80)
        box_h = min(160, int(SCREEN_HEIGHT * 0.11))
        box_rect = pygame.Rect(SCREEN_WIDTH // 2 - box_w // 2, SCREEN_HEIGHT // 2 - box_h // 2, box_w, box_h)
        pygame.draw.rect(screen, (50, 10, 10), box_rect, border_radius=12)
        pygame.draw.rect(screen, (200, 50, 50), box_rect, 2, border_radius=12)

        scale = get_mobile_scale()
        font = typo.display_bold(int(30 * scale))
        text_surf = font.render(notification_text, True, (255, 80, 80))
        screen.blit(text_surf, (box_rect.centerx - text_surf.get_width() // 2, box_rect.centery - text_surf.get_height() // 2))

    def draw_status_message(self, message):
        if not message:
            return
        msg_surf = self.ui_font.render(message, True, GOLD)
        msg_rect = msg_surf.get_rect(center=(SCREEN_WIDTH // 2, ACTION_BAR_Y - 20))
        bg_rect = msg_rect.inflate(24, 12)
        bg_surf = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
        pygame.draw.rect(bg_surf, (0, 0, 0, 160), bg_surf.get_rect(), border_radius=6)
        self.screen.blit(bg_surf, bg_rect.topleft)
        self.screen.blit(msg_surf, msg_rect)

    def get_card_rects(self, player_index, game_manager):
        player = game_manager.players[player_index]
        num_players = len(game_manager.players)
        pos = _get_seat_position(player.seat_index, num_players)
        card_positions = self._compute_card_positions(player, pos, game_manager)
        rects = []
        for slot_index in range(player.hand_size):
            if slot_index < len(card_positions):
                cx, cy = card_positions[slot_index]
                rects.append(pygame.Rect(cx, cy, CARD_WIDTH, CARD_HEIGHT))
            else:
                rects.append(pygame.Rect(0, 0, CARD_WIDTH, CARD_HEIGHT))
        return rects

    def get_card_center(self, player_index, slot_index, game_manager):
        rects = self.get_card_rects(player_index, game_manager)
        if slot_index < len(rects):
            r = rects[slot_index]
            return (r.centerx, r.centery)
        return (0, 0)

    def get_deck_rect(self):
        cx, cy = DECK_CENTER
        return pygame.Rect(cx - CARD_WIDTH // 2, cy - CARD_HEIGHT // 2, CARD_WIDTH, CARD_HEIGHT)

    def update(self, dt):
        self._pulse_time += dt
        if self.peek_reveal is not None:
            self.peek_reveal['timer'] -= dt
            if self.peek_reveal['timer'] <= 0:
                self.peek_reveal = None
        self.animation_queue.update(dt)

    def set_peek_reveal(self, card, x, y, duration):
        self.peek_reveal = {'card': card, 'x': x, 'y': y, 'timer': duration}

    def is_animating(self):
        return self.animation_queue.is_animating()

    def set_game_settings(self, settings):
        self.game_settings = settings

    def effective_anim_duration(self, base_duration):
        if self.game_settings and not self.game_settings.animations_enabled:
            return 0.01
        return base_duration

    def push_draw_animation(self, game_manager):
        deck_cx, deck_cy = DECK_CENTER
        drawn_cx, drawn_cy = DRAWN_CARD_POS
        event = VisualEvent(
            VisualEventType.CARD_SLIDE,
            start_pos=(deck_cx, deck_cy),
            end_pos=(drawn_cx, drawn_cy),
            card=game_manager.drawn_card,
            duration=self.effective_anim_duration(ANIM_DRAW_DURATION),
            start_face_up=True,
        )
        self.animation_queue.add(event)

    def push_swap_animation(self, game_manager, slot_index, swapped_card):
        drawn_cx, drawn_cy = DRAWN_CARD_POS
        human_idx = None
        for i, p in enumerate(game_manager.players):
            if p.is_human:
                human_idx = i
                break
        if human_idx is None:
            return
        slot_center = self.get_card_center(human_idx, slot_index, game_manager)
        discard_cx, discard_cy = DISCARD_POS
        slide_to_slot = VisualEvent(
            VisualEventType.CARD_SLIDE,
            start_pos=(drawn_cx, drawn_cy),
            end_pos=slot_center,
            card=game_manager.drawn_card,
            duration=self.effective_anim_duration(ANIM_SWAP_DURATION),
            start_face_up=True,
        )
        fade_to_discard = VisualEvent(
            VisualEventType.CARD_FADE_OUT,
            start_pos=slot_center,
            end_pos=(discard_cx, discard_cy),
            card=swapped_card,
            duration=self.effective_anim_duration(ANIM_SWAP_DURATION),
            start_face_up=True,
            start_scale=1.0,
            end_scale=0.6,
        )
        self.animation_queue.add(slide_to_slot)
        self.animation_queue.add(fade_to_discard)

    def push_unseen_swap_animation(self, game_manager, my_slot, target_player_idx, their_slot):
        human_idx = None
        for i, p in enumerate(game_manager.players):
            if p.is_human:
                human_idx = i
                break
        if human_idx is None:
            return
        my_center = self.get_card_center(human_idx, my_slot, game_manager)
        their_center = self.get_card_center(target_player_idx, their_slot, game_manager)
        my_card = game_manager.players[human_idx].hand[my_slot]
        their_card = game_manager.players[target_player_idx].hand[their_slot]
        arc_my = VisualEvent(
            VisualEventType.CARD_ARC,
            start_pos=my_center,
            end_pos=their_center,
            card=my_card,
            duration=self.effective_anim_duration(ANIM_UNSEEN_SWAP_DURATION),
            arc_height=80,
            start_face_up=False,
        )
        arc_their = VisualEvent(
            VisualEventType.CARD_ARC,
            start_pos=their_center,
            end_pos=my_center,
            card=their_card,
            duration=self.effective_anim_duration(ANIM_UNSEEN_SWAP_DURATION),
            arc_height=80,
            start_face_up=False,
        )
        flash = VisualEvent(
            VisualEventType.SCREEN_FLASH,
            start_pos=(0, 0),
            end_pos=(0, 0),
            duration=self.effective_anim_duration(ANIM_FLASH_DURATION),
            text_color=SWAP_GREEN,
        )
        self.animation_queue.add(flash)
        self.animation_queue.add(arc_my)
        self.animation_queue.add(arc_their)

    def push_seen_swap_animation(self, game_manager, my_slot, target_player_idx, their_slot, card_received):
        human_idx = None
        for i, p in enumerate(game_manager.players):
            if p.is_human:
                human_idx = i
                break
        if human_idx is None:
            return
        my_center = self.get_card_center(human_idx, my_slot, game_manager)
        their_center = self.get_card_center(target_player_idx, their_slot, game_manager)
        my_card = game_manager.players[human_idx].hand[my_slot]
        arc_my = VisualEvent(
            VisualEventType.CARD_ARC,
            start_pos=my_center,
            end_pos=their_center,
            card=my_card,
            duration=self.effective_anim_duration(ANIM_SEEN_SWAP_DURATION),
            arc_height=80,
            start_face_up=False,
        )
        arc_their = VisualEvent(
            VisualEventType.CARD_FLIP_ARC,
            start_pos=their_center,
            end_pos=my_center,
            card=card_received,
            duration=self.effective_anim_duration(ANIM_SEEN_SWAP_DURATION),
            arc_height=80,
            flip_at_peak=True,
            start_face_up=False,
            face_up_at_end=False,
        )
        flash = VisualEvent(
            VisualEventType.SCREEN_FLASH,
            start_pos=(0, 0),
            end_pos=(0, 0),
            duration=self.effective_anim_duration(ANIM_FLASH_DURATION),
            text_color=SWAP_GREEN,
        )
        self.animation_queue.add(flash)
        self.animation_queue.add(arc_my)
        self.animation_queue.add(arc_their)
        note_y = (my_center[1] + their_center[1]) / 2 - 60
        note_x = (my_center[0] + their_center[0]) / 2
        notif = VisualEvent(
            VisualEventType.NOTIFICATION_TEXT,
            start_pos=(note_x, note_y),
            end_pos=(note_x, note_y),
            duration=self.effective_anim_duration(ANIM_NOTIFICATION_DURATION),
            text=f"Received: {card_received.display_name}",
            text_color=GOLD,
        )
        self.animation_queue.add(notif)

    def push_discard_animation(self, game_manager):
        drawn_cx, drawn_cy = DRAWN_CARD_POS
        discard_cx, discard_cy = DISCARD_POS
        event = VisualEvent(
            VisualEventType.CARD_SLIDE,
            start_pos=(drawn_cx, drawn_cy),
            end_pos=(discard_cx, discard_cy),
            card=game_manager.drawn_card,
            duration=self.effective_anim_duration(ANIM_DISCARD_DURATION),
            start_face_up=True,
        )
        self.animation_queue.add(event)

    def push_peek_lift_animation(self, game_manager, target_pos):
        event = VisualEvent(
            VisualEventType.CARD_LIFT,
            start_pos=target_pos,
            end_pos=(target_pos[0], target_pos[1] - 15),
            duration=self.effective_anim_duration(ANIM_PEEK_LIFT_DURATION),
            start_face_up=False,
        )
        self.animation_queue.add(event)

    def push_pair_fly_animation(self, game_manager, pos1, card1, pos2=None, card2=None):
        discard_cx, discard_cy = DISCARD_POS
        fly1 = VisualEvent(
            VisualEventType.CARD_FADE_OUT,
            start_pos=pos1,
            end_pos=(discard_cx, discard_cy),
            card=card1,
            duration=self.effective_anim_duration(ANIM_PAIR_FLY_DURATION),
            start_face_up=True,
            start_scale=1.0,
            end_scale=0.5,
        )
        self.animation_queue.add(fly1)
        if pos2 is not None and card2 is not None:
            fly2 = VisualEvent(
                VisualEventType.CARD_FADE_OUT,
                start_pos=pos2,
                end_pos=(discard_cx + 30, discard_cy),
                card=card2,
                duration=self.effective_anim_duration(ANIM_PAIR_FLY_DURATION),
                start_face_up=True,
                start_scale=1.0,
                end_scale=0.5,
            )
            self.animation_queue.add(fly2)
        flash = VisualEvent(
            VisualEventType.SCREEN_FLASH,
            start_pos=(0, 0),
            end_pos=(0, 0),
            duration=self.effective_anim_duration(ANIM_FLASH_DURATION),
            text_color=PAIR_TEAL,
        )
        self.animation_queue.add(flash)

    def push_ai_peek_animation(self, player_idx, slot_idx, game_manager):
        center = self.get_card_center(player_idx, slot_idx, game_manager)
        lift = VisualEvent(
            VisualEventType.CARD_LIFT,
            start_pos=center,
            end_pos=(center[0], center[1] - 15),
            duration=self.effective_anim_duration(ANIM_PEEK_LIFT_DURATION),
            start_face_up=False,
        )
        pos = _get_seat_position(game_manager.players[player_idx].seat_index, len(game_manager.players))
        notif = VisualEvent(
            VisualEventType.NOTIFICATION_TEXT,
            start_pos=(pos[0], pos[1] - 60),
            end_pos=(pos[0], pos[1] - 60),
            duration=self.effective_anim_duration(ANIM_NOTIFICATION_DURATION),
            text=f"{game_manager.players[player_idx].name} peeked!",
            text_color=PEEK_BLUE,
        )
        self.animation_queue.add(lift)
        self.animation_queue.add(notif)

    def push_ai_swap_animation(self, game_manager, target_player_idx, their_slot):
        their_center = self.get_card_center(target_player_idx, their_slot, game_manager)
        discard_cx, discard_cy = DISCARD_POS
        fade_to_discard = VisualEvent(
            VisualEventType.CARD_FADE_OUT,
            start_pos=their_center,
            end_pos=(discard_cx, discard_cy),
            duration=self.effective_anim_duration(ANIM_SWAP_DURATION),
            start_face_up=False,
            start_scale=1.0,
            end_scale=0.6,
        )
        self.animation_queue.add(fade_to_discard)

    def push_ai_skip_animation(self, game_manager, player_idx):
        pos = _get_seat_position(game_manager.players[player_idx].seat_index, len(game_manager.players))
        notif = VisualEvent(
            VisualEventType.NOTIFICATION_TEXT,
            start_pos=(pos[0], pos[1] - 60),
            end_pos=(pos[0], pos[1] - 60),
            duration=self.effective_anim_duration(ANIM_NOTIFICATION_DURATION),
            text="Skip next player!",
            text_color=DECLARE_RED,
        )
        flash = VisualEvent(
            VisualEventType.SCREEN_FLASH,
            start_pos=(0, 0),
            end_pos=(0, 0),
            duration=self.effective_anim_duration(ANIM_FLASH_DURATION),
            text_color=GOLD,
        )
        self.animation_queue.add(flash)
        self.animation_queue.add(notif)

    def push_ai_pair_animation(self, game_manager, pos1, pos2=None):
        discard_cx, discard_cy = DISCARD_POS
        fly1 = VisualEvent(
            VisualEventType.CARD_FADE_OUT,
            start_pos=pos1,
            end_pos=(discard_cx, discard_cy),
            duration=self.effective_anim_duration(ANIM_PAIR_FLY_DURATION),
            start_face_up=False,
            start_scale=1.0,
            end_scale=0.5,
        )
        self.animation_queue.add(fly1)
        if pos2 is not None:
            fly2 = VisualEvent(
                VisualEventType.CARD_FADE_OUT,
                start_pos=pos2,
                end_pos=(discard_cx + 30, discard_cy),
                duration=self.effective_anim_duration(ANIM_PAIR_FLY_DURATION),
                start_face_up=False,
                start_scale=1.0,
                end_scale=0.5,
            )
            self.animation_queue.add(fly2)
        flash = VisualEvent(
            VisualEventType.SCREEN_FLASH,
            start_pos=(0, 0),
            end_pos=(0, 0),
            duration=self.effective_anim_duration(ANIM_FLASH_DURATION),
            text_color=PAIR_TEAL,
        )
        self.animation_queue.add(flash)

    def _draw_rounded_rect(self, surface, color, rect, radius):
        pygame.draw.rect(surface, color, rect, border_radius=radius)

    def _draw_dashed_rect(self, surface, color, rect, radius=0):
        dash_len = 8
        gap_len = 6
        points = [
            (rect.left, rect.top), (rect.right, rect.top),
            (rect.right, rect.bottom), (rect.left, rect.bottom)
        ]
        for i in range(4):
            start = points[i]
            end = points[(i + 1) % 4]
            dx = end[0] - start[0]
            dy = end[1] - start[1]
            length = math.sqrt(dx * dx + dy * dy)
            if length == 0:
                continue
            ux = dx / length
            uy = dy / length
            pos = 0
            drawing = True
            while pos < length:
                seg = dash_len if drawing else gap_len
                seg = min(seg, length - pos)
                if drawing:
                    sx = int(start[0] + ux * pos)
                    sy = int(start[1] + uy * pos)
                    ex = int(start[0] + ux * (pos + seg))
                    ey = int(start[1] + uy * (pos + seg))
                    pygame.draw.line(surface, color, (sx, sy), (ex, ey), 1)
                pos += seg
                drawing = not drawing

    def _draw_shadow(self, x, y):
        shadow_surf = pygame.Surface((CARD_WIDTH + 8, CARD_HEIGHT + 8), pygame.SRCALPHA)
        pygame.draw.rect(shadow_surf, (0, 0, 0, 20), (6, 8, CARD_WIDTH, CARD_HEIGHT), border_radius=CORNER_RADIUS)
        pygame.draw.rect(shadow_surf, (0, 0, 0, 35), (4, 5, CARD_WIDTH, CARD_HEIGHT), border_radius=CORNER_RADIUS)
        pygame.draw.rect(shadow_surf, (0, 0, 0, 50), (2, 3, CARD_WIDTH, CARD_HEIGHT), border_radius=CORNER_RADIUS)
        pygame.draw.rect(shadow_surf, (0, 0, 0, 70), (0, 0, CARD_WIDTH, CARD_HEIGHT), border_radius=CORNER_RADIUS)
        self.screen.blit(shadow_surf, (x - 4, y - 2))

    def draw_gear_icon(self, mouse_pos, settings_open=False):
        self._draw_hud_buttons(mouse_pos)

    def _hud_size(self):
        scale = get_mobile_scale()
        return int(44 * scale), int(42 * scale)

    def get_menu_rect(self):
        """Single consolidated menu button replacing gear/pause/quit trio."""
        w, h = self._hud_size()
        return pygame.Rect(SCREEN_WIDTH - w - 12, ACTION_BAR_Y + 16, w, h)

    # Legacy rect accessors for backward compat during transition.
    def get_gear_rect(self):
        return self.get_menu_rect()

    def get_pause_rect(self):
        return self.get_menu_rect()

    def get_quit_rect(self):
        return self.get_menu_rect()

    def _draw_hud_buttons(self, mouse_pos):
        th = theme_mod.active()
        scale = get_mobile_scale()
        rect = self.get_menu_rect()
        hovered = rect.collidepoint(mouse_pos)
        pygame.draw.rect(self.screen, (60, 60, 60) if not hovered else (90, 90, 90),
                         rect, border_radius=8)
        pygame.draw.rect(self.screen, th.brass_500, rect, 1, border_radius=8)
        cx, cy = rect.center
        color = th.brass_300 if hovered else th.brass_300

        # Hamburger icon: three horizontal lines.
        line_w = int(16 * scale)
        line_h = max(2, int(2 * scale))
        gap = int(5 * scale)
        for i in range(3):
            ly = cy - gap + i * gap
            pygame.draw.line(self.screen, color,
                             (cx - line_w // 2, ly), (cx + line_w // 2, ly), line_h)
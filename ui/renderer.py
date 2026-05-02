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
        self.small_font = typo.body(SMALL_FONT_SIZE)
        self.hovered_card = None
        self.hovered_button = None
        self.hovered_slot = None
        self.peek_reveal = None
        self._pulse_time = 0.0
        self.animation_queue = AnimationQueue()
        self.dragging_card = None
        self.drag_pos = None
        self.game_settings = None

    def draw(self, game_manager, mouse_pos=(0, 0), action_buttons=None,
             cancel_button=None, status_message="", awaiting_target=None):
        self.screen.fill(BG_GREEN)
        self._draw_table_felt()
        self._draw_status_bar(game_manager)
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
                self.draw_game_log(game_manager.game_log)
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
        container_surf = pygame.Surface((container_rect.width, container_rect.height), pygame.SRCALPHA)
        for i in range(container_rect.height):
            t = i / max(1, container_rect.height - 1)
            r = int(th.brass_900[0] * (0.40 + 0.30 * t))
            g = int(th.brass_900[1] * (0.40 + 0.30 * t))
            b = int(th.brass_900[2] * (0.40 + 0.30 * t))
            pygame.draw.line(container_surf, (r, g, b, 230), (0, i), (container_rect.width, i))
        mask = pygame.Surface(container_surf.get_size(), pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=10)
        container_surf.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        self.screen.blit(container_surf, container_rect.topleft)
        pygame.draw.line(self.screen, th.brass_500,
                         (0, container_rect.top + 1),
                         (SCREEN_WIDTH, container_rect.top + 1), 1)
        pygame.draw.rect(self.screen, th.brass_700, container_rect, 1, border_radius=10)

    def _draw_table_felt(self):
        th = theme_mod.active()
        if not hasattr(self, "_felt_cache") or self._felt_theme_key != th.name:
            self._felt_cache = self._build_felt_cache()
            self._felt_theme_key = th.name
        self.screen.blit(self._felt_cache, (0, 0))

    def _build_felt_cache(self):
        import random as _r
        th = theme_mod.active()
        out = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        out.fill(th.felt_rim)

        center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
        rx, ry = 1120, 608

        radial = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        for layer in range(40, 0, -1):
            t = layer / 40
            r = (
                int(th.felt_rim[0] + (th.felt_mid[0] - th.felt_rim[0]) * (1 - t)),
                int(th.felt_rim[1] + (th.felt_mid[1] - th.felt_rim[1]) * (1 - t)),
                int(th.felt_rim[2] + (th.felt_mid[2] - th.felt_rim[2]) * (1 - t)),
            )
            pygame.draw.ellipse(radial, r,
                                pygame.Rect(center[0] - int(rx * t), center[1] - int(ry * t),
                                            int(rx * t * 2), int(ry * t * 2)))
        out.blit(radial, (0, 0), special_flags=pygame.BLEND_RGBA_MAX)

        rng = _r.Random(42)
        wear = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        for _ in range(900):
            px = rng.randint(0, SCREEN_WIDTH)
            py = rng.randint(0, SCREEN_HEIGHT)
            dx = (px - center[0]) / rx
            dy = (py - center[1]) / ry
            if dx * dx + dy * dy > 1:
                continue
            a = rng.randint(6, 18)
            sz = rng.choice((1, 1, 1, 2))
            tone = rng.randint(-12, 12)
            cc = (max(0, min(255, th.felt_mid[0] + tone)),
                  max(0, min(255, th.felt_mid[1] + tone)),
                  max(0, min(255, th.felt_mid[2] + tone)), a)
            pygame.draw.circle(wear, cc, (px, py), sz)
        out.blit(wear, (0, 0))

        for i in range(8):
            t = i / 8
            inset = int(80 * t)
            pygame.draw.ellipse(out, (*th.felt_rim, ),
                                pygame.Rect(center[0] - rx - inset, center[1] - ry - inset,
                                            (rx + inset) * 2, (ry + inset) * 2),
                                1)

        pygame.draw.ellipse(out, th.brass_700,
                            pygame.Rect(center[0] - rx, center[1] - ry, rx * 2, ry * 2), 2)
        pygame.draw.ellipse(out, th.brass_500,
                            pygame.Rect(center[0] - rx - 4, center[1] - ry - 4,
                                        rx * 2 + 8, ry * 2 + 8), 1)

        for ring in (rx + 12, rx + 18):
            pygame.draw.ellipse(out, (*th.brass_900, ),
                                pygame.Rect(center[0] - ring, center[1] - int(ry * ring / rx),
                                            ring * 2, int(ry * ring / rx) * 2), 1)

        seal_font = typo.display_bold(30)
        seal = seal_font.render("D", True, (*th.brass_900, ))
        seal.set_alpha(40)
        out.blit(seal, seal.get_rect(center=center))

        return out

    def _draw_status_bar(self, game_manager):
        th = theme_mod.active()
        bar_rect = pygame.Rect(0, 0, SCREEN_WIDTH, STATUS_BAR_H)
        plate = pygame.Surface((SCREEN_WIDTH, STATUS_BAR_H))
        for i in range(STATUS_BAR_H):
            t = i / max(1, STATUS_BAR_H - 1)
            r = int(th.brass_900[0] + (th.brass_700[0] - th.brass_900[0]) * (1 - abs(t - 0.5) * 2))
            g = int(th.brass_900[1] + (th.brass_700[1] - th.brass_900[1]) * (1 - abs(t - 0.5) * 2))
            b = int(th.brass_900[2] + (th.brass_700[2] - th.brass_900[2]) * (1 - abs(t - 0.5) * 2))
            pygame.draw.line(plate, (r, g, b), (0, i), (SCREEN_WIDTH, i))
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

        round_surf = self.ui_font.render(f"Round {game_manager.round_number}", True, th.text_white)
        text_x = avatar_rect.right + 16
        self.screen.blit(round_surf, (text_x, (STATUS_BAR_H - round_surf.get_height()) // 2))

        name_surf = self.ui_font.render(current_player.name, True, th.brass_300)
        name_x = text_x + round_surf.get_width() + 20
        self.screen.blit(name_surf, (name_x, (STATUS_BAR_H - name_surf.get_height()) // 2))

        chip_text = state_label.upper()
        chip_surf = self.small_font.render(chip_text, True, th.brass_900)
        chip_w = chip_surf.get_width() + 20
        chip_h = STATUS_BAR_H - 14
        chip_x = SCREEN_WIDTH - chip_w - 14
        chip_y = (STATUS_BAR_H - chip_h) // 2
        chip_bg = pygame.Surface((chip_w, chip_h), pygame.SRCALPHA)
        pygame.draw.rect(chip_bg, th.brass_300, chip_bg.get_rect(), border_radius=chip_h // 2)
        pygame.draw.rect(chip_bg, th.brass_500, chip_bg.get_rect(), 1, border_radius=chip_h // 2)
        self.screen.blit(chip_bg, (chip_x, chip_y))
        self.screen.blit(chip_surf, (chip_x + 10, chip_y + (chip_h - chip_surf.get_height()) // 2))

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

        if hovered:
            t = pygame.time.get_ticks() / 1000.0
            shimmer = card_render.paint_back_glow(style, CARD_WIDTH, CARD_HEIGHT, t)
            self.screen.blit(shimmer, (x, y + lift_y), special_flags=pygame.BLEND_RGBA_ADD)

        if has_known_marker:
            badge_x = x + CARD_WIDTH - 14
            badge_y = y + 4 + lift_y
            pygame.draw.circle(self.screen, GOLD, (badge_x, badge_y + 5), 7)
            pygame.draw.circle(self.screen, (255, 230, 80), (badge_x, badge_y + 5), 5)
            tri_pts = [(badge_x - 3, badge_y + 8), (badge_x + 3, badge_y + 8),
                       (badge_x, badge_y + 13)]
            pygame.draw.polygon(self.screen, (200, 160, 0), tri_pts)

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
            count_surf = self.small_font.render(str(remaining), True, TEXT_WHITE)
            count_rect = count_surf.get_rect(center=(cx, cy + CARD_HEIGHT // 2 + 14))
            self.screen.blit(count_surf, count_rect)
        else:
            self.draw_empty_slot(dx, dy)
            empty_surf = self.small_font.render("Empty", True, DIM)
            empty_rect = empty_surf.get_rect(center=(cx, cy))
            self.screen.blit(empty_surf, empty_rect)

    def draw_discard(self, discard_pile):
        if not discard_pile:
            return
        cx, cy = DISCARD_POS
        dx = cx - CARD_WIDTH // 2
        dy = cy - CARD_HEIGHT // 2
        top_card = discard_pile[-1]
        top_card.face_up = True
        self.draw_card_face(dx, dy, top_card)
        label_surf = self.small_font.render("Discard", True, TEXT_DIM)
        label_rect = label_surf.get_rect(center=(cx, cy + CARD_HEIGHT // 2 + 14))
        self.screen.blit(label_surf, label_rect)

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

        name_color = GOLD if is_current else TEXT_WHITE
        raw_name_y = card_positions[0][1] - CARD_HEIGHT // 2 - 80 if card_positions else py - 112
        _, y_min, _, y_max = bounds
        name_y = max(y_min + 32, min(raw_name_y, y_max - CARD_HEIGHT - 96))
        name_surf = self.ui_font.render(player.name, True, name_color)
        name_rect = name_surf.get_rect(center=(px, name_y))
        if is_current:
            alpha = int(80 + 40 * math.sin(self._pulse_time * 3))
            glow_rect = name_rect.inflate(38, 19)
            glow_surf = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
            pygame.draw.rect(glow_surf, (*GOLD, alpha), glow_surf.get_rect(), border_radius=8)
            self.screen.blit(glow_surf, glow_rect.topleft)
        pill_surf = pygame.Surface((name_rect.width + 32, name_rect.height + 16), pygame.SRCALPHA)
        pygame.draw.rect(pill_surf, (*BG_DARK, 180), pill_surf.get_rect(), border_radius=8)
        self.screen.blit(pill_surf, (name_rect.centerx - name_rect.width // 2 - 26, name_rect.centery - name_rect.height // 2 - 13))
        self.screen.blit(name_surf, name_rect)
        info_y = name_y + name_surf.get_height() + 6
        if is_human:
            info_text = f"Cards: {player.card_count}"
        else:
            info_text = f"Cards: {player.card_count}"
        info_surf = self.small_font.render(info_text, True, TEXT_DIM)
        info_rect = info_surf.get_rect(center=(px, info_y))
        self.screen.blit(info_surf, info_rect)

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
        label_surf = self.small_font.render("DREW", True, GOLD)
        label_rect = label_surf.get_rect(center=(cx, dy - 12))
        self.screen.blit(label_surf, label_rect)
        rect = self.draw_card_face(dx, dy, card, show_power_label=True, show_pips=False)
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

    def draw_game_log(self, log_entries):
        th = theme_mod.active()
        panel_rect = pygame.Rect(LOG_PANEL_X, LOG_PANEL_Y, LOG_PANEL_W, LOG_PANEL_H)

        panel_surf = pygame.Surface((LOG_PANEL_W, LOG_PANEL_H), pygame.SRCALPHA)
        for i in range(LOG_PANEL_H):
            t = i / max(1, LOG_PANEL_H - 1)
            r = int(th.brass_900[0] * (0.34 + 0.18 * (1 - t)))
            g = int(th.brass_900[1] * (0.34 + 0.18 * (1 - t)))
            b = int(th.brass_900[2] * (0.34 + 0.18 * (1 - t)))
            pygame.draw.line(panel_surf, (r, g, b, 232), (0, i), (LOG_PANEL_W, i))
        mask = pygame.Surface(panel_surf.get_size(), pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=10)
        panel_surf.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        self.screen.blit(panel_surf, (LOG_PANEL_X, LOG_PANEL_Y))

        pygame.draw.line(self.screen, th.brass_300,
                         (LOG_PANEL_X + 12, LOG_PANEL_Y + 1),
                         (LOG_PANEL_X + LOG_PANEL_W - 12, LOG_PANEL_Y + 1), 1)
        pygame.draw.line(self.screen, th.brass_500,
                         (LOG_PANEL_X + 12, LOG_PANEL_Y + 2),
                         (LOG_PANEL_X + LOG_PANEL_W - 12, LOG_PANEL_Y + 2), 1)
        pygame.draw.rect(self.screen, th.brass_700, panel_rect, 2, border_radius=10)

        header_font = typo.header_italic(34)
        header_surf = header_font.render("Game Log", True, th.brass_300)
        header_pos = (LOG_PANEL_X + 22, LOG_PANEL_Y + 10)
        self.screen.blit(header_surf, header_pos)

        ornament = self.small_font.render("❖", True, th.brass_500)
        ornament_x = LOG_PANEL_X + LOG_PANEL_W - 22 - ornament.get_width()
        ornament_y = LOG_PANEL_Y + 10 + (header_surf.get_height() - ornament.get_height()) // 2
        self.screen.blit(ornament, (ornament_x, ornament_y))

        sep_y = LOG_PANEL_Y + header_surf.get_height() + 18
        pygame.draw.line(self.screen, th.brass_700,
                         (LOG_PANEL_X + 18, sep_y),
                         (LOG_PANEL_X + LOG_PANEL_W - 18, sep_y), 1)
        pygame.draw.line(self.screen, th.brass_500,
                         (LOG_PANEL_X + 18, sep_y + 3),
                         (LOG_PANEL_X + LOG_PANEL_W - 18, sep_y + 3), 1)

        content_top = sep_y + 14

        if not log_entries:
            empty_font = typo.body_italic(22)
            empty = empty_font.render("Awaiting the first move...", True, th.text_muted)
            er = empty.get_rect(midtop=(LOG_PANEL_X + LOG_PANEL_W // 2, content_top + 12))
            self.screen.blit(empty, er)
            return

        visible = log_entries[-10:]
        n = len(visible)
        bullet_x = LOG_PANEL_X + 22
        text_x = LOG_PANEL_X + 40
        line_h = 34
        max_text_w = LOG_PANEL_W - (text_x - LOG_PANEL_X) - 14

        for i, entry in enumerate(visible):
            text = str(entry.get('text', entry)) if isinstance(entry, dict) else str(entry)
            if self.log_font.size(text)[0] > max_text_w:
                while text and self.log_font.size(text + "…")[0] > max_text_w:
                    text = text[:-1]
                text = text + "…"

            age = (n - 1 - i)
            alpha = max(120, 255 - age * 13)
            y = content_top + i * line_h

            bullet_surf = self.log_font.render("◆", True, th.brass_500)
            bullet_surf.set_alpha(alpha)
            self.screen.blit(bullet_surf, (bullet_x, y))

            line_surf = self.log_font.render(text, True, th.text_white)
            line_surf.set_alpha(alpha)
            self.screen.blit(line_surf, (text_x, y))

    def draw_action_buttons(self, action_buttons):
        th = theme_mod.active()
        focus_key = getattr(self, "_focused_action", None)
        dim_keys = getattr(self, "_dim_actions", set())
        pulse_keys = getattr(self, "_pulse_actions", set())
        keybind_hints = getattr(self, "_action_keybinds", {})

        for name, btn in action_buttons.items():
            rect = btn['rect']
            hovered = rect.collidepoint(pygame.mouse.get_pos())
            focused = (name == focus_key)
            dim = (name in dim_keys)
            pulse = (name in pulse_keys)
            color = btn.get('hover_color', btn['color']) if (hovered or focused) else btn['color']

            shadow_surf = pygame.Surface((rect.width + 6, rect.height + 8), pygame.SRCALPHA)
            pygame.draw.rect(shadow_surf, (0, 0, 0, 90), (3, 5, rect.width, rect.height), border_radius=10)
            self.screen.blit(shadow_surf, (rect.x - 3, rect.y))

            plate = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            for i in range(rect.height):
                t = i / max(1, rect.height - 1)
                shade = 0.85 + 0.15 * (1 - abs(t - 0.4) * 2)
                cc = (int(color[0] * shade), int(color[1] * shade), int(color[2] * shade), 255)
                pygame.draw.line(plate, cc, (0, i), (rect.width, i))
            mask = pygame.Surface(plate.get_size(), pygame.SRCALPHA)
            pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=10)
            plate.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
            if dim:
                plate.set_alpha(140)
            self.screen.blit(plate, rect)

            pygame.draw.line(self.screen, th.brass_300, (rect.left + 4, rect.top + 2),
                             (rect.right - 4, rect.top + 2), 1)
            pygame.draw.rect(self.screen, th.brass_500, rect, 2, border_radius=10)

            label_color = th.text_white if not dim else th.text_dim
            text_surf = self.ui_font.render(btn['text'], True, label_color)
            text_rect = text_surf.get_rect(center=rect.center)
            self.screen.blit(text_surf, text_rect)

            kb = keybind_hints.get(name)
            if kb:
                chip = self.small_font.render(kb.upper(), True, th.brass_900)
                cw = chip.get_width() + 8
                ch = chip.get_height() + 2
                cx = rect.right - cw - 4
                cy = rect.top + 4
                chip_bg = pygame.Surface((cw, ch), pygame.SRCALPHA)
                pygame.draw.rect(chip_bg, th.brass_300, chip_bg.get_rect(), border_radius=3)
                self.screen.blit(chip_bg, (cx, cy))
                self.screen.blit(chip, (cx + 4, cy + 1))

            if pulse:
                t = pygame.time.get_ticks() / 1000.0
                pulse_a = int(120 * (0.5 + 0.5 * math.sin(t * 5.0)))
                glow = pygame.Surface((rect.width + 16, rect.height + 16), pygame.SRCALPHA)
                pygame.draw.rect(glow, (*th.brass_300, pulse_a),
                                 glow.get_rect(), 4, border_radius=12)
                self.screen.blit(glow, (rect.x - 8, rect.y - 8))

            if focused:
                pygame.draw.rect(self.screen, th.brass_300,
                                 rect.inflate(6, 6), 2, border_radius=12)

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

        box_w, box_h = 800, 160
        box_rect = pygame.Rect(SCREEN_WIDTH // 2 - box_w // 2, SCREEN_HEIGHT // 2 - box_h // 2, box_w, box_h)
        pygame.draw.rect(screen, (50, 10, 10), box_rect, border_radius=12)
        pygame.draw.rect(screen, (200, 50, 50), box_rect, 2, border_radius=12)
        
        font = typo.display_bold(30)
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

    def get_gear_rect(self):
        w, h = self._hud_size()
        return pygame.Rect(SCREEN_WIDTH - w - 12, ACTION_BAR_Y + 16, w, h)

    def get_pause_rect(self):
        w, h = self._hud_size()
        return pygame.Rect(SCREEN_WIDTH - w * 2 - 24, ACTION_BAR_Y + 16, w, h)

    def get_quit_rect(self):
        w, h = self._hud_size()
        return pygame.Rect(SCREEN_WIDTH - w * 3 - 36, ACTION_BAR_Y + 16, w, h)

    def _draw_hud_buttons(self, mouse_pos):
        th = theme_mod.active()
        scale = get_mobile_scale()
        for rect, glyph_kind, tooltip in (
            (self.get_quit_rect(),  "x",     "Quit to menu"),
            (self.get_pause_rect(), "pause", "Pause"),
            (self.get_gear_rect(),  "gear",  "Settings"),
        ):
            hovered = rect.collidepoint(mouse_pos)
            pygame.draw.rect(self.screen, (60, 60, 60) if not hovered else (90, 90, 90),
                             rect, border_radius=8)
            pygame.draw.rect(self.screen, th.brass_500, rect, 1, border_radius=8)
            cx, cy = rect.center
            color = th.brass_300 if hovered else th.brass_300
            if glyph_kind == "gear":
                r = int(9 * scale)
                pygame.draw.circle(self.screen, color, (cx, cy), r, 2)
                pygame.draw.circle(self.screen, color, (cx, cy), max(2, int(3 * scale)))
                for k in range(8):
                    a = math.pi * 2 * k / 8
                    x1 = cx + int(math.cos(a) * r + 1)
                    y1 = cy + int(math.sin(a) * r + 1)
                    x2 = cx + int(math.cos(a) * (r + int(3 * scale)))
                    y2 = cy + int(math.sin(a) * (r + int(3 * scale)))
                    pygame.draw.line(self.screen, color, (x1, y1), (x2, y2), max(1, int(2 * scale)))
            elif glyph_kind == "pause":
                bar_w = max(3, int(4 * scale))
                bar_h = int(16 * scale)
                pygame.draw.rect(self.screen, color,
                                 pygame.Rect(cx - bar_w - 3, cy - bar_h // 2, bar_w, bar_h),
                                 border_radius=1)
                pygame.draw.rect(self.screen, color,
                                 pygame.Rect(cx + 3, cy - bar_h // 2, bar_w, bar_h),
                                 border_radius=1)
            elif glyph_kind == "x":
                off = int(7 * scale)
                pygame.draw.line(self.screen, color, (cx - off, cy - off), (cx + off, cy + off), max(1, int(2 * scale)))
                pygame.draw.line(self.screen, color, (cx + off, cy - off), (cx - off, cy + off), max(1, int(2 * scale)))
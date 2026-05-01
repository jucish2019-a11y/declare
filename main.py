import sys
import os
import asyncio

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pygame
from config import (
    SCREEN_WIDTH, SCREEN_HEIGHT, FPS,
    BG_GREEN, BG_DARK, CARD_WHITE, BLACK, RED, GOLD, TEXT_WHITE, TEXT_BLACK,
    TEXT_DIM, HIGHLIGHT, DIM, PANEL_BG, CARD_BACK_BLUE,
    DECLARE_RED, DECLARE_RED_HOVER, CANCEL_GRAY, CANCEL_GRAY_HOVER,
    PEEK_BLUE, PEEK_BLUE_HOVER, SWAP_GREEN, SWAP_GREEN_HOVER,
    DISCARD_ORANGE, DISCARD_ORANGE_HOVER, PAIR_TEAL, PAIR_TEAL_HOVER,
    SHUFFLE_COLOR, SHUFFLE_HOVER, SELF_PAIR_COLOR, SELF_PAIR_HOVER,
    DROP_MATCH_COLOR, DROP_MATCH_HOVER,
    STATUS_BAR_H, ACTION_BAR_Y, ACTION_BAR_H,
    CARD_WIDTH, CARD_HEIGHT, CORNER_RADIUS, CARD_SPREAD, HAND_SIZE,
    DECK_CENTER, DRAWN_CARD_POS, DISCARD_POS,
    PLAYER_BOTTOM, PLAYER_TOP, PLAYER_LEFT, PLAYER_RIGHT,
    LOG_PANEL_X, LOG_PANEL_Y, LOG_PANEL_W, LOG_PANEL_H,
    UI_FONT_SIZE, SMALL_FONT_SIZE, POWER_LABELS,
    ANIM_DRAW_DURATION, ANIM_SWAP_DURATION, ANIM_UNSEEN_SWAP_DURATION,
    ANIM_SEEN_SWAP_DURATION, ANIM_DISCARD_DURATION, ANIM_PAIR_FLY_DURATION,
    ANIM_NOTIFICATION_DURATION, CARD_GRID_SPACING_X, CARD_GRID_SPACING_Y,
    ANIM_SHUFFLE_DURATION, ANIM_REACTIVE_DROP_DURATION, ANIM_PENALTY_DRAW_DURATION,
)
from game.game_manager import GameManager, GameState
from game.player import HumanPlayer
from game.ai import AIDecider
from game.rules import get_valid_actions, can_self_pair, can_react_to_discard, can_call_opponent_card
from game.settings import GameSettings
from ui.renderer import Renderer, _get_seat_position, _player_area_bounds
from ui.screens import MenuScreen, SetupScreen, PeekScreen, GameOverScreen
from ui.settings import SettingsMenu

import theme
import audio
import profile as profile_mod
from toasts import ToastManager
from particles import ParticleSystem
from pause import PauseOverlay
from feel import CameraShake, TimeWarp, EdgeFlash, Vignette, LampGlow
from tutorial import TutorialDirector, FirstLaunchSplash
from hints import HintEngine
from captions import CaptionStream
from profile_screen import ProfileScreen, HowToPlayScreen
from access_panel import AccessibilityPanel
import daily


def _should_offer_self_pair(gm, game_settings):
    if not gm.drawn_card_resolved:
        return False
    if not game_settings or not game_settings.self_pair_enabled:
        return False
    cp = gm.current_player()
    pairs = can_self_pair(cp)
    return bool(pairs)


def _schedule_end_turn(gm, game_settings, renderer):
    if _should_offer_self_pair(gm, game_settings):
        return
    gm.end_turn()


def _build_action_buttons(gm, ui_font, game_settings=None):
    buttons = {}
    cp = gm.current_player()
    valid = get_valid_actions(cp, gm.drawn_card, gm.has_drawn_this_turn)
    if not valid:
        return buttons
    btn_y = ACTION_BAR_Y + ACTION_BAR_H // 2
    btn_h = 44
    spacing = 8
    if gm.state == GameState.TURN_START:
        x = SCREEN_WIDTH // 2 - 120
        if 'declare' in valid:
            w = 160
            rect = pygame.Rect(x - w // 2, btn_y - btn_h // 2, w, btn_h)
            buttons['declare'] = {'rect': rect, 'text': 'Declare', 'color': DECLARE_RED, 'hover_color': DECLARE_RED_HOVER, 'font': ui_font}
            x += 180
        if 'draw' in valid:
            w = 140
            rect = pygame.Rect(x - w // 2, btn_y - btn_h // 2, w, btn_h)
            buttons['draw'] = {'rect': rect, 'text': 'Draw', 'color': SWAP_GREEN, 'hover_color': SWAP_GREEN_HOVER, 'font': ui_font}
    elif gm.state == GameState.DECIDE:
        x = SCREEN_WIDTH // 2 - 400

        if game_settings and game_settings.self_pair_enabled:
            if gm.drawn_card_resolved:
                pairs = can_self_pair(cp)
                if pairs:
                    w = 110
                    rect = pygame.Rect(x, btn_y - btn_h // 2, w, btn_h)
                    buttons['self_pair'] = {'rect': rect, 'text': 'Self-Pair', 'color': SELF_PAIR_COLOR, 'hover_color': SELF_PAIR_HOVER, 'font': ui_font}
                    x += w + spacing

        if 'play_power' in valid and gm.drawn_card and gm.drawn_card.power:
            power = gm.drawn_card.power
            label = POWER_LABELS.get(power, 'Power')
            w = 150
            rect = pygame.Rect(x, btn_y - btn_h // 2, w, btn_h)
            buttons['play_power'] = {'rect': rect, 'text': label, 'color': PEEK_BLUE, 'hover_color': PEEK_BLUE_HOVER, 'font': ui_font}
            x += w + spacing
        if 'swap' in valid:
            w = 110
            rect = pygame.Rect(x, btn_y - btn_h // 2, w, btn_h)
            buttons['swap'] = {'rect': rect, 'text': 'Swap', 'color': SWAP_GREEN, 'hover_color': SWAP_GREEN_HOVER, 'font': ui_font}
            x += w + spacing
        if 'discard' in valid:
            w = 120
            rect = pygame.Rect(x, btn_y - btn_h // 2, w, btn_h)
            buttons['discard'] = {'rect': rect, 'text': 'Discard', 'color': DISCARD_ORANGE, 'hover_color': DISCARD_ORANGE_HOVER, 'font': ui_font}
            x += w + spacing
        if 'pair_own' in valid:
            w = 130
            rect = pygame.Rect(x, btn_y - btn_h // 2, w, btn_h)
            buttons['pair_own'] = {'rect': rect, 'text': 'Pair Own', 'color': PAIR_TEAL, 'hover_color': PAIR_TEAL_HOVER, 'font': ui_font}
            x += w + spacing
        if 'pair_opponent' in valid:
            w = 160
            rect = pygame.Rect(x, btn_y - btn_h // 2, w, btn_h)
            buttons['pair_opponent'] = {'rect': rect, 'text': 'Pair Opponent', 'color': PAIR_TEAL, 'hover_color': PAIR_TEAL_HOVER, 'font': ui_font}
            x += w + spacing
        if 'declare' in valid:
            w = 130
            rect = pygame.Rect(x, btn_y - btn_h // 2, w, btn_h)
            buttons['declare'] = {'rect': rect, 'text': 'Declare', 'color': DECLARE_RED, 'hover_color': DECLARE_RED_HOVER, 'font': ui_font}

    elif gm.state == GameState.REACTION_WINDOW:
        x = SCREEN_WIDTH // 2 - 200
        rank = gm.reaction_rank
        label = f"Drop {rank}!"
        w = 140
        rect = pygame.Rect(x, btn_y - btn_h // 2, w, btn_h)
        buttons['drop_self'] = {'rect': rect, 'text': label, 'color': DROP_MATCH_COLOR, 'hover_color': DROP_MATCH_HOVER, 'font': ui_font}
        x += w + spacing

        if gm.reaction_source_player is not None:
            for opp in gm.players:
                if opp.seat_index == gm.reaction_source_player or opp.is_human:
                    continue
                opp_slots = can_call_opponent_card(cp, opp, rank)
                if opp_slots:
                    w = 180
                    rect = pygame.Rect(x, btn_y - btn_h // 2, w, btn_h)
                    buttons['drop_opponent'] = {'rect': rect, 'text': f"Call {opp.name}'s {rank}", 'color': PAIR_TEAL, 'hover_color': PAIR_TEAL_HOVER, 'font': ui_font}
                    x += w + spacing
                    break

        w = 100
        rect = pygame.Rect(x, btn_y - btn_h // 2, w, btn_h)
        buttons['pass_reaction'] = {'rect': rect, 'text': 'Pass', 'color': CANCEL_GRAY, 'hover_color': CANCEL_GRAY_HOVER, 'font': ui_font}

    return buttons


def _build_cancel_button(text, ui_font):
    w = 140
    h = 40
    rect = pygame.Rect(SCREEN_WIDTH // 2 - w // 2, ACTION_BAR_Y + ACTION_BAR_H + 2, w, h)
    return {'rect': rect, 'text': text, 'font': ui_font}


def _build_shuffle_button(player, seat_position, ui_font):
    px, py = seat_position
    w = 80
    h = 28
    sx = px - w // 2
    sy = py + CARD_HEIGHT // 2 + 40
    rect = pygame.Rect(sx, sy, w, h)
    return {'rect': rect, 'text': 'Shuffle', 'color': SHUFFLE_COLOR, 'hover_color': SHUFFLE_HOVER, 'font': ui_font}


def _ai_power_target(ai, player, players, card):
    power = card.power
    if power == 'peek_self':
        return {'slot': ai.peek_target_own(player.hand)}
    elif power == 'peek_opponent':
        p_idx, s_idx = ai.peek_target_opponent(players)
        return {'player_index': p_idx, 'slot': s_idx}
    elif power == 'seen_swap':
        return {
            'my_slot': ai.estimate_worst_slot() or 0,
            'target_player': ai._pick_opponent_with_most_unknown() or 0,
            'their_slot': 0,
        }
    elif power == 'unseen_swap':
        return {
            'my_slot': ai.estimate_worst_slot() or 0,
            'target_player': ai._pick_opponent_with_most_unknown() or 0,
            'their_slot': 0,
        }
    return {}


def _find_opponent_slot(player, players, opponent_index, rank):
    for (p_idx, s_idx), card in player.known_opponent_cards.items():
        if p_idx == opponent_index and card.rank == rank:
            return s_idx
    return 0


def _get_human_index(game_manager):
    for i, p in enumerate(game_manager.players):
        if p.is_human:
            return i
    return None


def _clamp_to_bounds(cx, cy, bounds):
    x_min, y_min, x_max, y_max = bounds
    cx = max(x_min + CARD_WIDTH // 2, min(x_max - CARD_WIDTH // 2, cx))
    cy = max(y_min + CARD_HEIGHT // 2, min(y_max - CARD_HEIGHT // 2, cy))
    return (cx, cy)


class _ScaledDisplay:
    def __init__(self):
        info = pygame.display.Info()
        max_w = max(800, info.current_w - 80)
        max_h = max(600, info.current_h - 160)
        scale = min(max_w / SCREEN_WIDTH, max_h / SCREEN_HEIGHT, 1.0)
        win_w = max(640, int(SCREEN_WIDTH * scale))
        win_h = max(360, int(SCREEN_HEIGHT * scale))
        self.window = pygame.display.set_mode((win_w, win_h), pygame.RESIZABLE)
        self.logical = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT)).convert()
        self.shake_offset = (0, 0)

    def to_logical(self, pos):
        win_w, win_h = self.window.get_size()
        if win_w <= 0 or win_h <= 0:
            return pos
        return (
            int(pos[0] * SCREEN_WIDTH / win_w),
            int(pos[1] * SCREEN_HEIGHT / win_h),
        )

    def set_shake(self, offset):
        self.shake_offset = offset

    def present(self):
        win_size = self.window.get_size()
        ox, oy = self.shake_offset
        if ox or oy:
            shaken = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            shaken.fill((0, 0, 0))
            shaken.blit(self.logical, (ox, oy))
            source = shaken
        else:
            source = self.logical

        if win_size == (SCREEN_WIDTH, SCREEN_HEIGHT):
            self.window.blit(source, (0, 0))
        else:
            scaled = pygame.transform.smoothscale(source, win_size)
            self.window.blit(scaled, (0, 0))
        pygame.display.flip()


def _translate_mouse_event(event, display):
    if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION):
        new_pos = display.to_logical(event.pos)
        attrs = dict(event.__dict__)
        attrs['pos'] = new_pos
        if event.type == pygame.MOUSEMOTION and 'rel' in attrs:
            win_w, win_h = display.window.get_size()
            if win_w > 0 and win_h > 0:
                attrs['rel'] = (
                    int(attrs['rel'][0] * SCREEN_WIDTH / win_w),
                    int(attrs['rel'][1] * SCREEN_HEIGHT / win_h),
                )
        return pygame.event.Event(event.type, attrs)
    return event


async def main():
    os.environ.setdefault("SDL_VIDEO_CENTERED", "1")
    os.environ.setdefault("SDL_HINT_WINDOWS_DPI_AWARENESS", "permonitorv2")
    pygame.init()
    audio.init()

    prof = profile_mod.load()
    theme.set_active(prof.settings.theme)
    theme.apply_text_scale(prof.settings.text_scale)
    theme.apply_motion_scale(prof.settings.motion_scale)
    theme.apply_particles(prof.settings.particles_enabled)
    audio.set_volume("sfx", prof.settings.sfx_volume)
    audio.set_volume("music", prof.settings.music_volume)
    audio.set_volume("voice", prof.settings.voice_volume)

    display = _ScaledDisplay()
    screen = display.logical
    pygame.display.set_caption("Declare")

    _orig_get_pos = pygame.mouse.get_pos
    pygame.mouse.get_pos = lambda: display.to_logical(_orig_get_pos())

    clock = pygame.time.Clock()
    toasts = ToastManager()
    particles = ParticleSystem()
    pause = PauseOverlay()
    paused = False
    cam = CameraShake()
    timewarp = TimeWarp()
    edge_flash = EdgeFlash()
    vignette = Vignette()
    lamp = LampGlow()
    tutorial = TutorialDirector(screen)
    first_launch = FirstLaunchSplash()
    if not prof.tutorial_complete:
        first_launch.show()
    captions = CaptionStream()
    profile_screen = ProfileScreen(screen)
    how_to_screen = HowToPlayScreen(screen)
    access_panel = AccessibilityPanel()
    last_human_action = {}
    declare_hold_until = 0.0

    ui_font = pygame.font.SysFont("arial", UI_FONT_SIZE)
    small_font = pygame.font.SysFont("arial", SMALL_FONT_SIZE)

    game_manager = None
    current_screen = "menu"
    game_over_result = None
    settings_open = False
    game_settings = GameSettings()
    game_settings.apply_persistent(prof.settings)
    hint_engine = HintEngine(game_settings)

    game_meta = {}
    game_start_time = 0.0
    last_log_index = 0
    prev_screen = "menu"
    achievement_queue = []

    renderer = Renderer(screen)
    renderer.set_game_settings(game_settings)
    menu_screen = MenuScreen(screen)
    setup_screen = SetupScreen(screen)
    peek_screen = PeekScreen(screen, game_settings.hand_size, game_settings.peek_count, game_settings.peek_phase_seconds)
    game_over_screen = GameOverScreen(screen)
    settings_menu = SettingsMenu(screen)
    settings_menu.attach_profile(prof)

    awaiting = None
    selected_slot = None
    swap_second_click = False
    pair_opponent_give_slot = None
    status_message = ""
    turn_end_timer = 0.0

    ai_phase = 'idle'
    ai_timer = 0.0

    dragging_slot = None
    drag_offset = (0, 0)

    react_opponent_index = None
    react_opponent_slot = None
    react_give_slot = None

    notification_text: str = ""
    notification_timer: float = 0.0

    running = True
    while running:
        await asyncio.sleep(0)
        dt = clock.tick(FPS) / 1000.0
        mouse_pos = pygame.mouse.get_pos()

        audio.update(dt)
        toasts.update(dt)
        particles.update(dt)
        pause.update(dt if paused else 0.0)
        cam.update(dt)
        edge_flash.update(dt)
        lamp.update(dt)
        tutorial.update(dt)
        first_launch.update(dt)
        access_panel.update(dt)
        time_scale = timewarp.update(dt)
        if not paused:
            game_dt = dt * time_scale
            if current_screen == "game" and game_manager is not None:
                particles.ambient_dust(SCREEN_WIDTH, SCREEN_HEIGHT,
                                       color=theme.active().lamp_glow)

        if game_manager and not paused:
            game_manager.update(dt)
        if not paused:
            renderer.update(dt * time_scale)

        if game_manager and current_screen == "game" and not paused:
            log = getattr(game_manager, "game_log", [])
            while last_log_index < len(log):
                _react_to_log_entry(log[last_log_index], particles, toasts, game_manager, renderer,
                                    cam=cam, edge_flash=edge_flash, timewarp=timewarp,
                                    hints=hint_engine, last_human_action=last_human_action,
                                    captions=captions if game_settings.captions else None)
                last_log_index += 1
        captions.update()

        if turn_end_timer > 0:
            turn_end_timer -= dt
            if turn_end_timer <= 0:
                turn_end_timer = 0
                if game_manager:
                    game_manager.end_turn()

        if notification_timer > 0:
            notification_timer -= dt
            if notification_timer <= 0:
                notification_text = ""

        for event in pygame.event.get():
            event = _translate_mouse_event(event, display)
            if event.type == pygame.QUIT:
                profile_mod.save(prof)
                running = False
                break

            if event.type == pygame.KEYDOWN and event.key == pygame.K_F1:
                if access_panel.active:
                    access_panel.close()
                else:
                    access_panel.open()
                continue

            if access_panel.active:
                a_action = access_panel.handle_event(event, prof, game_settings)
                if a_action:
                    continue

            if first_launch.active:
                fl_action = first_launch.handle_event(event)
                if fl_action == "tutorial":
                    tutorial.start()
                    audio.play("click")
                elif fl_action == "skip":
                    audio.play("click")
                if fl_action:
                    continue

            if tutorial.active:
                t_action = tutorial.handle_event(event)
                if t_action == "next":
                    if tutorial.advance():
                        prof.tutorial_complete = True
                        profile_mod.unlock(prof, "tutorial_done")
                        profile_mod.save(prof)
                        toasts.push("Tutorial complete!", kind="achievement",
                                    icon="*", life=3.0)
                elif t_action == "skip":
                    if tutorial.skip_chapter():
                        prof.tutorial_complete = True
                        profile_mod.unlock(prof, "tutorial_done")
                        profile_mod.save(prof)
                        toasts.push("Tutorial complete!", kind="achievement",
                                    icon="*", life=3.0)
                    audio.play("click")
                if t_action:
                    continue

            if paused:
                action, payload = pause.handle_event(event)
                if action == "select":
                    if payload == "resume":
                        paused = False
                        audio.unduck()
                        audio.play("ui_close")
                    elif payload == "restart":
                        if game_manager is not None:
                            configs = []
                            for p in game_manager.players:
                                configs.append({
                                    "name": p.name,
                                    "is_human": p.is_human,
                                    "difficulty": getattr(p, "difficulty", "medium"),
                                })
                            game_meta = _new_game_meta(len(configs), configs, game_settings)
                            game_start_time = pygame.time.get_ticks() / 1000.0
                            last_log_index = 0
                            game_manager = GameManager(configs, game_settings)
                            game_manager.setup_game()
                            peek_screen = PeekScreen(screen, game_manager.settings.hand_size,
                                                     game_manager.settings.peek_count,
                                                     game_settings.peek_phase_seconds)
                            paused = False
                            audio.unduck()
                            current_screen = "peek"
                    elif payload == "settings":
                        settings_open = True
                        paused = False
                        audio.unduck()
                    elif payload == "how_to_play":
                        current_screen = "how_to_play"
                        paused = False
                        audio.unduck()
                    elif payload == "quit_menu":
                        profile_mod.save(prof)
                        game_manager = None
                        game_over_result = None
                        current_screen = "menu"
                        paused = False
                        audio.unduck()
                        last_log_index = 0
                continue

            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                if awaiting is not None:
                    awaiting = None
                    selected_slot = None
                    swap_second_click = False
                    pair_opponent_give_slot = None
                    status_message = ""
                    game_manager.cancel_targeting()
                    audio.play("click")
                    continue

                if settings_open and current_screen == "game":
                    settings_open = False
                    audio.play("ui_close")
                    continue

                if current_screen == "game" and game_manager is not None:
                    paused = True
                    pause.reset()
                    audio.duck(0.35)
                    audio.play("ui_open")
                    continue

            if event.type == pygame.KEYDOWN and event.key == pygame.K_s:
                if current_screen == "game" and game_manager is not None:
                    settings_open = not settings_open
                    awaiting = None
                    selected_slot = None
                    swap_second_click = False
                    pair_opponent_give_slot = None
                    status_message = ""
                    game_manager.cancel_targeting()
                    continue

            if (current_screen == "game" and game_manager is not None
                    and event.type == pygame.KEYDOWN
                    and not awaiting and not paused and not settings_open):
                cp = game_manager.current_player()
                if cp.is_human:
                    NUMBER_TO_ACTION = {
                        pygame.K_1: "draw",
                        pygame.K_2: "declare",
                        pygame.K_3: "swap",
                        pygame.K_4: "discard",
                        pygame.K_5: "pair_own",
                        pygame.K_6: "play_power",
                        pygame.K_7: "pair_opponent",
                    }
                    if event.key in NUMBER_TO_ACTION:
                        target_action = NUMBER_TO_ACTION[event.key]
                        action_buttons_now = _build_action_buttons(game_manager, ui_font, game_settings)
                        if target_action in action_buttons_now:
                            btn = action_buttons_now[target_action]
                            synth = pygame.event.Event(
                                pygame.MOUSEBUTTONDOWN,
                                {"button": 1, "pos": btn["rect"].center}
                            )
                            pygame.event.post(synth)
                            audio.play("click")
                            continue

            if current_screen == "menu":
                action = menu_screen.handle_event(event)
                if action == "new_game":
                    current_screen = "setup"
                    setup_screen = SetupScreen(screen)
                    audio.play("click")
                elif action == "tutorial":
                    tutorial.start()
                    audio.play("click")
                elif action == "how_to_play":
                    current_screen = "how_to_play"
                    audio.play("ui_open")
                elif action == "profile":
                    current_screen = "profile"
                    audio.play("ui_open")
                elif action == "quit":
                    profile_mod.save(prof)
                    running = False

            elif current_screen == "profile":
                action = profile_screen.handle_event(event, prof)
                if action == "back":
                    current_screen = "menu"

            elif current_screen == "how_to_play":
                action = how_to_screen.handle_event(event)
                if action == "back":
                    current_screen = "menu"

            elif current_screen == "setup":
                action = setup_screen.handle_event(event)
                if action == "start_game":
                    game_over_result = None
                    configs = setup_screen.players_config[:setup_screen.num_players]
                    game_manager = GameManager(configs, game_settings)
                    game_manager.setup_game()
                    peek_screen = PeekScreen(screen, game_manager.settings.hand_size, game_manager.settings.peek_count, game_settings.peek_phase_seconds)
                    current_screen = "peek"
                    game_meta = _new_game_meta(len(configs), configs, game_settings)
                    game_start_time = pygame.time.get_ticks() / 1000.0
                    last_log_index = 0
                    toasts.clear()
                    particles.clear()
                    audio.play("shuffle")
                    prof.last_match_config = {
                        "configs": [{"name": c["name"], "is_human": c["is_human"],
                                     "difficulty": c.get("difficulty", "medium")} for c in configs],
                        "num_players": setup_screen.num_players,
                    }
                elif action == "back":
                    current_screen = "menu"

            elif current_screen == "peek":
                action = peek_screen.handle_event(event)
                if action == "peek_done":
                    game_manager.start_peek_phase()
                    awaiting = None
                    selected_slot = None
                    turn_end_timer = 0
                    ai_phase = 'idle'
                    ai_timer = 0
                    current_screen = "game"

            elif current_screen == "game":
                if settings_open:
                    result = settings_menu.handle_event(event, game_settings, game_manager)
                    if result == 'close':
                        settings_open = False
                        audio.play("ui_close")
                    elif result == 'updated':
                        prof.settings.captions = game_settings.captions
                        prof.settings.coach_mode = game_settings.coach_mode
                        prof.settings.streamer_mode = game_settings.streamer_mode
                        prof.settings.hint_tier = game_settings.hint_tier
                        prof.settings.motion_scale = game_settings.motion_scale
                        prof.settings.particles_enabled = game_settings.particles_enabled
                        profile_mod.save(prof)
                    continue

                if game_manager is None:
                    current_screen = "menu"
                    continue

                if game_manager.state == GameState.GAME_OVER:
                    if game_over_result is None:
                        game_over_result = game_manager.declaration_result or {
                            'winner': game_manager.winner,
                            'scores': {p.seat_index: p.score for p in game_manager.players},
                            'declarer_won': False,
                            'auto_win': False,
                        }
                    current_screen = "game_over"
                    continue

                cp = game_manager.current_player()
                if not cp.is_human and game_manager.state != GameState.REACTION_WINDOW:
                    continue

                if turn_end_timer > 0:
                    continue

                if renderer.is_animating():
                    continue

                human_idx = _get_human_index(game_manager)
                action_buttons = _build_action_buttons(game_manager, ui_font, game_settings)
                cancel_button = None
                if awaiting is not None:
                    cancel_button = _build_cancel_button("Cancel", ui_font)
                    if awaiting == 'swap':
                        status_message = "Click one of your cards to swap with the drawn card"
                    elif awaiting == 'peek_self':
                        status_message = "Click one of your unknown cards to peek"
                    elif awaiting == 'peek_opponent':
                        status_message = "Click an opponent's card to peek"
                    elif awaiting in ('unseen_swap', 'seen_swap'):
                        if selected_slot is None:
                            status_message = "Click one of YOUR cards first"
                        else:
                            status_message = "Now click an OPPONENT's card to swap"
                    elif awaiting == 'pair_own':
                        status_message = "Click your matching card to pair"
                    elif awaiting == 'pair_opponent':
                        if pair_opponent_give_slot is None:
                            status_message = "Click YOUR card to give away"
                        else:
                            status_message = "Click OPPONENT's matching card"
                    elif awaiting == 'self_pair_first':
                        status_message = "Click first card to self-pair"
                    elif awaiting == 'self_pair_second':
                        status_message = "Click second card to self-pair"
                    elif awaiting == 'react_drop_self':
                        status_message = "Click YOUR matching card to drop"
                    elif awaiting == 'react_drop_opp_give':
                        status_message = "Click YOUR card to give in exchange"
                    elif awaiting == 'react_drop_opp_target':
                        status_message = "Click OPPONENT's matching card"

                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    clicked_btn = None
                    for name, btn in action_buttons.items():
                        if btn['rect'].collidepoint(mouse_pos):
                            clicked_btn = name
                            break

                    if cancel_button and cancel_button['rect'].collidepoint(mouse_pos):
                        awaiting = None
                        selected_slot = None
                        swap_second_click = False
                        pair_opponent_give_slot = None
                        status_message = ""
                        game_manager.cancel_targeting()
                        continue

                    gear_rect = renderer.get_gear_rect()
                    if gear_rect.collidepoint(mouse_pos):
                        settings_open = not settings_open
                        awaiting = None
                        selected_slot = None
                        swap_second_click = False
                        pair_opponent_give_slot = None
                        status_message = ""
                        game_manager.cancel_targeting()
                        audio.play("ui_open" if settings_open else "ui_close")
                        continue

                    if renderer.get_pause_rect().collidepoint(mouse_pos):
                        paused = True
                        pause.reset()
                        audio.duck(0.35)
                        audio.play("ui_open")
                        continue

                    if renderer.get_quit_rect().collidepoint(mouse_pos):
                        profile_mod.save(prof)
                        game_manager = None
                        game_over_result = None
                        current_screen = "menu"
                        last_log_index = 0
                        toasts.push("Match abandoned.", kind="info", icon="!", life=2.0)
                        audio.play("ui_close")
                        continue

                    if game_settings and game_settings.shuffle_enabled and human_idx is not None:
                        num_players = len(game_manager.players)
                        seat_pos = _get_seat_position(human_idx, num_players)
                        shuffle_btn = _build_shuffle_button(game_manager.players[human_idx], seat_pos, ui_font)
                        if shuffle_btn['rect'].collidepoint(mouse_pos):
                            game_manager.shuffle_player_hand(human_idx)
                            continue

                    if clicked_btn:
                        if clicked_btn == 'draw' and game_manager.state == GameState.TURN_START:
                            game_manager.draw_card()
                            renderer.push_draw_animation(game_manager)
                            status_message = ""
                            awaiting = None

                        elif clicked_btn == 'declare':
                            if awaiting == 'confirm_declare':
                                game_manager.execute_player_action("declare", {})
                                game_manager.resolve_declaration()
                                game_over_result = game_manager.declaration_result
                                current_screen = "game_over"
                                awaiting = None
                                status_message = ""
                            elif game_settings.confirm_declare:
                                awaiting = 'confirm_declare'
                                selected_slot = None
                                swap_second_click = False
                                pair_opponent_give_slot = None
                                status_message = "Are you sure? Click again to Declare."
                            else:
                                game_manager.execute_player_action("declare", {})
                                game_manager.resolve_declaration()
                                game_over_result = game_manager.declaration_result
                                current_screen = "game_over"

                        elif clicked_btn == 'self_pair' and game_manager.state == GameState.DECIDE:
                            awaiting = 'self_pair_first'
                            selected_slot = None
                            status_message = "Click first card to self-pair"

                        elif clicked_btn == 'swap' and game_manager.state == GameState.DECIDE:
                            awaiting = 'swap'
                            selected_slot = None
                            status_message = "Click one of your cards to swap with the drawn card"

                        elif clicked_btn == 'discard' and game_manager.state == GameState.DECIDE:
                            discarded = game_manager.drawn_card
                            renderer.push_discard_animation(game_manager)
                            game_manager.execute_player_action("discard", {"drawn_card": discarded})
                            game_manager.check_game_over()
                            game_manager.start_reaction_window(discarded.rank, game_manager.current_player_index, discarded)
                            awaiting = None
                            status_message = ""
                            if game_manager.state != GameState.REACTION_WINDOW:
                                _schedule_end_turn(game_manager, game_settings, renderer)

                        elif clicked_btn == 'play_power' and game_manager.state == GameState.DECIDE:
                            card = game_manager.drawn_card
                            if card and card.power:
                                if card.power == 'peek_self':
                                    awaiting = 'peek_self'
                                    selected_slot = None
                                    status_message = "Click one of your unknown cards to peek"
                                elif card.power == 'peek_opponent':
                                    awaiting = 'peek_opponent'
                                    selected_slot = None
                                    status_message = "Click an opponent's card to peek"
                                elif card.power in ('unseen_swap', 'seen_swap'):
                                    awaiting = card.power
                                    selected_slot = None
                                    swap_second_click = False
                                    status_message = "Click one of YOUR cards first"
                                elif card.power == 'skip':
                                    game_manager.execute_player_action("play_power", {
                                        "card": card,
                                        "target_info": {},
                                    })
                                    game_manager.skip_next = True
                                    turn_end_timer = 0.5

                        elif clicked_btn == 'pair_own' and game_manager.state == GameState.DECIDE:
                            awaiting = 'pair_own'
                            selected_slot = None
                            status_message = "Click your matching card to pair"

                        elif clicked_btn == 'pair_opponent' and game_manager.state == GameState.DECIDE:
                            awaiting = 'pair_opponent'
                            pair_opponent_give_slot = None
                            selected_slot = None
                            status_message = "Click YOUR card to give away"

                        elif clicked_btn == 'drop_self' and game_manager.state == GameState.REACTION_WINDOW:
                            awaiting = 'react_drop_self'
                            selected_slot = None
                            status_message = "Click YOUR matching card to drop"

                        elif clicked_btn == 'drop_opponent' and game_manager.state == GameState.REACTION_WINDOW:
                            awaiting = 'react_drop_opp_give'
                            react_give_slot = None
                            status_message = "Click YOUR card to give in exchange"

                        elif clicked_btn == 'pass_reaction' and game_manager.state == GameState.REACTION_WINDOW:
                            game_manager.end_reaction_window()
                            awaiting = None
                            status_message = ""

                    else:
                        if awaiting is not None:
                            if awaiting == 'swap':
                                if human_idx is not None:
                                    rects = renderer.get_card_rects(human_idx, game_manager)
                                    for slot_idx, rect in enumerate(rects):
                                        if rect.collidepoint(mouse_pos) and game_manager.players[human_idx].hand[slot_idx] is not None:
                                            swapped_card = game_manager.players[human_idx].hand[slot_idx]
                                            renderer.push_swap_animation(game_manager, slot_idx, swapped_card)
                                            game_manager.execute_player_action("swap", {
                                                "my_slot": slot_idx,
                                                "drawn_card": game_manager.drawn_card,
                                            })
                                            awaiting = None
                                            status_message = ""
                                            _schedule_end_turn(game_manager, game_settings, renderer)
                                            break

                            elif awaiting == 'peek_self':
                                if human_idx is not None:
                                    rects = renderer.get_card_rects(human_idx, game_manager)
                                    for slot_idx, rect in enumerate(rects):
                                        if rect.collidepoint(mouse_pos) and game_manager.players[human_idx].hand[slot_idx] is not None:
                                            center = renderer.get_card_center(human_idx, slot_idx, game_manager)
                                            renderer.push_peek_lift_animation(game_manager, center)
                                            result = game_manager.execute_player_action("play_power", {
                                                "card": game_manager.drawn_card,
                                                "target_info": {"slot": slot_idx},
                                            })
                                            peeked_card = game_manager.players[human_idx].hand[slot_idx]
                                            card_rects = renderer.get_card_rects(human_idx, game_manager)
                                            if slot_idx < len(card_rects):
                                                r = card_rects[slot_idx]
                                                renderer.set_peek_reveal(peeked_card, r.x, r.y, game_settings.peek_reveal_time)
                                            awaiting = None
                                            status_message = ""
                                            _schedule_end_turn(game_manager, game_settings, renderer)
                                            break

                            elif awaiting == 'peek_opponent':
                                for player in game_manager.players:
                                    if player.is_human:
                                        continue
                                    rects = renderer.get_card_rects(player.seat_index, game_manager)
                                    for slot_idx, rect in enumerate(rects):
                                        if rect.collidepoint(mouse_pos) and player.hand[slot_idx] is not None:
                                            center = renderer.get_card_center(player.seat_index, slot_idx, game_manager)
                                            renderer.push_peek_lift_animation(game_manager, center)
                                            result = game_manager.execute_player_action("play_power", {
                                                "card": game_manager.drawn_card,
                                                "target_info": {"player_index": player.seat_index, "slot": slot_idx},
                                            })
                                            peeked_card = player.hand[slot_idx]
                                            card_rects = renderer.get_card_rects(player.seat_index, game_manager)
                                            if slot_idx < len(card_rects):
                                                r = card_rects[slot_idx]
                                                renderer.set_peek_reveal(peeked_card, r.x, r.y, game_settings.peek_reveal_time)
                                            awaiting = None
                                            status_message = ""
                                            _schedule_end_turn(game_manager, game_settings, renderer)
                                            break
                                    else:
                                        continue
                                    break

                            elif awaiting in ('unseen_swap', 'seen_swap'):
                                if selected_slot is None:
                                    if human_idx is not None:
                                        rects = renderer.get_card_rects(human_idx, game_manager)
                                        for slot_idx, rect in enumerate(rects):
                                            if rect.collidepoint(mouse_pos) and game_manager.players[human_idx].hand[slot_idx] is not None:
                                                selected_slot = slot_idx
                                                status_message = "Now click an OPPONENT's card to swap"
                                                break
                                else:
                                    for player in game_manager.players:
                                        if player.is_human:
                                            continue
                                        rects = renderer.get_card_rects(player.seat_index, game_manager)
                                        for slot_idx, rect in enumerate(rects):
                                            if rect.collidepoint(mouse_pos) and player.hand[slot_idx] is not None:
                                                if awaiting == 'seen_swap':
                                                    their_card_before = player.hand[slot_idx]
                                                    renderer.push_seen_swap_animation(
                                                        game_manager, selected_slot,
                                                        player.seat_index, slot_idx,
                                                        their_card_before,
                                                    )
                                                else:
                                                    renderer.push_unseen_swap_animation(
                                                        game_manager, selected_slot,
                                                        player.seat_index, slot_idx,
                                                    )
                                                game_manager.execute_player_action("play_power", {
                                                    "card": game_manager.drawn_card,
                                                    "target_info": {
                                                        "my_slot": selected_slot,
                                                        "target_player": player.seat_index,
                                                        "their_slot": slot_idx,
                                                    },
                                                })
                                                awaiting = None
                                                selected_slot = None
                                                status_message = ""
                                                _schedule_end_turn(game_manager, game_settings, renderer)
                                                break
                                        else:
                                            continue
                                        break

                            elif awaiting == 'pair_own':
                                if human_idx is not None:
                                    rects = renderer.get_card_rects(human_idx, game_manager)
                                    for slot_idx, rect in enumerate(rects):
                                        if rect.collidepoint(mouse_pos) and game_manager.players[human_idx].hand[slot_idx] is not None:
                                            drawn = game_manager.drawn_card
                                            matching = game_manager.players[human_idx].known_cards.get(slot_idx)
                                            if matching and matching.rank == drawn.rank:
                                                pair_card = game_manager.players[human_idx].hand[slot_idx]
                                                pos = renderer.get_card_center(human_idx, slot_idx, game_manager)
                                                drawn_pos = DRAWN_CARD_POS
                                                renderer.push_pair_fly_animation(game_manager, pos, pair_card, drawn_pos, drawn)
                                                game_manager.execute_player_action("pair_own", {
                                                    "player_slot": slot_idx,
                                                    "drawn_card": drawn,
                                                })
                                                awaiting = None
                                                status_message = ""
                                                _schedule_end_turn(game_manager, game_settings, renderer)
                                                break

                            elif awaiting == 'pair_opponent':
                                if pair_opponent_give_slot is None:
                                    if human_idx is not None:
                                        rects = renderer.get_card_rects(human_idx, game_manager)
                                        for slot_idx, rect in enumerate(rects):
                                            if rect.collidepoint(mouse_pos) and game_manager.players[human_idx].hand[slot_idx] is not None:
                                                pair_opponent_give_slot = slot_idx
                                                status_message = "Click OPPONENT's matching card"
                                                break
                                else:
                                    for player in game_manager.players:
                                        if player.is_human:
                                            continue
                                        rects = renderer.get_card_rects(player.seat_index, game_manager)
                                        for slot_idx, rect in enumerate(rects):
                                            if rect.collidepoint(mouse_pos) and player.hand[slot_idx] is not None:
                                                opp_pos = renderer.get_card_center(player.seat_index, slot_idx, game_manager)
                                                give_pos = renderer.get_card_center(human_idx, pair_opponent_give_slot, game_manager)
                                                renderer.push_pair_fly_animation(game_manager, opp_pos, None, give_pos, None)
                                                game_manager.execute_player_action("pair_opponent", {
                                                    "opponent_index": player.seat_index,
                                                    "opponent_slot": slot_idx,
                                                    "drawn_card": game_manager.drawn_card,
                                                    "give_slot": pair_opponent_give_slot,
                                                })
                                                awaiting = None
                                                pair_opponent_give_slot = None
                                                status_message = ""
                                                _schedule_end_turn(game_manager, game_settings, renderer)
                                                break
                                        else:
                                            continue
                                        break

                            elif awaiting == 'self_pair_first':
                                if human_idx is not None:
                                    rects = renderer.get_card_rects(human_idx, game_manager)
                                    for slot_idx, rect in enumerate(rects):
                                        if rect.collidepoint(mouse_pos) and game_manager.players[human_idx].hand[slot_idx] is not None:
                                            if slot_idx in game_manager.players[human_idx].known_cards:
                                                selected_slot = slot_idx
                                                awaiting = 'self_pair_second'
                                                status_message = "Click second card to self-pair"
                                            break

                            elif awaiting == 'self_pair_second':
                                if human_idx is not None and selected_slot is not None:
                                    if selected_slot not in game_manager.players[human_idx].known_cards:
                                        status_message = "Pick a card you've seen first"
                                        awaiting = None
                                        selected_slot = None
                                        turn_end_timer = 0
                                    else:
                                        rects = renderer.get_card_rects(human_idx, game_manager)
                                        for slot_idx, rect in enumerate(rects):
                                            if rect.collidepoint(mouse_pos) and slot_idx != selected_slot and game_manager.players[human_idx].hand[slot_idx] is not None:
                                                if slot_idx in game_manager.players[human_idx].known_cards:
                                                    card_a = game_manager.players[human_idx].known_cards.get(selected_slot)
                                                    card_b = game_manager.players[human_idx].known_cards.get(slot_idx)
                                                    if card_a and card_b and card_a.rank == card_b.rank:
                                                        pos_a = renderer.get_card_center(human_idx, selected_slot, game_manager)
                                                        pos_b = renderer.get_card_center(human_idx, slot_idx, game_manager)
                                                        renderer.push_pair_fly_animation(game_manager, pos_a, game_manager.players[human_idx].hand[selected_slot], pos_b, game_manager.players[human_idx].hand[slot_idx])
                                                        result = game_manager.execute_self_pair_action(selected_slot, slot_idx)
                                                        if not result.get('success', True) is False:
                                                            game_manager.check_game_over()
                                                        awaiting = None
                                                        selected_slot = None
                                                        status_message = ""
                                                        turn_end_timer = ANIM_PAIR_FLY_DURATION + 0.1
                                                break

                            elif awaiting == 'react_drop_self':
                                if human_idx is not None and game_manager.state == GameState.REACTION_WINDOW:
                                    rects = renderer.get_card_rects(human_idx, game_manager)
                                    for slot_idx, rect in enumerate(rects):
                                        if rect.collidepoint(mouse_pos) and game_manager.players[human_idx].hand[slot_idx] is not None:
                                            result = game_manager.attempt_reactive_drop_self(human_idx, slot_idx)
                                            if result.get('success'):
                                                pos = renderer.get_card_center(human_idx, slot_idx, game_manager)
                                                renderer.push_pair_fly_animation(game_manager, pos, result['result']['card'])
                                                game_manager.check_game_over()
                                                awaiting = None
                                                status_message = ""
                                                turn_end_timer = ANIM_REACTIVE_DROP_DURATION + 0.1
                                            else:
                                                awaiting = None
                                                status_message = "Wrong card! Penalty drawn."
                                                game_manager.end_reaction_window()
                                                turn_end_timer = ANIM_PENALTY_DRAW_DURATION + 0.2
                                            break

                            elif awaiting == 'react_drop_opp_give':
                                if human_idx is not None:
                                    rects = renderer.get_card_rects(human_idx, game_manager)
                                    for slot_idx, rect in enumerate(rects):
                                        if rect.collidepoint(mouse_pos) and game_manager.players[human_idx].hand[slot_idx] is not None:
                                            react_give_slot = slot_idx
                                            awaiting = 'react_drop_opp_target'
                                            status_message = "Click OPPONENT's matching card"
                                            break

                            elif awaiting == 'react_drop_opp_target':
                                if human_idx is not None and react_give_slot is not None:
                                    for player in game_manager.players:
                                        if player.is_human or player.seat_index == game_manager.reaction_source_player:
                                            continue
                                        rects = renderer.get_card_rects(player.seat_index, game_manager)
                                        for slot_idx, rect in enumerate(rects):
                                            if rect.collidepoint(mouse_pos) and player.hand[slot_idx] is not None:
                                                result = game_manager.attempt_reactive_drop_opponent(
                                                    human_idx, player.seat_index, slot_idx, react_give_slot
                                                )
                                                if result.get('success'):
                                                    opp_pos = renderer.get_card_center(player.seat_index, slot_idx, game_manager)
                                                    give_pos = renderer.get_card_center(human_idx, react_give_slot, game_manager)
                                                    renderer.push_pair_fly_animation(game_manager, opp_pos, result['result'].get('opponent_card'), give_pos, None)
                                                    game_manager.check_game_over()
                                                    awaiting = None
                                                    react_give_slot = None
                                                    status_message = ""
                                                    turn_end_timer = ANIM_REACTIVE_DROP_DURATION + 0.1
                                                else:
                                                    awaiting = None
                                                    react_give_slot = None
                                                    status_message = "Wrong call! Penalty drawn."
                                                    game_manager.end_reaction_window()
                                                    turn_end_timer = ANIM_PENALTY_DRAW_DURATION + 0.2
                                                break
                                        else:
                                            continue
                                        break

                        else:
                            human_player = game_manager.players[human_idx]
                            if human_idx is not None and cp.is_human and dragging_slot is None:
                                card_rects = renderer.get_card_rects(human_idx, game_manager)
                                for slot_idx, rect in enumerate(card_rects):
                                    if rect.collidepoint(mouse_pos) and human_player.hand[slot_idx] is not None:
                                        center = renderer.get_card_center(human_idx, slot_idx, game_manager)
                                        dragging_slot = slot_idx
                                        drag_offset = (
                                            mouse_pos[0] - center[0],
                                            mouse_pos[1] - center[1],
                                        )
                                        renderer.dragging_card = slot_idx
                                        renderer.drag_pos = mouse_pos
                                        break

                elif event.type == pygame.MOUSEMOTION:
                    if dragging_slot is not None:
                        renderer.drag_pos = mouse_pos

                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    if dragging_slot is not None and human_idx is not None:
                        human_player = game_manager.players[human_idx]
                        num_players = len(game_manager.players)
                        bounds = _player_area_bounds(human_player.seat_index, num_players)
                        drop_cx = mouse_pos[0] - drag_offset[0]
                        drop_cy = mouse_pos[1] - drag_offset[1]
                        clamped = _clamp_to_bounds(drop_cx, drop_cy, bounds)
                        human_player.card_positions[dragging_slot] = clamped
                        dragging_slot = None
                        renderer.dragging_card = None
                        renderer.drag_pos = None

            elif current_screen == "game_over":
                action = game_over_screen.handle_event(event)
                if action == "play_again":
                    game_over_result = None
                    current_screen = "setup"
                    setup_screen = SetupScreen(screen)
                elif action == "menu":
                    game_over_result = None
                    current_screen = "menu"

        if current_screen == "game" and game_manager is not None:
            cp = game_manager.current_player()

            if game_manager.state == GameState.REACTION_WINDOW and not cp.is_human:
                if renderer.is_animating():
                    pass
                else:
                    all_responded = True
                    for ai_p in game_manager.players:
                        if ai_p.is_human:
                            continue
                        if game_manager.reaction_responded:
                            break
                        ai_decider = AIDecider(ai_p, {'players': game_manager.players})
                        if game_manager.reaction_rank:
                            reaction = ai_decider.should_react_to_discard(game_manager.reaction_rank)
                            if reaction:
                                all_responded = False
                                if reaction['type'] == 'react_drop_self':
                                    result = game_manager.attempt_reactive_drop_self(ai_p.seat_index, reaction['slot'])
                                    if result.get('success'):
                                        pos = renderer.get_card_center(ai_p.seat_index, reaction['slot'], game_manager)
                                        renderer.push_ai_pair_animation(game_manager, pos)
                                        game_manager.check_game_over()
                                elif reaction['type'] == 'react_drop_opponent':
                                    result = game_manager.attempt_reactive_drop_opponent(
                                        ai_p.seat_index,
                                        reaction['opponent_index'],
                                        reaction['opponent_slot'],
                                        reaction['give_slot'],
                                    )
                                    if result.get('success'):
                                        opp_pos = renderer.get_card_center(reaction['opponent_index'], reaction['opponent_slot'], game_manager)
                                        renderer.push_ai_pair_animation(game_manager, opp_pos)
                                        game_manager.check_game_over()
                    if not game_manager.reaction_responded and not renderer.is_animating():
                        game_manager.end_reaction_window()
                    elif game_manager.reaction_responded and not renderer.is_animating():
                        game_manager.end_reaction_window()

            elif not cp.is_human and turn_end_timer <= 0 and game_manager.state != GameState.REACTION_WINDOW:
                if renderer.is_animating():
                    pass
                else:
                    ai_timer += dt
                    ai_idx = cp.seat_index

                    if ai_phase == 'idle':
                        ai_phase = 'drawing'
                        ai_timer = 0.0

                    if ai_phase == 'drawing' and ai_timer >= game_settings.ai_delay:
                        should_declare = AIDecider(cp, {'players': game_manager.players}).should_declare()
                        if should_declare:
                            game_manager.execute_player_action("declare", {})
                            game_manager.resolve_declaration()
                            game_over_result = game_manager.declaration_result
                            current_screen = "game_over"
                            ai_phase = 'idle'
                            ai_timer = 0
                            continue
                        game_manager.draw_card()
                        renderer.push_draw_animation(game_manager)
                        ai_phase = 'acting'
                        ai_timer = 0.0

                    if ai_phase == 'acting' and ai_timer >= 0.5:
                        ai = AIDecider(cp, {'players': game_manager.players})
                        drawn = game_manager.drawn_card
                        if drawn:
                            decision = ai.choose_action(drawn)
                            action_key = decision['action']

                            if action_key == 'play_power':
                                target_info = _ai_power_target(ai, cp, game_manager.players, drawn)
                                power = drawn.power

                                if power in ('peek_self', 'peek_opponent'):
                                    game_manager.execute_player_action('play_power', {
                                        'card': drawn,
                                        'target_info': target_info,
                                    })
                                    if power == 'peek_self' and target_info:
                                        slot = target_info.get('slot', 0)
                                        if cp.hand[slot] is not None:
                                            cp.known_cards[slot] = cp.hand[slot]
                                        renderer.push_ai_peek_animation(ai_idx, slot, game_manager)
                                    elif power == 'peek_opponent' and target_info:
                                        p_idx = target_info.get('player_index', 0)
                                        s_idx = target_info.get('slot', 0)
                                        target_p = next((p for p in game_manager.players if p.seat_index == p_idx), None)
                                        if target_p and target_p.hand[s_idx] is not None:
                                            cp.known_opponent_cards[(p_idx, s_idx)] = target_p.hand[s_idx]
                                        renderer.push_ai_peek_animation(p_idx, s_idx, game_manager)

                                elif power == 'skip':
                                    game_manager.execute_player_action('play_power', {
                                        'card': drawn,
                                        'target_info': target_info,
                                    })
                                    game_manager.skip_next = True
                                    renderer.push_ai_skip_animation(game_manager, ai_idx)

                                elif power in ('unseen_swap', 'seen_swap'):
                                    my_slot = target_info.get('my_slot', 0)
                                    target_player_idx = target_info.get('target_player', 0)
                                    their_slot = target_info.get('their_slot', 0)
                                    their_card_before = None
                                    if power == 'seen_swap':
                                        target_p = next((p for p in game_manager.players if p.seat_index == target_player_idx), None)
                                        if target_p:
                                            their_card_before = target_p.hand[their_slot]
                                    my_pos = renderer.get_card_center(ai_idx, my_slot, game_manager)
                                    their_pos = renderer.get_card_center(target_player_idx, their_slot, game_manager)
                                    game_manager.execute_player_action('play_power', {
                                        'card': drawn,
                                        'target_info': target_info,
                                    })
                                    if power == 'seen_swap':
                                        renderer.push_seen_swap_animation(
                                            game_manager, my_slot, target_player_idx, their_slot,
                                            their_card_before,
                                        )
                                    else:
                                        renderer.push_unseen_swap_animation(
                                            game_manager, my_slot, target_player_idx, their_slot,
                                        )

                                else:
                                    game_manager.execute_player_action('play_power', {
                                        'card': drawn,
                                        'target_info': target_info,
                                    })

                            elif action_key == 'swap':
                                slot = decision.get('target_slot', ai.estimate_worst_slot())
                                renderer.push_ai_swap_animation(game_manager, ai_idx, slot)
                                game_manager.execute_player_action('swap', {
                                    'my_slot': slot,
                                    'drawn_card': drawn,
                                })

                            elif action_key == 'discard':
                                renderer.push_discard_animation(game_manager)
                                game_manager.execute_player_action('discard', {'drawn_card': drawn})
                                game_manager.start_reaction_window(drawn.rank, ai_idx, drawn)

                            elif action_key == 'pair_own':
                                slot = decision.get('target_slot', 0)
                                pair_pos = renderer.get_card_center(ai_idx, slot, game_manager)
                                drawn_pos = DRAWN_CARD_POS
                                renderer.push_ai_pair_animation(game_manager, pair_pos, drawn_pos)
                                game_manager.execute_player_action('pair_own', {
                                    'player_slot': slot,
                                    'drawn_card': drawn,
                                })

                            elif action_key == 'pair_opponent':
                                give_slot = ai.choose_card_to_give()
                                opp_slot = _find_opponent_slot(cp, game_manager.players, decision['target_player'], drawn.rank)
                                opp_idx = decision.get('target_player', 0)
                                opp_pos = renderer.get_card_center(opp_idx, opp_slot, game_manager)
                                give_pos = renderer.get_card_center(ai_idx, give_slot, game_manager)
                                renderer.push_ai_pair_animation(game_manager, opp_pos, give_pos)
                                game_manager.execute_player_action('pair_opponent', {
                                    'opponent_index': decision['target_player'],
                                    'opponent_slot': opp_slot,
                                    'drawn_card': drawn,
                                    'give_slot': give_slot,
                                })

                        ai_phase = 'ending'
                        ai_timer = 0.0

                    if ai_phase == 'ending' and ai_timer >= 0.3:
                        _schedule_end_turn(game_manager, game_settings, renderer)
                        ai_phase = 'idle'
                        ai_timer = 0.0
                        awaiting = None
                        selected_slot = None
                        pair_opponent_give_slot = None
                        status_message = ""
                        if game_manager.state == GameState.GAME_OVER:
                            game_over_result = game_manager.declaration_result
                            current_screen = "game_over"

        if current_screen == "game" and game_manager is not None:
            if game_manager.state == GameState.GAME_OVER:
                if game_over_result is None:
                    game_over_result = game_manager.declaration_result or {
                        'winner': game_manager.winner,
                        'scores': {p.seat_index: p.score for p in game_manager.players},
                        'declarer_won': False,
                        'auto_win': False,
                    }
                current_screen = "game_over"
                continue

        if game_manager and game_manager.current_player().is_human and game_manager.state == GameState.TURN_START:
            awaiting = None
            selected_slot = None
            pair_opponent_give_slot = None
            swap_second_click = False
            status_message = ""

        if current_screen == "game_over" and prev_screen == "game" and game_manager is not None:
            _finalize_game_stats(prof, game_manager, game_over_result, game_meta,
                                  game_start_time, toasts, particles, achievement_queue)
        prev_screen = current_screen

        screen.fill(BG_GREEN)

        if current_screen == "menu":
            menu_screen.draw()

        elif current_screen == "profile":
            profile_screen.draw(prof)

        elif current_screen == "how_to_play":
            how_to_screen.draw()

        elif current_screen == "setup":
            setup_screen.draw()

        elif current_screen == "peek":
            peek_screen.draw(game_manager)
            result = peek_screen.update(dt)
            if result == "peek_done":
                game_manager.start_peek_phase()
                awaiting = None
                selected_slot = None
                ai_phase = 'idle'
                ai_timer = 0
                current_screen = "game"

        elif current_screen == "game":
            if game_manager is None:
                current_screen = "menu"
            else:
                cp = game_manager.current_player()
                human_idx = _get_human_index(game_manager)
                action_buttons = _build_action_buttons(game_manager, ui_font, game_settings) if cp.is_human or game_manager.state == GameState.REACTION_WINDOW else {}

                if game_manager.state == GameState.REACTION_WINDOW:
                    if human_idx is not None:
                        action_buttons = _build_action_buttons(game_manager, ui_font, game_settings)

                cancel_btn = None
                if awaiting is not None and cp.is_human:
                    cancel_btn = _build_cancel_button("Cancel", ui_font)

                if cp.is_human:
                    ai_decider_for_hints = AIDecider(cp, {'players': game_manager.players})
                    dim_keys, pulse_keys = hint_engine.evaluate_actions(
                        game_manager, action_buttons, ai_decider=ai_decider_for_hints,
                    )
                    renderer._dim_actions = dim_keys
                    renderer._pulse_actions = pulse_keys
                    renderer._action_keybinds = {
                        "draw": "1", "declare": "2", "swap": "3",
                        "discard": "4", "pair_own": "5",
                        "play_power": "6", "pair_opponent": "7",
                    }
                else:
                    renderer._dim_actions = set()
                    renderer._pulse_actions = set()
                    renderer._action_keybinds = {}

                renderer.draw(game_manager, mouse_pos, action_buttons, cancel_btn, status_message, awaiting)
                hint_engine.draw_recent_discards(screen, getattr(game_manager, "discard_pile", []))
                hint_engine.draw_coach(screen)

                power_label, power_color = hint_engine.power_label_for_drawn(game_manager)
                if power_label and game_manager.drawn_card:
                    label_surf = ui_font.render(f"Power: {power_label}", True, power_color)
                    pad = 8
                    bx = DRAWN_CARD_POS[0] - label_surf.get_width() // 2 - pad
                    by = DRAWN_CARD_POS[1] - 90
                    bg = pygame.Surface((label_surf.get_width() + pad * 2,
                                         label_surf.get_height() + 8), pygame.SRCALPHA)
                    pygame.draw.rect(bg, (0, 0, 0, 180), bg.get_rect(), border_radius=6)
                    pygame.draw.rect(bg, power_color, bg.get_rect(), 1, border_radius=6)
                    screen.blit(bg, (bx, by))
                    screen.blit(label_surf, (bx + pad, by + 4))

                if notification_text:
                    renderer.draw_reaction_result(notification_text, screen)

                if game_settings and game_settings.shuffle_enabled and cp.is_human and human_idx is not None:
                    num_players = len(game_manager.players)
                    seat_pos = _get_seat_position(human_idx, num_players)
                    shuffle_btn = _build_shuffle_button(game_manager.players[human_idx], seat_pos, ui_font)
                    hovered = shuffle_btn['rect'].collidepoint(mouse_pos)
                    color = shuffle_btn['hover_color'] if hovered else shuffle_btn['color']
                    pygame.draw.rect(screen, color, shuffle_btn['rect'], border_radius=6)
                    pygame.draw.rect(screen, (30, 30, 35), shuffle_btn['rect'], 1, border_radius=6)
                    btn_font = shuffle_btn['font']
                    text_surf = btn_font.render(shuffle_btn['text'], True, TEXT_WHITE)
                    text_rect = text_surf.get_rect(center=shuffle_btn['rect'].center)
                    screen.blit(text_surf, text_rect)

                if game_manager.state == GameState.REACTION_WINDOW:
                    font = pygame.font.SysFont("arial", 28, bold=True)
                    remaining = max(0, game_manager.reaction_timer)
                    banner_text = f"REACTION! Drop a {game_manager.reaction_rank}? ({remaining:.1f}s)"
                    banner_surf = font.render(banner_text, True, GOLD)
                    banner_rect = banner_surf.get_rect(center=(SCREEN_WIDTH // 2, STATUS_BAR_H + 30))
                    bg_rect = banner_rect.inflate(40, 16)
                    bg_surf = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
                    pygame.draw.rect(bg_surf, (0, 0, 0, 200), bg_surf.get_rect(), border_radius=10)
                    pygame.draw.rect(bg_surf, (*GOLD, 120), bg_surf.get_rect(), 2, border_radius=10)
                    screen.blit(bg_surf, bg_rect.topleft)
                    screen.blit(banner_surf, banner_rect)

        elif current_screen == "game_over":
            if game_over_result is None and game_manager:
                game_over_result = game_manager.declaration_result or {
                    'winner': game_manager.winner,
                    'scores': {p.seat_index: p.score for p in game_manager.players},
                    'declarer_won': False,
                    'auto_win': False,
                }
            game_over_screen.draw(game_manager, game_over_result or {})

        if current_screen == "game":
            if settings_open and game_manager:
                settings_menu.draw(game_settings, game_manager, mouse_pos)
            elif game_manager:
                renderer.draw_gear_icon(mouse_pos, settings_open)

        particles.draw(screen)
        edge_flash.draw(screen)
        if current_screen == "game":
            screen.blit(vignette.get(0.45), (0, 0))
        if current_screen == "game" and game_settings.streamer_mode:
            stream_cover = pygame.Surface((SCREEN_WIDTH, 220), pygame.SRCALPHA)
            stream_cover.fill((0, 0, 0, 220))
            label_font = pygame.font.SysFont("arial", 22, bold=True)
            label = label_font.render("STREAM-SAFE - Hand hidden", True, (200, 200, 200))
            stream_cover.blit(label, (24, 96))
            screen.blit(stream_cover, (0, SCREEN_HEIGHT - 220))
        if game_settings.captions:
            captions.draw(screen)
        toasts.draw(screen)

        if paused and current_screen == "game":
            pause.draw(screen)

        if tutorial.active:
            tutorial.draw(screen)
        if first_launch.active:
            first_launch.draw(screen)
        if access_panel.active:
            access_panel.draw(screen, prof, game_settings)

        display.set_shake(cam.offset())
        display.present()

    pygame.quit()
    sys.exit()


def _resume_ai_turn():
    pass


def _new_game_meta(player_count, configs, gs):
    diffs = [c.get("difficulty", "medium") for c in configs if not c.get("is_human")]
    return {
        "player_count": player_count,
        "ai_count": sum(1 for c in configs if not c.get("is_human")),
        "all_hard_ai": len(diffs) > 0 and all(d == "hard" for d in diffs),
        "pairs_made": 0,
        "pairs_on_opponents": 0,
        "powers_used": 0,
        "reactive_correct": 0,
        "reactive_wrong": 0,
        "cards_drawn": 0,
        "won": False,
        "declared_won": False,
        "declared_lost": False,
        "auto_win": False,
        "final_score_human": None,
        "play_seconds": 0.0,
    }


def _finalize_game_stats(prof, gm, result, meta, game_start_time, toasts, particles, queue):
    if not result:
        return
    play_seconds = max(0.0, pygame.time.get_ticks() / 1000.0 - game_start_time)
    human = next((p for p in gm.players if p.is_human), None)
    winner_idx = result.get("winner")
    won = (human is not None and winner_idx == human.seat_index)
    declared_won = bool(result.get("declarer_won")) and won
    declared_lost = bool(result.get("declarer_won") is False
                          and result.get("declarer_index") == (human.seat_index if human else -1))
    auto_win = bool(result.get("auto_win")) and won
    final_score = None
    if human is not None:
        scores = result.get("scores", {})
        final_score = scores.get(human.seat_index)

    meta_out = dict(meta)
    meta_out["won"] = won
    meta_out["declared_won"] = declared_won
    meta_out["declared_lost"] = declared_lost
    meta_out["auto_win"] = auto_win
    meta_out["final_score_human"] = final_score
    meta_out["play_seconds"] = play_seconds

    profile_mod.record_game_result(prof, meta_out)
    newly = profile_mod.evaluate_achievements(prof, meta_out)
    profile_mod.save(prof)

    for key in newly:
        rec = prof.achievements.get(key, {})
        title = rec.get("title", key)
        toasts.push(f"Achievement: {title}", kind="achievement", icon="★", life=4.0)
        particles.burst_achievement(960, 540)
        audio.play("achievement")
        queue.append(key)


def _react_to_log_entry(entry, particles, toasts, gm, renderer,
                        cam=None, edge_flash=None, timewarp=None,
                        hints=None, last_human_action=None,
                        captions=None):
    def cap(key):
        if captions is not None:
            text = audio.caption(key)
            if text:
                captions.push(text)
    text = entry if isinstance(entry, str) else str(entry)
    low = text.lower()

    try:
        from config import DECK_CENTER, DRAWN_CARD_POS, DISCARD_POS
    except ImportError:
        DECK_CENTER = (640, 400)
        DRAWN_CARD_POS = (860, 400)
        DISCARD_POS = (750, 400)

    if "drew" in low and "as penalty" not in low:
        audio.play("draw"); cap("draw")
    elif "discarded" in low or "discards" in low:
        audio.play("place"); cap("place")
        x, y = DISCARD_POS
        particles.trail(x, y)
        if cam: cam.kick(amp=1.5, duration=0.10)
        if hints and "you " in low:
            drawn = getattr(gm, "drawn_card", None)
            hints.evaluate_post_turn(gm, {"kind": "discard"}, drawn)
    elif "paired" in low or "pairs" in low:
        audio.play("pair"); cap("pair")
        x, y = DRAWN_CARD_POS
        particles.burst_pair(x, y)
        toasts.push("Pair!", kind="success", icon="*", life=1.6)
        if cam: cam.kick(amp=2.5, duration=0.18)
    elif "peek" in low:
        audio.play("power_peek"); cap("power_peek")
        particles.burst_power(*DECK_CENTER, color=(111, 207, 227))
    elif "swap" in low and "swapped" in low:
        audio.play("power_swap"); cap("power_swap")
        particles.burst_power(*DECK_CENTER, color=(120, 220, 140))
        if cam: cam.kick(amp=1.5, duration=0.12)
    elif "skip" in low and ("skipped" in low or "skips" in low):
        audio.play("power_skip"); cap("power_skip")
        if cam: cam.kick(amp=2.0, duration=0.14)
    elif "declared" in low or "declares" in low:
        audio.play("declare"); cap("declare")
        toasts.push("Declared!", kind="warn", icon="!", life=2.6)
        particles.burst_declare(960, 540)
        if cam: cam.kick(amp=4.0, duration=0.45, freq=18)
        if edge_flash: edge_flash.fire(duration=0.9, thickness=36)
        if timewarp: timewarp.slowmo(factor=0.45, duration=1.4)
    elif "wrong card" in low or "penalty" in low:
        audio.play("wrong_react"); cap("wrong_react")
        particles.burst_penalty(960, 540)
        if cam: cam.kick(amp=4.5, duration=0.30, freq=28)
        if edge_flash:
            edge_flash.fire(color=(212, 72, 72), duration=0.5, thickness=24)
    elif "reaction" in low and ("opens" in low or "begins" in low or "window" in low):
        audio.play("react_open"); cap("react_open")
        if edge_flash: edge_flash.fire(duration=0.6, thickness=28)
    elif "self-paired" in low:
        audio.play("pair"); cap("pair")
        x, y = DRAWN_CARD_POS
        particles.burst_pair(x, y)
        toasts.push("Self-Pair!", kind="success", icon="*", life=1.6)
        if cam: cam.kick(amp=3.0, duration=0.20)
    elif "shuffled their cards" in low:
        audio.play("shuffle")
        particles.burst_power(*DECK_CENTER, color=(180, 140, 255))
        toasts.push("Shuffled!", kind="info", icon="#", life=1.2)
        if cam: cam.kick(amp=2.0, duration=0.15)
    elif "dropped" in low and "match" in low:
        audio.play("pair"); cap("pair")
        x, y = DECK_CENTER
        particles.burst_pair(x, y)
        toasts.push("Match!", kind="success", icon="*", life=1.6)
        if cam: cam.kick(amp=3.0, duration=0.20)
    elif "called opponent" in low:
        audio.play("pair"); cap("pair")
        x, y = DECK_CENTER
        particles.burst_pair(x, y)
        toasts.push("Called!", kind="success", icon="*", life=1.6)
        if cam: cam.kick(amp=3.0, duration=0.20)


if __name__ == "__main__":
    asyncio.run(main())

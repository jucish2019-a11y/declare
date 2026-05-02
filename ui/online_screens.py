"""Online multiplayer screens: Nickname → Online menu → Room lobby.

These mirror the existing screen pattern (`draw()` + `handle_event()`),
producing string action codes consumed by main.py. The screens are intentionally
simple: they do not drive any networking themselves — they only emit user intent
back to main.py, which talks to the OnlineClient.
"""
from __future__ import annotations

import pygame

from config import (
    SCREEN_WIDTH, SCREEN_HEIGHT, TEXT_WHITE, GOLD, TEXT_DIM,
    TITLE_FONT_SIZE, SUBTITLE_FONT_SIZE, UI_FONT_SIZE, SMALL_FONT_SIZE,
    SWAP_GREEN, SWAP_GREEN_HOVER, DECLARE_RED, DECLARE_RED_HOVER,
    PEEK_BLUE, PEEK_BLUE_HOVER, DISCARD_ORANGE, DISCARD_ORANGE_HOVER,
    PAIR_TEAL, PAIR_TEAL_HOVER, get_mobile_scale,
)
import typography as typo

from ui.screens import Button, _screen_background


# ----------------------------------------------------------------- helpers

def _draw_panel_bg(screen):
    screen.blit(_screen_background(), (0, 0))


def _draw_title(screen, title_font, text, y=200):
    import theme as theme_mod
    th = theme_mod.active()
    for offset, alpha in ((4, 70), (0, 255)):
        col = th.brass_300 if alpha == 255 else th.brass_700
        s = title_font.render(text, True, col)
        s.set_alpha(alpha)
        screen.blit(s, s.get_rect(center=(SCREEN_WIDTH // 2 + offset, y + offset)))


def _draw_subtitle(screen, font, text, y, color=None):
    import theme as theme_mod
    th = theme_mod.active()
    s = font.render(text, True, color or th.brass_300)
    screen.blit(s, s.get_rect(center=(SCREEN_WIDTH // 2, y)))


def _draw_text_input(screen, rect, text, font, *, focused, placeholder=""):
    """Brass-trimmed text input. Returns nothing; just paints."""
    import theme as theme_mod
    th = theme_mod.active()
    panel = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    pygame.draw.rect(panel, (0, 0, 0, 200), panel.get_rect(), border_radius=12)
    screen.blit(panel, rect.topleft)
    pygame.draw.rect(screen,
                     th.brass_300 if focused else th.brass_500,
                     rect, 2, border_radius=12)
    show = text if text else placeholder
    color = TEXT_WHITE if text else TEXT_DIM
    surf = font.render(show, True, color)
    screen.blit(surf, surf.get_rect(midleft=(rect.left + 24, rect.centery)))
    if focused and (pygame.time.get_ticks() // 500) % 2 == 0 and text:
        # Caret after the text.
        caret_x = rect.left + 24 + surf.get_width() + 4
        pygame.draw.line(screen, TEXT_WHITE,
                         (caret_x, rect.top + 14),
                         (caret_x, rect.bottom - 14), 2)


# ----------------------------------------------------------------- nickname

NICKNAME_MAX = 20


class NicknameScreen:
    """One-shot nickname prompt. Emits ('continue', nickname) on confirm."""

    def __init__(self, screen, initial: str = ""):
        self.screen = screen
        scale = get_mobile_scale()
        self.title_font = typo.display_bold(int(TITLE_FONT_SIZE * 1.0))
        self.subtitle_font = typo.header_italic(SUBTITLE_FONT_SIZE)
        self.input_font = typo.body(int(UI_FONT_SIZE * 1.1 * scale))
        self.button_font = typo.body_bold(int(UI_FONT_SIZE * scale))
        self.text = initial[:NICKNAME_MAX]
        self.input_rect = pygame.Rect(0, 0, 720, 96)
        self.input_rect.center = (SCREEN_WIDTH // 2, 720)
        self.continue_button = Button(
            SCREEN_WIDTH // 2 + 200, 880, int(280 * scale), int(64 * scale),
            "Continue", SWAP_GREEN, SWAP_GREEN_HOVER, icon="continue",
        )
        self.back_button = Button(
            SCREEN_WIDTH // 2 - 200, 880, int(280 * scale), int(64 * scale),
            "Back", DECLARE_RED, DECLARE_RED_HOVER, icon="back",
        )
        self.buttons = [self.continue_button, self.back_button]

    def draw(self):
        _draw_panel_bg(self.screen)
        _draw_title(self.screen, self.title_font, "Enter Nickname", y=320)
        _draw_subtitle(self.screen, self.subtitle_font,
                       "Other players will see this name in the room.", y=420)
        _draw_text_input(self.screen, self.input_rect, self.text,
                          self.input_font, focused=True,
                          placeholder="e.g. Alice")
        for b in self.buttons:
            b.draw(self.screen, self.button_font)

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            for b in self.buttons:
                b.update_hover(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.continue_button.is_clicked(event.pos) and self.text.strip():
                return ("continue", self.text.strip())
            if self.back_button.is_clicked(event.pos):
                return ("back", None)
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                if self.text.strip():
                    return ("continue", self.text.strip())
            elif event.key == pygame.K_ESCAPE:
                return ("back", None)
            elif event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.unicode and event.unicode.isprintable():
                if len(self.text) < NICKNAME_MAX:
                    self.text += event.unicode
        return None


# ----------------------------------------------------------------- online menu

class OnlineMenuScreen:
    """Main online hub: Create / Join (with code) / Random Match (Phase 2)."""

    def __init__(self, screen):
        self.screen = screen
        scale = get_mobile_scale()
        self.title_font = typo.display_bold(int(TITLE_FONT_SIZE * 1.0))
        self.subtitle_font = typo.header_italic(SUBTITLE_FONT_SIZE)
        self.button_font = typo.body_bold(int(UI_FONT_SIZE * scale))
        self.input_font = typo.body(int(UI_FONT_SIZE * 1.1 * scale))
        self.status_font = typo.body(int(SMALL_FONT_SIZE * scale))
        self.code_input = ""
        self.code_focus = False
        self.code_input_rect = pygame.Rect(0, 0, 360, 80)
        self.code_input_rect.center = (SCREEN_WIDTH // 2 + 80, 760)

        cx = SCREEN_WIDTH // 2
        bw = int(420 * scale)
        bh = int(72 * scale)
        self.create_button = Button(cx, 600, bw, bh,
                                    "Create Private Room",
                                    SWAP_GREEN, SWAP_GREEN_HOVER)
        self.join_button = Button(cx - 240, 760, int(180 * scale), bh,
                                   "Join", PEEK_BLUE, PEEK_BLUE_HOVER)
        self.random_button = Button(cx, 920, bw, bh,
                                     "Random Match (coming soon)",
                                     PAIR_TEAL, PAIR_TEAL_HOVER)
        self.back_button = Button(120, 60, int(140 * scale), int(40 * scale),
                                   "Back", DECLARE_RED, DECLARE_RED_HOVER, icon="back")
        self.buttons = [self.create_button, self.join_button,
                         self.random_button, self.back_button]

        self.status_text: str = ""

    def set_status(self, text: str) -> None:
        self.status_text = text

    def draw(self):
        _draw_panel_bg(self.screen)
        _draw_title(self.screen, self.title_font, "Online", y=320)
        _draw_subtitle(self.screen, self.subtitle_font,
                       "Create a private room or join one with a code.",
                       y=420)

        # Create
        self.create_button.draw(self.screen, self.button_font)

        # Join: code input + Join button
        _draw_text_input(self.screen, self.code_input_rect, self.code_input,
                          self.input_font, focused=self.code_focus,
                          placeholder="ROOM CODE")
        self.join_button.draw(self.screen, self.button_font)

        # Random Match (disabled-looking)
        self.random_button.draw(self.screen, self.button_font)
        veil = pygame.Surface(self.random_button.rect.size, pygame.SRCALPHA)
        pygame.draw.rect(veil, (0, 0, 0, 110), veil.get_rect(), border_radius=12)
        self.screen.blit(veil, self.random_button.rect.topleft)

        # Status (e.g. "connecting..." / "connection failed")
        if self.status_text:
            s = self.status_font.render(self.status_text, True, GOLD)
            self.screen.blit(s, s.get_rect(center=(SCREEN_WIDTH // 2, 1080)))

        self.back_button.draw(self.screen, self.button_font)

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            for b in self.buttons:
                b.update_hover(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.code_focus = self.code_input_rect.collidepoint(event.pos)
            if self.create_button.is_clicked(event.pos):
                return ("create_room", None)
            if self.join_button.is_clicked(event.pos) and self.code_input.strip():
                return ("join_room", self.code_input.strip().upper())
            if self.random_button.is_clicked(event.pos):
                return ("random_match", None)  # main.py shows a "coming soon" toast
            if self.back_button.is_clicked(event.pos):
                return ("back", None)
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return ("back", None)
            if self.code_focus:
                if event.key == pygame.K_BACKSPACE:
                    self.code_input = self.code_input[:-1]
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    if self.code_input.strip():
                        return ("join_room", self.code_input.strip().upper())
                elif event.unicode and event.unicode.isalnum():
                    if len(self.code_input) < 6:
                        self.code_input += event.unicode.upper()
        return None


# ----------------------------------------------------------------- lobby

class OnlineLobbyScreen:
    """Pre-game lobby: shows the room code, players, host controls."""

    def __init__(self, screen):
        self.screen = screen
        scale = get_mobile_scale()
        self.title_font = typo.display_bold(int(TITLE_FONT_SIZE * 0.9))
        self.subtitle_font = typo.header_italic(SUBTITLE_FONT_SIZE)
        self.code_font = typo.display_bold(int(TITLE_FONT_SIZE * 1.6))
        self.label_font = typo.body(int(UI_FONT_SIZE * scale))
        self.button_font = typo.body_bold(int(UI_FONT_SIZE * scale))
        self.note_font = typo.body(int(SMALL_FONT_SIZE * scale))

        cx = SCREEN_WIDTH // 2
        bw = int(280 * scale)
        bh = int(64 * scale)
        self.start_button = Button(cx + 200, 1180, bw, bh,
                                    "Start Game",
                                    SWAP_GREEN, SWAP_GREEN_HOVER, icon="start")
        self.leave_button = Button(cx - 200, 1180, bw, bh,
                                    "Leave",
                                    DECLARE_RED, DECLARE_RED_HOVER, icon="back")
        self.ai_toggle_rect = pygame.Rect(0, 0, 320, 56)
        self.ai_toggle_rect.center = (cx, 1080)
        self.buttons = [self.start_button, self.leave_button]

        self.lobby_payload: dict | None = None
        self.your_seat: int = -1
        self.status_text: str = ""

    def set_lobby(self, payload: dict, your_seat: int) -> None:
        self.lobby_payload = payload
        self.your_seat = your_seat

    def set_status(self, text: str) -> None:
        self.status_text = text

    def draw(self):
        import theme as theme_mod
        th = theme_mod.active()
        _draw_panel_bg(self.screen)

        if self.lobby_payload is None:
            _draw_title(self.screen, self.title_font, "Connecting...", y=320)
            return

        code = self.lobby_payload.get("code", "----")
        host_seat = self.lobby_payload.get("host_seat", 0)
        is_host = self.your_seat == host_seat
        ai_fill = bool(self.lobby_payload.get("ai_fill", True))
        max_players = int(self.lobby_payload.get("max_players", 4))
        players = self.lobby_payload.get("players", [])

        _draw_title(self.screen, self.title_font, "Room", y=200)
        _draw_subtitle(self.screen, self.subtitle_font,
                       "Share this code with friends to join.", y=300)

        # Big room code in brass.
        code_surf = typo.render_with_letter_spacing(
            self.code_font, code, th.brass_300, spacing_px=20,
        )
        self.screen.blit(code_surf,
                          code_surf.get_rect(center=(SCREEN_WIDTH // 2, 460)))

        # Player slots (one row per seat).
        row_y = 600
        seat_to_player = {int(p["seat"]): p for p in players}
        for seat in range(max_players):
            entry = seat_to_player.get(seat)
            row_rect = pygame.Rect(
                SCREEN_WIDTH // 2 - 360, row_y - 28, 720, 56)
            pygame.draw.rect(self.screen, (*th.panel_bg, 220), row_rect,
                              border_radius=10)
            pygame.draw.rect(self.screen, th.brass_500, row_rect, 1, border_radius=10)
            seat_label = self.label_font.render(f"Seat {seat + 1}", True, th.text_dim)
            self.screen.blit(seat_label,
                              seat_label.get_rect(midleft=(row_rect.left + 24, row_rect.centery)))
            if entry is not None:
                name = entry.get("nickname", f"P{seat+1}")
                tag = " (you)" if seat == self.your_seat else (" (host)" if seat == host_seat else "")
                surf = self.label_font.render(name + tag, True, TEXT_WHITE)
                self.screen.blit(surf, surf.get_rect(midleft=(row_rect.left + 200, row_rect.centery)))
            else:
                tag = "AI fill" if ai_fill else "(empty)"
                col = th.brass_300 if ai_fill else th.text_dim
                surf = self.label_font.render(tag, True, col)
                self.screen.blit(surf, surf.get_rect(midleft=(row_rect.left + 200, row_rect.centery)))
            row_y += 76

        # AI fill toggle (host only).
        if is_host:
            tcol = th.brass_300 if ai_fill else th.text_dim
            pygame.draw.rect(self.screen, (*th.panel_bg, 220),
                              self.ai_toggle_rect, border_radius=10)
            pygame.draw.rect(self.screen, tcol, self.ai_toggle_rect,
                              2, border_radius=10)
            txt = f"AI fill empty seats: {'ON' if ai_fill else 'OFF'}"
            s = self.label_font.render(txt, True, tcol)
            self.screen.blit(s, s.get_rect(center=self.ai_toggle_rect.center))

        # Buttons.
        if is_host:
            self.start_button.draw(self.screen, self.button_font)
        else:
            note = self.note_font.render("Waiting for host to start...", True, GOLD)
            self.screen.blit(note,
                              note.get_rect(center=(SCREEN_WIDTH // 2 + 200, 1212)))
        self.leave_button.draw(self.screen, self.button_font)

        # Status banner.
        if self.status_text:
            s = self.note_font.render(self.status_text, True, GOLD)
            self.screen.blit(s, s.get_rect(center=(SCREEN_WIDTH // 2, 1280)))

    def handle_event(self, event):
        if self.lobby_payload is None:
            return None
        host_seat = self.lobby_payload.get("host_seat", 0)
        is_host = self.your_seat == host_seat
        if event.type == pygame.MOUSEMOTION:
            for b in self.buttons:
                b.update_hover(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if is_host and self.ai_toggle_rect.collidepoint(event.pos):
                return ("toggle_ai_fill", None)
            if is_host and self.start_button.is_clicked(event.pos):
                return ("start_game", None)
            if self.leave_button.is_clicked(event.pos):
                return ("leave", None)
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            return ("leave", None)
        return None

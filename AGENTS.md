# Declare — Agent Context

## Project Overview

**Declare** is a 2-4 player card game of memory, strategy, and bluffing, built in **Python + Pygame** and deployed to web via **Pygbag (WASM)**.

- **Repo:** https://github.com/jucish2019-a11y/declare
- **Tech:** Python 3.11+, pygame >= 2.5.0, pygame-ce >= 2.5.0
- **Web deploy:** GitHub Pages via pygbag (`python build_web.py`)
- **Logical resolution:** 2560x1440 (scaled to window with letterboxing)

## Recent Work (Session History)

### 1. Responsive Design Fixes (Completed)
- Aspect-ratio letterboxing in `main.py` (`present()`)
- Mobile touch targets increased (`get_mobile_scale()` 1.15x → 1.5x)
- Removed viewport zoom lock (`maximum-scale=1.0, user-scalable=no`)
- CSS custom properties + media queries in `web/index.html` and `web/declare.tmpl`
- Proportional panel sizes (access panel, pause, profile screen)
- Mobile font scaling applied consistently across overlays
- Build resolution aligned to 2560x1440

### 2. Merge — VicOlaitan's AAA Parlor Visual Overhaul (Completed)
- Merged `origin/master` (4 commits: visual redesign, lighting, HUD, themes)
- Resolved conflicts in `pause.py` and `profile_screen.py`
- New features: 3 unlockable themes, theme gallery, card back unlocks, atmospheric lighting toggle, larger brass-themed UI

### 3. Performance Optimizations (Completed)
- Cached per-frame gradient surfaces in `Renderer`, `SettingsMenu`, `MenuScreen`
- Cached decorative overlays (hand pool, center stack, pile halo)
- Cached rotated card fan images by rounded angle
- Replaced per-particle Surface allocation with direct draws
- Reduced iteration counts:
  - Vignette: 30 → 16 circles
  - Lamp glow flare: 20 → 10 circles
  - Felt body (initial build): 48 → 24 ellipses
  - Lamp pool (initial build): 56 → 20 circles
  - Hand pool: 18 → 10 ellipses
  - Center stack: 24 → 12 ellipses
  - Pile halo: 20 → 12 rects
  - Card highlight: 20 → 8 circles
  - Fan glow: 18 → 10 ellipses

### 4. UI Simplification (Completed — 2026-05-03)
- Main Menu: 6 items → 4 buttons (Play, Play Online, Help, Quit)
  - Help combines Tutorial + How To Play
  - Settings and Profile accessed in-game via hamburger menu
- Pause Menu: 5 items → 4 items (Resume, Restart Match, Settings, Quit to Menu)
- In-Game HUD: 3 icons → single hamburger menu button (gear/pause/quit consolidated)
- Settings Panel: 6 tabs → 3 tabs (Display, Gameplay, Preferences)
- MenuScreen uses single `Button` class with optional icon support

### 5. Merge — VicOlaitan's Latest Updates (Completed — 2026-05-03)
- Merged `origin/master` (6 commits: server multiplayer, card back equip, textured letterboxes, settings alignment, setup fonts, winner fix)
- Resolved conflicts in `main.py`, `ui/settings.py`
- New features integrated:
  - Card back equipping from Profile screen (click unlocked back → golden border)
  - Textured letterbox bars (felt texture in-game, menu backdrop in menus)
  - Settings row alignment constants (`_LABEL_COL_W`, `_ROW_H`, `_BTN_H`)
  - Setup screen text enlargement (`small_font` 13→22, `section_font` 14→24)
  - Atmospheric lighting default `True` → `False`
  - Winner comparison fix (compares `seat_index` instead of Player object)
- Server multiplayer backbone added (`server/` directory) — no client UI yet

### 6. Merge — Online Multiplayer Client (Completed — 2026-05-03)
- Merged `origin/master` (2 commits: client networking Phase 1B, runtime server URL override)
- Resolved conflicts in `main.py`, `ui/screens.py`
- New features integrated:
  - Online flow screens: Nickname, Online Menu, Online Lobby (`ui/online_screens.py`)
  - WebSocket client: `online/browser_ws.py`, `online/desktop_ws.py`, `online/client.py`
  - Proxy GameManager for server-authoritative state (`online/proxy_manager.py`)
  - Runtime server URL override (`online/url.py`) — no rebuild needed
- Preserved UI simplification:
  - Main Menu kept at 4 buttons (added Play Online, removed Tutorial/How To Play/Profile/Settings)
  - Settings kept at 3 tabs
  - HUD kept as single hamburger button
  - Performance caches (`_cached` pattern, fan glow/rotation caches) restored

## Pending Feedback / TODO

None active.

## Files Most Recently Modified

- `main.py` — letterboxing (`canvas_rect()`), `present(frame_mode)` textured bars, online flow routing
- `config.py` — `get_mobile_scale()` 1.5x, `MIN_TOUCH_TARGET`, proportional `PLAYER_AREA`
- `ui/renderer.py` — cached gradients, `get_felt_texture()`, reduced iterations, single HUD menu button
- `ui/screens.py` — 4-button menu (Play, Online, Help, Quit), cached card fan/glow, setup font sizes, `get_menu_bg_texture()`
- `ui/settings.py` — cached panel/tabs/pills, 3-tab structure, row alignment constants
- `ui/online_screens.py` — nickname, online menu, online lobby screens
- `online/` — browser_ws, desktop_ws, client, proxy_manager, url modules
- `profile_screen.py` — proportional sizing, card back equip click handler, `_back_rects`
- `feel.py` — reduced vignette/lamp steps
- `particles.py` — direct draw motes (no Surface alloc)
- `pause.py`, `access_panel.py`, `toasts.py`, `captions.py` — mobile font scaling
- `web/index.html`, `web/declare.tmpl` — responsive CSS, custom properties, no zoom lock
- `web/build_web.py` — aligned resolution to 2560x1440

## Build & Deploy

```bash
# Local test
python main.py

# Web build
python web/build_web.py

# Serve locally
cd build/web && python -m http.server 8000
```

## Key Contacts

- **Primary dev:** jucish2019-a11y (repo owner)
- **Collaborator:** VicOlaitan (visual design / aesthetic updates)

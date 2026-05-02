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

## Pending Feedback / TODO

### UI Simplification (User Feedback — 2026-05-02)

**Problem:** The user feels there are **too many options** and **too many menu things on the UI**.

Reference screenshots show a mobile web app (timarche.net) with a cluttered hamburger menu and bottom tab bar. The user wants the Declare UI to be simpler and cleaner.

**Specific pain points in Declare:**

1. **Main Menu** (6 items): Play, Tutorial, How To Play, Profile & Stats, Settings, Quit
   - Suggestion: Collapse secondary items. Keep Play prominently. Move Tutorial/How To inside the game or behind a single "Help" button. Move Settings to an in-game gear icon only.

2. **Pause Menu** (5 items): Resume, Restart Match, Settings, How To Play, Quit to Menu
   - Suggestion: Remove Settings and How To Play from pause (accessible via HUD gear icon instead). Keep: Resume, Restart, Quit.

3. **Settings Panel** (6 tabs): Display, Gameplay, AI, Accessibility, Audio, Profile
   - Suggestion: Group into fewer tabs or use a simpler layout. Many options could be preset defaults with only critical toggles exposed.

4. **In-Game HUD:** Gear icon + Pause icon + Quit icon + action rail buttons + shuffle button + status bar + game log panel + player nameplates
   - Suggestion: Reduce HUD chrome. Consolidate gear/pause/quit into a single menu button. Consider auto-hiding the game log. Reduce decorative ornament density.

5. **Action Rail** during gameplay can show 6-7 buttons at once
   - Suggestion: Group related actions or use contextual smart defaults to reduce button count.

**Design principles from reference:**
- Fewer, larger tap targets
- Clear visual hierarchy (primary action prominent, secondary actions hidden)
- Bottom tab bar for primary navigation (not applicable to game, but principle of limiting top-level choices applies)
- Single "hamburger" or "more" button for everything else

## Files Most Recently Modified

- `main.py` — letterboxing, `_game_rect()`, touch coordinate mapping
- `config.py` — `get_mobile_scale()` 1.5x, `MIN_TOUCH_TARGET`, proportional `PLAYER_AREA`
- `ui/renderer.py` — cached gradients, reduced iterations
- `ui/screens.py` — cached card fan, cached fan glow
- `ui/settings.py` — cached panel/tabs/pills
- `feel.py` — reduced vignette/lamp steps
- `particles.py` — direct draw motes (no Surface alloc)
- `pause.py`, `profile_screen.py`, `access_panel.py`, `toasts.py`, `captions.py` — mobile font scaling
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

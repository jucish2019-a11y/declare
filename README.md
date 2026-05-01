# Declare

**A card game of memory, strategy, and bluffing — built with Python and Pygame.**

Declare is a 2–4 player card game where the goal is to have the **lowest score** when someone declares. Players draw cards, use powers, swap, discard, and pair cards to minimize their hand. But memory and observation are everything — watching what others know and don't know gives you the edge to out-bluff them.

---

## Play Online

**No installation required — play Declare directly in your browser:**

### [:arrow_forward: Live Demo](https://jucish2019-a11y.github.io/declare/)

The web version runs via WebAssembly (pygbag) and supports the full game including tutorial. Progress is saved to browser localStorage.

> **Note:** The web demo is best played on desktop with a keyboard. Some browsers may require a click to start (audio policy).

---

## What's New in This Version

This build merges the **polished UI systems** from [VicOlaitan's Declare-master](https://github.com/VicOlaitan/Declare-master) with the **5 new game mechanics** from [Declare.v1](https://github.com/jucish2019-a11y/Declare.v1):

### New Mechanics

| Mechanic | Description |
|----------|-------------|
| **Self-Pair** | Pair two of your own known cards at any time — free action, doesn't consume your turn. Both cards are discarded. |
| **Shuffle** | Rearrange all your face-down cards into random positions at any time — clears what opponents know about your hand. |
| **Reactive Drop (Self)** | When an opponent discards, drop one of your known matching cards to intercept it before it's placed. |
| **Reactive Drop (Opponent)** | Call an opponent's known matching card directly — they give you the card and you discard both. |
| **Wrong-Drop Penalty** | If your reactive call or drop is wrong, the opponent whose card you tried to call shuffles their hand, and you draw a penalty card. |

All five can be toggled on/off in the settings menu.

---

## Rules

### Setup

- Each player receives **4 cards face-down** (configurable 2–6)
- Players peek at their **bottom N cards** (configurable 0–5) — these are marked with a gold dot and shown face-up
- Peek slots are fixed at the start: the bottom `peek_count` slots are known, the rest are unknown

### On Your Turn

1. **Draw** one card from the deck (click the deck or press `1`)
2. **Act** — choose one of these, in any order:
   - **Play a power card** (7–Q) — automatically offered as a button when drawn
   - **Swap** the drawn card with one of your face-down cards
   - **Discard** the drawn card to the discard pile
   - **Pair** the drawn card with a matching card (yours or an opponent's known card)
   - **Self-Pair** two of your own known cards at any time (free action)
   - **Shuffle** your hand at any time (free action)
3. **Declare** — if you believe you have the lowest score, declare at the start of your turn (before drawing)

### After Your Turn

- If you discarded, any player with a **known card matching the discarded rank** may react:
  - **Reactive Drop (Self):** Drop your own matching card to intercept
  - **Reactive Drop (Opponent):** Call an opponent's known matching card to take it
  - Reaction window is timed (default 3 seconds, configurable 2–5s)
  - Wrong calls trigger the opponent shuffle + a penalty card draw

### Scoring & Winning

- At **declaration**, scores are compared. **Lowest score wins.**
- Wrong declarations receive a **2× score penalty**
- **Zero cards = automatic win** (even if others have lower scores)
- You can also win by reducing your hand to 0 cards through pairing

---

### Card Values & Powers

| Card | Value | Power |
|------|-------|-------|
| A | 1 | — |
| 2–6 | face value | — |
| 7 | 7 | **Peek Self** — look at one of your own face-down cards |
| 8 | 8 | **Peek Self** — look at one of your own face-down cards |
| 9 | 9 | **Peek Opponent** — look at one opponent's face-down card |
| 10 | 10 | **Peek Opponent** — look at one opponent's face-down card |
| J | 11 | **Skip** — next player's turn is skipped |
| Q | 12 | **Unseen Swap** — swap one of your cards with an opponent's, both hidden |
| Red K (♥♦) | 13 | **Seen Swap** — swap with an opponent, both players see the cards |
| Black K (♠♣) | 0 | **None** — Black Kings have no power and are worth 0 points |

### Pairing

- Two cards of the **same rank** can be paired and discarded
- **Pair your own:** both cards are removed, no exchange
- **Pair with opponent:** you give one of your cards to the opponent, both matching cards are discarded
- Maximum stack size is **2 cards** — you cannot group three or four of a kind

---

## Installation

### Play in Your Browser (no install)

Open **[https://jucish2019-a11y.github.io/declare/](https://jucish2019-a11y.github.io/declare/)** — the full game runs in-browser.

### Run Locally

```bash
git clone https://github.com/jucish2019-a11y/declare.git
cd declare
```

#### 2. Install dependencies

```bash
pip install -r requirements.txt
```

#### 3. Download font assets (optional — falls back to system fonts)

```bash
python download_fonts.py
```

#### 4. Run the game

```bash
python main.py
```

---

## Controls

### Mouse

- **Left-click** — select cards, press buttons, interact with deck and discard pile
- **Drag cards** — drag face-down cards to reposition them in free layout mode

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `1` | Draw a card |
| `2` | Declare (start of turn, before drawing) |
| `3` | Swap drawn card with a face-down card |
| `4` | Discard drawn card |
| `5` | Pair drawn card with your own matching card |
| `6` | Play power card (7–Q) |
| `7` | Pair drawn card with an opponent's matching card |
| `S` | Open settings |
| `F1` | Toggle accessibility panel |
| `ESC` | Cancel targeting / close settings / open pause menu |
| `Tab` | Cycle settings tabs |

---

## Accessibility Features

Open the **Accessibility Panel** with `F1` or from the in-game settings:

### Color-Blind Modes

- **Parlor** — warm gold and green table feel
- **Deutan** — deuteranopia-friendly palette
- **Protan** — protanopia-friendly palette
- **Tritan** — tritanopia-friendly palette
- **High Contrast** — maximum contrast for all UI elements

### Vision & Motor

- **Text Scale** — scale all text from 80% to 150%
- **Motion Scale** — slow or speed up all animations (20%–100% of normal)
- **Particles** — toggle particle effects on pair/declare/power events
- **Captions** — display text captions for all audio cues

### Coaching

- **Hint Tier** — None / Subtle / Memory / All:
  - *Subtle* dims non-recommended actions
  - *Memory* highlights cards you haven't looked at recently
  - *All* adds a coach overlay with strategic reminders
- **Coach Mode** — persistent coaching tips during gameplay

### Streamer Mode

Hides all personal game information (your hand and score) from the display for safe streaming.

---

## Settings Menu

Press `S` or click the gear icon during a game. Six tabs:

| Tab | Options |
|-----|---------|
| **Display** | Card layout (Line / Square / Free), animations on/off, show game log, show known markers, show own score |
| **Gameplay** | Hand size (2–6), peek count (0–5), peek phase duration, reaction window timer (2s/3s/5s), confirm declare, **Self-Pairing** on/off, **Shuffle Cards** on/off, **Wrong-Drop Penalty** on/off, **Table Felt** (Forest/Burgundy/Navy/Charcoal/Emerald) |
| **AI** | AI difficulty (Easy/Medium/Hard), AI delay (Fast/Normal/Slow), peek reveal time |
| **Accessibility** | Theme, text scale, motion scale, particles, captions, hint tier, coach mode |
| **Audio** | Master volume, SFX volume, music volume, voice volume |
| **Profile** | Streamer mode, total games played/won, win streaks, achievements |

Settings persist across sessions via the profile system.

---

## Project Structure

```
declare/
├── main.py                 # Entry point, game loop, UI integration
├── config.py               # All game constants, colors, layout values
├── requirements.txt        # pygame >= 2.5.0, pygame-ce >= 2.5.0
│
├── game/
│   ├── card.py             # Card and Deck classes
│   ├── player.py           # Player base class, HumanPlayer, AIPlayer
│   ├── rules.py            # RulesEngine, all validation & execution logic
│   ├── game_manager.py     # Game state machine, turn flow, reaction windows
│   ├── ai.py               # AIDecider: declaration, actions, self-pair, shuffle, reactions
│   └── settings.py         # GameSettings dataclass
│
├── ui/
│   ├── renderer.py         # Main game renderer (table, cards, player areas)
│   ├── animations.py        # VisualEvent, AnimationQueue for card animations
│   ├── screens.py          # MenuScreen, SetupScreen, PeekScreen, GameOverScreen
│   ├── settings.py         # 6-tab settings menu
│   └── fonts.py            # Font download and caching
│
├── theme.py                # Color-blind themes, text/motion scale
├── typography.py            # Cinzel + Playfair Display font rendering
├── audio.py                # Procedural sound synthesis (no external files)
├── card_render.py          # PNG card images + procedural fallback
├── particles.py            # Particle system (sparks, embers, rings)
├── feel.py                 # Camera shake, time warp, edge flash, vignette, lamp glow
├── toasts.py                # Toast notification system
├── captions.py              # Accessibility captions stream
├── hints.py                # 3-tier hint engine + coach mode
├── pause.py                # Pause overlay with resume/restart/settings/how-to/quit
├── tutorial.py             # 9-chapter tutorial + first-launch splash
├── access_panel.py         # F1 accessibility panel
├── profile.py              # Stats, achievements, persistent profile
├── profile_screen.py        # Profile screen + How To Play
├── daily.py                # Daily challenge seed generation
├── download_cards.py       # Download PNG card assets
├── download_fonts.py        # Download Google Fonts
│
├── assets/
│   ├── cards/              # 52 PNG card images + back_red.png
│   └── fonts/              # Cinzel-Regular.ttf, Inter-Regular.ttf,
│                           #   PlayfairDisplay-Regular.ttf, PlayfairDisplay-Italic.ttf
│
└── web/
    ├── build_web.py        # Pygbag build script for web export
    └── index.html          # Web placeholder
```

---

## Architecture

The game is organized into **three layers**:

### Game Logic Layer (`game/`)
- Pure Python — no pygame imports
- `Card`, `Deck`, `Player`, `HumanPlayer`, `AIPlayer`
- `RulesEngine` validates and executes all actions
- `GameManager` holds the state machine (MENU → SETUP → PEEK_PHASE → TURN_START → DRAW → DECIDE → REACTION_WINDOW → TURN_END → ...)
- `AIDecider` encapsulates all AI decision-making per difficulty

### Rendering Layer (`ui/`)
- All pygame rendering is contained here
- `Renderer` draws the table felt, player areas, cards, action buttons, and the game log
- `AnimationQueue` handles card slide/arc/fade/lift events
- `screens.py` handles menu, setup, peek, and game-over screens
- `card_render.py` uses PNG card images with procedural fallback

### UI Integration Layer (`main.py`)
- `async def main()` runs the event loop (supports both native and WASM via pygbag)
- Manages screen routing (menu / setup / peek / game / game_over / profile / how_to_play)
- Integrates all polish systems: audio, particles, feel (camera shake/time warp/vignette/edge flash), toasts, hints, captions, tutorial, accessibility panel, pause, and profile

---

## Profile & Achievements

On first launch, a profile is created at `~/.declare/profile.json` (native) or browser localStorage (web demo). It tracks:

- Games played and won
- Win streaks (current and longest)
- Declarations attempted, won, and lost
- Auto-wins (zero cards)
- Pairs made (own hand and opponent hands)
- Powers used
- Reactive pair accuracy (correct vs wrong)
- 20+ achievements including streaks, milestones, and special feats

Achievements unlock with a toast notification and particle burst on screen.

---

## Audio

All sound effects are **procedurally synthesized** — no external audio files. The `audio.py` module generates:
- Card draw/swap/tap sounds
- Pair chime, power peeks, swaps, skip thud
- Declare fanfare with camera shake
- Wrong-drop buzzer
- Achievement jingle
- UI drawer open/close sounds

Volume is adjustable per bus (sfx/music/voice) in the settings.

---

## Keyboard Shortcut Reference

| Key | Game Action |
|-----|-------------|
| `1` | Draw |
| `2` | Declare (pre-draw) |
| `3` | Swap |
| `4` | Discard |
| `5` | Pair own |
| `6` | Play power |
| `7` | Pair opponent |

| Key | Navigation |
|-----|------------|
| `S` | Toggle settings |
| `F1` | Toggle accessibility panel |
| `ESC` | Cancel / close / pause |
| `Tab` | Cycle settings tabs |

---

## Credits

Declare is a collaborative project between two developers:

- **[jucish2019-a11y](https://github.com/jucish2019-a11y)** — game logic, new mechanics (reactive drop, self-pair, shuffle, wrong-drop penalty), Declare.v1
- **[VicOlaitan](https://github.com/VicOlaitan)** — UI polish, theme system, audio, particles, feel effects, Declare-master

This merged version brings the polished UI and systems of Declare-master together with the expanded game mechanics of Declare.v1 into a single unified codebase.

---

## License

MIT
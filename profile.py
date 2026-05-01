"""Player profile: persistent stats, settings, unlocks, achievements.

Single JSON file at ~/.declare/profile.json (native) or localStorage (web).
Schema-versioned for future migrations. All writes are atomic (write-temp + rename)
on native; localStorage on web.
"""
import json
import os
import sys
import tempfile
import time
from dataclasses import dataclass, field, asdict


SCHEMA_VERSION = 1


def _using_js_storage():
    return sys.platform == "emscripten"


def _load_js_storage():
    import js
    raw = js.localStorage.getItem("declare_profile")
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return None


def _save_js_storage(data):
    import js
    js.localStorage.setItem("declare_profile", json.dumps(data))


def _profile_dir():
    return os.path.join(os.path.expanduser("~"), ".declare")


def _profile_path():
    return os.path.join(_profile_dir(), "profile.json")


@dataclass
class Stats:
    games_played: int = 0
    games_won: int = 0
    declares_attempted: int = 0
    declares_won: int = 0
    declares_lost: int = 0
    auto_wins: int = 0
    pairs_made: int = 0
    pairs_on_opponents: int = 0
    powers_used: int = 0
    reactive_pairs_correct: int = 0
    reactive_pairs_wrong: int = 0
    cards_drawn: int = 0
    longest_win_streak: int = 0
    current_win_streak: int = 0
    fastest_auto_win_seconds: float = 0.0
    total_play_seconds: float = 0.0
    by_player_count: dict = field(default_factory=lambda: {"2": 0, "3": 0, "4": 0})
    final_scores_log: list = field(default_factory=list)


@dataclass
class Achievement:
    key: str
    title: str
    description: str
    unlocked: bool = False
    unlocked_at: float = 0.0


ACHIEVEMENTS_CATALOG = [
    ("first_blood",        "First Blood",          "Win your first game."),
    ("declared_winner",    "Caller",               "Win a game by declaring."),
    ("declared_loser",     "Burned",               "Lose a declaration."),
    ("auto_win",           "Vanish",               "Win by clearing your hand."),
    ("zero_score",         "Zero Hour",            "Declare with a score of 0."),
    ("under_five",         "Razor Thin",           "Declare with a score under 5."),
    ("streak_3",           "On a Roll",            "Win three games in a row."),
    ("streak_5",           "Hot Hand",             "Win five games in a row."),
    ("streak_10",          "Living Legend",        "Win ten games in a row."),
    ("ten_games",          "Regular",              "Play 10 games."),
    ("fifty_games",        "House Favorite",       "Play 50 games."),
    ("hundred_games",      "Habituated",           "Play 100 games."),
    ("ten_pairs",          "Matchmaker",           "Pair 10 cards across all games."),
    ("fifty_pairs",        "Pattern Seeker",       "Pair 50 cards."),
    ("twenty_powers",      "Magician",             "Use 20 power cards."),
    ("sharp_react",        "Quick Hands",          "Make 10 correct reactive pairs."),
    ("clean_react",        "Composed",             "Make 5 reactive pairs without a wrong one."),
    ("hardmode_win",       "Iron Will",            "Win against three Hard AI opponents."),
    ("colorblind_friend",  "Inclusive",            "Try a color-blind theme."),
    ("tutorial_done",      "Schooled",             "Finish the tutorial."),
]


@dataclass
class SettingsBag:
    """Settings that persist across sessions, distinct from per-match game settings."""
    theme: str = "default"
    text_scale: float = 1.0
    motion_scale: float = 1.0
    particles_enabled: bool = True
    music_volume: float = 0.5
    sfx_volume: float = 0.7
    voice_volume: float = 0.6
    captions: bool = False
    hint_tier: int = 1
    coach_mode: bool = False
    streamer_mode: bool = False
    hold_to_declare: bool = False
    keybinds: dict = field(default_factory=lambda: {
        "draw":     "1",
        "declare":  "2",
        "swap":     "3",
        "discard":  "4",
        "pair_own": "5",
        "play_pwr": "6",
        "pair_opp": "7",
        "settings": "s",
        "pause":    "escape",
        "peek":     "p",
    })


@dataclass
class Profile:
    schema_version: int = SCHEMA_VERSION
    created_at: float = 0.0
    last_played_at: float = 0.0
    tutorial_complete: bool = False
    last_match_config: dict = field(default_factory=dict)
    unlocked_card_backs: list = field(default_factory=lambda: ["classic"])
    stats: Stats = field(default_factory=Stats)
    achievements: dict = field(default_factory=dict)
    settings: SettingsBag = field(default_factory=SettingsBag)

    def __post_init__(self):
        for key, title, desc in ACHIEVEMENTS_CATALOG:
            self.achievements.setdefault(key, asdict(Achievement(key=key, title=title, description=desc)))


def load() -> Profile:
    if _using_js_storage():
        data = _load_js_storage()
        if data is not None:
            return _from_dict(data)
        prof = Profile(created_at=time.time(), last_played_at=time.time())
        return prof
    path = _profile_path()
    if not os.path.exists(path):
        prof = Profile(created_at=time.time(), last_played_at=time.time())
        save(prof)
        return prof
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        prof = Profile(created_at=time.time(), last_played_at=time.time())
        return prof

    return _from_dict(data)


def _from_dict(data: dict) -> Profile:
    prof = Profile()
    prof.schema_version = data.get("schema_version", SCHEMA_VERSION)
    prof.created_at = data.get("created_at", time.time())
    prof.last_played_at = data.get("last_played_at", time.time())
    prof.tutorial_complete = data.get("tutorial_complete", False)
    prof.last_match_config = data.get("last_match_config", {})
    prof.unlocked_card_backs = data.get("unlocked_card_backs", ["classic"])

    stats_data = data.get("stats", {})
    prof.stats = Stats(
        games_played=stats_data.get("games_played", 0),
        games_won=stats_data.get("games_won", 0),
        declares_attempted=stats_data.get("declares_attempted", 0),
        declares_won=stats_data.get("declares_won", 0),
        declares_lost=stats_data.get("declares_lost", 0),
        auto_wins=stats_data.get("auto_wins", 0),
        pairs_made=stats_data.get("pairs_made", 0),
        pairs_on_opponents=stats_data.get("pairs_on_opponents", 0),
        powers_used=stats_data.get("powers_used", 0),
        reactive_pairs_correct=stats_data.get("reactive_pairs_correct", 0),
        reactive_pairs_wrong=stats_data.get("reactive_pairs_wrong", 0),
        cards_drawn=stats_data.get("cards_drawn", 0),
        longest_win_streak=stats_data.get("longest_win_streak", 0),
        current_win_streak=stats_data.get("current_win_streak", 0),
        fastest_auto_win_seconds=stats_data.get("fastest_auto_win_seconds", 0.0),
        total_play_seconds=stats_data.get("total_play_seconds", 0.0),
        by_player_count=stats_data.get("by_player_count", {"2": 0, "3": 0, "4": 0}),
        final_scores_log=stats_data.get("final_scores_log", []),
    )

    settings_data = data.get("settings", {})
    prof.settings = SettingsBag(
        theme=settings_data.get("theme", "default"),
        text_scale=settings_data.get("text_scale", 1.0),
        motion_scale=settings_data.get("motion_scale", 1.0),
        particles_enabled=settings_data.get("particles_enabled", True),
        music_volume=settings_data.get("music_volume", 0.5),
        sfx_volume=settings_data.get("sfx_volume", 0.7),
        voice_volume=settings_data.get("voice_volume", 0.6),
        captions=settings_data.get("captions", False),
        hint_tier=settings_data.get("hint_tier", 1),
        coach_mode=settings_data.get("coach_mode", False),
        streamer_mode=settings_data.get("streamer_mode", False),
        hold_to_declare=settings_data.get("hold_to_declare", False),
        keybinds=settings_data.get("keybinds", SettingsBag().keybinds),
    )

    ach_data = data.get("achievements", {})
    for key, title, desc in ACHIEVEMENTS_CATALOG:
        rec = ach_data.get(key, {})
        prof.achievements[key] = {
            "key": key,
            "title": title,
            "description": desc,
            "unlocked": rec.get("unlocked", False),
            "unlocked_at": rec.get("unlocked_at", 0.0),
        }

    return prof


def save(prof: Profile):
    data = {
        "schema_version": prof.schema_version,
        "created_at": prof.created_at,
        "last_played_at": time.time(),
        "tutorial_complete": prof.tutorial_complete,
        "last_match_config": prof.last_match_config,
        "unlocked_card_backs": prof.unlocked_card_backs,
        "stats": asdict(prof.stats),
        "settings": asdict(prof.settings),
        "achievements": prof.achievements,
    }
    if _using_js_storage():
        _save_js_storage(data)
        return
    os.makedirs(_profile_dir(), exist_ok=True)
    path = _profile_path()
    fd, tmp = tempfile.mkstemp(prefix="profile.", suffix=".tmp", dir=_profile_dir())
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, path)
    except OSError:
        try:
            os.unlink(tmp)
        except OSError:
            pass


def unlock(prof: Profile, key: str) -> bool:
    if key not in prof.achievements:
        return False
    if prof.achievements[key].get("unlocked"):
        return False
    prof.achievements[key]["unlocked"] = True
    prof.achievements[key]["unlocked_at"] = time.time()
    return True


def evaluate_achievements(prof: Profile, last_game_meta: dict) -> list:
    """Return list of achievement keys newly unlocked from current state."""
    s = prof.stats
    newly = []

    if s.games_won >= 1 and unlock(prof, "first_blood"):
        newly.append("first_blood")
    if last_game_meta.get("declared_won") and unlock(prof, "declared_winner"):
        newly.append("declared_winner")
    if last_game_meta.get("declared_lost") and unlock(prof, "declared_loser"):
        newly.append("declared_loser")
    if last_game_meta.get("auto_win") and unlock(prof, "auto_win"):
        newly.append("auto_win")
    fs = last_game_meta.get("final_score_human")
    if fs == 0 and unlock(prof, "zero_score"):
        newly.append("zero_score")
    if fs is not None and fs < 5 and unlock(prof, "under_five"):
        newly.append("under_five")
    if s.current_win_streak >= 3 and unlock(prof, "streak_3"):
        newly.append("streak_3")
    if s.current_win_streak >= 5 and unlock(prof, "streak_5"):
        newly.append("streak_5")
    if s.current_win_streak >= 10 and unlock(prof, "streak_10"):
        newly.append("streak_10")
    if s.games_played >= 10 and unlock(prof, "ten_games"):
        newly.append("ten_games")
    if s.games_played >= 50 and unlock(prof, "fifty_games"):
        newly.append("fifty_games")
    if s.games_played >= 100 and unlock(prof, "hundred_games"):
        newly.append("hundred_games")
    if s.pairs_made >= 10 and unlock(prof, "ten_pairs"):
        newly.append("ten_pairs")
    if s.pairs_made >= 50 and unlock(prof, "fifty_pairs"):
        newly.append("fifty_pairs")
    if s.powers_used >= 20 and unlock(prof, "twenty_powers"):
        newly.append("twenty_powers")
    if s.reactive_pairs_correct >= 10 and unlock(prof, "sharp_react"):
        newly.append("sharp_react")
    if (s.reactive_pairs_correct >= 5 and s.reactive_pairs_wrong == 0
            and unlock(prof, "clean_react")):
        newly.append("clean_react")
    if (last_game_meta.get("won")
            and last_game_meta.get("all_hard_ai")
            and last_game_meta.get("ai_count") == 3
            and unlock(prof, "hardmode_win")):
        newly.append("hardmode_win")

    if prof.stats.games_won >= 5 and "deco_brass" not in prof.unlocked_card_backs:
        prof.unlocked_card_backs.append("deco_brass")
    if prof.stats.games_won >= 15 and "deco_emerald" not in prof.unlocked_card_backs:
        prof.unlocked_card_backs.append("deco_emerald")
    if prof.stats.games_won >= 40 and "deco_obsidian" not in prof.unlocked_card_backs:
        prof.unlocked_card_backs.append("deco_obsidian")

    return newly


def record_game_result(prof: Profile, meta: dict):
    """Update aggregate stats from a finished game's meta dict.

    Expected meta keys: won (bool), declared_won/declared_lost (bool),
    auto_win (bool), player_count (int), all_hard_ai (bool),
    final_score_human (int|None), play_seconds (float), pairs_made (int),
    powers_used (int), reactive_correct (int), reactive_wrong (int),
    cards_drawn (int), pairs_on_opponents (int), ai_count (int).
    """
    s = prof.stats
    s.games_played += 1
    if meta.get("won"):
        s.games_won += 1
        s.current_win_streak += 1
        if s.current_win_streak > s.longest_win_streak:
            s.longest_win_streak = s.current_win_streak
    else:
        s.current_win_streak = 0

    if meta.get("declared_won"):
        s.declares_attempted += 1
        s.declares_won += 1
    if meta.get("declared_lost"):
        s.declares_attempted += 1
        s.declares_lost += 1
    if meta.get("auto_win"):
        s.auto_wins += 1
        secs = meta.get("play_seconds", 0.0)
        if s.fastest_auto_win_seconds == 0 or secs < s.fastest_auto_win_seconds:
            s.fastest_auto_win_seconds = secs

    s.pairs_made += meta.get("pairs_made", 0)
    s.pairs_on_opponents += meta.get("pairs_on_opponents", 0)
    s.powers_used += meta.get("powers_used", 0)
    s.reactive_pairs_correct += meta.get("reactive_correct", 0)
    s.reactive_pairs_wrong += meta.get("reactive_wrong", 0)
    s.cards_drawn += meta.get("cards_drawn", 0)
    s.total_play_seconds += meta.get("play_seconds", 0.0)

    pc = str(meta.get("player_count", 2))
    s.by_player_count[pc] = s.by_player_count.get(pc, 0) + 1

    if meta.get("final_score_human") is not None:
        s.final_scores_log.append(meta["final_score_human"])
        if len(s.final_scores_log) > 100:
            s.final_scores_log = s.final_scores_log[-100:]

from dataclasses import dataclass, field
from config import (
    DEFAULT_AI_DELAY, DEFAULT_PEEK_REVEAL_TIME, DEFAULT_PEEK_PHASE_SECONDS,
    DEFAULT_ANIMATIONS_ENABLED, DEFAULT_SHOW_OWN_SCORE, DEFAULT_SHOW_KNOWN_MARKER,
    DEFAULT_SHOW_GAME_LOG, DEFAULT_CONFIRM_DECLARE, DEFAULT_AI_DIFFICULTY,
    DEFAULT_LAYOUT_MODE, DEFAULT_HAND_SIZE, DEFAULT_PEEK_COUNT, DEFAULT_FELT,
    DEFAULT_SELF_PAIR_ENABLED, DEFAULT_SHUFFLE_ENABLED, DEFAULT_WRONG_DROP_PENALTY,
    DEFAULT_REACTION_WINDOW_SECONDS,
)


@dataclass
class GameSettings:
    ai_delay: float = DEFAULT_AI_DELAY
    peek_reveal_time: float = DEFAULT_PEEK_REVEAL_TIME
    peek_phase_seconds: float = DEFAULT_PEEK_PHASE_SECONDS
    animations_enabled: bool = DEFAULT_ANIMATIONS_ENABLED
    show_own_score: bool = DEFAULT_SHOW_OWN_SCORE
    show_known_marker: bool = DEFAULT_SHOW_KNOWN_MARKER
    show_game_log: bool = DEFAULT_SHOW_GAME_LOG
    confirm_declare: bool = DEFAULT_CONFIRM_DECLARE
    layout_mode: str = DEFAULT_LAYOUT_MODE
    hand_size: int = DEFAULT_HAND_SIZE
    peek_count: int = DEFAULT_PEEK_COUNT
    felt_style: str = DEFAULT_FELT
    ai_difficulties: dict = field(default_factory=dict)
    self_pair_enabled: bool = DEFAULT_SELF_PAIR_ENABLED
    shuffle_enabled: bool = DEFAULT_SHUFFLE_ENABLED
    wrong_drop_penalty: bool = DEFAULT_WRONG_DROP_PENALTY
    reaction_window_seconds: float = DEFAULT_REACTION_WINDOW_SECONDS

    hint_tier: int = 1
    coach_mode: bool = False
    streamer_mode: bool = False
    motion_scale: float = 1.0
    particles_enabled: bool = True
    captions: bool = False
    atmospheric_lighting: bool = True

    def effective_anim_duration(self, base_duration: float) -> float:
        if not self.animations_enabled:
            return 0.01
        return base_duration * max(0.2, min(1.0, self.motion_scale))

    def get_ai_delay_for(self, seat_index: int) -> float:
        return self.ai_difficulties.get(seat_index, DEFAULT_AI_DIFFICULTY)

    def apply_persistent(self, settings_bag):
        self.motion_scale = settings_bag.motion_scale
        self.particles_enabled = settings_bag.particles_enabled
        self.captions = settings_bag.captions
        self.hint_tier = settings_bag.hint_tier
        self.coach_mode = settings_bag.coach_mode
        self.streamer_mode = settings_bag.streamer_mode
        self.atmospheric_lighting = getattr(settings_bag, 'atmospheric_lighting', True)
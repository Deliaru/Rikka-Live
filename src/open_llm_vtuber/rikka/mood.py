"""Short-term cross-turn mood state for Rikka."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .settings import MoodSettings


def _now_ms() -> int:
    return int(time.time() * 1000)


EMOTION_VALENCE_DELTA = {
    "happy": 0.25,
    "soft_smile": 0.15,
    "teasing": 0.10,
    "curious": 0.05,
    "neutral": 0.0,
    "quiet": -0.05,
    "worried": -0.20,
    "surprised": 0.0,
}
SURPRISE_SPIKE = 0.15


def _clamp(value: float, lower: float, upper: float) -> float:
    return min(upper, max(lower, value))


@dataclass
class MoodState:
    """Small, non-persistent mood model for recent direct conversation turns."""

    clock_ms: Callable[[], int] = _now_ms
    valence: float = 0.0
    surprise: float = 0.0
    last_update_ms: int = 0

    def register_emotion(self, emotion: str, settings: MoodSettings) -> None:
        if not settings.enabled:
            return
        self._decay(settings)
        normalized = str(emotion or "").strip()
        self.valence = _clamp(
            self.valence + EMOTION_VALENCE_DELTA.get(normalized, 0.0),
            -1.0,
            1.0,
        )
        if normalized == "surprised":
            self.surprise = _clamp(self.surprise + SURPRISE_SPIKE, 0.0, 0.19)
        self.last_update_ms = self.clock_ms()

    def snapshot(self, settings: MoodSettings) -> dict[str, object]:
        self._decay(settings)
        return {
            "valence": round(self.valence, 3),
            "surprise": round(self.surprise, 3),
            "label": self._label(),
            "updated_at_ms": self.last_update_ms,
        }

    def prompt_block(self, settings: MoodSettings) -> str:
        if not settings.enabled:
            return ""
        label = self.snapshot(settings)["label"]
        return f"【当前心情】{label}。这是内在状态：让它影响语气和 emotion 的选择，但不要直接复述这段话。"

    def tts_overrides(self, settings: MoodSettings) -> dict[str, float] | None:
        if not settings.enabled or not settings.tts_adjustment_enabled:
            return None
        self._decay(settings)
        overrides: dict[str, float] = {}
        if self.valence >= 0.3:
            overrides["happy"] = round(_clamp(0.10 + 0.05 * self.valence, 0.10, 0.15), 3)
        elif self.valence <= -0.3:
            overrides["sad"] = round(
                _clamp(0.05 + 0.14 * abs(self.valence), 0.0, 0.19),
                3,
            )
        if self.surprise >= 0.08:
            overrides["surprise"] = round(_clamp(self.surprise, 0.0, 0.19), 3)
        return overrides or None

    def idle_expression_emotion(self, settings: MoodSettings) -> str:
        """Return the existing expression preset name to use as idle mood."""
        if not settings.enabled:
            return "neutral"
        self._decay(settings)
        if self.surprise >= 0.08:
            return "curious"
        if self.valence >= 0.3:
            return "soft_smile"
        if self.valence <= -0.3:
            return "worried"
        return "neutral"

    def reset(self) -> None:
        self.valence = 0.0
        self.surprise = 0.0
        self.last_update_ms = 0

    def _label(self) -> str:
        labels: list[str] = []
        if self.valence >= 0.3:
            labels.append("心情不错，语气可以更明快一点")
        elif self.valence <= -0.3:
            labels.append("有点低落，语气放轻放缓")
        else:
            labels.append("平稳")
        if self.surprise >= 0.08:
            labels.append("刚被惊到，还有点回不过神")
        return "；".join(labels)

    def _decay(self, settings: MoodSettings) -> None:
        now = self.clock_ms()
        if self.last_update_ms <= 0:
            self.last_update_ms = now
            return
        elapsed_minutes = max(0.0, (now - self.last_update_ms) / 60000.0)
        if elapsed_minutes <= 0:
            return
        self.valence *= 0.5 ** (elapsed_minutes / settings.half_life_minutes)
        self.surprise *= 0.5 ** elapsed_minutes
        if abs(self.valence) < 0.02:
            self.valence = 0.0
        if self.surprise < 0.01:
            self.surprise = 0.0
        self.last_update_ms = now


_DEFAULT_MOOD_STATE: MoodState | None = None


def get_default_mood_state() -> MoodState:
    global _DEFAULT_MOOD_STATE
    if _DEFAULT_MOOD_STATE is None:
        _DEFAULT_MOOD_STATE = MoodState()
    return _DEFAULT_MOOD_STATE


def apply_rikka_mood_effects(
    *,
    emotion: str,
    settings: MoodSettings,
    live2d_model: Any = None,
    actions: Any = None,
    register: bool = True,
    enable_idle_expression: bool = True,
) -> dict[str, Any] | None:
    """Apply one validated Rikka emotion to mood, actions, and TTS metadata."""
    if not settings.enabled:
        return None

    mood = get_default_mood_state()
    if register:
        mood.register_emotion(emotion, settings)

    if enable_idle_expression and actions is not None and live2d_model is not None:
        try:
            from .presentation import resolve_rikka_expression

            idle_expression = resolve_rikka_expression(
                live2d_model,
                mood.idle_expression_emotion(settings),
            )
            if (
                isinstance(idle_expression, dict)
                and isinstance(idle_expression.get("preset"), dict)
            ):
                actions.mood_idle_expression = idle_expression
        except Exception:
            # Mood state should never break the speaking path.
            pass

    if not settings.tts_adjustment_enabled:
        return None
    overrides = mood.tts_overrides(settings)
    if not overrides:
        return None
    return {"emotion_vec": overrides}

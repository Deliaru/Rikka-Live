"""Idle inner-activity state for Rikka."""

from __future__ import annotations

import random
import time
from collections.abc import Callable
from dataclasses import dataclass

from .settings import InnerLifeSettings


def _now_ms() -> int:
    return int(time.time() * 1000)


DEFAULT_ACTIVITY_POOL = [
    "盯着屏幕角落发呆",
    "听主播这边的动静",
    "在心里哼一小段歌",
    "回味今天看到的弹幕",
    "盘算等会儿要聊什么",
    "整理想象中的刘海",
]


@dataclass
class InnerLifeState:
    """Non-persistent current idle activity."""

    clock_ms: Callable[[], int] = _now_ms
    current_activity: str = ""
    rotated_at_ms: int = 0
    _next_rotation_ms: int = 0

    def current(self, settings: InnerLifeSettings) -> str:
        if not settings.enabled:
            return ""
        now = self.clock_ms()
        if not self.current_activity or now >= self._next_rotation_ms:
            self._rotate(settings, now)
        return self.current_activity

    def snapshot(self, settings: InnerLifeSettings) -> dict[str, object]:
        activity = self.current(settings) if settings.enabled else ""
        return {
            "activity": activity,
            "rotated_at_ms": self.rotated_at_ms,
            "next_rotation_ms": self._next_rotation_ms,
        }

    def prompt_block(self, settings: InnerLifeSettings) -> str:
        activity = self.current(settings)
        if not activity:
            return ""
        return f"【你现在正在做的事】{activity}。被问“在干嘛/在做什么”时可以自然提到；没被问就不要刻意说。"

    def reset(self) -> None:
        self.current_activity = ""
        self.rotated_at_ms = 0
        self._next_rotation_ms = 0

    def _rotate(self, settings: InnerLifeSettings, now: int) -> None:
        pool = settings.activities or DEFAULT_ACTIVITY_POOL
        candidates = [item for item in pool if item and item != self.current_activity]
        self.current_activity = random.choice(candidates or pool)
        self.rotated_at_ms = now
        jitter = random.uniform(0.7, 1.3)
        self._next_rotation_ms = now + int(settings.rotation_minutes * jitter * 60000)


_DEFAULT_INNER_LIFE: InnerLifeState | None = None


def get_default_inner_life() -> InnerLifeState:
    global _DEFAULT_INNER_LIFE
    if _DEFAULT_INNER_LIFE is None:
        _DEFAULT_INNER_LIFE = InnerLifeState()
    return _DEFAULT_INNER_LIFE

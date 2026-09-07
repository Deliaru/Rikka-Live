"""Low-interruption proactive speech state for Rikka co-streaming."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Literal

from .settings import ProactiveSettings


def _now_ms() -> int:
    return int(time.time() * 1000)


ProactiveKind = Literal["screen_comment", "idle_speech"]


@dataclass
class ProactiveCoordinator:
    """Tracks cooldowns and status for opt-in proactive speech."""

    clock_ms: Any = _now_ms
    last_user_activity_ms: int = 0
    last_rikka_speech_ms: int = 0
    last_screen_comment_ms: int = 0
    last_idle_speech_ms: int = 0
    last_tick_ms: int = 0
    last_tick_result: dict[str, Any] = field(default_factory=dict)
    screen_comment_times: list[int] = field(default_factory=list)
    idle_speech_times: list[int] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.last_user_activity_ms <= 0:
            self.last_user_activity_ms = self.clock_ms()

    def mark_user_activity(self) -> None:
        self.last_user_activity_ms = self.clock_ms()

    def mark_rikka_speech(self, kind: ProactiveKind | None = None) -> None:
        now = self.clock_ms()
        self.last_rikka_speech_ms = now
        if kind == "screen_comment":
            self.last_screen_comment_ms = now
            self.screen_comment_times.append(now)
        elif kind == "idle_speech":
            self.last_idle_speech_ms = now
            self.idle_speech_times.append(now)

    def record_tick(self, result: dict[str, Any]) -> None:
        self.last_tick_ms = self.clock_ms()
        self.last_tick_result = self._safe_result(result)

    def decision(
        self,
        settings: ProactiveSettings,
        kind: ProactiveKind,
        live2d_connected: bool,
        capture_ready: bool,
        conversation_active: bool,
    ) -> dict[str, Any]:
        now = self.clock_ms()
        if kind == "screen_comment" and not settings.screen_comments_enabled:
            return self._blocked(kind, "screen comments disabled")
        if kind == "idle_speech" and not settings.idle_speech_enabled:
            return self._blocked(kind, "idle speech disabled")
        if not live2d_connected:
            return self._blocked(kind, "no Live2D client connected")
        if conversation_active:
            return self._blocked(kind, "conversation is active")
        if kind == "screen_comment" and not capture_ready:
            return self._blocked(kind, "no screen keyframe available")
        if now - self.last_user_activity_ms < settings.min_user_idle_ms:
            return self._blocked(kind, "user was active recently")

        if kind == "screen_comment":
            if now - self.last_screen_comment_ms < settings.screen_comment_cooldown_ms:
                return self._blocked(kind, "screen comment cooldown active")
            if self._count_since(self.screen_comment_times, now - 3600000) >= (
                settings.max_screen_comments_per_hour
            ):
                return self._blocked(kind, "screen comment hourly cap reached")
        else:
            if now - self.last_idle_speech_ms < settings.idle_speech_cooldown_ms:
                return self._blocked(kind, "idle speech cooldown active")
            if self._count_since(self.idle_speech_times, now - 3600000) >= (
                settings.max_idle_speeches_per_hour
            ):
                return self._blocked(kind, "idle speech hourly cap reached")

        return {
            "kind": kind,
            "allowed": True,
            "reason": "ready",
            "now_ms": now,
        }

    def status(self, settings: ProactiveSettings) -> dict[str, Any]:
        now = self.clock_ms()
        return {
            "enabled": {
                "screen_comments": settings.screen_comments_enabled,
                "idle_speech": settings.idle_speech_enabled,
            },
            "scheduler_interval_ms": settings.scheduler_interval_ms,
            "last_user_activity_ms": self.last_user_activity_ms,
            "last_rikka_speech_ms": self.last_rikka_speech_ms,
            "last_screen_comment_ms": self.last_screen_comment_ms,
            "last_idle_speech_ms": self.last_idle_speech_ms,
            "screen_comments_last_hour": self._count_since(
                self.screen_comment_times,
                now - 3600000,
            ),
            "idle_speeches_last_hour": self._count_since(
                self.idle_speech_times,
                now - 3600000,
            ),
            "last_tick_ms": self.last_tick_ms,
            "last_tick_result": self.last_tick_result,
            "low_interruption_defaults": True,
        }

    def _blocked(self, kind: ProactiveKind, reason: str) -> dict[str, Any]:
        return {
            "kind": kind,
            "allowed": False,
            "reason": reason,
            "now_ms": self.clock_ms(),
        }

    def _count_since(self, values: list[int], since_ms: int) -> int:
        return len([value for value in values if value >= since_ms])

    def _safe_result(self, result: dict[str, Any]) -> dict[str, Any]:
        return {
            "triggered": bool(result.get("triggered")),
            "kind": result.get("kind"),
            "reason": result.get("reason"),
            "decisions": result.get("decisions", {}),
            "capture": self._safe_capture(result.get("capture")),
            "screen_change": self._safe_screen_change(result.get("screen_change")),
        }

    def _safe_capture(self, capture: Any) -> Any:
        if not isinstance(capture, dict):
            return capture
        return {
            key: value
            for key, value in capture.items()
            if key not in {"data", "data_base64", "keyframe_base64"}
        }

    def _safe_screen_change(self, screen_change: Any) -> Any:
        if not isinstance(screen_change, dict):
            return screen_change
        return {
            key: value
            for key, value in screen_change.items()
            if key not in {"data", "data_base64", "keyframe_base64"}
        }


_DEFAULT_COORDINATOR: ProactiveCoordinator | None = None


def get_default_proactive_coordinator() -> ProactiveCoordinator:
    global _DEFAULT_COORDINATOR
    if _DEFAULT_COORDINATOR is None:
        _DEFAULT_COORDINATOR = ProactiveCoordinator()
    return _DEFAULT_COORDINATOR

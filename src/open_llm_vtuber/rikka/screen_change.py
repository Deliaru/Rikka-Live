"""Cheap local frame-difference gate for proactive screen comments."""

from __future__ import annotations

import base64
import time
from collections.abc import Callable
from dataclasses import dataclass
from io import BytesIO
from typing import Any

from .capture import CapturedFrame
from .settings import ProactiveSettings


THUMB_SIZE = (32, 18)


def _now_ms() -> int:
    return int(time.time() * 1000)


@dataclass
class ScreenChangeDetector:
    """Compare transient in-memory thumbnails without storing raw frames."""

    clock_ms: Callable[[], int] = _now_ms

    def __post_init__(self) -> None:
        self._baseline: bytes | None = None
        self._baseline_at_ms: int = 0
        self._pending_thumbnail: bytes | None = None
        self._last_score: float | None = None
        self._last_frame_at_ms: int = 0
        self._last_error: str = ""

    def evaluate(self, frame: CapturedFrame, settings: ProactiveSettings) -> dict[str, Any]:
        self._pending_thumbnail = None
        self._last_frame_at_ms = self.clock_ms()
        if self._baseline is None:
            self._pending_thumbnail = self._try_thumbnail(frame)
            self._last_score = None
            return {
                "changed": True,
                "score": None,
                "reason": "first frame",
            }

        thumbnail = self._try_thumbnail(frame)
        if thumbnail is None:
            self._last_score = None
            return {
                "changed": False,
                "score": None,
                "reason": "decode error",
            }

        self._pending_thumbnail = thumbnail
        score = sum(
            abs(current - baseline)
            for current, baseline in zip(thumbnail, self._baseline)
        ) / (255.0 * len(thumbnail))
        self._last_score = score
        return {
            "changed": score >= settings.screen_change_threshold,
            "score": round(score, 4),
            "reason": "changed" if score >= settings.screen_change_threshold else "unchanged",
        }

    def commit_baseline(self) -> None:
        if self._pending_thumbnail is None:
            return
        self._baseline = self._pending_thumbnail
        self._baseline_at_ms = self.clock_ms()

    def status(self) -> dict[str, Any]:
        return {
            "baseline_at_ms": self._baseline_at_ms,
            "last_score": None if self._last_score is None else round(self._last_score, 4),
            "last_frame_at_ms": self._last_frame_at_ms,
            "last_error": self._last_error,
        }

    def reset(self) -> None:
        self._baseline = None
        self._baseline_at_ms = 0
        self._pending_thumbnail = None
        self._last_score = None
        self._last_frame_at_ms = 0
        self._last_error = ""

    def _try_thumbnail(self, frame: CapturedFrame) -> bytes | None:
        try:
            from PIL import Image

            raw = base64.b64decode(frame.data_base64, validate=True)
            with Image.open(BytesIO(raw)) as image:
                thumbnail = image.convert("L").resize(THUMB_SIZE).tobytes()
            self._last_error = ""
            return thumbnail
        except Exception as exc:
            self._last_error = str(exc)[:160]
            return None


_DEFAULT_SCREEN_CHANGE_DETECTOR: ScreenChangeDetector | None = None


def get_default_screen_change_detector() -> ScreenChangeDetector:
    global _DEFAULT_SCREEN_CHANGE_DETECTOR
    if _DEFAULT_SCREEN_CHANGE_DETECTOR is None:
        _DEFAULT_SCREEN_CHANGE_DETECTOR = ScreenChangeDetector()
    return _DEFAULT_SCREEN_CHANGE_DETECTOR

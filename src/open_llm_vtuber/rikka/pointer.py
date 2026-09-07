"""Privacy-safe global pointer status for Live2D gaze tracking."""

from __future__ import annotations

import platform
import time
from typing import Any, Callable

from .settings import OverlaySettings


def _now_ms() -> int:
    return int(time.time() * 1000)


PointerReader = Callable[[], tuple[tuple[int, int], tuple[int, int, int, int]]]


class GlobalPointerTracker:
    """Reads the local pointer position without exposing extra window content."""

    def __init__(
        self,
        pointer_reader: PointerReader | None = None,
        platform_name: str | None = None,
        clock_ms: Callable[[], int] = _now_ms,
    ):
        self._pointer_reader = pointer_reader
        self._platform_name = platform_name
        self._clock_ms = clock_ms

    @property
    def is_available(self) -> bool:
        return (self._platform_name or platform.system()) == "Windows"

    def unavailable_reason(self) -> str:
        if not self.is_available:
            return "global pointer tracking is only available on Windows"
        return ""

    def status(self, settings: OverlaySettings) -> dict[str, Any]:
        enabled = settings.global_pointer_tracking_enabled
        if not enabled:
            return {
                "available": self.is_available,
                "enabled": False,
                "status": "disabled",
                "reason": "global pointer tracking is disabled in /rikka/settings",
            }
        if not self.is_available:
            return {
                "available": False,
                "enabled": True,
                "status": "unavailable",
                "reason": self.unavailable_reason(),
            }
        try:
            (x, y), bounds = self._read_pointer()
        except Exception as exc:
            return {
                "available": True,
                "enabled": True,
                "status": "error",
                "reason": str(exc),
            }

        left, top, right, bottom = bounds
        width = max(1, right - left)
        height = max(1, bottom - top)
        primary_x = x - left
        primary_y = y - top
        normalized_x = ((x - left) / width) * 2 - 1
        normalized_y = -(((y - top) / height) * 2 - 1)
        return {
            "available": True,
            "enabled": True,
            "status": "tracked",
            "reason": "",
            "x": x,
            "y": y,
            "primary_x": primary_x,
            "primary_y": primary_y,
            "normalized_x": max(-1.0, min(1.0, normalized_x)),
            "normalized_y": max(-1.0, min(1.0, normalized_y)),
            "coordinate_space": "primary_screen",
            "bounds": {
                "left": left,
                "top": top,
                "right": right,
                "bottom": bottom,
                "width": width,
                "height": height,
            },
            "captured_at_ms": self._clock_ms(),
        }

    def _read_pointer(self) -> tuple[tuple[int, int], tuple[int, int, int, int]]:
        if self._pointer_reader:
            return self._pointer_reader()
        try:
            import win32api
            import win32con
        except Exception as exc:
            raise RuntimeError("pywin32 is required for global pointer tracking") from exc

        x, y = win32api.GetCursorPos()
        left = 0
        top = 0
        width = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
        height = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
        return (x, y), (left, top, left + width, top + height)


_DEFAULT_POINTER_TRACKER: GlobalPointerTracker | None = None


def get_default_pointer_tracker() -> GlobalPointerTracker:
    global _DEFAULT_POINTER_TRACKER
    if _DEFAULT_POINTER_TRACKER is None:
        _DEFAULT_POINTER_TRACKER = GlobalPointerTracker()
    return _DEFAULT_POINTER_TRACKER

"""Privacy-gated Windows window capture for Rikka co-streaming."""

from __future__ import annotations

import base64
import io
import platform
import time
from dataclasses import dataclass
from typing import Any

from .settings import CaptureSettings, RikkaSettingsStore, get_default_settings_store


def _now_ms() -> int:
    return int(time.time() * 1000)


@dataclass(frozen=True)
class WindowInfo:
    """Privacy-safe metadata for a capturable window."""

    handle: int
    title: str
    process_name: str = ""
    bounds: tuple[int, int, int, int] = (0, 0, 0, 0)
    is_foreground: bool = False
    is_minimized: bool = False

    def to_dict(self) -> dict[str, Any]:
        left, top, right, bottom = self.bounds
        return {
            "handle": self.handle,
            "title": self.title,
            "process_name": self.process_name,
            "bounds": {
                "left": left,
                "top": top,
                "right": right,
                "bottom": bottom,
                "width": max(0, right - left),
                "height": max(0, bottom - top),
            },
            "is_foreground": self.is_foreground,
            "is_minimized": self.is_minimized,
        }


class CaptureDependencyError(RuntimeError):
    """Raised when optional screenshot dependencies are not installed."""


@dataclass(frozen=True)
class CapturedFrame:
    """Transient in-memory screenshot payload."""

    data_base64: str
    mime_type: str
    captured_at_ms: int
    window: WindowInfo
    width: int
    height: int

    def data_url(self) -> str:
        return f"data:{self.mime_type};base64,{self.data_base64}"

    def to_public_dict(self, include_payload: bool = False) -> dict[str, Any]:
        payload = {
            "captured_at_ms": self.captured_at_ms,
            "mime_type": self.mime_type,
            "width": self.width,
            "height": self.height,
            "window": self.window.to_dict(),
            "raw_media_persisted": False,
        }
        if include_payload:
            payload["data"] = self.data_url()
        return payload


class WindowEnumerator:
    """OS adapter for visible-window enumeration and screenshot capture."""

    @property
    def is_available(self) -> bool:
        return platform.system() == "Windows"

    def unavailable_reason(self) -> str:
        if platform.system() != "Windows":
            return "window capture is only available on Windows"
        return ""

    def list_windows(self) -> list[WindowInfo]:
        if not self.is_available:
            return []
        try:
            import win32gui
        except Exception:
            return []

        foreground = None
        try:
            foreground = win32gui.GetForegroundWindow()
        except Exception:
            foreground = None

        windows: list[WindowInfo] = []

        def collect(handle: int, _extra: object) -> None:
            try:
                if not win32gui.IsWindowVisible(handle):
                    return
                title = (win32gui.GetWindowText(handle) or "").strip()
                if not title:
                    return
                bounds = tuple(win32gui.GetWindowRect(handle))
                if bounds[2] <= bounds[0] or bounds[3] <= bounds[1]:
                    return
                windows.append(
                    WindowInfo(
                        handle=handle,
                        title=title,
                        process_name=self._process_name(handle),
                        bounds=bounds,
                        is_foreground=handle == foreground,
                        is_minimized=bool(win32gui.IsIconic(handle)),
                    )
                )
            except Exception:
                return

        win32gui.EnumWindows(collect, None)
        return windows

    def capture_window(
        self,
        window: WindowInfo,
        settings: CaptureSettings,
    ) -> CapturedFrame:
        if not self.is_available:
            raise RuntimeError(self.unavailable_reason())
        try:
            from mss import mss
            from PIL import Image
        except Exception as exc:
            raise CaptureDependencyError("mss and pillow are required for capture") from exc

        left, top, right, bottom = window.bounds
        width = max(1, right - left)
        height = max(1, bottom - top)
        monitor = {"left": left, "top": top, "width": width, "height": height}
        with mss() as sct:
            shot = sct.grab(monitor)
        image = Image.frombytes("RGB", shot.size, shot.rgb)
        if image.width > settings.max_width:
            ratio = settings.max_width / image.width
            image = image.resize(
                (settings.max_width, max(1, int(image.height * ratio)))
            )

        output = io.BytesIO()
        image.save(output, format="JPEG", quality=settings.jpeg_quality, optimize=True)
        return CapturedFrame(
            data_base64=base64.b64encode(output.getvalue()).decode("ascii"),
            mime_type="image/jpeg",
            captured_at_ms=_now_ms(),
            window=window,
            width=image.width,
            height=image.height,
        )

    def _process_name(self, handle: int) -> str:
        try:
            import win32api
            import win32con
            import win32process
        except Exception:
            return ""
        try:
            _, pid = win32process.GetWindowThreadProcessId(handle)
            process = win32api.OpenProcess(
                win32con.PROCESS_QUERY_INFORMATION | win32con.PROCESS_VM_READ,
                False,
                pid,
            )
            path = win32process.GetModuleFileNameEx(process, 0)
            return path.rsplit("\\", 1)[-1]
        except Exception:
            return ""


class WindowCaptureService:
    """Privacy-gated transient keyframe capture service."""

    def __init__(
        self,
        settings_store: RikkaSettingsStore | None = None,
        enumerator: WindowEnumerator | None = None,
        clock_ms=_now_ms,
    ):
        self.settings_store = settings_store or get_default_settings_store()
        self.enumerator = enumerator or WindowEnumerator()
        self._clock_ms = clock_ms
        self._latest_frame: CapturedFrame | None = None
        self._last_capture_status: dict[str, Any] = {
            "status": "idle",
            "reason": "not captured yet",
        }
        self._last_attachment_status: dict[str, Any] = {
            "status": "idle",
            "reason": "no user turn attachment yet",
        }

    def list_windows(self) -> dict[str, Any]:
        if not self.enumerator.is_available:
            return {
                "available": False,
                "reason": self.enumerator.unavailable_reason(),
                "windows": [],
            }
        return {
            "available": True,
            "reason": "",
            "windows": [window.to_dict() for window in self.enumerator.list_windows()],
        }

    def status(self) -> dict[str, Any]:
        settings = self.settings_store.snapshot()
        capture_settings = settings.capture
        enabled = settings.screen_capture_enabled or capture_settings.enabled
        status = {
            "available": self.enumerator.is_available,
            "enabled": enabled,
            "mode": capture_settings.mode,
            "allow_foreground_debug": capture_settings.allow_foreground_debug,
            "raw_media_persisted": False,
            "latest_frame": (
                self._latest_frame.to_public_dict(include_payload=False)
                if self._latest_frame
                else None
            ),
            "last_attachment": self._last_attachment_status,
            **self._last_capture_status,
        }
        if not self.enumerator.is_available:
            status["status"] = "unavailable"
            status["reason"] = self.enumerator.unavailable_reason()
        elif not enabled:
            status["status"] = "disabled"
            status["reason"] = "screen capture is disabled in /rikka/settings"
        return status

    def latest_frame(self) -> CapturedFrame | None:
        return self._latest_frame

    def record_attachment_status(
        self,
        status: str,
        reason: str,
        **metadata: Any,
    ) -> dict[str, Any]:
        self._last_attachment_status = {
            "status": status,
            "reason": reason,
            "at_ms": self._clock_ms(),
            **metadata,
        }
        return self._last_attachment_status

    def ingest_keyframe(
        self,
        data_base64: str,
        reason: str = "manual_upload",
        event_id: str | None = None,
        mime_type: str = "image/jpeg",
    ) -> CapturedFrame:
        window = WindowInfo(
            handle=0,
            title=reason or "manual keyframe",
            process_name="manual",
            bounds=(0, 0, 0, 0),
        )
        frame = CapturedFrame(
            data_base64=data_base64.split(",", 1)[-1],
            mime_type=mime_type,
            captured_at_ms=self._clock_ms(),
            window=window,
            width=0,
            height=0,
        )
        self._latest_frame = frame
        self._last_capture_status = {
            "status": "queued",
            "reason": reason,
            "event_id": event_id,
        }
        return frame

    def capture_keyframe(self, force: bool = False) -> dict[str, Any]:
        settings = self.settings_store.snapshot()
        capture_settings = settings.capture
        enabled = settings.screen_capture_enabled or capture_settings.enabled
        if not enabled:
            return self._set_status(
                "disabled",
                "screen capture is disabled in /rikka/settings",
            )
        if not settings.keyframe_upload_enabled:
            return self._set_status(
                "blocked",
                "keyframe upload is disabled in /rikka/settings",
            )
        if not self.enumerator.is_available:
            return self._set_status("unavailable", self.enumerator.unavailable_reason())

        if (
            not force
            and self._latest_frame
            and self._clock_ms() - self._latest_frame.captured_at_ms
            < capture_settings.interval_ms
        ):
            return self._set_status("cooldown", "capture interval has not elapsed")

        target = self._resolve_target(capture_settings)
        if target is None:
            return dict(self._last_capture_status)

        try:
            frame = self.enumerator.capture_window(target, capture_settings)
        except CaptureDependencyError as exc:
            return self._set_status("unavailable", str(exc))
        except Exception as exc:
            return self._set_status("error", str(exc))
        self._latest_frame = frame
        return self._set_status(
            "captured",
            "keyframe captured",
            latest_frame=frame.to_public_dict(include_payload=False),
        )

    def _resolve_target(self, settings: CaptureSettings) -> WindowInfo | None:
        windows = [window for window in self.enumerator.list_windows() if not window.is_minimized]
        if settings.mode == "foreground_debug":
            if not settings.allow_foreground_debug:
                self._set_status(
                    "blocked",
                    "foreground capture requires allow_foreground_debug=true",
                )
                return None
            target = next((window for window in windows if window.is_foreground), None)
            if target is None:
                self._set_status("waiting_for_target", "no foreground window found")
            return target

        target = self._match_whitelist(windows, settings)
        if target is None:
            self._set_status(
                "waiting_for_target",
                "no whitelist game window is currently available",
            )
        return target

    def _match_whitelist(
        self,
        windows: list[WindowInfo],
        settings: CaptureSettings,
    ) -> WindowInfo | None:
        title_patterns = [
            pattern.lower()
            for pattern in settings.window_title_allowlist
            if pattern.strip()
        ]
        process_patterns = [
            pattern.lower()
            for pattern in settings.process_name_allowlist
            if pattern.strip()
        ]
        if not title_patterns and not process_patterns:
            return None
        for window in windows:
            title = window.title.lower()
            process = window.process_name.lower()
            if any(pattern in title for pattern in title_patterns):
                return window
            if any(pattern in process for pattern in process_patterns):
                return window
        return None

    def _set_status(
        self,
        status: str,
        reason: str,
        **metadata: Any,
    ) -> dict[str, Any]:
        self._last_capture_status = {
            "status": status,
            "reason": reason,
            **metadata,
        }
        return {
            "available": self.enumerator.is_available,
            "enabled": self.settings_store.snapshot().screen_capture_enabled
            or self.settings_store.snapshot().capture.enabled,
            "raw_media_persisted": False,
            **self._last_capture_status,
        }


_DEFAULT_CAPTURE_SERVICE: WindowCaptureService | None = None


def get_default_capture_service() -> WindowCaptureService:
    global _DEFAULT_CAPTURE_SERVICE
    if _DEFAULT_CAPTURE_SERVICE is None:
        _DEFAULT_CAPTURE_SERVICE = WindowCaptureService()
    return _DEFAULT_CAPTURE_SERVICE

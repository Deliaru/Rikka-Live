"""Helpers for attaching transient screen keyframes to LLM turns."""

from __future__ import annotations

from typing import Any

from .capture import CapturedFrame, WindowCaptureService


def frame_to_image_payload(frame: CapturedFrame) -> dict[str, str]:
    """Convert a transient keyframe to the existing BatchInput image shape."""
    return {
        "source": "screen",
        "data": frame.data_url(),
        "mime_type": frame.mime_type,
    }


def latest_screen_images(
    capture_service: WindowCaptureService,
) -> list[dict[str, str]]:
    frame = capture_service.latest_frame()
    if frame is None:
        return []
    return [frame_to_image_payload(frame)]


def screen_context_metadata(
    frame: CapturedFrame | None,
) -> dict[str, Any]:
    if frame is None:
        return {
            "screen_context": "unavailable",
        }
    return {
        "screen_context": "attached",
        "screen_captured_at_ms": frame.captured_at_ms,
        "screen_window_title": frame.window.title,
        "raw_media_attached": True,
    }

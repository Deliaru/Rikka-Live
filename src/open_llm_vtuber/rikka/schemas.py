"""Shared contracts for Rikka Live inputs and structured responses."""

from __future__ import annotations

import time
from typing import Any, ClassVar, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .text_safety import clean_public_text, clean_response_text, truncate_text

LiveEventType = Literal[
    "chat.message",
    "chat.gift",
    "chat.guard",
    "chat.super_chat",
    "chat.follow",
    "room.state",
    "host.note",
    "game.roi_changed",
    "game.result_detected",
    "system.test_event",
]

LiveEventSource = Literal["debug", "bilibili", "screen", "host", "system"]

LiveEventActorPlatform = Literal[
    "bilibili",
    "debug",
    "host",
    "screen",
    "system",
    "local",
]

# Static/default emotion vocabulary. The response `emotion` field itself is a
# validated free string so configured expression presets can extend the
# vocabulary without code changes; unknown values fall back to "neutral" at
# presentation resolution time.
RikkaEmotion = Literal[
    "neutral",
    "soft_smile",
    "curious",
    "happy",
    "worried",
    "surprised",
    "teasing",
    "quiet",
]

RikkaMotion = Literal[
    "idle",
    "nod",
    "tilt_head",
    "look_close",
    "look_away",
    "small_wave",
    "thinking",
]

RikkaGaze = Literal["camera", "chat", "game", "down", "away"]

RikkaPriority = Literal["low", "normal", "high"]

RikkaReasonCode = Literal[
    "reply_chat",
    "thank_gift",
    "game_comment",
    "host_note",
    "memory_recall",
    "idle_fill",
    "safety_fallback",
]

MemoryKind = Literal[
    "viewer_note",
    "stream_summary",
    "joke",
    "preference",
    "blocked_topic",
]


def _now_ms() -> int:
    return int(time.time() * 1000)


class LiveEventActor(BaseModel):
    """Optional actor metadata for normalized live events."""

    model_config = ConfigDict(extra="forbid")

    platform: LiveEventActorPlatform | None = None
    user_id: str | None = None
    display_name: str | None = None
    medal: str | None = None
    is_admin: bool | None = None

    @field_validator("user_id", "display_name", "medal", mode="before")
    @classmethod
    def clean_actor_text(cls, value: Any) -> str | None:
        cleaned = clean_public_text(value)
        return cleaned or None


class LiveEventPrivacy(BaseModel):
    """Privacy flags attached to every event."""

    model_config = ConfigDict(extra="forbid")

    contains_raw_media: bool = False
    cloud_upload_allowed: bool = False


class LiveEvent(BaseModel):
    """Normalized event contract for debug, Bilibili, screen, and host inputs."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: str(uuid4()))
    type: LiveEventType
    source: LiveEventSource
    timestamp_ms: int = Field(default_factory=_now_ms)
    actor: LiveEventActor | None = None
    text: str | None = None
    amount: float | None = None
    room_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    privacy: LiveEventPrivacy = Field(default_factory=LiveEventPrivacy)

    @field_validator("id", "text", "room_id", mode="before")
    @classmethod
    def clean_optional_text(cls, value: Any) -> str | None:
        cleaned = clean_public_text(value)
        return cleaned or None

    @model_validator(mode="after")
    def normalize_payload_for_privacy(self) -> "LiveEvent":
        if self.privacy.contains_raw_media:
            self.payload = {
                "redacted": True,
                "reason": "raw media is never stored in event history by default",
            }
        return self


class MemoryWrite(BaseModel):
    """A validated memory write proposed by Rikka's structured response."""

    model_config = ConfigDict(extra="forbid")

    kind: MemoryKind
    key: str = Field(min_length=1, max_length=80)
    value: str = Field(min_length=1, max_length=500)

    @field_validator("key", "value", mode="before")
    @classmethod
    def clean_memory_text(cls, value: Any) -> str:
        return clean_public_text(value)


class RikkaResponse(BaseModel):
    """Structured response contract consumed by presentation and TTS."""

    model_config = ConfigDict(extra="forbid")

    SUBTITLE_LIMIT: ClassVar[int] = 80
    SPOKEN_LIMIT: ClassVar[int] = 180
    EMOTION_NAME_LIMIT: ClassVar[int] = 64

    spoken_text: str
    subtitle_text: str
    emotion: str = "neutral"
    motion: RikkaMotion = "idle"
    gaze: RikkaGaze = "camera"
    priority: RikkaPriority = "normal"
    interruptible: bool = True
    reason_code: RikkaReasonCode
    memory_writes: list[MemoryWrite] = Field(default_factory=list)

    @field_validator("emotion", mode="before")
    @classmethod
    def normalize_emotion(cls, value: Any) -> str:
        cleaned = clean_public_text(value).lower()
        return cleaned[: cls.EMOTION_NAME_LIMIT] if cleaned else "neutral"

    @field_validator("spoken_text", "subtitle_text", mode="before")
    @classmethod
    def clean_output_text(cls, value: Any) -> str:
        return clean_response_text(value)

    @model_validator(mode="after")
    def repair_public_text(self) -> "RikkaResponse":
        self.spoken_text = truncate_text(self.spoken_text, self.SPOKEN_LIMIT)
        self.subtitle_text = truncate_text(
            self.subtitle_text or self.spoken_text,
            self.SUBTITLE_LIMIT,
        )
        if not self.spoken_text:
            raise ValueError("spoken_text cannot be empty after cleaning")
        if not self.subtitle_text:
            raise ValueError("subtitle_text cannot be empty after cleaning")
        return self

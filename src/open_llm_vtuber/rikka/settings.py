"""Local privacy/provider settings for the first Rikka Live demo."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .text_safety import clean_public_text

DEFAULT_SETTINGS_PATH = Path("cache") / "rikka_settings.json"
logger = logging.getLogger(__name__)
MOJIBAKE_MARKERS = ("Ã", "Â", "å", "ã", "\ufffd")


def _looks_like_mojibake(value: str) -> bool:
    return any(marker in value for marker in MOJIBAKE_MARKERS) or any(
        0x80 <= ord(char) <= 0x9F for char in value
    )


def _repair_mojibake_text(value: str) -> str:
    if not _looks_like_mojibake(value):
        return value
    try:
        repaired = value.encode("latin1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return value
    if repaired and repaired != value and not _looks_like_mojibake(repaired):
        return repaired
    return value


def _repair_mojibake(value: Any) -> Any:
    if isinstance(value, str):
        return _repair_mojibake_text(value)
    if isinstance(value, list):
        return [_repair_mojibake(item) for item in value]
    if isinstance(value, dict):
        return {key: _repair_mojibake(item) for key, item in value.items()}
    return value


class CaptureSettings(BaseModel):
    """Window capture settings with privacy-first defaults."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    mode: Literal["whitelist", "foreground_debug"] = "whitelist"
    allow_foreground_debug: bool = False
    window_title_allowlist: list[str] = Field(default_factory=list)
    process_name_allowlist: list[str] = Field(default_factory=list)
    interval_ms: int = Field(3000, ge=500, le=120000)
    min_change_interval_ms: int = Field(12000, ge=1000, le=300000)
    jpeg_quality: int = Field(76, ge=20, le=95)
    max_width: int = Field(1280, ge=320, le=3840)
    attach_to_user_turns: bool = True


class CaptureSettingsUpdate(BaseModel):
    """Partial update for capture settings."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool | None = None
    mode: Literal["whitelist", "foreground_debug"] | None = None
    allow_foreground_debug: bool | None = None
    window_title_allowlist: list[str] | None = None
    process_name_allowlist: list[str] | None = None
    interval_ms: int | None = Field(None, ge=500, le=120000)
    min_change_interval_ms: int | None = Field(None, ge=1000, le=300000)
    jpeg_quality: int | None = Field(None, ge=20, le=95)
    max_width: int | None = Field(None, ge=320, le=3840)
    attach_to_user_turns: bool | None = None


class ProactiveSettings(BaseModel):
    """Low-interruption proactive speech settings."""

    model_config = ConfigDict(extra="forbid")

    screen_comments_enabled: bool = False
    idle_speech_enabled: bool = False
    scheduler_interval_ms: int = Field(15000, ge=1000, le=600000)
    screen_comment_cooldown_ms: int = Field(180000, ge=10000, le=3600000)
    idle_speech_cooldown_ms: int = Field(900000, ge=60000, le=7200000)
    min_user_idle_ms: int = Field(45000, ge=5000, le=3600000)
    max_screen_comments_per_hour: int = Field(8, ge=0, le=60)
    max_idle_speeches_per_hour: int = Field(2, ge=0, le=30)
    screen_change_gate_enabled: bool = True
    screen_change_threshold: float = Field(0.12, ge=0.01, le=1.0)
    # Wake-free follow-up window opened after proactive speech playback finishes.
    # 0 disables it; the runtime may bind it to the active microphone owner.
    proactive_followup_window_ms: int = Field(18000, ge=0, le=120000)


class ProactiveSettingsUpdate(BaseModel):
    """Partial update for proactive speech settings."""

    model_config = ConfigDict(extra="forbid")

    screen_comments_enabled: bool | None = None
    idle_speech_enabled: bool | None = None
    scheduler_interval_ms: int | None = Field(None, ge=1000, le=600000)
    screen_comment_cooldown_ms: int | None = Field(None, ge=10000, le=3600000)
    idle_speech_cooldown_ms: int | None = Field(None, ge=60000, le=7200000)
    min_user_idle_ms: int | None = Field(None, ge=5000, le=3600000)
    max_screen_comments_per_hour: int | None = Field(None, ge=0, le=60)
    max_idle_speeches_per_hour: int | None = Field(None, ge=0, le=30)
    screen_change_gate_enabled: bool | None = None
    screen_change_threshold: float | None = Field(None, ge=0.01, le=1.0)
    proactive_followup_window_ms: int | None = Field(None, ge=0, le=120000)


class MoodSettings(BaseModel):
    """Short-term mood settings."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    tts_adjustment_enabled: bool = True
    half_life_minutes: float = Field(10.0, ge=1.0, le=120.0)


class MoodSettingsUpdate(BaseModel):
    """Partial update for short-term mood settings."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool | None = None
    tts_adjustment_enabled: bool | None = None
    half_life_minutes: float | None = Field(None, ge=1.0, le=120.0)


class InnerLifeSettings(BaseModel):
    """Idle inner-activity settings."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    rotation_minutes: float = Field(18.0, ge=5.0, le=120.0)
    activities: list[str] = Field(default_factory=list)

    @field_validator("activities")
    @classmethod
    def clean_activities(cls, value: list[str]) -> list[str]:
        return [
            cleaned
            for item in value
            if (cleaned := clean_public_text(str(item or "").strip()))
        ]


class InnerLifeSettingsUpdate(BaseModel):
    """Partial update for idle inner-activity settings."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool | None = None
    rotation_minutes: float | None = Field(None, ge=5.0, le=120.0)
    activities: list[str] | None = None

    @field_validator("activities")
    @classmethod
    def clean_activities(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        return [
            cleaned
            for item in value
            if (cleaned := clean_public_text(str(item or "").strip()))
        ]


class IdentitySettings(BaseModel):
    """Source identity labels used in Rikka prompts."""

    model_config = ConfigDict(extra="forbid")

    host_display_name: str = "Deliaru"
    audience_display_name: str = "\u5f39\u5e55"

    @field_validator("host_display_name", "audience_display_name", mode="before")
    @classmethod
    def clean_identity_name(cls, value: Any) -> str:
        return clean_public_text(str(value or "").strip())


class IdentitySettingsUpdate(BaseModel):
    """Partial update for source identity labels."""

    model_config = ConfigDict(extra="forbid")

    host_display_name: str | None = None
    audience_display_name: str | None = None

    @field_validator("host_display_name", "audience_display_name", mode="before")
    @classmethod
    def clean_identity_name(cls, value: Any) -> str | None:
        if value is None:
            return None
        return clean_public_text(str(value or "").strip())


class AgentToolSettings(BaseModel):
    """Self-directed conversation tool settings."""

    model_config = ConfigDict(extra="forbid")

    tools_enabled: bool = False
    look_at_screen_enabled: bool = True
    get_time_enabled: bool = True
    web_search_enabled: bool = True
    filler_enabled: bool = True
    result_pre_silence_ms: int = Field(1000, ge=0, le=5000)
    max_tool_rounds: int = Field(3, ge=1, le=5)
    web_search_timeout_seconds: int = Field(15, ge=5, le=60)


class AgentToolSettingsUpdate(BaseModel):
    """Partial update for self-directed conversation tools."""

    model_config = ConfigDict(extra="forbid")

    tools_enabled: bool | None = None
    look_at_screen_enabled: bool | None = None
    get_time_enabled: bool | None = None
    web_search_enabled: bool | None = None
    filler_enabled: bool | None = None
    result_pre_silence_ms: int | None = Field(None, ge=0, le=5000)
    max_tool_rounds: int | None = Field(None, ge=1, le=5)
    web_search_timeout_seconds: int | None = Field(None, ge=5, le=60)


class MemorySettings(BaseModel):
    """Small fact-memory storage settings."""

    model_config = ConfigDict(extra="forbid")

    summary_per_kind: int = Field(5, ge=1, le=20)
    per_kind_cap: int = Field(50, ge=5, le=500)


class MemorySettingsUpdate(BaseModel):
    """Partial update for small fact-memory storage."""

    model_config = ConfigDict(extra="forbid")

    summary_per_kind: int | None = Field(None, ge=1, le=20)
    per_kind_cap: int | None = Field(None, ge=5, le=500)


class AudioInteractionSettings(BaseModel):
    """Microphone-only wake-gated conversation settings."""

    model_config = ConfigDict(extra="forbid")

    wake_gate_enabled: bool = False
    wake_phrases: list[str] = Field(default_factory=lambda: ["六花", "Rikka", "りっか"])
    wake_asr_confusions: list[str] = Field(default_factory=lambda: ["柳华", "有花"])
    wake_active_window_ms: int = Field(18000, ge=3000, le=120000)
    mic_conversation_enabled: bool = True


class AudioInteractionSettingsUpdate(BaseModel):
    """Partial update for microphone-only wake settings."""

    model_config = ConfigDict(extra="forbid")

    wake_gate_enabled: bool | None = None
    wake_phrases: list[str] | None = None
    wake_asr_confusions: list[str] | None = None
    wake_active_window_ms: int | None = Field(None, ge=3000, le=120000)
    mic_conversation_enabled: bool | None = None


class OverlaySettings(BaseModel):
    """Project-owned overlay behavior and subtitle presentation settings."""

    model_config = ConfigDict(extra="forbid")

    asr_hud_visible: bool = True
    dock_layout_mode: Literal["corner", "free"] = "corner"
    dock_left_px: int | None = Field(None, ge=0, le=3840)
    dock_top_px: int | None = Field(None, ge=0, le=2160)
    global_pointer_tracking_enabled: bool = True
    pointer_tracking_mode: Literal["classic_lapp", "natural_layered", "off"] = (
        "natural_layered"
    )
    pointer_tracking_intensity: float = Field(1.0, ge=0.0, le=2.0)
    pointer_tracking_smoothness: float = Field(0.65, ge=0.0, le=1.0)
    pointer_tracking_deadzone: float = Field(0.05, ge=0.0, le=0.4)
    subtitle_visible: bool = True
    subtitle_layout_mode: Literal["anchor", "free"] = "anchor"
    subtitle_anchor: Literal["bottom_left", "bottom_right", "bottom_center"] = (
        "bottom_left"
    )
    subtitle_max_width_px: int = Field(520, ge=240, le=960)
    subtitle_offset_x_px: int = Field(44, ge=0, le=400)
    subtitle_offset_y_px: int = Field(96, ge=0, le=400)
    subtitle_left_px: int = Field(44, ge=0, le=3840)
    subtitle_top_px: int = Field(520, ge=0, le=2160)
    subtitle_width_px: int = Field(520, ge=240, le=1400)


class OverlaySettingsUpdate(BaseModel):
    """Partial update for overlay settings."""

    model_config = ConfigDict(extra="forbid")

    asr_hud_visible: bool | None = None
    dock_layout_mode: Literal["corner", "free"] | None = None
    dock_left_px: int | None = Field(None, ge=0, le=3840)
    dock_top_px: int | None = Field(None, ge=0, le=2160)
    global_pointer_tracking_enabled: bool | None = None
    pointer_tracking_mode: Literal["classic_lapp", "natural_layered", "off"] | None = (
        None
    )
    pointer_tracking_intensity: float | None = Field(None, ge=0.0, le=2.0)
    pointer_tracking_smoothness: float | None = Field(None, ge=0.0, le=1.0)
    pointer_tracking_deadzone: float | None = Field(None, ge=0.0, le=0.4)
    subtitle_visible: bool | None = None
    subtitle_layout_mode: Literal["anchor", "free"] | None = None
    subtitle_anchor: Literal["bottom_left", "bottom_right", "bottom_center"] | None = (
        None
    )
    subtitle_max_width_px: int | None = Field(None, ge=240, le=960)
    subtitle_offset_x_px: int | None = Field(None, ge=0, le=400)
    subtitle_offset_y_px: int | None = Field(None, ge=0, le=400)
    subtitle_left_px: int | None = Field(None, ge=0, le=3840)
    subtitle_top_px: int | None = Field(None, ge=0, le=2160)
    subtitle_width_px: int | None = Field(None, ge=240, le=1400)


class Live2DSettings(BaseModel):
    """Live2D expressiveness feature gates for instant rollback."""

    model_config = ConfigDict(extra="forbid")

    expressions_enabled: bool = True
    thinking_state_enabled: bool = True


class Live2DSettingsUpdate(BaseModel):
    """Partial update for Live2D expressiveness gates."""

    model_config = ConfigDict(extra="forbid")

    expressions_enabled: bool | None = None
    thinking_state_enabled: bool | None = None


class TtsPostProcessingSettings(BaseModel):
    """Opt-in generated-audio tail cleanup (trim + fade).

    Conservative v1: applies only to the tail of generated TTS audio.
    Default disabled; when disabled the TTS payload is byte-compatible
    with the unprocessed path. See task 06-14-tts-audio-tail-cleanup.
    """

    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    trim_max_ms: int = Field(200, ge=0, le=1000)
    trim_rms_threshold_db: float = Field(-40.0, ge=-60.0, le=-20.0)
    trim_min_tail_ms: int = Field(80, ge=0, le=300)
    fade_out_ms: int = Field(15, ge=0, le=50)


class TtsPostProcessingSettingsUpdate(BaseModel):
    """Partial update for generated-audio tail cleanup."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool | None = None
    trim_max_ms: int | None = Field(None, ge=0, le=1000)
    trim_rms_threshold_db: float | None = Field(None, ge=-60.0, le=-20.0)
    trim_min_tail_ms: int | None = Field(None, ge=0, le=300)
    fade_out_ms: int | None = Field(None, ge=0, le=50)


class RikkaSettings(BaseModel):
    """User-editable local settings with privacy-safe defaults."""

    model_config = ConfigDict(extra="forbid")

    screen_capture_enabled: bool = False
    keyframe_upload_enabled: bool = False
    debug_media_logging_enabled: bool = False
    multimodal_provider: str = "not_configured"
    capture: CaptureSettings = Field(default_factory=CaptureSettings)
    proactive: ProactiveSettings = Field(default_factory=ProactiveSettings)
    audio: AudioInteractionSettings = Field(default_factory=AudioInteractionSettings)
    overlay: OverlaySettings = Field(default_factory=OverlaySettings)
    live2d: Live2DSettings = Field(default_factory=Live2DSettings)
    agent: AgentToolSettings = Field(default_factory=AgentToolSettings)
    memory: MemorySettings = Field(default_factory=MemorySettings)
    mood: MoodSettings = Field(default_factory=MoodSettings)
    inner_life: InnerLifeSettings = Field(default_factory=InnerLifeSettings)
    identity: IdentitySettings = Field(default_factory=IdentitySettings)
    tts_post_processing: TtsPostProcessingSettings = Field(
        default_factory=TtsPostProcessingSettings
    )


class RikkaSettingsUpdate(BaseModel):
    """Partial settings update payload."""

    model_config = ConfigDict(extra="forbid")

    screen_capture_enabled: bool | None = None
    keyframe_upload_enabled: bool | None = None
    debug_media_logging_enabled: bool | None = None
    multimodal_provider: str | None = None
    capture: CaptureSettingsUpdate | None = None
    proactive: ProactiveSettingsUpdate | None = None
    audio: AudioInteractionSettingsUpdate | None = None
    overlay: OverlaySettingsUpdate | None = None
    live2d: Live2DSettingsUpdate | None = None
    agent: AgentToolSettingsUpdate | None = None
    memory: MemorySettingsUpdate | None = None
    mood: MoodSettingsUpdate | None = None
    inner_life: InnerLifeSettingsUpdate | None = None
    identity: IdentitySettingsUpdate | None = None
    tts_post_processing: TtsPostProcessingSettingsUpdate | None = None


class RikkaSettingsStore:
    """JSON-backed settings store for local demo switches."""

    def __init__(self, path: str | Path = DEFAULT_SETTINGS_PATH):
        self.path = Path(path)
        self._settings = self._load()

    def _load(self) -> RikkaSettings:
        if not self.path.exists():
            return RikkaSettings()
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            repaired = _repair_mojibake(raw)
            settings = RikkaSettings.model_validate(repaired)
            if repaired != raw:
                self._settings = settings
                self._save()
            return settings
        except Exception as exc:
            logger.warning(f"Failed to read Rikka settings store: {exc}")
            return RikkaSettings()

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self.dump(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def snapshot(self) -> RikkaSettings:
        return self._settings

    def dump(self) -> dict[str, Any]:
        return self._settings.model_dump(mode="json")

    def update(self, patch: RikkaSettingsUpdate | dict[str, Any]) -> RikkaSettings:
        update = (
            patch
            if isinstance(patch, RikkaSettingsUpdate)
            else RikkaSettingsUpdate.model_validate(patch)
        )
        data = self.dump()
        for key, value in _repair_mojibake(
            update.model_dump(exclude_none=True)
        ).items():
            if isinstance(value, dict) and isinstance(data.get(key), dict):
                data[key] = {**data[key], **value}
            else:
                data[key] = value
        self._settings = RikkaSettings.model_validate(data)
        self._save()
        return self._settings

    def reset(self) -> RikkaSettings:
        self._settings = RikkaSettings()
        self._save()
        return self._settings


_DEFAULT_STORE: RikkaSettingsStore | None = None


def get_default_settings_store() -> RikkaSettingsStore:
    global _DEFAULT_STORE
    if _DEFAULT_STORE is None:
        _DEFAULT_STORE = RikkaSettingsStore()
    return _DEFAULT_STORE


def live2d_expressions_enabled(store: RikkaSettingsStore | None = None) -> bool:
    """Return the `live2d.expressions_enabled` rollback gate value."""
    target = store if store is not None else get_default_settings_store()
    return target.snapshot().live2d.expressions_enabled


def live2d_thinking_state_enabled(store: RikkaSettingsStore | None = None) -> bool:
    """Return the `live2d.thinking_state_enabled` rollback gate value."""
    target = store if store is not None else get_default_settings_store()
    return target.snapshot().live2d.thinking_state_enabled

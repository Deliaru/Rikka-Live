"""Presentation adapters for validated Rikka responses."""

from __future__ import annotations

from typing import Any

from loguru import logger

from ..agent.output_types import Actions
from ..live2d_model import Live2dModel
from .schemas import RikkaResponse


FALLBACK_EMOTION = "neutral"
DEFAULT_EXPRESSION_FADE_MS = 300
DEFAULT_EXPRESSION_HOLD_AFTER_SPEECH_MS = 2000
DEFAULT_GESTURE_DURATION_MS = 1000
DEFAULT_GESTURE_COOLDOWN_MS = 1200

# Legacy alias table for models that still map emotions to exp3 indices
# through `emo_map` (e.g. mao_pro). Preset-driven models bypass this.
RIKKA_EMOTION_ALIASES: dict[str, tuple[str, ...]] = {
    "neutral": ("neutral",),
    "soft_smile": ("soft_smile", "happy", "joy", "smirk", "neutral"),
    "curious": ("curious", "surprised", "surprise", "neutral"),
    "happy": ("happy", "soft_smile", "joy", "smirk", "neutral"),
    "worried": ("worried", "sadness", "fear", "neutral"),
    "surprised": ("surprised", "surprise", "curious", "neutral"),
    "teasing": ("teasing", "smirk", "happy", "joy", "neutral"),
    "quiet": ("quiet", "neutral", "sadness"),
}


def _model_mapping(live2d_model: Live2dModel, key: str) -> dict[str, Any]:
    model_info = getattr(live2d_model, "model_info", {}) or {}
    value = model_info.get(key, {})
    return value if isinstance(value, dict) else {}


def _coerce_number(value: Any, default: float) -> float:
    if isinstance(value, int | float) and not isinstance(value, bool):
        return float(value)
    return default


def _sanitize_expression_preset(preset: dict[str, Any]) -> dict[str, Any]:
    raw_parameters = preset.get("parameters", {})
    parameters = (
        {
            str(key): float(value)
            for key, value in raw_parameters.items()
            if isinstance(value, int | float) and not isinstance(value, bool)
        }
        if isinstance(raw_parameters, dict)
        else {}
    )
    safe: dict[str, Any] = {
        "parameters": parameters,
        "fade_ms": int(
            _coerce_number(preset.get("fade_ms"), DEFAULT_EXPRESSION_FADE_MS)
        ),
        "hold_after_speech_ms": int(
            _coerce_number(
                preset.get("hold_after_speech_ms"),
                DEFAULT_EXPRESSION_HOLD_AFTER_SPEECH_MS,
            )
        ),
    }
    label = preset.get("label")
    if isinstance(label, str) and label.strip():
        safe["label"] = label.strip()
    return safe


def resolve_rikka_expression(
    live2d_model: Live2dModel,
    emotion: str,
) -> Any | None:
    """Resolve a structured Rikka emotion to a frontend Live2D expression.

    Models with configured `expressionPresets` get a `{"name", "preset"}`
    payload with the resolved preset inlined, so a stale overlay preset table
    cannot desync from the backend. Unknown or unconfigured emotions fall back
    to the `neutral` preset. Models without presets keep the legacy `emo_map`
    expression-index behavior.
    """
    emotion_key = str(emotion or "").strip().lower() or FALLBACK_EMOTION
    presets = _model_mapping(live2d_model, "expressionPresets")
    if presets:
        preset = presets.get(emotion_key)
        if not isinstance(preset, dict) or preset.get("enabled") is False:
            if emotion_key != FALLBACK_EMOTION:
                logger.debug(
                    "No expression preset for Rikka emotion '{}'; "
                    "falling back to neutral.",
                    emotion,
                )
            emotion_key = FALLBACK_EMOTION
            preset = presets.get(FALLBACK_EMOTION)
        if not isinstance(preset, dict):
            return None
        return {"name": emotion_key, "preset": _sanitize_expression_preset(preset)}

    emo_map = getattr(live2d_model, "emo_map", None) or {}
    aliases = RIKKA_EMOTION_ALIASES.get(emotion_key, (emotion_key, FALLBACK_EMOTION))
    for key in aliases:
        if key in emo_map:
            return emo_map[key]

    logger.debug(
        "No Live2D expression mapping found for Rikka emotion '{}'.",
        emotion,
    )
    return None


def resolve_rikka_motion(
    live2d_model: Live2dModel,
    motion: str,
) -> dict[str, Any] | None:
    """Resolve a structured Rikka motion to a frontend Live2D motion payload.

    Models with a configured `gestureMap` get procedural gesture envelope
    payloads (`name`/`kind`/`amplitude`/`duration_ms`/`cooldown_ms`). Models
    without it keep the legacy `motionMap` group/index behavior.
    """
    motion_key = motion.lower()
    gesture_map = _model_mapping(live2d_model, "gestureMap")
    if gesture_map:
        raw_payload = gesture_map.get(motion_key)
        if not isinstance(raw_payload, dict) or raw_payload.get("enabled") is False:
            return None
        return {
            "name": motion_key,
            "kind": str(raw_payload.get("kind", motion_key)),
            "amplitude": _coerce_number(raw_payload.get("amplitude"), 1.0),
            "duration_ms": int(
                _coerce_number(
                    raw_payload.get("duration_ms"), DEFAULT_GESTURE_DURATION_MS
                )
            ),
            "cooldown_ms": int(
                _coerce_number(
                    raw_payload.get("cooldown_ms"), DEFAULT_GESTURE_COOLDOWN_MS
                )
            ),
        }

    motion_map = _model_mapping(live2d_model, "motionMap")
    raw_payload = motion_map.get(motion_key)
    if not isinstance(raw_payload, dict) or raw_payload.get("enabled") is False:
        return None

    payload = dict(raw_payload)
    return {
        "name": motion_key,
        "group": str(payload.get("group", "")),
        "index": payload.get("index"),
        "priority": str(payload.get("priority", "normal")),
        "cooldown_ms": payload.get("cooldown_ms", DEFAULT_GESTURE_COOLDOWN_MS),
    }


def resolve_rikka_gaze(
    live2d_model: Live2dModel,
    gaze: str,
) -> dict[str, Any] | None:
    """Resolve a structured Rikka gaze target to Live2D parameter nudges."""
    gaze_key = gaze.lower()
    gaze_map = _model_mapping(live2d_model, "gazeMap")
    raw_payload = gaze_map.get(gaze_key)
    if not isinstance(raw_payload, dict) or raw_payload.get("enabled") is False:
        return None

    payload = dict(raw_payload)
    parameters = payload.get("parameters", {})
    if not isinstance(parameters, dict):
        return None
    safe_parameters = {
        str(key): float(value)
        for key, value in parameters.items()
        if isinstance(value, int | float)
    }
    if not safe_parameters:
        return None

    return {
        "name": gaze_key,
        "parameters": safe_parameters,
        "hold_ms": payload.get("hold_ms", 1200),
        "fade_ms": payload.get("fade_ms", 220),
        "restore_ms": payload.get("restore_ms", 700),
    }


def rikka_response_to_actions(
    response: RikkaResponse,
    live2d_model: Live2dModel,
    *,
    enable_expression_actions: bool = True,
) -> Actions:
    """Convert a validated Rikka response into frontend action payloads.

    Expression actions default on; call sites gate them through the Rikka
    setting `live2d.expressions_enabled` for instant rollback.
    """
    expressions = None
    if enable_expression_actions:
        expression = resolve_rikka_expression(live2d_model, response.emotion)
        if expression is not None:
            expressions = [expression]

    motion = resolve_rikka_motion(live2d_model, response.motion)
    gaze = resolve_rikka_gaze(live2d_model, response.gaze)
    return Actions(
        expressions=expressions,
        motions=[motion] if motion else None,
        gaze=gaze,
    )

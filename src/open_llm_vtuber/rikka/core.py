"""Core planning, validation, and normalization for Rikka Live."""

from __future__ import annotations

import json
import ast
import re
from typing import Any

from pydantic import BaseModel, ValidationError

from .identity import event_default_actor_name, identity_names
from .schemas import LiveEvent, RikkaResponse
from .settings import get_default_settings_store
from .text_safety import clean_public_text, clean_response_text, truncate_text


SPOKEN_TEXT_FIELD_RE = re.compile(
    r"(?is)([\"']?)spoken_text\1\s*[:=]\s*"
)
PROVIDER_ERROR_PREFIX = "Error calling the "
SECRET_OR_MEDIA_MARKER_RE = re.compile(
    r"(?is)(sk-[A-Za-z0-9_-]{8,}|bearer\s+[A-Za-z0-9._-]{8,}|data:image/|data:audio/)"
)
MEANINGFUL_PLAIN_TEXT_RE = re.compile(r"[\u4e00-\u9fffA-Za-z0-9]")
HIDDEN_REASONING_MARKER_RE = re.compile(
    r"(?is)<\s*/?\s*(thinking|think|analysis|chain_of_thought|cot)\b"
)


class RikkaValidationResult(BaseModel):
    """Result returned by structured response validation."""

    ok: bool
    response: RikkaResponse
    errors: list[str] = []
    repaired: bool = False
    repair_notes: list[str] = []


def _fallback_response(
    reason_code: str = "safety_fallback",
    text: str = "嗯...我听到了。先把这段回响轻轻放好。",
) -> RikkaResponse:
    return RikkaResponse(
        spoken_text=text,
        subtitle_text=text,
        emotion="soft_smile",
        motion="thinking",
        gaze="camera",
        priority="normal",
        interruptible=True,
        reason_code=reason_code,
        memory_writes=[],
    )


def _extract_json_object(raw: str) -> dict[str, Any]:
    cleaned = clean_public_text(raw)
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`").strip()
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()

    decoder = json.JSONDecoder()
    for start, char in enumerate(cleaned):
        if char != "{":
            continue
        try:
            payload, _end = decoder.raw_decode(cleaned[start:])
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    raise ValueError("No JSON object found in response")


def _infer_memory_kind(item: dict[str, Any]) -> str:
    text = f"{item.get('kind', '')} {item.get('key', '')} {item.get('value', '')}".lower()
    if any(token in text for token in ("blocked", "block", "ban", "forbid", "不要聊", "别聊")):
        return "blocked_topic"
    if any(token in text for token in ("joke", "梗", "笑话")):
        return "joke"
    if any(token in text for token in ("preference", "like", "likes", "喜欢", "爱吃", "偏好")):
        return "preference"
    if any(token in text for token in ("stream", "summary", "status", "condition", "病情", "庭院")):
        return "stream_summary"
    return "viewer_note"


def _normalize_memory_writes_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Repair common LLM memory_writes shape drift without relaxing public schema."""
    writes = payload.get("memory_writes")
    if not isinstance(writes, list):
        return payload

    normalized_writes: list[dict[str, Any]] = []
    allowed_keys = {"kind", "key", "value"}
    for item in writes:
        if not isinstance(item, dict):
            normalized_writes.append(item)
            continue
        normalized = {key: item[key] for key in allowed_keys if key in item}
        if "kind" not in normalized:
            normalized["kind"] = _infer_memory_kind(item)
        normalized_writes.append(normalized)

    return {**payload, "memory_writes": normalized_writes}


def _normalize_response_payload(payload: dict[str, Any]) -> dict[str, Any]:
    payload = _normalize_memory_writes_payload(payload)
    if payload.get("gaze") == "screen":
        payload = {**payload, "gaze": "game"}
    return payload


def _repair_incomplete_response_payload(
    payload: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    """Fill safe defaults for common incomplete structured JSON responses."""
    repaired = dict(payload)
    notes: list[str] = []

    spoken_text = clean_public_text(repaired.get("spoken_text"))
    if "subtitle_text" not in repaired and spoken_text:
        repaired["subtitle_text"] = spoken_text
        notes.append("subtitle_text defaulted from spoken_text")

    defaults = {
        "reason_code": "idle_fill",
    }
    for key, value in defaults.items():
        if key not in repaired:
            repaired[key] = value
            notes.append(f"{key} defaulted")

    return repaired, notes


def _default_response_payload_from_spoken_text(spoken_text: str) -> dict[str, Any]:
    return {
        "spoken_text": spoken_text,
        "subtitle_text": spoken_text,
        "emotion": "neutral",
        "motion": "idle",
        "gaze": "camera",
        "priority": "normal",
        "interruptible": True,
        "reason_code": "idle_fill",
        "memory_writes": [],
    }


def _parse_quoted_string_at(text: str, start: int) -> str:
    quote = text[start]
    if quote == '"':
        value, _end = json.JSONDecoder().raw_decode(text[start:])
        if not isinstance(value, str):
            raise ValueError("spoken_text is not a string")
        return value

    end = start + 1
    escaped = False
    while end < len(text):
        char = text[end]
        if char == "\\" and not escaped:
            escaped = True
            end += 1
            continue
        if char == quote and not escaped:
            value = ast.literal_eval(text[start : end + 1])
            if not isinstance(value, str):
                raise ValueError("spoken_text is not a string")
            return value
        escaped = False
        end += 1
    raise ValueError("spoken_text string is unterminated")


def _extract_spoken_text_value(raw: Any, payload: dict[str, Any] | None = None) -> str:
    if isinstance(payload, dict) and "spoken_text" in payload:
        return clean_response_text(payload.get("spoken_text"))
    if isinstance(raw, dict) and "spoken_text" in raw:
        return clean_response_text(raw.get("spoken_text"))

    text = str(raw or "")
    for match in SPOKEN_TEXT_FIELD_RE.finditer(text):
        start = match.end()
        while start < len(text) and text[start].isspace():
            start += 1
        if start >= len(text):
            continue
        try:
            if text[start] in {"'", '"'}:
                value = _parse_quoted_string_at(text, start)
            else:
                end = start
                while end < len(text) and text[end] not in {",", "\n", "\r", "}"}:
                    end += 1
                value = text[start:end].strip()
            cleaned = clean_response_text(value)
            if cleaned:
                return cleaned
        except (ValueError, SyntaxError, json.JSONDecodeError):
            continue
    return ""


def _extract_plain_response_text(raw: Any) -> str:
    if not isinstance(raw, str):
        return ""

    text = raw.strip()
    if not text or text.startswith(PROVIDER_ERROR_PREFIX):
        return ""
    if text.startswith(("{", "[")) or SPOKEN_TEXT_FIELD_RE.search(text):
        return ""
    if HIDDEN_REASONING_MARKER_RE.search(text):
        return ""
    if SECRET_OR_MEDIA_MARKER_RE.search(text):
        return ""

    cleaned = clean_response_text(text)
    if not cleaned or not MEANINGFUL_PLAIN_TEXT_RE.search(cleaned):
        return ""
    return cleaned


def validate_rikka_response(raw: Any) -> RikkaValidationResult:
    """Validate and repair an LLM/provider response into RikkaResponse."""
    errors: list[str] = []
    payload: dict[str, Any] | None = None

    try:
        payload = raw if isinstance(raw, dict) else _extract_json_object(str(raw))
        repair_notes: list[str] = []
        if isinstance(payload, dict):
            payload, repair_notes = _repair_incomplete_response_payload(payload)
            payload = _normalize_response_payload(payload)
        response = RikkaResponse.model_validate(payload)
        return RikkaValidationResult(
            ok=True,
            response=response,
            errors=[],
            repaired=bool(repair_notes),
            repair_notes=repair_notes,
        )
    except (ValidationError, ValueError, json.JSONDecodeError, TypeError) as exc:
        errors.append(str(exc))

    spoken_text = _extract_spoken_text_value(raw, payload)
    if spoken_text:
        response = RikkaResponse.model_validate(
            _default_response_payload_from_spoken_text(spoken_text)
        )
        return RikkaValidationResult(
            ok=True,
            response=response,
            errors=[],
            repaired=True,
            repair_notes=[
                "spoken_text extracted from malformed response",
                "response fields defaulted from spoken_text repair",
            ],
        )

    plain_text = _extract_plain_response_text(raw)
    if plain_text:
        response = RikkaResponse.model_validate(
            _default_response_payload_from_spoken_text(plain_text)
        )
        return RikkaValidationResult(
            ok=True,
            response=response,
            errors=[],
            repaired=True,
            repair_notes=[
                "plain text used as spoken_text",
                "response fields defaulted from plain text repair",
            ],
        )

    return RikkaValidationResult(
        ok=False,
        response=_fallback_response(),
        errors=errors,
    )


def normalize_live_event(payload: dict[str, Any]) -> LiveEvent:
    """Normalize external payloads into the shared LiveEvent contract."""
    event_payload = payload.get("event", payload)
    event_payload = dict(event_payload)

    if "privacy" not in event_payload:
        event_payload["privacy"] = {
            "contains_raw_media": False,
            "cloud_upload_allowed": False,
        }
    if "source" not in event_payload:
        event_payload["source"] = "debug"

    return LiveEvent.model_validate(event_payload)


def _event_comment(event: LiveEvent) -> RikkaResponse:
    try:
        identity_settings = get_default_settings_store().snapshot().identity
    except Exception:
        identity_settings = None
    actor_name = event_default_actor_name(event, identity_settings)
    host_name, audience_name = identity_names(identity_settings)

    event_text = truncate_text(event.text or "", 42)

    if event.type == "chat.gift":
        text = f"谢谢{actor_name or '你'}的礼物。它落下来的声音，很轻，也很亮。"
        return _fallback_response("thank_gift", text)

    if event.type == "chat.message":
        if event_text:
            suffix = "" if event_text.endswith(("。", "！", "？", ".", "!", "?")) else "。"
            text = (
                f"{actor_name or audience_name}的回响我看到了："
                f"{event_text}{suffix}嗯，我会好好接住的。"
            )
        else:
            text = f"{actor_name or audience_name}的回响我看到了。嗯，我会好好接住的。"
        return _fallback_response("reply_chat", text)

    if event.type == "host.note":
        text = f"收到{host_name}的提示了。{event_text or '我会把节奏放得轻一点。'}"
        return _fallback_response("host_note", text)

    if event.type in {"game.roi_changed", "game.result_detected"}:
        text = f"画面有变化了。{event_text or '像是方块边缘闪了一下，我先轻轻提醒你。'}"
        return _fallback_response("game_comment", text)

    text = event_text or "测试回响收到了。系统这边，声音很安静。"
    return _fallback_response("idle_fill", text)


def plan_rikka_response(
    event: LiveEvent,
    candidate_response: Any | None = None,
) -> RikkaValidationResult:
    """Return a validated Rikka response for an event.

    If an LLM candidate is supplied, this validates and repairs it. Otherwise it
    returns a deterministic fallback suitable for local debug and offline tests.
    """
    if candidate_response is not None:
        return validate_rikka_response(candidate_response)

    return RikkaValidationResult(
        ok=True,
        response=_event_comment(event),
        errors=[],
    )

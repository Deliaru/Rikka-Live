"""Privacy-safe log redaction helpers."""

from __future__ import annotations

import re
from typing import Any


LOG_PATTERNS = ("*.log", "*.err", "*.out")
SECRET_VALUE_RE = re.compile(r"(?i)\bsk-[A-Za-z0-9_-]{12,}\b")
BEARER_RE = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{12,}")
DATA_MEDIA_RE = re.compile(
    r"data:(?:audio|image)/[^;,\s]+;base64,[A-Za-z0-9+/=]{40,}"
)
BASE64_BLOB_RE = re.compile(r"\b[A-Za-z0-9+/]{120,}={0,2}\b")
KEY_VALUE_SECRET_RE = re.compile(
    r"(?i)(['\"]?(?:llm_api_key|api_key|sessdata|voice_audio_base64|voice_id|authorization|access_token|secret)['\"]?\s*[:=]\s*)"
    r"(['\"][^'\"]*['\"]|[^,\s}\]]+)"
)
RAW_PAYLOAD_MARKERS = (
    "Messages:",
    "'messages':",
    '"messages":',
    "voice_audio_base64",
    "data:audio/",
)
MAX_LOG_LINE_LENGTH = 1200


def redact_log_text(value: Any, *, max_length: int = MAX_LOG_LINE_LENGTH) -> str:
    """Return privacy-safe text for local files and debug routes."""
    text = str(value or "")
    provider_payload_marker = next(
        (marker for marker in RAW_PAYLOAD_MARKERS if marker in text),
        "",
    )
    if provider_payload_marker and len(text) > max_length:
        prefix = text.split(provider_payload_marker, 1)[0].rstrip()
        text = f"{prefix} {provider_payload_marker} [redacted provider payload]"

    text = DATA_MEDIA_RE.sub("data:media/[redacted];base64,[redacted]", text)
    text = BASE64_BLOB_RE.sub("[redacted base64]", text)
    text = BEARER_RE.sub("Bearer [redacted]", text)
    text = KEY_VALUE_SECRET_RE.sub(r"\1[redacted]", text)
    text = SECRET_VALUE_RE.sub("sk-[redacted]", text)

    if len(text) > max_length:
        text = f"{text[:max_length - 16]}... [truncated]"
    return text


def redact_debug_text(value: Any) -> str:
    """Return privacy-safe diagnostic text for debug surfaces."""
    return redact_log_text(value)

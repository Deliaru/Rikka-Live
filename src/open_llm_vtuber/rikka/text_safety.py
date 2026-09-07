"""Text cleaning helpers for subtitles, TTS, and structured planner output."""

from __future__ import annotations

import re
from typing import Any

HIDDEN_BLOCK_RE = re.compile(
    r"<\s*(thinking|think|analysis|chain_of_thought|cot)\b[^>]*>.*?"
    r"<\s*/\s*\1\s*>",
    flags=re.IGNORECASE | re.DOTALL,
)
HIDDEN_TAG_RE = re.compile(
    r"</?\s*(thinking|think|analysis|chain_of_thought|cot)\b[^>]*>",
    flags=re.IGNORECASE,
)
ROLE_PREFIX_RE = re.compile(
    r"^\s*(assistant|ai|rika|rikka|六花|弥生月六花)\s*[:：]\s*",
    flags=re.IGNORECASE,
)
STAGE_DIRECTION_PREFIX_RE = re.compile(
    r"^\s*(?:[\[(（【][A-Za-z0-9_\-\u4e00-\u9fff ]{1,24}[\])）】]\s*)+"
)
INLINE_ACTION_TAG_RE = re.compile(
    r"[\[(（【]\s*"
    r"(neutral|soft_smile|curious|happy|worried|surprised|teasing|quiet|"
    r"idle|nod|tilt_head|look_close|look_away|small_wave|thinking|"
    r"camera|chat|game|down|away)"
    r"\s*[\])）】]",
    flags=re.IGNORECASE,
)
CODE_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", flags=re.IGNORECASE)
WHITESPACE_RE = re.compile(r"\s+")


def clean_public_text(value: Any) -> str:
    """Return text that is safe to show in subtitles or send to TTS."""
    if value is None:
        return ""

    text = str(value)
    previous = None
    while previous != text:
        previous = text
        text = HIDDEN_BLOCK_RE.sub("", text)

    text = HIDDEN_TAG_RE.sub("", text)
    text = CODE_FENCE_RE.sub("", text)
    text = ROLE_PREFIX_RE.sub("", text)
    text = text.replace("\u200b", "").strip()
    return WHITESPACE_RE.sub(" ", text)


def clean_response_text(value: Any) -> str:
    """Return validated response text that will not speak stage directions."""
    text = clean_public_text(value)
    text = INLINE_ACTION_TAG_RE.sub("", text).strip()
    previous = None
    while previous != text:
        previous = text
        text = STAGE_DIRECTION_PREFIX_RE.sub("", text).strip()
    return WHITESPACE_RE.sub(" ", text)


def truncate_text(text: str, limit: int) -> str:
    """Truncate user-facing text without splitting the caller's schema."""
    text = clean_response_text(text)
    if len(text) <= limit:
        return text
    if limit <= 3:
        return text[:limit]
    return f"{text[: limit - 3].rstrip()}..."

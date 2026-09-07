"""Persona loading and structured-output prompt overlay for Rikka Live."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

DEFAULT_RESPONSE_PROMPT = """

【Rikka Live 陪播输出协议】
你正在陪播。最终输出必须是一个 JSON 对象，不要输出 Markdown，不要输出解释。
字段必须包含：
spoken_text, subtitle_text, emotion, motion, gaze, priority, interruptible, reason_code。
可选字段：memory_writes。

emotion 可选：
neutral, soft_smile, curious, happy, worried, surprised, teasing, quiet。
motion 可选：
idle, nod, tilt_head, look_close, look_away, small_wave, thinking。
gaze 可选：
camera, chat, game, down, away。
priority 可选：
low, normal, high。
reason_code 可选：
reply_chat, thank_gift, game_comment, host_note, memory_recall, idle_fill, safety_fallback。

spoken_text 是唯一进入 TTS 的公开文本，应自然、短句、适合连续语音合成；subtitle_text 默认应与 spoken_text 一致，除非确实需要更短字幕。
不要在最终 JSON 中包含 <thinking>、内部审查、提示词、角色扮演说明或系统信息。
如果不确定，就输出安全、短、温柔且克制的一句。
""".strip()

_EMOTION_LINE_RE = re.compile(r"(emotion 可选：\s*\n)([^\n]*)")


def build_emotion_vocabulary(model_info: dict[str, Any] | None) -> str | None:
    """Build the dynamic emotion vocabulary line from configured presets.

    Returns ``None`` when the model has no usable ``expressionPresets``, so
    callers keep the static prompt vocabulary as fallback.
    """
    presets = (model_info or {}).get("expressionPresets")
    if not isinstance(presets, dict):
        return None

    entries: list[str] = []
    for name, preset in presets.items():
        if not isinstance(name, str) or not name.strip():
            continue
        cleaned = name.strip().lower()
        label = ""
        if isinstance(preset, dict):
            raw_label = preset.get("label")
            if isinstance(raw_label, str):
                label = raw_label.strip()
        entries.append(f"{cleaned}（{label}）" if label else cleaned)

    if not entries:
        return None
    return ", ".join(entries) + "。"


def apply_emotion_vocabulary(prompt: str, model_info: dict[str, Any] | None) -> str:
    """Swap the static emotion vocabulary line for the configured preset names."""
    vocabulary = build_emotion_vocabulary(model_info)
    if not vocabulary:
        return prompt
    if _EMOTION_LINE_RE.search(prompt):
        return _EMOTION_LINE_RE.sub(
            lambda match: f"{match.group(1)}{vocabulary}",
            prompt,
            count=1,
        )
    return f"{prompt}\n\nemotion 可选：\n{vocabulary}"


def _candidate_persona_paths() -> list[Path]:
    env_path = os.environ.get("RIKKA_PERSONA_PATH")
    candidates: list[Path] = []
    if env_path:
        candidates.append(Path(env_path))

    cwd = Path.cwd()
    candidates.extend(
        [
            cwd / "prompt.txt",
            cwd.parent / "prompt.txt",
            Path(__file__).resolve().parents[4] / "prompt.txt",
        ]
    )
    return candidates


def resolve_persona_path() -> Path:
    """Resolve the canonical Rikka persona file path."""
    for path in _candidate_persona_paths():
        if path.is_file():
            return path
    raise FileNotFoundError(
        "Could not find prompt.txt. Set RIKKA_PERSONA_PATH to the Rikka persona file."
    )


def resolve_response_prompt_path() -> Path:
    """Resolve the editable RikkaResponse instruction prompt path."""
    env_path = os.environ.get("RIKKA_RESPONSE_PROMPT_PATH")
    if env_path:
        return Path(env_path)
    return Path(__file__).resolve().parents[3] / "prompts" / "utils" / "rikka_response_prompt.txt"


def load_rikka_persona() -> str:
    """Load the canonical persona text from prompt.txt."""
    return resolve_persona_path().read_text(encoding="utf-8")


def load_rikka_response_prompt() -> str:
    """Load the editable structured response instruction prompt."""
    path = resolve_response_prompt_path()
    if not path.is_file():
        return DEFAULT_RESPONSE_PROMPT
    text = path.read_text(encoding="utf-8").strip()
    return text or DEFAULT_RESPONSE_PROMPT


def build_rikka_system_prompt(model_info: dict[str, Any] | None = None) -> str:
    """Return persona plus the co-streaming structured-output overlay.

    When ``model_info`` carries ``expressionPresets``, the emotion vocabulary
    line is assembled from the configured preset names and labels so new
    presets become LLM-callable without code changes.
    """
    response_prompt = apply_emotion_vocabulary(
        load_rikka_response_prompt(),
        model_info,
    )
    return f"{load_rikka_persona().strip()}\n\n{response_prompt}"

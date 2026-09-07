"""Xiaomi MiMo V2.5 TTS provider."""

from __future__ import annotations

import base64
import mimetypes
import os
from pathlib import Path
from typing import Any

from loguru import logger
from openai import OpenAI

from .tts_interface import TTSInterface

MAX_VOICE_BASE64_BYTES = 10 * 1024 * 1024
PRESET_MODEL = "mimo-v2.5-tts"
VOICE_DESIGN_MODEL = "mimo-v2.5-tts-voicedesign"
VOICE_CLONE_MODEL = "mimo-v2.5-tts-voiceclone"
KNOWN_PRESET_VOICES = {
    "mimo_default",
    "冰糖",
    "茉莉",
    "苏打",
    "白桦",
    "Mia",
    "Chloe",
    "Milo",
    "Dean",
}
DEFAULT_STYLE_PROMPT = (
    "温柔、克制、清澈，语速略慢，像在直播中轻轻回应观众。"
)
DEFAULT_VOICE_DESIGN_PROMPT = (
    "A young Chinese woman with a clear, gentle, slightly cool voice; "
    "soft but lively, suitable for a virtual livestream companion."
)


class TTSEngine(TTSInterface):
    """Generate audio through Xiaomi MiMo's OpenAI-compatible TTS API."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.xiaomimimo.com/v1",
        model: str = PRESET_MODEL,
        voice: str = "mimo_default",
        voice_design_prompt: str = DEFAULT_VOICE_DESIGN_PROMPT,
        voice_audio_path: str = "",
        voice_audio_base64: str = "",
        voice_mime_type: str = "audio/mpeg",
        style_prompt: str = DEFAULT_STYLE_PROMPT,
        audio_format: str = "wav",
        optimize_text_preview: bool = False,
        timeout_seconds: float = 45.0,
    ):
        self.api_key = api_key
        self.base_url = base_url or "https://api.xiaomimimo.com/v1"
        self.model = model or PRESET_MODEL
        self.voice = voice or "mimo_default"
        self.voice_design_prompt = voice_design_prompt or DEFAULT_VOICE_DESIGN_PROMPT
        self.voice_audio_path = voice_audio_path or ""
        self.voice_audio_base64 = voice_audio_base64 or ""
        self.voice_mime_type = voice_mime_type or "audio/mpeg"
        self.style_prompt = style_prompt or DEFAULT_STYLE_PROMPT
        self.audio_format = (audio_format or "wav").lower()
        self.optimize_text_preview = optimize_text_preview
        self.timeout_seconds = (
            timeout_seconds if timeout_seconds and timeout_seconds > 0 else 45.0
        )
        self.file_extension = "wav" if self.audio_format == "wav" else self.audio_format

        if self.audio_format not in {"wav", "mp3"}:
            logger.warning(
                f"Unsupported Xiaomi MiMo audio format '{self.audio_format}', using wav."
            )
            self.audio_format = "wav"
            self.file_extension = "wav"

        self.client = OpenAI(
            api_key=api_key,
            base_url=self.base_url,
            timeout=self.timeout_seconds,
        )
        logger.info(f"Xiaomi MiMo TTS initialized with model {self.model}")
        if self._uses_preset_voice() and self.voice not in KNOWN_PRESET_VOICES:
            logger.warning(
                f"Xiaomi MiMo preset voice '{self.voice}' is not in the documented "
                "preset list; the API may reject it."
            )

    def _uses_voice_clone(self) -> bool:
        return self.model == VOICE_CLONE_MODEL or self.model.endswith("voiceclone")

    def _uses_voice_design(self) -> bool:
        return self.model == VOICE_DESIGN_MODEL or self.model.endswith("voicedesign")

    def _uses_preset_voice(self) -> bool:
        return not self._uses_voice_clone() and not self._uses_voice_design()

    def _infer_mime_type(self, path: Path) -> str:
        guessed, _ = mimetypes.guess_type(path)
        if guessed in {"audio/mpeg", "audio/mp3", "audio/wav"}:
            return guessed
        if path.suffix.lower() == ".wav":
            return "audio/wav"
        return self.voice_mime_type or "audio/mpeg"

    def _load_voice(self) -> str:
        if self.voice_audio_base64:
            value = self.voice_audio_base64.strip()
            if value.startswith("data:"):
                return value
            if len(value.encode("utf-8")) > MAX_VOICE_BASE64_BYTES:
                raise ValueError("Xiaomi MiMo voice_audio_base64 exceeds 10 MB")
            return f"data:{self.voice_mime_type};base64,{value}"

        if not self.voice_audio_path:
            raise ValueError(
                "Xiaomi MiMo voice clone requires voice_audio_path or voice_audio_base64"
            )

        path = Path(self.voice_audio_path)
        if not path.is_file():
            raise FileNotFoundError(f"Voice sample not found: {path}")

        voice_base64 = base64.b64encode(path.read_bytes()).decode("utf-8")
        if len(voice_base64.encode("utf-8")) > MAX_VOICE_BASE64_BYTES:
            raise ValueError("Xiaomi MiMo voice sample exceeds 10 MB after base64")
        return f"data:{self._infer_mime_type(path)};base64,{voice_base64}"

    def _extract_audio_data(self, message: Any) -> str:
        audio = getattr(message, "audio", None)
        if isinstance(audio, dict):
            return audio.get("data", "")
        return getattr(audio, "data", "")

    def _build_messages(self, text: str) -> list[dict[str, str]]:
        user_prompt = (
            self.voice_design_prompt
            if self._uses_voice_design()
            else self.style_prompt
        )
        return [
            {
                "role": "user",
                "content": user_prompt or "",
            },
            {
                "role": "assistant",
                "content": text,
            },
        ]

    def _build_audio_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"format": self.audio_format}
        if self._uses_voice_clone():
            payload["voice"] = self._load_voice()
        elif self._uses_voice_design():
            if self.optimize_text_preview:
                payload["optimize_text_preview"] = True
        else:
            payload["voice"] = self.voice
        return payload

    def generate_audio(self, text: str, file_name_no_ext=None) -> str | None:
        if not self.api_key:
            logger.error("Xiaomi MiMo API key is empty.")
            return None

        file_name = self.generate_cache_file_name(
            file_name_no_ext,
            self.file_extension,
        )

        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=self._build_messages(text),
                audio=self._build_audio_payload(),
            )
            message = completion.choices[0].message
            audio_data = self._extract_audio_data(message)
            if not audio_data:
                raise ValueError("Xiaomi MiMo response did not include audio data")

            audio_bytes = base64.b64decode(audio_data)
            with open(file_name, "wb") as output_file:
                output_file.write(audio_bytes)

            return file_name
        except Exception as exc:
            logger.error(f"Xiaomi MiMo TTS generation failed: {exc}")
            if os.path.exists(file_name):
                os.remove(file_name)
            return None

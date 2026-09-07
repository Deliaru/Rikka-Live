"""HTTP adapters for local and cloud IndexTTS2 speech providers."""

from __future__ import annotations

import base64
import os
import re
import shutil
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests
from loguru import logger

from ..rikka.text_safety import clean_response_text
from .indextts2_emotion import (
    DEFAULT_QUIET_COMPANION_VECTOR,
    EMOTION_KEYS,
    clamp_quiet_companion_alpha,
    normalize_emotion_vector,
)
from .tts_interface import TTSInterface

LOCAL_MODE = "local"
CLOUD_MODE = "cloud"
DEFAULT_LOCAL_API_URL = "http://127.0.0.1:7861/tts"
DEFAULT_MODELVERSE_BASE_URL = "https://api.modelverse.cn/v1"
DEFAULT_INDEXTTS2_MODEL = "IndexTeam/IndexTTS-2"
DEFAULT_CLOUD_STYLE = "default"
QUIET_COMPANION_STYLE = "quiet_companion"
PUNCTUATION_ONLY_RE = re.compile(r"[\s.,!?，。！？'\"』」）】、…\-—~]+")


class TTSEngine(TTSInterface):
    """Generate audio through cloud ModelVerse or a local IndexTTS2 service."""

    accepts_rikka_emotion_kwargs = True

    def __init__(
        self,
        mode: str = CLOUD_MODE,
        api_key: str = "",
        base_url: str = DEFAULT_MODELVERSE_BASE_URL,
        model: str = DEFAULT_INDEXTTS2_MODEL,
        voice_id: str = "",
        default_tts_style: str = DEFAULT_CLOUD_STYLE,
        quiet_companion_emo_alpha: float = 1.0,
        quiet_companion_emo_vec: list[float] | dict[str, float] | None = None,
        api_url: str = DEFAULT_LOCAL_API_URL,
        speaker_audio_path: str = "private/voice/rikka_voice_clone.wav",
        emo_audio_path: str = "",
        emo_alpha: float = 0.6,
        use_emo_text: bool = False,
        emo_text: str = "",
        use_random: bool = False,
        audio_format: str = "wav",
        timeout_seconds: float = 180.0,
        sentence_split_enabled: bool = False,
        sentence_split_method: str = "regex",
        max_text_tokens_per_segment: int = 80,
        sentence_interval_ms: int = 0,
    ):
        self.mode = (mode or CLOUD_MODE).lower()
        if self.mode not in {CLOUD_MODE, LOCAL_MODE}:
            logger.warning(
                f"Unsupported IndexTTS2 mode '{self.mode}', using cloud mode."
            )
            self.mode = CLOUD_MODE

        self.api_key = api_key or ""
        self.base_url = (base_url or DEFAULT_MODELVERSE_BASE_URL).rstrip("/")
        self.model = model or DEFAULT_INDEXTTS2_MODEL
        self.voice_id = voice_id or ""
        self.default_tts_style = default_tts_style or DEFAULT_CLOUD_STYLE
        self.quiet_companion_emo_alpha = clamp_quiet_companion_alpha(
            quiet_companion_emo_alpha
        )
        self.quiet_companion_emo_vec = normalize_emotion_vector(
            quiet_companion_emo_vec,
            default=DEFAULT_QUIET_COMPANION_VECTOR,
        )
        self.api_url = api_url or DEFAULT_LOCAL_API_URL
        self.speaker_audio_path = speaker_audio_path or ""
        self.emo_audio_path = emo_audio_path or ""
        self.emo_alpha = emo_alpha
        self.use_emo_text = use_emo_text
        self.emo_text = emo_text or ""
        self.use_random = use_random
        self.audio_format = (audio_format or "wav").lower()
        if self.audio_format not in {"wav", "mp3"}:
            logger.warning(
                f"Unsupported IndexTTS2 audio format '{self.audio_format}', using wav."
            )
            self.audio_format = "wav"
        self.file_extension = "wav" if self.mode == CLOUD_MODE else self.audio_format
        self.timeout_seconds = (
            timeout_seconds if timeout_seconds and timeout_seconds > 0 else 180.0
        )
        self.sentence_split_enabled = bool(sentence_split_enabled)
        self.sentence_split_method = (
            sentence_split_method if sentence_split_method in {"regex", "pysbd"} else "regex"
        )
        self.max_text_tokens_per_segment = max_text_tokens_per_segment or 80
        self.sentence_interval_ms = max(0, int(sentence_interval_ms or 0))

    def _build_local_payload(self, text: str) -> dict[str, Any]:
        return {
            "text": text,
            "speaker_audio_path": self._resolve_local_path(self.speaker_audio_path),
            "emo_audio_path": self._resolve_local_path(self.emo_audio_path),
            "emo_alpha": self.emo_alpha,
            "use_emo_text": self.use_emo_text,
            "emo_text": self.emo_text,
            "use_random": self.use_random,
            "audio_format": self.audio_format,
            "sentence_split_enabled": self.sentence_split_enabled,
            "sentence_split_method": self.sentence_split_method,
            "max_text_tokens_per_segment": self.max_text_tokens_per_segment,
        }

    def _clean_cloud_input(self, text: str) -> str:
        cleaned = clean_response_text(text)
        if not cleaned or not PUNCTUATION_ONLY_RE.sub("", cleaned):
            raise ValueError("IndexTTS2 cloud input is empty after cleaning")
        return cleaned

    def _emotion_overrides_from(
        self,
        emotion_vec: list[float] | dict[str, float] | None,
    ) -> dict[str, float]:
        if emotion_vec is None:
            return {}
        if isinstance(emotion_vec, dict):
            values = {
                key: float(value)
                for key, value in emotion_vec.items()
                if key in EMOTION_KEYS
            }
            raw_values = list(values.values())
        else:
            if len(emotion_vec) != len(EMOTION_KEYS):
                raise ValueError("IndexTTS2 emotion vector must have 8 dimensions")
            values = {
                key: float(value)
                for key, value in zip(EMOTION_KEYS, emotion_vec)
            }
            raw_values = list(values.values())

        if any(value < 0 or value > 1.2 for value in raw_values):
            raise ValueError("IndexTTS2 emotion values must be within [0, 1.2]")
        if sum(raw_values) > 1.5:
            raise ValueError("IndexTTS2 emotion vector sum must not exceed 1.5")
        return values

    def _build_quiet_companion_vector(
        self,
        emotion_vec: list[float] | dict[str, float] | None = None,
    ) -> list[float]:
        requested = self._emotion_overrides_from(emotion_vec)
        vector = list(self.quiet_companion_emo_vec)
        if "happy" in requested:
            vector[0] = min(0.15, max(0.05, requested["happy"]))
        if "sad" in requested:
            vector[2] = min(0.19, max(0.0, requested["sad"]))
        if "surprise" in requested:
            vector[6] = min(0.19, max(0.0, requested["surprise"]))
        return vector

    def _build_cloud_payload(
        self,
        text: str,
        tts_style: str | None = None,
        emotion_vec: list[float] | dict[str, float] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model,
            "input": self._clean_cloud_input(text),
            "voice": self.voice_id,
        }
        style = tts_style or self.default_tts_style
        if style == QUIET_COMPANION_STYLE:
            payload.update(
                {
                    "emo_control_method": 2,
                    "emo_alpha": self.quiet_companion_emo_alpha,
                    "emo_vec": self._build_quiet_companion_vector(emotion_vec),
                    "emo_random": False,
                }
            )
        if self.sentence_split_enabled:
            payload["max_text_tokens_per_segment"] = int(
                self.max_text_tokens_per_segment or 80
            )
        if self.sentence_interval_ms > 0:
            payload["interval_silence"] = round(self.sentence_interval_ms / 1000, 3)
        return payload

    def _build_payload(
        self,
        text: str,
        tts_style: str | None = None,
        emotion_vec: list[float] | dict[str, float] | None = None,
    ) -> dict[str, Any]:
        if self.mode == CLOUD_MODE:
            return self._build_cloud_payload(text, tts_style, emotion_vec)
        return self._build_local_payload(text)

    def _resolve_local_path(self, path: str) -> str:
        if not path:
            return ""
        return str(Path(path).expanduser().resolve())

    def _cloud_speech_url(self) -> str:
        return f"{self.base_url}/audio/speech"

    def _cloud_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "audio/wav, application/json",
        }

    def _log_non_audio_json_response(self, response: requests.Response) -> None:
        try:
            payload = response.json()
        except ValueError:
            return
        code = payload.get("code") or payload.get("error") or payload.get("message")
        if code:
            logger.error(f"IndexTTS2 provider returned JSON error: {code}")
        if str(code).lower() in {"invalid_voice_id", "voice_not_found"}:
            logger.error("IndexTTS2 cloud voice upload or refresh is required.")

    def _write_audio_response(
        self,
        response: requests.Response,
        file_name: str,
    ) -> str:
        content_type = response.headers.get("content-type", "")
        if content_type.startswith("audio/") or not content_type.startswith(
            "application/json"
        ):
            with open(file_name, "wb") as output_file:
                output_file.write(response.content)
            return file_name

        self._log_non_audio_json_response(response)
        payload = response.json()
        audio_base64 = (
            payload.get("audio_base64")
            or payload.get("audio")
            or payload.get("data")
            or ""
        )
        if audio_base64:
            if audio_base64.startswith("data:"):
                audio_base64 = audio_base64.split(",", 1)[-1]
            with open(file_name, "wb") as output_file:
                output_file.write(base64.b64decode(audio_base64))
            return file_name

        audio_path = payload.get("audio_path") or payload.get("path")
        if audio_path:
            path = Path(audio_path)
            if not path.is_file():
                raise FileNotFoundError(f"IndexTTS2 response path not found: {path}")
            shutil.copyfile(path, file_name)
            return file_name

        audio_url = payload.get("audio_url") or payload.get("url")
        if audio_url:
            if audio_url.startswith("/"):
                audio_url = urljoin(self.api_url, audio_url)
            audio_response = requests.get(audio_url, timeout=self.timeout_seconds)
            audio_response.raise_for_status()
            with open(file_name, "wb") as output_file:
                output_file.write(audio_response.content)
            return file_name

        raise ValueError("IndexTTS2 response did not include audio data")

    def _request_audio(
        self,
        text: str,
        tts_style: str | None = None,
        emotion_vec: list[float] | dict[str, float] | None = None,
    ) -> requests.Response:
        if self.mode == CLOUD_MODE:
            return requests.post(
                self._cloud_speech_url(),
                json=self._build_cloud_payload(text, tts_style, emotion_vec),
                headers=self._cloud_headers(),
                timeout=self.timeout_seconds,
            )
        return requests.post(
            self.api_url,
            json=self._build_local_payload(text),
            timeout=self.timeout_seconds,
        )

    def generate_audio(
        self,
        text: str,
        file_name_no_ext=None,
        tts_style: str | None = None,
        emotion_vec: list[float] | dict[str, float] | None = None,
    ) -> str | None:
        if self.mode == CLOUD_MODE:
            if not self.api_key:
                logger.error("IndexTTS2 cloud API key is empty.")
                return None
            if not self.voice_id:
                logger.error("IndexTTS2 cloud voice_id is empty; voice refresh required.")
                return None

        file_name = self.generate_cache_file_name(
            file_name_no_ext,
            self.file_extension,
        )
        try:
            response = self._request_audio(text, tts_style, emotion_vec)
            response.raise_for_status()
            return self._write_audio_response(response, file_name)
        except Exception as exc:
            logger.error(f"IndexTTS2 TTS generation failed: {exc}")
            if os.path.exists(file_name):
                os.remove(file_name)
            return None

"""Debug console helpers for Rikka Live.

The routes using this module expose only a narrow, demo-safe subset of the
runtime configuration and local logs. Secrets are accepted for writes but are
never returned verbatim.
"""

from __future__ import annotations

import importlib.util
import json
import re
import time
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..utils.log_redaction import LOG_PATTERNS, redact_debug_text, redact_log_text
from ..tts.indextts2_emotion import (
    DEFAULT_QUIET_COMPANION_VECTOR,
    clamp_quiet_companion_alpha,
    normalize_emotion_vector,
)
from .bilibili import normalize_room_ids
from .persona import (
    DEFAULT_RESPONSE_PROMPT,
    load_rikka_response_prompt,
    resolve_persona_path,
    resolve_response_prompt_path,
)


CONFIG_PATH = Path("conf.yaml")
LOG_DIR = Path("logs")
SECRET_KEYS = {
    "api_key",
    "llm_api_key",
    "voice_audio_base64",
    "voice_id",
    "sessdata",
}
ERROR_LINE_RE = re.compile(
    r"(?i)(^|[^a-z0-9_])(error|exception|traceback|fatal|failed|timeout)([^a-z0-9_]|$)"
)

LLM_PROVIDER_VALUES = (
    "stateless_llm_with_template",
    "openai_compatible_llm",
    "claude_llm",
    "llama_cpp_llm",
    "ollama_llm",
    "lmstudio_llm",
    "openai_llm",
    "gemini_llm",
    "zhipu_llm",
    "deepseek_llm",
    "groq_llm",
    "mistral_llm",
)
OPENAI_STYLE_LLM_PROVIDERS = {
    "openai_compatible_llm",
    "openai_llm",
    "gemini_llm",
    "zhipu_llm",
    "deepseek_llm",
    "groq_llm",
    "mistral_llm",
    "lmstudio_llm",
    "ollama_llm",
}
ASR_PROVIDER_VALUES = (
    "none",
    "sherpa_onnx_asr",
)


class LLMDebugConfigUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: Literal[
        "stateless_llm_with_template",
        "openai_compatible_llm",
        "claude_llm",
        "llama_cpp_llm",
        "ollama_llm",
        "lmstudio_llm",
        "openai_llm",
        "gemini_llm",
        "zhipu_llm",
        "deepseek_llm",
        "groq_llm",
        "mistral_llm",
    ] | None = None
    api_mode: Literal["chat", "responses"] | None = None
    base_url: str | None = None
    model: str | None = None
    api_key: str | None = Field(default=None, alias="api_key")


class XiaomiMimoDebugConfigUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    api_key: str | None = None
    base_url: str | None = None
    model: str | None = None
    voice: str | None = None
    voice_audio_path: str | None = None
    style_prompt: str | None = None
    timeout_seconds: float | None = None


class IndexTTS2DebugConfigUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: Literal["cloud", "local"] | None = None
    api_key: str | None = None
    base_url: str | None = None
    model: str | None = None
    voice_id: str | None = None
    default_tts_style: Literal["default", "quiet_companion"] | None = None
    quiet_companion_emo_alpha: float | None = None
    quiet_companion_emo_vec: list[float] | None = None
    api_url: str | None = None
    speaker_audio_path: str | None = None
    emo_audio_path: str | None = None
    emo_alpha: float | None = None
    use_emo_text: bool | None = None
    emo_text: str | None = None
    use_random: bool | None = None
    timeout_seconds: float | None = None
    sentence_split_enabled: bool | None = None
    sentence_split_method: Literal["regex", "pysbd"] | None = None
    max_text_tokens_per_segment: int | None = None
    sentence_interval_ms: int | None = None

    @field_validator("quiet_companion_emo_alpha")
    @classmethod
    def validate_quiet_companion_emo_alpha(cls, value: float | None) -> float | None:
        if value is None:
            return None
        return clamp_quiet_companion_alpha(value)

    @field_validator("quiet_companion_emo_vec")
    @classmethod
    def validate_quiet_companion_emo_vec(
        cls,
        value: list[float] | None,
    ) -> list[float] | None:
        if value is None:
            return None
        return normalize_emotion_vector(
            value,
            default=DEFAULT_QUIET_COMPANION_VECTOR,
        )


class TTSDebugConfigUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str | None = None
    xiaomi_mimo_tts: XiaomiMimoDebugConfigUpdate | None = None
    indextts2_tts: IndexTTS2DebugConfigUpdate | None = None


class ASRDebugConfigUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: Literal[
        "none",
        "sherpa_onnx_asr",
    ] | None = None


class BilibiliLiveDebugConfigUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    room_ids: list[int] | None = None
    sessdata: str | None = None

    @field_validator("room_ids", mode="before")
    @classmethod
    def validate_room_ids(cls, value: Any) -> list[int] | None:
        if value is None:
            return None
        if isinstance(value, str):
            raw_items = re.split(r"[\s,]+", value)
        else:
            raw_items = value
        return normalize_room_ids(raw_items)


class LiveDebugConfigUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bilibili_live: BilibiliLiveDebugConfigUpdate | None = None


class PromptTextUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str | None = None


class PromptsDebugConfigUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    persona: PromptTextUpdate | None = None
    response: PromptTextUpdate | None = None


class DebugConfigUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    llm: LLMDebugConfigUpdate | None = None
    tts: TTSDebugConfigUpdate | None = None
    asr: ASRDebugConfigUpdate | None = None
    live: LiveDebugConfigUpdate | None = None
    prompts: PromptsDebugConfigUpdate | None = None


def _read_yaml(path: Path = CONFIG_PATH) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}
    return data if isinstance(data, dict) else {}


def _write_yaml(data: dict[str, Any], path: Path = CONFIG_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        yaml.safe_dump(data, file, allow_unicode=True, sort_keys=False)


def _mask_secret(value: Any) -> str:
    if not value:
        return ""
    text = str(value)
    if len(text) <= 8:
        return "configured"
    return f"{text[:3]}...{text[-4:]}"


def _resolve_config_relative_path(config_path: Path, value: Any) -> Path | None:
    if not value:
        return None
    path = Path(str(value))
    if not path.is_absolute():
        path = config_path.parent / path
    return path.resolve()


def _sherpa_required_model_fields(model_type: str) -> tuple[str, ...]:
    return {
        "transducer": ("encoder", "decoder", "joiner", "tokens"),
        "paraformer": ("paraformer", "tokens"),
        "nemo_ctc": ("nemo_ctc", "tokens"),
        "wenet_ctc": ("wenet_ctc", "tokens"),
        "tdnn_ctc": ("tdnn_model", "tokens"),
        "whisper": ("whisper_encoder", "whisper_decoder", "tokens"),
        "sense_voice": ("sense_voice", "tokens"),
    }.get(model_type, ())


def _sherpa_onnx_status(
    asr_config: dict[str, Any],
    config_path: Path,
) -> dict[str, Any]:
    sherpa = asr_config.get("sherpa_onnx_asr") or {}
    if not isinstance(sherpa, dict) or not sherpa:
        return {
            "ready": False,
            "reason": "sherpa_onnx_asr config block is missing",
            "dependency_installed": importlib.util.find_spec("sherpa_onnx") is not None,
            "missing_files": [],
        }

    model_type = str(sherpa.get("model_type") or "sense_voice")
    missing_files = []
    for field in _sherpa_required_model_fields(model_type):
        resolved = _resolve_config_relative_path(config_path, sherpa.get(field))
        if resolved is None or not resolved.exists():
            missing_files.append(
                {
                    "field": field,
                    "path": str(resolved) if resolved else "",
                }
            )

    dependency_installed = importlib.util.find_spec("sherpa_onnx") is not None
    ready = dependency_installed and not missing_files
    reason = "ready"
    if not dependency_installed:
        reason = "sherpa_onnx package is not installed"
    elif missing_files:
        reason = "sherpa_onnx model files are missing"
    streaming = sherpa.get("streaming")
    streaming_missing_files = []
    if isinstance(streaming, dict) and streaming:
        streaming_model_type = str(streaming.get("model_type") or "transducer")
        streaming_required = {
            "transducer": ("encoder", "decoder", "joiner", "tokens"),
            "paraformer": ("encoder", "decoder", "tokens"),
            "zipformer": ("encoder", "decoder", "joiner", "tokens"),
            "zipformer2_ctc": ("model", "tokens"),
        }.get(streaming_model_type, ("tokens",))
        for field in streaming_required:
            resolved = _resolve_config_relative_path(config_path, streaming.get(field))
            if resolved is None or not resolved.exists():
                streaming_missing_files.append(
                    {"field": field, "path": str(resolved) if resolved else ""}
                )
        streaming_status = (
            "streaming_model_missing"
            if streaming_missing_files
            else "streaming_ready"
        )
    else:
        streaming_model_type = None
        streaming_status = "streaming_config_missing"

    return {
        "ready": ready,
        "reason": reason,
        "dependency_installed": dependency_installed,
        "model_type": model_type,
        "sample_rate": sherpa.get("sample_rate", 16000),
        "provider": sherpa.get("provider", "cpu"),
        "missing_files": missing_files,
        "streaming_status": streaming_status,
        "streaming_model_type": streaming_model_type,
        "streaming_missing_files": streaming_missing_files,
    }


def _redact_log_line(line: str) -> str:
    """Return a privacy-safe log line for the browser debug console."""
    return redact_log_text(line)


def _secret_ready(value: Any) -> bool:
    return bool(str(value or "").strip())


def _read_path(data: dict[str, Any], path: list[str]) -> Any:
    current: Any = data
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _ensure_path(data: dict[str, Any], path: list[str]) -> dict[str, Any]:
    current = data
    for key in path:
        child = current.get(key)
        if not isinstance(child, dict):
            child = {}
            current[key] = child
        current = child
    return current


def _apply_non_empty(target: dict[str, Any], key: str, value: Any) -> None:
    if value is None:
        return
    if isinstance(value, str) and value == "":
        return
    target[key] = value


def _read_text_file(path: Path, fallback: str = "") -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return fallback


def _write_prompt_file(path: Path, text: str) -> bool:
    current = _read_text_file(path)
    if current == text:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return True


def snapshot_debug_config(
    config_path: str | Path = CONFIG_PATH,
    *,
    updated_at_ms: int | None = None,
) -> dict[str, Any]:
    config_path = Path(config_path)
    raw = _read_yaml(config_path)
    character = raw.get("character_config") or {}
    agent = character.get("agent_config") or {}
    agent_settings = agent.get("agent_settings") or {}
    basic_agent = agent_settings.get("basic_memory_agent") or {}
    llm_configs = agent.get("llm_configs") or {}
    llm_provider = basic_agent.get("llm_provider") or "not_configured"
    llm_selected = llm_configs.get(llm_provider) or {}

    tts_config = character.get("tts_config") or {}
    tts_provider = tts_config.get("tts_model") or "not_configured"
    mimo = tts_config.get("xiaomi_mimo_tts") or {}
    indextts2 = tts_config.get("indextts2_tts") or {}
    asr_config = character.get("asr_config") or {}
    asr_provider = asr_config.get("asr_model") or "none"
    live_config = raw.get("live_config") or {}
    bilibili = live_config.get("bilibili_live") or {}
    persona_path = resolve_persona_path()
    response_prompt_path = resolve_response_prompt_path()

    return {
        "path": str(config_path.resolve()),
        "restart_required": False,
        "updated_at_ms": updated_at_ms,
        "llm": {
            "provider": llm_provider,
            "available_providers": list(LLM_PROVIDER_VALUES),
            "api_mode": llm_selected.get("api_mode", "chat"),
            "base_url": llm_selected.get("base_url", ""),
            "model": llm_selected.get("model", ""),
            "api_key_configured": _secret_ready(llm_selected.get("llm_api_key")),
            "api_key_preview": _mask_secret(llm_selected.get("llm_api_key")),
        },
        "tts": {
            "provider": tts_provider,
            "xiaomi_mimo_tts": {
                "base_url": mimo.get("base_url", ""),
                "model": mimo.get("model", ""),
                "voice": mimo.get("voice", ""),
                "voice_audio_path": mimo.get("voice_audio_path", ""),
                "style_prompt": mimo.get("style_prompt", ""),
                "timeout_seconds": mimo.get("timeout_seconds", 45.0),
                "api_key_configured": _secret_ready(mimo.get("api_key")),
                "api_key_preview": _mask_secret(mimo.get("api_key")),
            },
            "indextts2_tts": {
                "mode": indextts2.get("mode", "cloud"),
                "base_url": indextts2.get(
                    "base_url",
                    "https://api.modelverse.cn/v1",
                ),
                "model": indextts2.get("model", "IndexTeam/IndexTTS-2"),
                "api_key_configured": _secret_ready(indextts2.get("api_key")),
                "api_key_preview": _mask_secret(indextts2.get("api_key")),
                "voice_id_configured": _secret_ready(indextts2.get("voice_id")),
                "voice_id_preview": _mask_secret(indextts2.get("voice_id")),
                "default_tts_style": indextts2.get("default_tts_style", "default"),
                "quiet_companion_emo_alpha": indextts2.get(
                    "quiet_companion_emo_alpha",
                    1.0,
                ),
                "quiet_companion_emo_vec": indextts2.get(
                    "quiet_companion_emo_vec",
                    list(DEFAULT_QUIET_COMPANION_VECTOR),
                ),
                "api_url": indextts2.get("api_url", "http://127.0.0.1:7861/tts"),
                "speaker_audio_path": indextts2.get(
                    "speaker_audio_path",
                    "private/voice/rikka_voice_clone.wav",
                ),
                "emo_audio_path": indextts2.get("emo_audio_path", ""),
                "emo_alpha": indextts2.get("emo_alpha", 0.6),
                "use_emo_text": indextts2.get("use_emo_text", False),
                "emo_text": indextts2.get("emo_text", ""),
                "use_random": indextts2.get("use_random", False),
                "timeout_seconds": indextts2.get("timeout_seconds", 180.0),
                "sentence_split_enabled": indextts2.get(
                    "sentence_split_enabled",
                    False,
                ),
                "sentence_split_method": indextts2.get(
                    "sentence_split_method",
                    "regex",
                ),
                "max_text_tokens_per_segment": indextts2.get(
                    "max_text_tokens_per_segment",
                    80,
                ),
                "sentence_interval_ms": indextts2.get("sentence_interval_ms", 0),
            },
        },
        "asr": {
            "provider": asr_provider,
            "available_providers": list(ASR_PROVIDER_VALUES),
            "configured_blocks": sorted(
                key
                for key, value in asr_config.items()
                if key != "asr_model" and isinstance(value, dict) and value
            ),
            "sherpa_onnx_asr": _sherpa_onnx_status(asr_config, config_path),
            "restart_required": True,
        },
        "live": {
            "bilibili_live": {
                "room_ids": normalize_room_ids(bilibili.get("room_ids")),
                "sessdata_configured": _secret_ready(bilibili.get("sessdata")),
                "sessdata_preview": _mask_secret(bilibili.get("sessdata")),
            },
        },
        "prompts": {
            "persona": {
                "path": str(persona_path.resolve()),
                "text": _read_text_file(persona_path),
            },
            "response": {
                "path": str(response_prompt_path.resolve()),
                "text": load_rikka_response_prompt() or DEFAULT_RESPONSE_PROMPT,
            },
        },
    }


def patch_debug_config(
    update: DebugConfigUpdate,
    config_path: str | Path = CONFIG_PATH,
) -> dict[str, Any]:
    config_path = Path(config_path)
    raw = _read_yaml(config_path)
    changed = False

    if update.llm:
        basic = _ensure_path(
            raw,
            ["character_config", "agent_config", "agent_settings", "basic_memory_agent"],
        )
        llm_provider = update.llm.provider or basic.get("llm_provider")
        if update.llm.provider:
            basic["llm_provider"] = update.llm.provider
            changed = True
        if llm_provider:
            selected = _ensure_path(
                raw,
                ["character_config", "agent_config", "llm_configs", llm_provider],
            )
            before = json.dumps(selected, sort_keys=True, ensure_ascii=False)
            _apply_non_empty(selected, "base_url", update.llm.base_url)
            _apply_non_empty(selected, "model", update.llm.model)
            _apply_non_empty(selected, "llm_api_key", update.llm.api_key)
            if llm_provider in OPENAI_STYLE_LLM_PROVIDERS:
                _apply_non_empty(selected, "api_mode", update.llm.api_mode)
            changed = changed or before != json.dumps(
                selected,
                sort_keys=True,
                ensure_ascii=False,
            )

    if update.tts:
        tts_root = _ensure_path(raw, ["character_config", "tts_config"])
        if update.tts.provider:
            tts_root["tts_model"] = update.tts.provider
            changed = True
        if update.tts.xiaomi_mimo_tts:
            selected = _ensure_path(raw, ["character_config", "tts_config", "xiaomi_mimo_tts"])
            before = json.dumps(selected, sort_keys=True, ensure_ascii=False)
            patch = update.tts.xiaomi_mimo_tts
            for key in (
                "api_key",
                "base_url",
                "model",
                "voice",
                "voice_audio_path",
                "style_prompt",
                "timeout_seconds",
            ):
                _apply_non_empty(selected, key, getattr(patch, key))
            changed = changed or before != json.dumps(
                selected,
                sort_keys=True,
                ensure_ascii=False,
            )
        if update.tts.indextts2_tts:
            selected = _ensure_path(raw, ["character_config", "tts_config", "indextts2_tts"])
            before = json.dumps(selected, sort_keys=True, ensure_ascii=False)
            patch = update.tts.indextts2_tts
            for key in (
                "mode",
                "api_key",
                "base_url",
                "model",
                "voice_id",
                "default_tts_style",
                "quiet_companion_emo_alpha",
                "quiet_companion_emo_vec",
                "api_url",
                "speaker_audio_path",
                "emo_audio_path",
                "emo_alpha",
                "use_emo_text",
                "emo_text",
                "use_random",
                "timeout_seconds",
                "sentence_split_enabled",
                "sentence_split_method",
                "max_text_tokens_per_segment",
                "sentence_interval_ms",
            ):
                _apply_non_empty(selected, key, getattr(patch, key))
            changed = changed or before != json.dumps(
                selected,
                sort_keys=True,
                ensure_ascii=False,
            )

    if update.asr:
        asr_root = _ensure_path(raw, ["character_config", "asr_config"])
        before = json.dumps(asr_root, sort_keys=True, ensure_ascii=False)
        if update.asr.provider:
            asr_root["asr_model"] = update.asr.provider
        changed = changed or before != json.dumps(
            asr_root,
            sort_keys=True,
            ensure_ascii=False,
        )

    if update.live and update.live.bilibili_live:
        bilibili_root = _ensure_path(raw, ["live_config", "bilibili_live"])
        before = json.dumps(bilibili_root, sort_keys=True, ensure_ascii=False)
        patch = update.live.bilibili_live
        if patch.room_ids is not None:
            bilibili_root["room_ids"] = normalize_room_ids(patch.room_ids)
        _apply_non_empty(bilibili_root, "sessdata", patch.sessdata)
        changed = changed or before != json.dumps(
            bilibili_root,
            sort_keys=True,
            ensure_ascii=False,
        )

    if update.prompts:
        if update.prompts.persona and update.prompts.persona.text is not None:
            changed = _write_prompt_file(
                resolve_persona_path(),
                update.prompts.persona.text,
            ) or changed
        if update.prompts.response and update.prompts.response.text is not None:
            changed = _write_prompt_file(
                resolve_response_prompt_path(),
                update.prompts.response.text,
            ) or changed

    if changed:
        _write_yaml(raw, config_path)
    snapshot = snapshot_debug_config(config_path, updated_at_ms=int(time.time() * 1000))
    snapshot["restart_required"] = changed
    return snapshot


def list_log_files(log_dir: str | Path = LOG_DIR) -> list[Path]:
    log_dir = Path(log_dir)
    if not log_dir.exists():
        return []
    files: dict[Path, Path] = {}
    for pattern in LOG_PATTERNS:
        for path in log_dir.glob(pattern):
            if path.is_file():
                files[path.resolve()] = path
    return sorted(files.values(), key=lambda path: path.stat().st_mtime, reverse=True)


def _tail_text(path: Path, max_lines: int) -> list[str]:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    return [_redact_log_line(line) for line in lines[-max_lines:]]


def log_snapshot(
    log_dir: str | Path = LOG_DIR,
    *,
    max_files: int = 8,
    max_lines: int = 80,
) -> dict[str, Any]:
    files = []
    for path in list_log_files(log_dir)[:max_files]:
        stat = path.stat()
        files.append(
            {
                "name": path.name,
                "path": str(path.resolve()),
                "size": stat.st_size,
                "updated_at_ms": int(stat.st_mtime * 1000),
                "lines": _tail_text(path, max_lines),
            }
        )
    return {"files": files}


def error_snapshot(
    log_dir: str | Path = LOG_DIR,
    *,
    max_errors: int = 20,
) -> dict[str, Any]:
    errors: list[dict[str, Any]] = []
    for path in list_log_files(log_dir):
        for index, line in enumerate(_tail_text(path, 300), start=1):
            if ERROR_LINE_RE.search(line):
                errors.append(
                    {
                        "source": path.name,
                        "line": index,
                        "message": _redact_log_line(line)[-500:],
                    }
                )
    return {"errors": errors[-max_errors:]}

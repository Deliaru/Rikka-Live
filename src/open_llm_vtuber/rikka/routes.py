"""FastAPI routes for Rikka Live local debug and settings scaffolding."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, TYPE_CHECKING

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from pydantic import ValidationError

from .core import normalize_live_event, validate_rikka_response
from .bilibili import BilibiliLiveManager, normalize_room_ids
from .capture import WindowCaptureService, get_default_capture_service
from .debug_console import (
    CONFIG_PATH,
    LOG_DIR,
    DebugConfigUpdate,
    IndexTTS2DebugConfigUpdate,
    error_snapshot,
    log_snapshot,
    patch_debug_config,
    redact_debug_text,
    snapshot_debug_config,
)
from .flow import RikkaFlowMonitor
from .memory import get_default_memory_store
from .inner_life import get_default_inner_life
from .mood import get_default_mood_state
from .agent_tools import configure_default_tool_runner, get_default_tool_runner
from .persona import resolve_persona_path
from .planner import RikkaStructuredPlanner
from .pointer import GlobalPointerTracker, get_default_pointer_tracker
from .proactive import ProactiveCoordinator, get_default_proactive_coordinator
from .screen_change import get_default_screen_change_detector
from .schemas import MemoryKind, MemoryWrite
from .settings import (
    RikkaSettingsStore,
    RikkaSettingsUpdate,
    get_default_settings_store,
)
from ..config_manager import read_yaml, validate_config
from ..tts.indextts2_emotion import (
    DEFAULT_QUIET_COMPANION_VECTOR,
    clamp_quiet_companion_alpha,
    normalize_emotion_vector,
)

if TYPE_CHECKING:
    from ..service_context import ServiceContext
    from ..websocket_handler import WebSocketHandler


class RikkaEventHistory:
    """Small in-process privacy-safe event history for local debugging."""

    def __init__(self, limit: int = 100):
        self.limit = limit
        self._events: list[dict[str, Any]] = []

    def add(self, event: dict[str, Any]) -> None:
        self._events.append(event)
        self._events = self._events[-self.limit :]

    def add_diagnostic(
        self,
        kind: str,
        status: str,
        reason: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        now_ms = int(time.time() * 1000)
        self.add(
            {
                "id": f"diag-{kind}-{now_ms}",
                "type": f"diagnostic.{kind}",
                "source": "system",
                "text": reason,
                "created_at_ms": now_ms,
                "payload": {
                    "status": status,
                    "reason": reason,
                    **_privacy_safe_metadata(metadata or {}),
                },
                "privacy": {"contains_raw_media": False},
            }
        )

    def list(self) -> list[dict[str, Any]]:
        return self._events


def _privacy_safe_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    safe: dict[str, Any] = {}
    for key, value in metadata.items():
        key_text = str(key)
        if any(secret in key_text.lower() for secret in ("key", "token", "sessdata")):
            continue
        if key_text in {"data", "data_base64", "keyframe_base64", "audio"}:
            continue
        if isinstance(value, dict):
            safe[key_text] = _privacy_safe_metadata(value)
        elif isinstance(value, list):
            safe[key_text] = [
                _privacy_safe_metadata(item) if isinstance(item, dict) else str(item)[:120]
                for item in value[:8]
            ]
        elif isinstance(value, (str, int, float, bool)) or value is None:
            safe[key_text] = value if not isinstance(value, str) else value[:240]
        else:
            safe[key_text] = str(value)[:120]
    return safe


class BilibiliConnectPayload(BaseModel):
    room_id: int | None = None
    room_ids: list[int] = Field(default_factory=list)
    sessdata: str = ""
    use_proxy: bool = False
    proxy_url: str | None = None
    speak: bool = True


class BilibiliTestEventPayload(BaseModel):
    text: str = "六花，B站测试弹幕来了。"
    user_name: str = "B站观众"
    user_id: str = "debug-bilibili"
    room_id: str = "0"


class MultimodalFallbackPayload(BaseModel):
    reason: str = "manual_debug"
    event_id: str | None = None
    keyframe_base64: str | None = None
    mime_type: str = "image/jpeg"


class FrontendActionPayload(BaseModel):
    flow_id: str | None = None
    event_id: str | None = None
    kind: str = "action"
    status: str = "ok"
    detail: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class TtsRuntimePatchPayload(BaseModel):
    indextts2_tts: IndexTTS2DebugConfigUpdate | None = None


def extract_debug_event_envelope(
    payload: dict[str, Any],
) -> tuple[dict[str, Any], Any | None, bool]:
    """Extract a debug LiveEvent envelope without leaking control fields."""
    raw_event = payload.get("event", payload)
    if not isinstance(raw_event, dict):
        raise ValueError("debug speak payload requires an event object")

    event_payload = dict(raw_event)
    event_candidate = event_payload.pop("candidate_response", None)
    candidate_response = payload.get("candidate_response")
    if candidate_response is None:
        candidate_response = event_candidate
    speak = bool(payload.get("speak", True))
    return event_payload, candidate_response, speak


def _provider_status(
    context: "ServiceContext",
    planner_status: dict[str, Any] | None = None,
    settings_store: RikkaSettingsStore | None = None,
) -> dict[str, Any]:
    tts_model = None
    tts_details: dict[str, Any] = {}
    llm_provider = None
    if context and context.character_config:
        tts_config = context.character_config.tts_config
        tts_model = tts_config.tts_model
        selected_tts_config = getattr(tts_config, tts_model, None) if tts_model else None
        if tts_model == "xiaomi_mimo_tts" and selected_tts_config:
            model = selected_tts_config.model
            tts_details = {
                "model": model,
                "voice": selected_tts_config.voice,
                "audio_format": selected_tts_config.audio_format,
                "timeout_seconds": selected_tts_config.timeout_seconds,
                "api_key_configured": bool(selected_tts_config.api_key),
                "voice_clone_ready": bool(
                    selected_tts_config.voice_audio_path
                    or selected_tts_config.voice_audio_base64
                ),
            }
        elif tts_model == "indextts2_tts" and selected_tts_config:
            provider_mode = selected_tts_config.mode
            tts_details = {
                "mode": provider_mode,
                "timeout_seconds": selected_tts_config.timeout_seconds,
            }
            if provider_mode == "cloud":
                tts_details.update(
                    {
                        "base_url": selected_tts_config.base_url,
                        "model": selected_tts_config.model,
                        "api_key_configured": bool(selected_tts_config.api_key),
                        "voice_id_configured": bool(selected_tts_config.voice_id),
                        "voice_refresh_required": not bool(
                            selected_tts_config.voice_id
                        ),
                        "default_tts_style": (
                            selected_tts_config.default_tts_style
                        ),
                        "quiet_companion_emo_alpha": getattr(
                            selected_tts_config,
                            "quiet_companion_emo_alpha",
                            1.0,
                        ),
                        "quiet_companion_emo_vec": getattr(
                            selected_tts_config,
                            "quiet_companion_emo_vec",
                            list(DEFAULT_QUIET_COMPANION_VECTOR),
                        ),
                        "sentence_split_enabled": (
                            selected_tts_config.sentence_split_enabled
                        ),
                        "sentence_split_method": (
                            selected_tts_config.sentence_split_method
                        ),
                        "max_text_tokens_per_segment": (
                            selected_tts_config.max_text_tokens_per_segment
                        ),
                        "sentence_interval_ms": (
                            selected_tts_config.sentence_interval_ms
                        ),
                        "audio_format": "wav",
                    }
                )
            else:
                tts_details.update(
                    {
                        "api_url": selected_tts_config.api_url,
                        "audio_format": selected_tts_config.audio_format,
                        "speaker_reference_ready": bool(
                            selected_tts_config.speaker_audio_path
                            and Path(selected_tts_config.speaker_audio_path).is_file()
                        ),
                        "emotion_reference_ready": bool(
                            selected_tts_config.emo_audio_path
                            and Path(selected_tts_config.emo_audio_path).is_file()
                        ),
                        "emo_alpha": selected_tts_config.emo_alpha,
                        "use_emo_text": selected_tts_config.use_emo_text,
                        "use_random": selected_tts_config.use_random,
                        "sentence_split_enabled": (
                            selected_tts_config.sentence_split_enabled
                        ),
                        "sentence_split_method": (
                            selected_tts_config.sentence_split_method
                        ),
                        "max_text_tokens_per_segment": (
                            selected_tts_config.max_text_tokens_per_segment
                        ),
                        "sentence_interval_ms": (
                            selected_tts_config.sentence_interval_ms
                        ),
                    }
                )
        agent_config = getattr(context.character_config, "agent_config", None)
        agent_settings = getattr(agent_config, "agent_settings", None)
        basic_agent = getattr(agent_settings, "basic_memory_agent", None)
        llm_provider = getattr(basic_agent, "llm_provider", None)

    cloud_tts = {
        "azure_tts",
        "fish_api_tts",
        "minimax_tts",
        "openai_tts",
        "siliconflow_tts",
        "xiaomi_mimo_tts",
    }
    settings = (
        settings_store.snapshot()
        if settings_store is not None
        else get_default_settings_store().snapshot()
    )
    return {
        "tts": {
            "provider": tts_model,
            "mode": "cloud" if tts_model in cloud_tts else "local",
            **tts_details,
        },
        "llm": {
            "provider": llm_provider,
            "mode": "cloud_or_local_by_endpoint",
        },
        "planner": planner_status or {},
        "privacy": {
            "raw_screen_audio_persisted_by_default": False,
            "screen_capture_enabled": settings.screen_capture_enabled,
            "keyframe_upload_enabled": settings.keyframe_upload_enabled,
            "debug_media_logging_enabled": settings.debug_media_logging_enabled,
            "multimodal_provider": settings.multimodal_provider,
            "capture": {
                "enabled": settings.capture.enabled,
                "mode": settings.capture.mode,
                "allow_foreground_debug": settings.capture.allow_foreground_debug,
                "window_title_allowlist": settings.capture.window_title_allowlist,
                "process_name_allowlist": settings.capture.process_name_allowlist,
                "interval_ms": settings.capture.interval_ms,
                "min_change_interval_ms": settings.capture.min_change_interval_ms,
                "jpeg_quality": settings.capture.jpeg_quality,
                "max_width": settings.capture.max_width,
                "attach_to_user_turns": settings.capture.attach_to_user_turns,
            },
            "proactive": {
                "screen_comments_enabled": (
                    settings.proactive.screen_comments_enabled
                ),
                "idle_speech_enabled": settings.proactive.idle_speech_enabled,
                "scheduler_interval_ms": settings.proactive.scheduler_interval_ms,
                "screen_comment_cooldown_ms": (
                    settings.proactive.screen_comment_cooldown_ms
                ),
                "idle_speech_cooldown_ms": (
                    settings.proactive.idle_speech_cooldown_ms
                ),
                "min_user_idle_ms": settings.proactive.min_user_idle_ms,
                "max_screen_comments_per_hour": (
                    settings.proactive.max_screen_comments_per_hour
                ),
                "max_idle_speeches_per_hour": (
                    settings.proactive.max_idle_speeches_per_hour
                ),
                "screen_change_gate_enabled": (
                    settings.proactive.screen_change_gate_enabled
                ),
                "screen_change_threshold": settings.proactive.screen_change_threshold,
            },
            "mood": settings.mood.model_dump(mode="json"),
            "inner_life": settings.inner_life.model_dump(mode="json"),
            "identity": settings.identity.model_dump(mode="json"),
            "audio": {
                "wake_gate_enabled": settings.audio.wake_gate_enabled,
                "wake_phrases": settings.audio.wake_phrases,
                "wake_asr_confusions": settings.audio.wake_asr_confusions,
                "wake_active_window_ms": settings.audio.wake_active_window_ms,
                "mic_conversation_enabled": settings.audio.mic_conversation_enabled,
            },
            "overlay": {
                "asr_hud_visible": settings.overlay.asr_hud_visible,
                "dock_layout_mode": settings.overlay.dock_layout_mode,
                "dock_left_px": settings.overlay.dock_left_px,
                "dock_top_px": settings.overlay.dock_top_px,
                "global_pointer_tracking_enabled": (
                    settings.overlay.global_pointer_tracking_enabled
                ),
                "pointer_tracking_mode": settings.overlay.pointer_tracking_mode,
                "pointer_tracking_intensity": (
                    settings.overlay.pointer_tracking_intensity
                ),
                "pointer_tracking_smoothness": (
                    settings.overlay.pointer_tracking_smoothness
                ),
                "pointer_tracking_deadzone": settings.overlay.pointer_tracking_deadzone,
                "subtitle_visible": settings.overlay.subtitle_visible,
                "subtitle_layout_mode": settings.overlay.subtitle_layout_mode,
                "subtitle_anchor": settings.overlay.subtitle_anchor,
                "subtitle_max_width_px": settings.overlay.subtitle_max_width_px,
                "subtitle_offset_x_px": settings.overlay.subtitle_offset_x_px,
                "subtitle_offset_y_px": settings.overlay.subtitle_offset_y_px,
                "subtitle_left_px": settings.overlay.subtitle_left_px,
                "subtitle_top_px": settings.overlay.subtitle_top_px,
                "subtitle_width_px": settings.overlay.subtitle_width_px,
            },
        },
    }


def _apply_indextts2_runtime_patch(
    context: "ServiceContext",
    update: IndexTTS2DebugConfigUpdate,
) -> dict[str, Any]:
    if context is None or getattr(context, "character_config", None) is None:
        raise RuntimeError("service context is not available")
    tts_config = context.character_config.tts_config
    if tts_config.tts_model != "indextts2_tts":
        raise RuntimeError("current TTS provider is not indextts2_tts")
    selected_tts_config = getattr(tts_config, "indextts2_tts", None)
    tts_engine = getattr(context, "tts_engine", None)
    if selected_tts_config is None or tts_engine is None:
        raise RuntimeError("IndexTTS2 runtime provider is not loaded")

    applied: dict[str, Any] = {}
    for field_name, value in update.model_dump(exclude_none=True).items():
        if isinstance(value, str):
            value = value.strip()
            if not value:
                continue
        if field_name == "emo_alpha":
            value = min(1.0, max(0.0, float(value)))
        if field_name == "quiet_companion_emo_alpha":
            value = clamp_quiet_companion_alpha(value)
        if field_name == "quiet_companion_emo_vec":
            value = normalize_emotion_vector(
                value,
                default=DEFAULT_QUIET_COMPANION_VECTOR,
            )
        if field_name == "max_text_tokens_per_segment":
            value = min(400, max(10, int(value)))
        if field_name == "sentence_interval_ms":
            value = min(3000, max(0, int(value)))
        if field_name == "timeout_seconds":
            value = max(1.0, float(value))
        setattr(selected_tts_config, field_name, value)
        if hasattr(tts_engine, field_name):
            setattr(tts_engine, field_name, value)
        if field_name in {"api_key", "voice_id"}:
            applied[field_name] = "configured"
        else:
            applied[field_name] = value
    return applied


def init_rikka_routes(
    default_context_cache: "ServiceContext",
    ws_handler: "WebSocketHandler | None" = None,
    settings_store: RikkaSettingsStore | None = None,
    capture_service: WindowCaptureService | None = None,
    proactive_coordinator: ProactiveCoordinator | None = None,
    pointer_tracker: GlobalPointerTracker | None = None,
    config_path: str | Path = CONFIG_PATH,
    log_dir: str | Path = LOG_DIR,
) -> APIRouter:
    router = APIRouter(prefix="/rikka", tags=["rikka-live"])
    history = RikkaEventHistory()
    memory = get_default_memory_store()
    settings = settings_store or get_default_settings_store()
    capture = capture_service or get_default_capture_service()
    capture.settings_store = settings
    configure_default_tool_runner(settings_store=settings, capture_service=capture)
    proactive = proactive_coordinator or get_default_proactive_coordinator()
    pointer = pointer_tracker or get_default_pointer_tracker()
    screen_change = (
        ws_handler.screen_change_detector
        if ws_handler and hasattr(ws_handler, "screen_change_detector")
        else get_default_screen_change_detector()
    )
    planner = RikkaStructuredPlanner(default_context_cache, memory)
    flow_monitor = RikkaFlowMonitor()
    flow_monitor.set_event_sink(history.add)
    if ws_handler:
        ws_handler.rikka_flow_monitor = flow_monitor

    async def apply_persisted_debug_config(changed: bool) -> dict[str, Any]:
        if not changed:
            return {
                "ok": True,
                "status": "unchanged",
                "restart_required": False,
                "reason": "no persisted config changes",
            }
        if default_context_cache is None or not callable(
            getattr(default_context_cache, "load_from_config", None)
        ):
            return {
                "ok": False,
                "status": "unavailable",
                "restart_required": True,
                "reason": "service context is not available",
            }
        try:
            next_config = validate_config(read_yaml(str(config_path)))
            await default_context_cache.load_from_config(next_config)
            planner.clear_llm_cache()
            if ws_handler and hasattr(ws_handler, "rikka_planner"):
                for client_uid, session_context in list(
                    getattr(ws_handler, "client_contexts", {}).items()
                ):
                    await session_context.load_cache(
                        config=default_context_cache.config.model_copy(deep=True),
                        system_config=default_context_cache.system_config.model_copy(
                            deep=True
                        ),
                        character_config=(
                            default_context_cache.character_config.model_copy(
                                deep=True
                            )
                        ),
                        live2d_model=default_context_cache.live2d_model,
                        asr_engine=default_context_cache.asr_engine,
                        tts_engine=default_context_cache.tts_engine,
                        vad_engine=default_context_cache.vad_engine,
                        agent_engine=default_context_cache.agent_engine,
                        translate_engine=default_context_cache.translate_engine,
                        mcp_server_registery=(
                            default_context_cache.mcp_server_registery
                        ),
                        tool_adapter=default_context_cache.tool_adapter,
                        send_text=getattr(session_context, "send_text", None),
                        client_uid=client_uid,
                    )
                ws_handler.rikka_planner.clear_llm_cache()
                ws_handler.rikka_planner.set_context(default_context_cache)
            return {
                "ok": True,
                "status": "applied",
                "restart_required": False,
                "reason": "persisted config was applied to the current runtime",
            }
        except Exception as exc:
            return {
                "ok": False,
                "status": "failed",
                "restart_required": True,
                "reason": redact_debug_text(str(exc)),
            }

    async def process_live_event(
        payload: dict[str, Any],
        candidate_response: Any | None = None,
    ) -> dict[str, Any]:
        event = normalize_live_event(payload)
        event_data = event.model_dump(mode="json")
        flow_id = event_data["id"]
        flow_monitor.start(flow_id, event_data)
        flow_monitor.record(flow_id, "normalize", "ok", detail="LiveEvent validated")

        flow_monitor.record(flow_id, "planner", "running", detail="planning response")
        result = await planner.plan(
            event,
            candidate_response=candidate_response,
        )
        planner_status = planner.status()
        planner_error = redact_debug_text(str(planner_status.get("last_error") or ""))
        planner_stage_ok = result.ok and not planner_error
        flow_monitor.record(
            flow_id,
            "planner",
            "ok" if planner_stage_ok else "error",
            detail=planner_status.get("mode", "") if planner_stage_ok else planner_error,
            metadata={
                "mode": planner_status.get("mode"),
                "latency_ms": planner_status.get("last_latency_ms"),
                "model": planner_status.get("model"),
                "retry_after_ms": planner_status.get("retry_after_ms"),
                "error_kind": planner_status.get("last_error_kind"),
                "error": planner_error,
            },
        )
        flow_monitor.record(
            flow_id,
            "validate",
            "ok" if result.ok else "error",
            detail="response validated" if result.ok else "; ".join(result.errors),
            metadata={
                "reason_code": result.response.reason_code,
                "emotion": result.response.emotion,
                "motion": result.response.motion,
                "gaze": result.response.gaze,
                "subtitle_text": result.response.subtitle_text,
            },
        )
        applied_memory = memory.apply_writes(result.response.memory_writes)
        flow_monitor.record(
            flow_id,
            "memory",
            "ok",
            detail=f"{len(applied_memory)} memory write(s)",
        )
        providers = _provider_status(default_context_cache, planner_status, settings)
        return {
            "event": event_data,
            "validation": {
                "ok": result.ok,
                "errors": result.errors,
            },
            "response": result.response.model_dump(mode="json"),
            "memory_applied": applied_memory,
            "providers": providers,
            "planner": providers["planner"],
            "flow": flow_monitor.summary(flow_id),
        }

    async def emit_live2d_result(result: dict[str, Any], speak: bool) -> dict[str, Any]:
        flow_id = (result.get("flow") or {}).get("id") or (result.get("event") or {}).get("id")
        flow_monitor.record(
            flow_id,
            "delivery",
            "running",
            detail="broadcasting to Live2D",
            metadata={"speak": speak},
        )
        if ws_handler:
            delivery = await ws_handler.emit_preplanned_rikka_result(
                result,
                speak=speak,
            )
        else:
            delivery = {
                "ok": False,
                "delivered_clients": 0,
                "failed_clients": [],
                "reason": "Live2D bridge is not available",
            }
        flow_monitor.record(
            flow_id,
            "delivery",
            "ok" if delivery.get("ok") else "error",
            detail=delivery.get("reason") or f"{delivery.get('delivered_clients', 0)} client(s)",
            metadata=delivery,
        )
        return delivery

    bilibili_manager = BilibiliLiveManager(
        process_live_event,
        result_emitter=emit_live2d_result,
    )

    def configured_bilibili_defaults() -> tuple[list[int], str]:
        config = getattr(default_context_cache, "config", None)
        live_config = getattr(config, "live_config", None)
        bilibili_config = getattr(live_config, "bilibili_live", None)
        if not bilibili_config:
            return [], ""
        return list(bilibili_config.room_ids), bilibili_config.sessdata

    def live2d_status() -> dict[str, Any]:
        if not ws_handler:
            return {
                "connected_clients": 0,
                "client_uids": [],
                "live2d_bridge_ready": False,
            }
        return {
            **ws_handler.rikka_client_status(),
            "live2d_bridge_ready": True,
        }

    def debug_flow_diagnostics() -> dict[str, Any]:
        bilibili_status = bilibili_manager.status()
        live2d = live2d_status()
        planner_status = planner.status()
        providers = _provider_status(default_context_cache, planner_status, settings)
        live2d_count = int(live2d.get("connected_clients") or 0)
        if bilibili_status.get("state") == "failed" or bilibili_status.get("last_error"):
            blocker = "bilibili_failed"
            detail = bilibili_status.get("last_error") or "Bilibili connector failed"
        elif bilibili_status.get("state") in {"idle", "stopped"}:
            blocker = "bilibili_idle"
            detail = "Bilibili connector is not running"
        elif bilibili_status.get("state") == "starting":
            blocker = "bilibili_starting"
            detail = bilibili_status.get("state_detail") or "Bilibili is starting"
        elif live2d_count <= 0:
            blocker = "live2d_offline"
            detail = "No Live2D main client is connected"
        elif int(bilibili_status.get("received_real_events") or 0) <= 0:
            blocker = "waiting_real_danmaku"
            detail = bilibili_status.get("state_detail") or "Waiting for real danmaku"
        else:
            blocker = "ready"
            detail = "Real danmaku intake and Live2D delivery are observable"
        return {
            "bilibili": bilibili_status,
            "live2d": live2d,
            "planner": planner_status,
            "tts": providers.get("tts", {}),
            "privacy": providers.get("privacy", {}),
            "blocker": blocker,
            "detail": detail,
        }

    @router.get("/health")
    async def health():
        persona_path = None
        try:
            persona_path = str(resolve_persona_path())
        except FileNotFoundError:
            persona_path = None
        providers = _provider_status(default_context_cache, planner.status(), settings)
        providers["bilibili"] = bilibili_manager.status()
        return {
            "ok": True,
            "persona_path": persona_path,
            "providers": providers,
        }

    @router.get("/events")
    async def events():
        return {"events": history.list()}

    @router.get("/debug/config")
    async def debug_config_get():
        return {"config": snapshot_debug_config(config_path)}

    @router.patch("/debug/config")
    async def debug_config_patch(payload: DebugConfigUpdate):
        config = patch_debug_config(payload, config_path)
        runtime_apply = await apply_persisted_debug_config(
            bool(config.get("restart_required"))
        )
        config["runtime_apply"] = runtime_apply
        if runtime_apply.get("ok") and runtime_apply.get("status") == "applied":
            config["restart_required"] = False
        return {
            "config": config,
            "providers": _provider_status(default_context_cache, planner.status(), settings),
        }

    @router.patch("/debug/runtime-tts")
    async def debug_runtime_tts_patch(payload: TtsRuntimePatchPayload):
        if payload.indextts2_tts is None:
            raise HTTPException(status_code=422, detail="indextts2_tts patch required")
        try:
            applied = _apply_indextts2_runtime_patch(
                default_context_cache,
                payload.indextts2_tts,
            )
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return {
            "applied": applied,
            "restart_required": False,
            "providers": _provider_status(default_context_cache, planner.status(), settings),
        }

    @router.get("/debug/logs")
    async def debug_logs(max_files: int = 8, max_lines: int = 80):
        return log_snapshot(log_dir, max_files=max_files, max_lines=max_lines)

    @router.get("/debug/errors")
    async def debug_errors():
        snapshot = error_snapshot(log_dir)
        provider_errors: list[dict[str, str]] = []
        planner_status = planner.status()
        if planner_status.get("last_error"):
            provider_errors.append(
                {
                    "source": "planner",
                    "message": redact_debug_text(planner_status["last_error"]),
                }
            )
        bilibili_status = bilibili_manager.status()
        if bilibili_status.get("last_error"):
            provider_errors.append(
                {
                    "source": "bilibili",
                    "message": redact_debug_text(bilibili_status["last_error"]),
                }
            )
        return {**snapshot, "provider_errors": provider_errors}

    @router.get("/debug/flow")
    async def debug_flow():
        return {
            **flow_monitor.snapshot(),
            "diagnostics": debug_flow_diagnostics(),
        }

    @router.post("/debug/frontend-action")
    async def frontend_action(payload: FrontendActionPayload):
        action = flow_monitor.record_frontend_action(payload.model_dump())
        history.add_diagnostic(
            "frontend_action",
            action.get("status", "ok"),
            f"{action.get('kind')}: {action.get('detail') or action.get('status')}",
            {
                "flow_id": action.get("flow_id"),
                "kind": action.get("kind"),
                "metadata": action.get("metadata", {}),
            },
        )
        return {"action": action}

    @router.get("/settings")
    async def settings_get():
        return {"settings": settings.dump()}

    @router.patch("/settings")
    async def settings_patch(payload: RikkaSettingsUpdate):
        updated = settings.update(payload)
        return {
            "settings": updated.model_dump(mode="json"),
            "providers": _provider_status(
                default_context_cache,
                planner.status(),
                settings,
            ),
        }

    @router.post("/settings/reset")
    async def settings_reset():
        updated = settings.reset()
        return {"settings": updated.model_dump(mode="json")}

    @router.get("/capture/status")
    async def capture_status():
        return {"capture": capture.status()}

    @router.get("/capture/windows")
    async def capture_windows():
        return capture.list_windows()

    @router.post("/capture/keyframe")
    async def capture_keyframe():
        result = capture.capture_keyframe(force=True)
        history.add_diagnostic(
            "capture",
            result.get("status", "unknown"),
            result.get("reason", ""),
            result,
        )
        return {"capture": result}

    @router.get("/proactive/status")
    async def proactive_status():
        live2d = live2d_status()
        capture_state = capture.status()
        live2d_connected = (
            ws_handler._live2d_client_connected()
            if ws_handler and hasattr(ws_handler, "_live2d_client_connected")
            else int(live2d.get("connected_clients") or 0) > 0
        )
        conversation_active = (
            ws_handler._conversation_active_for_proactive()
            if ws_handler and hasattr(ws_handler, "_conversation_active_for_proactive")
            else False
        )
        return {
            "proactive": proactive.status(settings.snapshot().proactive),
            "screen_comment_decision": proactive.decision(
                settings.snapshot().proactive,
                "screen_comment",
                live2d_connected=live2d_connected,
                capture_ready=bool(capture_state.get("latest_frame")),
                conversation_active=conversation_active,
            ),
            "idle_speech_decision": proactive.decision(
                settings.snapshot().proactive,
                "idle_speech",
                live2d_connected=live2d_connected,
                capture_ready=bool(capture_state.get("latest_frame")),
                conversation_active=conversation_active,
            ),
        }

    @router.get("/liveliness/status")
    async def liveliness_status():
        current = settings.snapshot()
        mood_status = get_default_mood_state().snapshot(current.mood)
        inner_life_status = get_default_inner_life().snapshot(current.inner_life)
        return {
            "mood": {
                "enabled": current.mood.enabled,
                "tts_adjustment_enabled": current.mood.tts_adjustment_enabled,
                **mood_status,
            },
            "inner_life": {
                "enabled": current.inner_life.enabled,
                **inner_life_status,
            },
            "screen_change": {
                "gate_enabled": current.proactive.screen_change_gate_enabled,
                "threshold": current.proactive.screen_change_threshold,
                **screen_change.status(),
            },
        }

    @router.post("/liveliness/reset")
    async def liveliness_reset():
        get_default_mood_state().reset()
        get_default_inner_life().reset()
        screen_change.reset()
        return await liveliness_status()

    @router.get("/agent/status")
    async def agent_status():
        current = settings.snapshot()
        agent_tools = get_default_tool_runner()
        status = agent_tools.status()
        return {
            "enabled": current.agent.tools_enabled,
            "tools": status["tools"],
            "filler_enabled": current.agent.filler_enabled,
            "result_pre_silence_ms": current.agent.result_pre_silence_ms,
            "max_tool_rounds": current.agent.max_tool_rounds,
            "web_search_timeout_seconds": current.agent.web_search_timeout_seconds,
            "mcp": status["mcp"],
            "last_tool": status["last_tool"],
            "last_error": status["last_error"],
        }

    @router.get("/overlay/status")
    async def overlay_status():
        overlay_settings = settings.snapshot().overlay
        return {
            "settings": overlay_settings.model_dump(mode="json"),
            "live2d": live2d_status(),
            "capture": capture.status(),
            "pointer": pointer.status(overlay_settings),
            "privacy": _provider_status(
                default_context_cache,
                planner.status(),
                settings,
            )["privacy"],
        }

    @router.get("/overlay/pointer")
    async def overlay_pointer_status():
        return {"pointer": pointer.status(settings.snapshot().overlay)}

    @router.post("/multimodal/keyframe")
    async def multimodal_keyframe(payload: MultimodalFallbackPayload):
        current = settings.snapshot()
        if not current.keyframe_upload_enabled:
            raise HTTPException(
                status_code=403,
                detail="keyframe upload is disabled; enable it in /rikka/settings first",
            )
        frame = None
        if payload.keyframe_base64:
            frame = capture.ingest_keyframe(
                payload.keyframe_base64,
                reason=payload.reason,
                event_id=payload.event_id,
                mime_type=payload.mime_type,
            )
        latest_frame = frame or capture.latest_frame()
        capture_state = capture.status()
        provider_configured = current.multimodal_provider not in {
            "",
            "none",
            "not_configured",
        }
        no_frame_reason = None
        if latest_frame is None:
            if not (current.screen_capture_enabled or current.capture.enabled):
                no_frame_reason = "capture_disabled"
            elif not current.capture.attach_to_user_turns:
                no_frame_reason = "attach_to_user_turns_disabled"
            else:
                capture_status = capture_state.get("status")
                no_frame_reason = (
                    capture_status
                    if capture_status
                    not in {None, "", "idle", "cooldown", "captured"}
                    else "no_latest_frame"
                )
        result = {
            "status": "queued_stub",
            "provider": current.multimodal_provider,
            "provider_configured": provider_configured,
            "reason": payload.reason,
            "event_id": payload.event_id,
            "keyframe_supplied": bool(payload.keyframe_base64),
            "latest_frame": latest_frame.to_public_dict(include_payload=False)
            if latest_frame
            else None,
            "no_frame_reason": no_frame_reason,
            "capture_status": capture_state.get("status"),
            "capture_reason": capture_state.get("reason"),
            "attach_to_user_turns": current.capture.attach_to_user_turns,
            "normal_user_turn_is_e2e_test": True,
            "raw_media_persisted": False,
        }
        history.add_diagnostic(
            "multimodal_keyframe",
            result["status"],
            payload.reason,
            result,
        )
        return result

    @router.post("/debug/event")
    async def debug_event(payload: dict[str, Any]):
        try:
            event_payload, candidate_response, _ = extract_debug_event_envelope(payload)
            return await process_live_event(event_payload, candidate_response)
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail=exc.errors()) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @router.get("/debug/clients")
    async def debug_clients():
        return live2d_status()

    @router.post("/debug/speak")
    async def debug_speak(payload: dict[str, Any]):
        try:
            event_payload, candidate_response, speak = extract_debug_event_envelope(
                payload
            )
            result = await process_live_event(event_payload, candidate_response)
            delivery = await emit_live2d_result(result, speak)
            return {**result, "delivery": delivery}
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail=exc.errors()) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @router.get("/bilibili/status")
    async def bilibili_status():
        configured_rooms, _ = configured_bilibili_defaults()
        return {
            "status": bilibili_manager.status(),
            "configured_room_ids": configured_rooms,
        }

    @router.post("/bilibili/connect")
    async def bilibili_connect(payload: BilibiliConnectPayload):
        configured_rooms, configured_sessdata = configured_bilibili_defaults()
        requested_room_ids = [
            *(payload.room_ids or []),
            *([payload.room_id] if payload.room_id else []),
        ]
        room_ids = normalize_room_ids(requested_room_ids) or normalize_room_ids(
            configured_rooms
        )
        sessdata = payload.sessdata or configured_sessdata
        try:
            status = await bilibili_manager.connect(
                room_ids=room_ids,
                sessdata=sessdata,
                use_proxy=payload.use_proxy,
                proxy_url=payload.proxy_url,
                speak=payload.speak,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except RuntimeError as exc:
            status_code = 409 if "already running" in str(exc) else 503
            raise HTTPException(status_code=status_code, detail=str(exc)) from exc
        return {"status": status}

    @router.post("/bilibili/disconnect")
    async def bilibili_disconnect():
        return {"status": await bilibili_manager.disconnect()}

    @router.post("/bilibili/test-event")
    async def bilibili_test_event(payload: BilibiliTestEventPayload):
        try:
            return await bilibili_manager.publish_test_event(
                text=payload.text,
                user_name=payload.user_name,
                user_id=payload.user_id,
                room_id=payload.room_id,
            )
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail=exc.errors()) from exc

    @router.post("/response/validate")
    async def response_validate(payload: dict[str, Any]):
        raw = payload.get("response", payload)
        result = validate_rikka_response(raw)
        return {
            "validation": {
                "ok": result.ok,
                "errors": result.errors,
            },
            "response": result.response.model_dump(mode="json"),
        }

    @router.get("/memory")
    async def memory_dump():
        return {"memory": memory.dump(), "summary": memory.summary()}

    @router.post("/memory")
    async def memory_upsert(payload: dict[str, Any]):
        try:
            item = memory.upsert(MemoryWrite.model_validate(payload))
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail=exc.errors()) from exc
        return {"item": item, "memory": memory.dump()}

    @router.delete("/memory/{kind}/{key}")
    async def memory_delete(kind: MemoryKind, key: str):
        return {"deleted": memory.delete(kind, key), "memory": memory.dump()}

    @router.post("/memory/reset")
    async def memory_reset():
        memory.reset()
        return {"memory": memory.dump()}

    @router.get("/live2d/presets")
    async def live2d_presets_get():
        context = default_context_cache
        if not context or not context.live2d_model:
            raise HTTPException(status_code=503, detail="Live2D model not loaded")
        model_info = context.live2d_model.model_info
        model_name = context.live2d_model.live2d_model_name
        return {
            "model_name": model_name,
            "expressionPresets": model_info.get("expressionPresets", {}),
            "gestureMap": model_info.get("gestureMap", {}),
            "idleMicro": model_info.get("idleMicro", {}),
            "speakingSmile": model_info.get("speakingSmile", {}),
        }

    @router.patch("/live2d/presets")
    async def live2d_presets_patch(payload: dict[str, Any]):
        context = default_context_cache
        if not context or not context.live2d_model:
            raise HTTPException(status_code=503, detail="Live2D model not loaded")
        model_name = context.live2d_model.live2d_model_name
        model_dict_path = Path(context.live2d_model.model_dict_path)
        if not model_dict_path.is_file():
            raise HTTPException(status_code=503, detail="model_dict.json not found")
        try:
            model_dict = json.loads(model_dict_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Failed to read model_dict.json: {exc}") from exc
        model_entry = next((m for m in model_dict if m.get("name") == model_name), None)
        if not model_entry:
            raise HTTPException(status_code=404, detail=f"Model entry '{model_name}' not found in model_dict.json")
        allowed_keys = {"expressionPresets", "gestureMap", "idleMicro", "speakingSmile"}
        forbidden_params = {"arm", "hand", "wrist", "Param60", "Param63", "Param68", "Param73"}
        for key, value in payload.items():
            if key not in allowed_keys:
                raise HTTPException(status_code=422, detail=f"Unknown config key: {key}")
            if key == "expressionPresets" and isinstance(value, dict):
                for preset_name, preset in value.items():
                    if not isinstance(preset, dict):
                        continue
                    params = preset.get("parameters", {})
                    if not isinstance(params, dict):
                        continue
                    for param_id in params.keys():
                        if any(f in str(param_id).lower() for f in ["arm", "hand", "wrist"]):
                            raise HTTPException(status_code=422, detail=f"Forbidden param in {preset_name}: {param_id}")
                        if param_id in forbidden_params:
                            raise HTTPException(status_code=422, detail=f"Forbidden param in {preset_name}: {param_id}")
                    for param_id, val in params.items():
                        if not isinstance(val, (int, float)):
                            raise HTTPException(status_code=422, detail=f"Non-numeric value in {preset_name}.{param_id}")
        for key, value in payload.items():
            model_entry[key] = value
        try:
            model_dict_path.write_text(json.dumps(model_dict, indent=4, ensure_ascii=False), encoding="utf-8")
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Failed to write model_dict.json: {exc}") from exc
        context.live2d_model.set_model(model_name)
        if ws_handler:
            await ws_handler.broadcast_model_conf_update(context.live2d_model.model_info)
        return {
            "ok": True,
            "model_name": model_name,
            "updated_keys": list(payload.keys()),
        }

    return router

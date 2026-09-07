from dataclasses import dataclass
import time
import uuid
from typing import Any, Dict, List, Optional, Callable, TypedDict
from fastapi import WebSocket, WebSocketDisconnect
import asyncio
import json
from enum import Enum
import numpy as np
from loguru import logger

from .service_context import ServiceContext
from .chat_group import (
    ChatGroupManager,
    handle_group_operation,
    handle_client_disconnect,
    broadcast_to_group,
)
from .message_handler import message_handler
from .utils.stream_audio import prepare_audio_payload
from .chat_history_manager import (
    create_new_history,
    get_history,
    delete_history,
    get_history_list,
)
from .config_manager.utils import scan_config_alts_directory, scan_bg_directory
from .conversations.conversation_handler import (
    handle_conversation_trigger,
    handle_group_interrupt,
    handle_individual_interrupt,
)
from .agent.output_types import Actions, DisplayText
from .conversations.tts_manager import TTSTaskManager
from .rikka.core import normalize_live_event
from .rikka.capture import get_default_capture_service
from .rikka.memory import get_default_memory_store
from .rikka.inner_life import get_default_inner_life
from .rikka.mood import apply_rikka_mood_effects
from .rikka.planner import RikkaStructuredPlanner
from .rikka.presentation import rikka_response_to_actions
from .rikka.proactive import ProactiveCoordinator, get_default_proactive_coordinator
from .rikka.schemas import RikkaResponse
from .rikka.screen_change import get_default_screen_change_detector
from .rikka.settings import (
    RikkaSettingsStore,
    get_default_settings_store,
    live2d_expressions_enabled,
)
from .rikka.wake_gate import get_default_wake_gate


class MessageType(Enum):
    """Enum for WebSocket message types"""

    GROUP = ["add-client-to-group", "remove-client-from-group"]
    HISTORY = [
        "fetch-history-list",
        "fetch-and-set-history",
        "create-new-history",
        "delete-history",
    ]
    CONVERSATION = ["mic-audio-end", "text-input", "ai-speak-signal"]
    CONFIG = ["fetch-configs", "switch-config"]
    CONTROL = ["interrupt-signal", "audio-play-start"]
    DATA = ["mic-audio-data"]


class WSMessage(TypedDict, total=False):
    """Type definition for WebSocket messages"""

    type: str
    action: Optional[str]
    text: Optional[str]
    audio: Optional[List[float]]
    sample_rate: Optional[int]
    sampleRate: Optional[int]
    images: Optional[List[str]]
    history_uid: Optional[str]
    file: Optional[str]
    display_text: Optional[dict]
    client_kind: Optional[str]
    always_on_enabled: Optional[bool]
    mic_permission: Optional[str]
    listening: Optional[bool]
    explicit_owner: Optional[bool]


@dataclass
class MicClientState:
    client_uid: str
    client_kind: str = "unknown"
    always_on_enabled: bool = False
    mic_permission: str = "unknown"
    listening: bool = False
    explicit_owner: bool = False
    last_reason: str = "registered"
    updated_at_ms: int = 0

    def is_eligible(self, asr_enabled: bool) -> bool:
        if not asr_enabled:
            return False
        if not self.always_on_enabled:
            return False
        if self.mic_permission != "granted":
            return False
        return self.listening

    def to_dict(self) -> dict[str, Any]:
        return {
            "client_uid": self.client_uid,
            "client_kind": self.client_kind,
            "always_on_enabled": self.always_on_enabled,
            "mic_permission": self.mic_permission,
            "listening": self.listening,
            "explicit_owner": self.explicit_owner,
            "reason": self.last_reason,
            "updated_at_ms": self.updated_at_ms,
        }


def extract_rikka_live_event_message(
    data: dict,
) -> tuple[dict[str, Any], Any | None, bool]:
    """Extract the normalized event payload from a Rikka WebSocket envelope."""
    raw_event = data.get("event")
    if not isinstance(raw_event, dict):
        raise ValueError("rikka-live-event message requires an event object")

    event_payload = dict(raw_event)
    event_candidate = event_payload.pop("candidate_response", None)
    candidate_response = data.get("candidate_response")
    if candidate_response is None:
        candidate_response = event_candidate
    speak = bool(data.get("speak", False))
    return event_payload, candidate_response, speak


def _positive_int(value: Any) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def resample_audio_chunk(
    audio: np.ndarray,
    source_sample_rate: int | None,
    target_sample_rate: int,
) -> np.ndarray:
    """Convert browser microphone chunks to the ASR engine sample rate."""
    if audio.size == 0:
        return audio.astype(np.float32, copy=False)
    if not source_sample_rate or source_sample_rate == target_sample_rate:
        return audio.astype(np.float32, copy=False)
    if target_sample_rate <= 0:
        return audio.astype(np.float32, copy=False)

    target_length = max(
        1,
        int(round(audio.size * float(target_sample_rate) / float(source_sample_rate))),
    )
    if target_length == audio.size:
        return audio.astype(np.float32, copy=False)

    source_positions = np.linspace(0.0, 1.0, num=audio.size, endpoint=False)
    target_positions = np.linspace(0.0, 1.0, num=target_length, endpoint=False)
    return np.interp(target_positions, source_positions, audio).astype(np.float32)


class WebSocketHandler:
    """Handles WebSocket connections and message routing"""

    def __init__(
        self,
        default_context_cache: ServiceContext,
        settings_store: RikkaSettingsStore | None = None,
        capture_service: Any | None = None,
        proactive_coordinator: ProactiveCoordinator | None = None,
    ):
        """Initialize the WebSocket handler with default context"""
        self.client_connections: Dict[str, WebSocket] = {}
        self.client_contexts: Dict[str, ServiceContext] = {}
        self.chat_group_manager = ChatGroupManager()
        self.current_conversation_tasks: Dict[str, Optional[asyncio.Task]] = {}
        self.default_context_cache = default_context_cache
        self.rikka_flow_monitor = None
        self.received_data_buffers: Dict[str, np.ndarray] = {}
        self.rikka_memory = get_default_memory_store()
        self.rikka_settings = settings_store or get_default_settings_store()
        self.capture_service = capture_service or get_default_capture_service()
        self.screen_change_detector = get_default_screen_change_detector()
        self.proactive_coordinator = (
            proactive_coordinator or get_default_proactive_coordinator()
        )
        self._proactive_task: asyncio.Task | None = None
        self.mic_clients: Dict[str, MicClientState] = {}
        self.client_kinds: Dict[str, str] = {}
        self.active_mic_owner_uid: str | None = None
        self.active_mic_owner_since_ms: int | None = None
        self.playback_guard_by_client: Dict[str, bool] = {}
        self.streaming_asr_sessions: Dict[str, Any] = {}
        self.rikka_planner = RikkaStructuredPlanner(
            default_context_cache,
            self.rikka_memory,
        )

        # Message handlers mapping
        self._message_handlers = self._init_message_handlers()

    def _init_message_handlers(self) -> Dict[str, Callable]:
        """Initialize message type to handler mapping"""
        return {
            "add-client-to-group": self._handle_group_operation,
            "remove-client-from-group": self._handle_group_operation,
            "request-group-info": self._handle_group_info,
            "fetch-history-list": self._handle_history_list_request,
            "fetch-and-set-history": self._handle_fetch_history,
            "create-new-history": self._handle_create_history,
            "delete-history": self._handle_delete_history,
            "interrupt-signal": self._handle_interrupt,
            "mic-audio-data": self._handle_audio_data,
            "mic-audio-end": self._handle_conversation_trigger,
            "raw-audio-data": self._handle_raw_audio_data,
            "text-input": self._handle_conversation_trigger,
            "ai-speak-signal": self._handle_conversation_trigger,
            "fetch-configs": self._handle_fetch_configs,
            "switch-config": self._handle_config_switch,
            "fetch-backgrounds": self._handle_fetch_backgrounds,
            "audio-play-start": self._handle_audio_play_start,
            "request-init-config": self._handle_init_config_request,
            "heartbeat": self._handle_heartbeat,
            "rikka-live-event": self._handle_rikka_live_event,
            "client-capabilities": self._handle_client_capabilities,
            "mic-owner-request": self._handle_client_capabilities,
            "mic-owner-release": self._handle_mic_owner_release,
            "frontend-playback-state": self._handle_frontend_playback_state,
            "live2d-param-preview": self._handle_live2d_param_preview,
            "live2d-param-preview-result": self._handle_live2d_param_preview_result,
            "live2d-gesture-preview": self._handle_live2d_gesture_preview,
            "live2d-gesture-preview-result": self._handle_live2d_gesture_preview_result,
        }

    async def handle_new_connection(
        self, websocket: WebSocket, client_uid: str
    ) -> None:
        """
        Handle new WebSocket connection setup

        Args:
            websocket: The WebSocket connection
            client_uid: Unique identifier for the client

        Raises:
            Exception: If initialization fails
        """
        try:
            session_service_context = await self._init_service_context(
                websocket.send_text, client_uid
            )

            await self._store_client_data(
                websocket, client_uid, session_service_context
            )

            await self._send_initial_messages(
                websocket, client_uid, session_service_context
            )

            logger.info(f"Connection established for client {client_uid}")
            self._ensure_proactive_loop()

        except Exception as e:
            logger.error(
                f"Failed to initialize connection for client {client_uid}: {e}"
            )
            await self._cleanup_failed_connection(client_uid)
            raise

    async def _store_client_data(
        self,
        websocket: WebSocket,
        client_uid: str,
        session_service_context: ServiceContext,
    ):
        """Store client data and initialize group status"""
        self.client_connections[client_uid] = websocket
        self.client_contexts[client_uid] = session_service_context
        self.received_data_buffers[client_uid] = np.array([])

        self.chat_group_manager.client_group_map[client_uid] = ""
        await self.send_group_update(websocket, client_uid)

    async def _send_initial_messages(
        self,
        websocket: WebSocket,
        client_uid: str,
        session_service_context: ServiceContext,
    ):
        """Send initial connection messages to the client"""
        await websocket.send_text(
            json.dumps({"type": "full-text", "text": "Connection established"})
        )

        await websocket.send_text(
            json.dumps(
                {
                    "type": "set-model-and-conf",
                    "model_info": session_service_context.live2d_model.model_info,
                    "conf_name": session_service_context.character_config.conf_name,
                    "conf_uid": session_service_context.character_config.conf_uid,
                    "client_uid": client_uid,
                }
            )
        )

        # Send initial group status
        await self.send_group_update(websocket, client_uid)

        # Start microphone only when ASR is enabled for this session.
        if not getattr(session_service_context.asr_engine, "is_disabled", False):
            await websocket.send_text(
                json.dumps({"type": "control", "text": "start-mic"})
            )
        else:
            await websocket.send_text(
                json.dumps({"type": "control", "text": "mic-disabled"})
            )
        await websocket.send_text(json.dumps(self._mic_owner_payload("connected")))

    async def _init_service_context(
        self, send_text: Callable, client_uid: str
    ) -> ServiceContext:
        """Initialize service context for a new session by cloning the default context"""
        session_service_context = ServiceContext()
        await session_service_context.load_cache(
            config=self.default_context_cache.config.model_copy(deep=True),
            system_config=self.default_context_cache.system_config.model_copy(
                deep=True
            ),
            character_config=self.default_context_cache.character_config.model_copy(
                deep=True
            ),
            live2d_model=self.default_context_cache.live2d_model,
            asr_engine=self.default_context_cache.asr_engine,
            tts_engine=self.default_context_cache.tts_engine,
            vad_engine=self.default_context_cache.vad_engine,
            agent_engine=self.default_context_cache.agent_engine,
            translate_engine=self.default_context_cache.translate_engine,
            mcp_server_registery=self.default_context_cache.mcp_server_registery,
            tool_adapter=self.default_context_cache.tool_adapter,
            send_text=send_text,
            client_uid=client_uid,
        )
        return session_service_context

    async def handle_websocket_communication(
        self, websocket: WebSocket, client_uid: str
    ) -> None:
        """
        Handle ongoing WebSocket communication

        Args:
            websocket: The WebSocket connection
            client_uid: Unique identifier for the client
        """
        try:
            while True:
                try:
                    data = await websocket.receive_json()
                    message_handler.handle_message(client_uid, data)
                    await self._route_message(websocket, client_uid, data)
                except WebSocketDisconnect:
                    raise
                except json.JSONDecodeError:
                    logger.error("Invalid JSON received")
                    continue
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    await websocket.send_text(
                        json.dumps({"type": "error", "message": str(e)})
                    )
                    continue

        except WebSocketDisconnect:
            logger.info(f"Client {client_uid} disconnected")
            raise
        except Exception as e:
            logger.error(f"Fatal error in WebSocket communication: {e}")
            raise

    async def _route_message(
        self, websocket: WebSocket, client_uid: str, data: WSMessage
    ) -> None:
        """
        Route incoming message to appropriate handler

        Args:
            websocket: The WebSocket connection
            client_uid: Client identifier
            data: Message data
        """
        msg_type = data.get("type")
        if not msg_type:
            logger.warning("Message received without type")
            return

        handler = self._message_handlers.get(msg_type)
        if handler:
            await handler(websocket, client_uid, data)
        else:
            if msg_type != "frontend-playback-complete":
                logger.warning(f"Unknown message type: {msg_type}")

    async def _handle_group_operation(
        self, websocket: WebSocket, client_uid: str, data: dict
    ) -> None:
        """Handle group-related operations"""
        operation = data.get("type")
        target_uid = data.get(
            "invitee_uid" if operation == "add-client-to-group" else "target_uid"
        )

        await handle_group_operation(
            operation=operation,
            client_uid=client_uid,
            target_uid=target_uid,
            chat_group_manager=self.chat_group_manager,
            client_connections=self.client_connections,
            send_group_update=self.send_group_update,
        )

    async def handle_disconnect(self, client_uid: str) -> None:
        """Handle client disconnection"""
        await self._release_mic_client(client_uid, "disconnect")
        group = self.chat_group_manager.get_client_group(client_uid)
        if group:
            await handle_group_interrupt(
                group_id=group.group_id,
                heard_response="",
                current_conversation_tasks=self.current_conversation_tasks,
                chat_group_manager=self.chat_group_manager,
                client_contexts=self.client_contexts,
                broadcast_to_group=self.broadcast_to_group,
            )

        await handle_client_disconnect(
            client_uid=client_uid,
            chat_group_manager=self.chat_group_manager,
            client_connections=self.client_connections,
            send_group_update=self.send_group_update,
        )

        # Clean up other client data
        self.client_connections.pop(client_uid, None)
        self.client_contexts.pop(client_uid, None)
        self.client_kinds.pop(client_uid, None)
        self.received_data_buffers.pop(client_uid, None)
        if client_uid in self.current_conversation_tasks:
            task = self.current_conversation_tasks[client_uid]
            if task and not task.done():
                task.cancel()
            self.current_conversation_tasks.pop(client_uid, None)

        # Call context close to clean up resources (e.g., MCPClient)
        context = self.client_contexts.get(client_uid)
        if context:
            await context.close()

        logger.info(f"Client {client_uid} disconnected")
        message_handler.cleanup_client(client_uid)
        self._stop_proactive_loop_if_idle()

    async def _cleanup_failed_connection(self, client_uid: str) -> None:
        """Clean up failed connection data"""
        await self._release_mic_client(client_uid, "connection_failed")
        self.client_connections.pop(client_uid, None)
        self.client_contexts.pop(client_uid, None)
        self.client_kinds.pop(client_uid, None)
        self.received_data_buffers.pop(client_uid, None)
        self.chat_group_manager.client_group_map.pop(client_uid, None)

        if client_uid in self.current_conversation_tasks:
            task = self.current_conversation_tasks[client_uid]
            if task and not task.done():
                task.cancel()
            self.current_conversation_tasks.pop(client_uid, None)

        message_handler.cleanup_client(client_uid)

    def _now_ms(self) -> int:
        return int(time.time() * 1000)

    def _asr_enabled_for_client(self, client_uid: str | None = None) -> bool:
        context = (
            self.client_contexts.get(client_uid, self.default_context_cache)
            if client_uid
            else self.default_context_cache
        )
        return not getattr(getattr(context, "asr_engine", None), "is_disabled", False)

    def _streaming_status_for_client(self, client_uid: str | None = None) -> str:
        if not self._asr_enabled_for_client(client_uid):
            return "asr_disabled"
        context = (
            self.client_contexts.get(client_uid, self.default_context_cache)
            if client_uid
            else self.default_context_cache
        )
        asr_engine = getattr(context, "asr_engine", None)
        status = getattr(asr_engine, "streaming_status", None)
        if callable(status):
            try:
                value = str(status())
                if value:
                    return value
            except Exception as exc:
                logger.warning(f"Failed to read streaming ASR status: {exc}")
                return "streaming_unavailable"
        if getattr(asr_engine, "is_streaming_capable", False):
            return "streaming_ready"
        return "offline_fallback"

    def _mic_priority(self, state: MicClientState) -> int:
        if state.explicit_owner:
            return 0
        if state.client_kind == "console":
            return 1
        if state.client_kind == "overlay":
            return 2
        return 3

    def _eligible_mic_owner(self) -> MicClientState | None:
        eligible = [
            state
            for state in self.mic_clients.values()
            if state.is_eligible(self._asr_enabled_for_client(state.client_uid))
            and state.client_uid in self.client_connections
        ]
        if not eligible:
            return None
        return sorted(eligible, key=self._mic_priority)[0]

    def _mic_owner_payload(self, reason: str = "state_updated") -> dict[str, Any]:
        owner_state = (
            self.mic_clients.get(self.active_mic_owner_uid)
            if self.active_mic_owner_uid
            else None
        )
        return {
            "type": "asr-owner-state",
            "owner": owner_state.to_dict() if owner_state else None,
            "owner_client_uid": self.active_mic_owner_uid,
            "owner_since_ms": self.active_mic_owner_since_ms,
            "reason": reason,
            "streaming_status": self._streaming_status_for_client(
                self.active_mic_owner_uid
            ),
            "clients": [state.to_dict() for state in self.mic_clients.values()],
        }

    async def _broadcast_mic_owner_state(self, reason: str = "state_updated") -> None:
        payload = self._mic_owner_payload(reason)
        for websocket in list(self.client_connections.values()):
            try:
                await websocket.send_text(json.dumps(payload))
            except Exception as exc:
                logger.debug(f"Failed to broadcast mic owner state: {exc}")

    async def _recompute_mic_owner(self, reason: str = "state_updated") -> None:
        previous_owner = self.active_mic_owner_uid
        next_owner = self._eligible_mic_owner()
        next_uid = next_owner.client_uid if next_owner else None
        if next_uid != previous_owner:
            self.active_mic_owner_uid = next_uid
            self.active_mic_owner_since_ms = self._now_ms() if next_uid else None
            if previous_owner and previous_owner in self.received_data_buffers:
                self.received_data_buffers[previous_owner] = np.array(
                    [], dtype=np.float32
                )
        await self._broadcast_mic_owner_state(reason)

    async def _release_mic_client(self, client_uid: str, reason: str) -> None:
        changed = False
        if client_uid in self.mic_clients:
            self.mic_clients.pop(client_uid, None)
            changed = True
        getattr(self, "streaming_asr_sessions", {}).pop(client_uid, None)
        self.playback_guard_by_client.pop(client_uid, None)
        if self.active_mic_owner_uid == client_uid:
            self.active_mic_owner_uid = None
            self.active_mic_owner_since_ms = None
            changed = True
        if changed:
            await self._recompute_mic_owner(reason)

    def _mic_protocol_active(self) -> bool:
        return bool(getattr(self, "mic_clients", {}))

    def _client_is_mic_owner(self, client_uid: str) -> bool:
        if not self._mic_protocol_active():
            return True
        return getattr(self, "active_mic_owner_uid", None) == client_uid

    def _streaming_session_for_client(self, client_uid: str):
        if self._streaming_status_for_client(client_uid) != "streaming_ready":
            return None
        if not hasattr(self, "streaming_asr_sessions"):
            self.streaming_asr_sessions = {}
        if client_uid in self.streaming_asr_sessions:
            return self.streaming_asr_sessions[client_uid]
        context = self.client_contexts.get(client_uid, self.default_context_cache)
        asr_engine = getattr(context, "asr_engine", None)
        create_session = getattr(asr_engine, "create_streaming_session", None)
        if not callable(create_session):
            return None
        try:
            session = create_session()
        except Exception as exc:
            logger.warning(f"Failed to create streaming ASR session: {exc}")
            return None
        self.streaming_asr_sessions[client_uid] = session
        return session

    async def _emit_streaming_partial(
        self, websocket: WebSocket, client_uid: str, text: str
    ) -> None:
        if not text:
            return
        await websocket.send_text(
            json.dumps(
                {
                    "type": "asr-streaming-partial",
                    "text": text,
                    "client_uid": client_uid,
                }
            )
        )
        settings = self.rikka_settings.snapshot()
        decision = get_default_wake_gate().preview(text, settings.audio)
        await websocket.send_text(
            json.dumps(
                {
                    "type": "wake-gate",
                    "source": "partial",
                    **decision.to_dict(),
                }
            )
        )

    async def _handle_streaming_final(
        self, websocket: WebSocket, client_uid: str, text: str
    ) -> None:
        final_text = (text or "").strip()
        if not final_text:
            return
        flow_id = f"mic-{uuid.uuid4().hex[:12]}"
        self.rikka_flow_monitor.start(
            flow_id,
            {
                "id": flow_id,
                "source": "mic",
                "type": "mic_streaming",
                "text": final_text,
                "actor": {"display_name": "microphone"},
            },
        )
        self.rikka_flow_monitor.record(
            flow_id,
            "normalize",
            "ok",
            detail="streaming microphone transcript ready",
            metadata={"source_client_uid": client_uid},
        )
        await websocket.send_text(
            json.dumps(
                {
                    "type": "user-input-transcription",
                    "source": "streaming_final",
                    "text": final_text,
                }
            )
        )
        response_client_uid = self._response_client_for_mic_source(client_uid)
        response_websocket = self.client_connections.get(response_client_uid, websocket)
        response_context = self.client_contexts.get(
            response_client_uid,
            self.client_contexts[client_uid],
        )
        if response_client_uid != client_uid:
            await response_websocket.send_text(
                json.dumps(
                    {
                        "type": "user-input-transcription",
                        "source": "streaming_final",
                        "text": final_text,
                    }
                )
            )
        if self.playback_guard_by_client.get(client_uid):
            self.rikka_flow_monitor.record(
                flow_id,
                "validate",
                "skipped",
                detail="playback_echo_guard",
            )
            self.rikka_flow_monitor.record(
                flow_id,
                "complete",
                "skipped",
                detail="ignored streaming microphone turn during playback",
            )
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "wake-gate",
                        "source": "final",
                        "active": False,
                        "should_process": False,
                        "woke": False,
                        "reason": "playback_echo_guard",
                        "text": "",
                    }
                )
            )
            return
        settings = self.rikka_settings.snapshot()
        decision = get_default_wake_gate().evaluate(
            client_uid,
            final_text,
            settings.audio,
        )
        await websocket.send_text(
            json.dumps(
                {
                    "type": "wake-gate",
                    "source": "final",
                    **decision.to_dict(),
                }
            )
        )
        if response_client_uid != client_uid:
            await response_websocket.send_text(
                json.dumps(
                    {
                        "type": "wake-gate",
                        "source": "final",
                        **decision.to_dict(),
                    }
                )
            )
        if not decision.should_process:
            self.rikka_flow_monitor.record(
                flow_id,
                "validate",
                "skipped",
                detail=decision.reason,
                metadata=decision.to_flow_metadata(),
            )
            self.rikka_flow_monitor.record(
                flow_id,
                "complete",
                "skipped",
                detail="wake gate did not accept streaming microphone turn",
            )
            return
        self.rikka_flow_monitor.record(
            flow_id,
            "validate",
            "ok",
            detail=decision.reason,
            metadata=decision.to_flow_metadata(),
        )
        active_task = self.current_conversation_tasks.get(response_client_uid)
        if active_task and not active_task.done():
            self.rikka_flow_monitor.record(
                flow_id,
                "complete",
                "skipped",
                detail="response client already has an active conversation",
            )
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "wake-gate",
                        "source": "final",
                        **decision.to_dict(),
                        "should_process": False,
                        "reason": "conversation_already_running",
                    }
                )
            )
            return
        if response_client_uid == client_uid and self._client_kind(client_uid) == "console":
            self.rikka_flow_monitor.record(
                flow_id,
                "complete",
                "skipped",
                detail="no Overlay/Live2D response client connected",
            )
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "error",
                        "message": "Wake accepted, but no Overlay/Live2D response client is connected.",
                    }
                )
            )
            return
        if response_client_uid != client_uid:
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "asr-response-target",
                        "source_client_uid": client_uid,
                        "target_client_uid": response_client_uid,
                        "target_client_kind": self._client_kind(response_client_uid),
                    }
                )
            )
        await handle_conversation_trigger(
            msg_type="text-input",
            data={
                "type": "text-input",
                "text": decision.text,
                "metadata": {
                    "asr_streaming": True,
                    "rikka_flow_id": flow_id,
                    "wake_client_uid": client_uid,
                    "wake_window_after_playback_ms": (
                        settings.audio.wake_active_window_ms
                        if decision.woke and decision.reason == "wake_phrase_matched"
                        else None
                    ),
                    "source_client_uid": client_uid,
                    "response_client_uid": response_client_uid,
                },
            },
            client_uid=response_client_uid,
            context=response_context,
            websocket=response_websocket,
            client_contexts=self.client_contexts,
            client_connections=self.client_connections,
            chat_group_manager=self.chat_group_manager,
            received_data_buffers=self.received_data_buffers,
            current_conversation_tasks=self.current_conversation_tasks,
            broadcast_to_group=self.broadcast_to_group,
            flow_monitor=self.rikka_flow_monitor,
        )
        self._stop_proactive_loop_if_idle()

    def _client_kind(self, client_uid: str) -> str:
        return (self.mic_clients.get(client_uid) or MicClientState(client_uid)).client_kind

    def _response_client_for_mic_source(self, client_uid: str) -> str:
        """Route console-owned microphone turns to a visual Overlay/Live2D client."""
        source_kind = self._client_kind(client_uid)
        if source_kind != "console":
            return client_uid
        for candidate_uid, state in self.mic_clients.items():
            if (
                candidate_uid != client_uid
                and state.client_kind == "overlay"
                and candidate_uid in self.client_connections
            ):
                return candidate_uid
        for candidate_uid, state in self.mic_clients.items():
            if (
                candidate_uid != client_uid
                and state.client_kind != "console"
                and candidate_uid in self.client_connections
            ):
                return candidate_uid
        return client_uid

    def _wake_client_for_proactive_response(self, response_client_uid: str) -> str:
        """Bind proactive follow-up listening to the active microphone owner."""
        mic_owner_uid = getattr(self, "active_mic_owner_uid", None)
        if mic_owner_uid and mic_owner_uid in self.client_connections:
            return mic_owner_uid
        return response_client_uid

    def _ensure_proactive_loop(self) -> None:
        if self._proactive_task and not self._proactive_task.done():
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        self._proactive_task = loop.create_task(self._proactive_loop())

    def _stop_proactive_loop_if_idle(self) -> None:
        if self.client_connections:
            return
        if self._proactive_task and not self._proactive_task.done():
            self._proactive_task.cancel()
        self._proactive_task = None

    async def _proactive_loop(self) -> None:
        while True:
            interval_ms = self.rikka_settings.snapshot().proactive.scheduler_interval_ms
            await asyncio.sleep(max(1.0, interval_ms / 1000))
            try:
                await self.tick_proactive_once()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.error(f"Error in proactive scheduler tick: {exc}")

    def _conversation_active(self) -> bool:
        self._prune_finished_conversation_tasks()
        return any(
            task is not None and not task.done()
            for task in self.current_conversation_tasks.values()
        )

    def _conversation_active_for_proactive(self) -> bool:
        self._prune_finished_conversation_tasks()
        return any(
            task is not None
            and not task.done()
            and self._client_kind(task_key) != "console"
            for task_key, task in self.current_conversation_tasks.items()
        )

    def _prune_finished_conversation_tasks(self) -> None:
        for task_key, task in list(self.current_conversation_tasks.items()):
            if task is None or task.done():
                self.current_conversation_tasks.pop(task_key, None)

    def _live2d_client_connected(self) -> bool:
        return any(
            client_uid in self.client_contexts
            and self._client_kind(client_uid) != "console"
            for client_uid in self.client_connections
        )

    def _first_available_live2d_client(self) -> tuple[str, WebSocket] | None:
        for client_uid, websocket in self.client_connections.items():
            if (
                client_uid in self.client_contexts
                and self._client_kind(client_uid) == "overlay"
            ):
                return client_uid, websocket
        for client_uid, websocket in self.client_connections.items():
            if (
                client_uid in self.client_contexts
                and self._client_kind(client_uid) != "console"
            ):
                return client_uid, websocket
        return None

    def _proactive_prompt(self, kind: str) -> str:
        if kind == "screen_comment":
            return (
                "请根据最近一张游戏画面，用低打扰的陪播语气说一句。"
                "只有画面真的值得回应时才说，保持简短、自然，不要复述调试信息。"
            )
        base = (
            "现在用户暂时没有说话。请用低打扰的陪伴语气自己说一句，"
            "保持简短、自然，不要打断正在进行的内容。"
        )
        try:
            settings = self.rikka_settings.snapshot()
            if settings.inner_life.enabled:
                activity = get_default_inner_life().current(settings.inner_life)
                if activity:
                    return f"{base}你现在正在{activity}，可以围绕它轻声说一句。"
        except Exception as exc:
            logger.warning(f"Failed to include inner life in proactive prompt: {exc}")
        return base

    async def tick_proactive_once(self) -> dict[str, Any]:
        settings = self.rikka_settings.snapshot()
        live2d_connected = self._live2d_client_connected()
        conversation_active = self._conversation_active_for_proactive()
        capture_result: dict[str, Any] | None = None
        screen_change: dict[str, Any] | None = None

        def finish(result: dict[str, Any]) -> dict[str, Any]:
            self.proactive_coordinator.record_tick(result)
            return result

        if settings.proactive.screen_comments_enabled:
            capture_result = self.capture_service.capture_keyframe(force=False)
        latest_frame = self.capture_service.latest_frame()
        capture_enabled = settings.screen_capture_enabled or settings.capture.enabled
        screen_capture_ready = bool(
            capture_enabled
            and settings.keyframe_upload_enabled
            and settings.capture.attach_to_user_turns
            and latest_frame
        )
        if (
            settings.proactive.screen_comments_enabled
            and settings.proactive.screen_change_gate_enabled
            and latest_frame is not None
        ):
            screen_change = self.screen_change_detector.evaluate(
                latest_frame,
                settings.proactive,
            )

        decisions = {
            "screen_comment": self.proactive_coordinator.decision(
                settings.proactive,
                "screen_comment",
                live2d_connected=live2d_connected,
                capture_ready=screen_capture_ready,
                conversation_active=conversation_active,
            ),
            "idle_speech": self.proactive_coordinator.decision(
                settings.proactive,
                "idle_speech",
                live2d_connected=live2d_connected,
                capture_ready=screen_capture_ready,
                conversation_active=conversation_active,
            ),
        }
        if (
            decisions["screen_comment"].get("allowed")
            and screen_change is not None
            and not screen_change.get("changed")
        ):
            decisions["screen_comment"] = {
                "kind": "screen_comment",
                "allowed": False,
                "reason": "screen unchanged",
                "score": screen_change.get("score"),
                "now_ms": self._now_ms(),
            }

        for kind in ("screen_comment", "idle_speech"):
            if not decisions[kind].get("allowed"):
                continue
            client = self._first_available_live2d_client()
            if client is None:
                return finish({
                    "triggered": False,
                    "reason": "no client context available",
                    "decisions": decisions,
                    "capture": capture_result,
                    "screen_change": screen_change,
                })
            client_uid, websocket = client
            await handle_conversation_trigger(
                msg_type="ai-speak-signal",
                data={
                    "type": "ai-speak-signal",
                    "kind": kind,
                    "text": self._proactive_prompt(kind),
                    "metadata": {
                        "wake_client_uid": self._wake_client_for_proactive_response(
                            client_uid
                        ),
                    },
                },
                client_uid=client_uid,
                context=self.client_contexts[client_uid],
                websocket=websocket,
                client_contexts=self.client_contexts,
                client_connections=self.client_connections,
                chat_group_manager=self.chat_group_manager,
                received_data_buffers=self.received_data_buffers,
                current_conversation_tasks=self.current_conversation_tasks,
                broadcast_to_group=self.broadcast_to_group,
                flow_monitor=self.rikka_flow_monitor,
            )
            self.proactive_coordinator.mark_rikka_speech(kind)
            if kind == "screen_comment":
                self.screen_change_detector.commit_baseline()
            return finish({
                "triggered": True,
                "kind": kind,
                "client_uid": client_uid,
                "decisions": decisions,
                "capture": capture_result,
                "screen_change": screen_change,
            })

        return finish({
            "triggered": False,
            "reason": "not allowed",
            "decisions": decisions,
            "capture": capture_result,
            "screen_change": screen_change,
        })

    async def broadcast_to_group(
        self, group_members: list[str], message: dict, exclude_uid: str = None
    ) -> None:
        """Broadcasts a message to group members"""
        await broadcast_to_group(
            group_members=group_members,
            message=message,
            client_connections=self.client_connections,
            exclude_uid=exclude_uid,
        )

    async def send_group_update(self, websocket: WebSocket, client_uid: str):
        """Sends group information to a client"""
        group = self.chat_group_manager.get_client_group(client_uid)
        if group:
            current_members = self.chat_group_manager.get_group_members(client_uid)
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "group-update",
                        "members": current_members,
                        "is_owner": group.owner_uid == client_uid,
                    }
                )
            )
        else:
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "group-update",
                        "members": [],
                        "is_owner": False,
                    }
                )
            )

    async def _handle_interrupt(
        self, websocket: WebSocket, client_uid: str, data: WSMessage
    ) -> None:
        """Handle conversation interruption"""
        heard_response = data.get("text", "")
        context = self.client_contexts[client_uid]
        group = self.chat_group_manager.get_client_group(client_uid)

        if group and len(group.members) > 1:
            await handle_group_interrupt(
                group_id=group.group_id,
                heard_response=heard_response,
                current_conversation_tasks=self.current_conversation_tasks,
                chat_group_manager=self.chat_group_manager,
                client_contexts=self.client_contexts,
                broadcast_to_group=self.broadcast_to_group,
            )
        else:
            await handle_individual_interrupt(
                client_uid=client_uid,
                current_conversation_tasks=self.current_conversation_tasks,
                context=context,
                heard_response=heard_response,
            )

    async def _handle_history_list_request(
        self, websocket: WebSocket, client_uid: str, data: WSMessage
    ) -> None:
        """Handle request for chat history list"""
        context = self.client_contexts[client_uid]
        histories = get_history_list(context.character_config.conf_uid)
        await websocket.send_text(
            json.dumps({"type": "history-list", "histories": histories})
        )

    async def _handle_fetch_history(
        self, websocket: WebSocket, client_uid: str, data: dict
    ):
        """Handle fetching and setting specific chat history"""
        history_uid = data.get("history_uid")
        if not history_uid:
            return

        context = self.client_contexts[client_uid]
        # Update history_uid in service context
        context.history_uid = history_uid
        context.agent_engine.set_memory_from_history(
            conf_uid=context.character_config.conf_uid,
            history_uid=history_uid,
        )

        messages = [
            msg
            for msg in get_history(
                context.character_config.conf_uid,
                history_uid,
            )
            if msg["role"] != "system"
        ]
        await websocket.send_text(
            json.dumps({"type": "history-data", "messages": messages})
        )

    async def _handle_create_history(
        self, websocket: WebSocket, client_uid: str, data: WSMessage
    ) -> None:
        """Handle creation of new chat history"""
        context = self.client_contexts[client_uid]
        history_uid = create_new_history(context.character_config.conf_uid)
        if history_uid:
            context.history_uid = history_uid
            context.agent_engine.set_memory_from_history(
                conf_uid=context.character_config.conf_uid,
                history_uid=history_uid,
            )
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "new-history-created",
                        "history_uid": history_uid,
                    }
                )
            )

    async def _handle_delete_history(
        self, websocket: WebSocket, client_uid: str, data: dict
    ):
        """Handle deletion of chat history"""
        history_uid = data.get("history_uid")
        if not history_uid:
            return

        context = self.client_contexts[client_uid]
        success = delete_history(
            context.character_config.conf_uid,
            history_uid,
        )
        await websocket.send_text(
            json.dumps(
                {
                    "type": "history-deleted",
                    "success": success,
                    "history_uid": history_uid,
                }
            )
        )
        if history_uid == context.history_uid:
            context.history_uid = None

    async def _handle_audio_data(
        self, websocket: WebSocket, client_uid: str, data: WSMessage
    ) -> None:
        """Handle incoming audio data"""
        if not self._client_is_mic_owner(client_uid):
            await websocket.send_text(
                json.dumps(
                    {
                        **self._mic_owner_payload("non_owner_audio_ignored"),
                        "ignored_client_uid": client_uid,
                    }
                )
            )
            return
        audio_data = data.get("audio", [])
        if audio_data:
            context = self.client_contexts.get(client_uid, self.default_context_cache)
            asr_engine = getattr(context, "asr_engine", None)
            target_sample_rate = _positive_int(
                getattr(asr_engine, "SAMPLE_RATE", None)
            ) or 16000
            source_sample_rate = _positive_int(
                data.get("sample_rate") or data.get("sampleRate")
            )
            chunk = np.array(audio_data, dtype=np.float32)
            chunk = resample_audio_chunk(
                chunk,
                source_sample_rate=source_sample_rate,
                target_sample_rate=target_sample_rate,
            )
            streaming_session = self._streaming_session_for_client(client_uid)
            if streaming_session is not None:
                result = await streaming_session.accept_audio(chunk)
                if result.partial:
                    await self._emit_streaming_partial(
                        websocket, client_uid, result.partial
                    )
                if result.endpoint and result.final:
                    await self._handle_streaming_final(
                        websocket, client_uid, result.final
                    )
                return
            self.received_data_buffers[client_uid] = np.append(
                self.received_data_buffers[client_uid],
                chunk,
            )

    async def _handle_raw_audio_data(
        self, websocket: WebSocket, client_uid: str, data: WSMessage
    ) -> None:
        """Handle incoming raw audio data for VAD processing"""
        context = self.client_contexts[client_uid]
        if context.vad_engine is None:
            logger.debug("Ignoring raw audio data because VAD is disabled.")
            return

        chunk = data.get("audio", [])
        if chunk:
            for audio_bytes in context.vad_engine.detect_speech(chunk):
                if audio_bytes == b"<|PAUSE|>":
                    await websocket.send_text(
                        json.dumps({"type": "control", "text": "interrupt"})
                    )
                elif audio_bytes == b"<|RESUME|>":
                    pass
                elif len(audio_bytes) > 1024:
                    # Detected audio activity (voice)
                    self.received_data_buffers[client_uid] = np.append(
                        self.received_data_buffers[client_uid],
                        np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32),
                    )
                    await websocket.send_text(
                        json.dumps({"type": "control", "text": "mic-audio-end"})
                    )

    async def _handle_conversation_trigger(
        self, websocket: WebSocket, client_uid: str, data: WSMessage
    ) -> None:
        """Handle triggers that start a conversation"""
        if data.get("type") == "mic-audio-end" and not self._client_is_mic_owner(
            client_uid
        ):
            await websocket.send_text(
                json.dumps(
                    {
                        **self._mic_owner_payload("non_owner_final_ignored"),
                        "ignored_client_uid": client_uid,
                    }
                )
            )
            return
        if data.get("type") == "mic-audio-end":
            streaming_session = getattr(self, "streaming_asr_sessions", {}).get(
                client_uid
            )
            if streaming_session is not None:
                result = await streaming_session.finish()
                self.streaming_asr_sessions.pop(client_uid, None)
                if result.final:
                    await self._handle_streaming_final(
                        websocket, client_uid, result.final
                    )
                return
        await handle_conversation_trigger(
            msg_type=data.get("type", ""),
            data=data,
            client_uid=client_uid,
            context=self.client_contexts[client_uid],
            websocket=websocket,
            client_contexts=self.client_contexts,
            client_connections=self.client_connections,
            chat_group_manager=self.chat_group_manager,
            received_data_buffers=self.received_data_buffers,
            current_conversation_tasks=self.current_conversation_tasks,
            broadcast_to_group=self.broadcast_to_group,
            flow_monitor=self.rikka_flow_monitor,
        )

    async def _handle_fetch_configs(
        self, websocket: WebSocket, client_uid: str, data: WSMessage
    ) -> None:
        """Handle fetching available configurations"""
        context = self.client_contexts[client_uid]
        config_files = scan_config_alts_directory(context.system_config.config_alts_dir)
        await websocket.send_text(
            json.dumps({"type": "config-files", "configs": config_files})
        )

    async def _handle_config_switch(
        self, websocket: WebSocket, client_uid: str, data: dict
    ):
        """Handle switching to a different configuration"""
        config_file_name = data.get("file")
        if config_file_name:
            context = self.client_contexts[client_uid]
            await context.handle_config_switch(websocket, config_file_name)

    async def _handle_fetch_backgrounds(
        self, websocket: WebSocket, client_uid: str, data: WSMessage
    ) -> None:
        """Handle fetching available background images"""
        bg_files = scan_bg_directory()
        await websocket.send_text(
            json.dumps({"type": "background-files", "files": bg_files})
        )

    async def _handle_audio_play_start(
        self, websocket: WebSocket, client_uid: str, data: WSMessage
    ) -> None:
        """
        Handle audio playback start notification
        """
        group_members = self.chat_group_manager.get_group_members(client_uid)
        if len(group_members) > 1:
            display_text = data.get("display_text")
            if display_text:
                silent_payload = prepare_audio_payload(
                    audio_path=None,
                    display_text=display_text,
                    actions=None,
                    forwarded=True,
                )
                await self.broadcast_to_group(
                    group_members, silent_payload, exclude_uid=client_uid
                )

    async def _handle_group_info(
        self, websocket: WebSocket, client_uid: str, data: WSMessage
    ) -> None:
        """Handle group info request"""
        await self.send_group_update(websocket, client_uid)

    async def _handle_init_config_request(
        self, websocket: WebSocket, client_uid: str, data: WSMessage
    ) -> None:
        """Handle request for initialization configuration"""
        context = self.client_contexts.get(client_uid)
        if not context:
            context = self.default_context_cache

        await websocket.send_text(
            json.dumps(
                {
                    "type": "set-model-and-conf",
                    "model_info": context.live2d_model.model_info,
                    "conf_name": context.character_config.conf_name,
                    "conf_uid": context.character_config.conf_uid,
                    "client_uid": client_uid,
                }
            )
        )

    async def _handle_heartbeat(
        self, websocket: WebSocket, client_uid: str, data: WSMessage
    ) -> None:
        """Handle heartbeat messages from clients"""
        try:
            await websocket.send_json({"type": "heartbeat-ack"})
        except Exception as e:
            logger.error(f"Error sending heartbeat acknowledgment: {e}")

    async def _handle_client_capabilities(
        self, websocket: WebSocket, client_uid: str, data: WSMessage
    ) -> None:
        """Register browser microphone ownership eligibility."""
        raw_kind = str(data.get("client_kind") or data.get("kind") or "unknown")
        client_kind = raw_kind if raw_kind in {"console", "overlay"} else "unknown"
        self.client_kinds[client_uid] = client_kind
        state = self.mic_clients.get(client_uid) or MicClientState(
            client_uid=client_uid,
            updated_at_ms=self._now_ms(),
        )
        state.client_kind = client_kind
        if "always_on_enabled" in data:
            state.always_on_enabled = bool(data.get("always_on_enabled"))
        if "mic_permission" in data:
            state.mic_permission = str(data.get("mic_permission") or "unknown")
        if "listening" in data:
            state.listening = bool(data.get("listening"))
        if "explicit_owner" in data:
            state.explicit_owner = bool(data.get("explicit_owner"))
        if data.get("type") == "mic-owner-request":
            state.explicit_owner = True
            state.always_on_enabled = True
        state.last_reason = str(data.get("reason") or data.get("type") or "updated")
        state.updated_at_ms = self._now_ms()
        self.mic_clients[client_uid] = state
        await self._recompute_mic_owner(state.last_reason)

    async def _handle_mic_owner_release(
        self, websocket: WebSocket, client_uid: str, data: WSMessage
    ) -> None:
        """Mark a browser client ineligible for microphone ownership."""
        state = self.mic_clients.get(client_uid)
        if state:
            state.listening = False
            state.explicit_owner = False
            state.last_reason = str(data.get("reason") or "released")
            state.updated_at_ms = self._now_ms()
        await self._recompute_mic_owner("released")

    async def _handle_frontend_playback_state(
        self, websocket: WebSocket, client_uid: str, data: WSMessage
    ) -> None:
        """Track browser playback windows so ASR wake evaluation can ignore echo."""
        playing = bool(data.get("playing"))
        self.playback_guard_by_client[client_uid] = playing
        await websocket.send_text(
            json.dumps(
                {
                    "type": "asr-playback-guard",
                    "client_uid": client_uid,
                    "active": playing,
                }
            )
        )

    async def _handle_rikka_live_event(
        self, websocket: WebSocket, client_uid: str, data: dict
    ) -> None:
        """Handle normalized Rikka Live events from debug UI or connectors."""
        context = self.client_contexts[client_uid]
        event_payload, candidate_response, speak = extract_rikka_live_event_message(data)
        event = normalize_live_event(event_payload)
        self.rikka_planner.set_context(context)
        result = await self.rikka_planner.plan(
            event,
            candidate_response=candidate_response,
        )
        response = result.response
        if result.ok:
            self._register_rikka_mood_for_event(response, event.model_dump(mode="json"))
        applied_memory = self.rikka_memory.apply_writes(response.memory_writes)

        await self._emit_rikka_result_to_client(
            websocket=websocket,
            context=context,
            event_data=event.model_dump(mode="json"),
            validation_ok=result.ok,
            validation_errors=result.errors,
            response=response,
            applied_memory=applied_memory,
            planner_status=self.rikka_planner.status(),
            speak=speak,
        )
        return

    async def _speak_rikka_response(
        self,
        websocket: WebSocket,
        context: ServiceContext,
        response: RikkaResponse,
        flow_id: str | None = None,
    ) -> None:
        """Speak a validated Rikka response through one connected Live2D client."""
        tts_manager = TTSTaskManager()
        display_text = DisplayText(
            text=response.spoken_text,
            name=context.character_config.character_name,
            avatar=context.character_config.avatar,
        )
        actions = rikka_response_to_actions(
            response,
            context.live2d_model,
            enable_expression_actions=live2d_expressions_enabled(self.rikka_settings),
        )
        tts_meta = self._apply_rikka_mood_to_output(
            response=response,
            live2d_model=context.live2d_model,
            actions=actions,
        )

        self._record_flow(
            flow_id,
            "tts",
            "running",
            "synthesizing audio",
            {"actions": actions.to_dict()},
        )
        try:
            await tts_manager.speak(
                tts_text=response.spoken_text,
                display_text=display_text,
                actions=actions,
                live2d_model=context.live2d_model,
                tts_engine=context.tts_engine,
                websocket_send=websocket.send_text,
                tts_meta=tts_meta,
            )
            if tts_manager.task_list:
                await asyncio.gather(*tts_manager.task_list)
            await tts_manager.wait_for_payloads()
            self._record_flow(flow_id, "tts", "ok", "audio payload emitted")
            if actions.to_dict():
                self._record_flow(
                    flow_id,
                    "actions",
                    "running",
                    "audio action payload sent; waiting for frontend telemetry",
                    {"actions": actions.to_dict()},
                )
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "backend-synth-complete",
                        "flow": {"id": flow_id} if flow_id else {},
                    }
                )
            )
            self._record_flow(flow_id, "complete", "ok", "backend synth complete")
        except Exception as exc:
            self._record_flow(flow_id, "tts", "error", str(exc))
            raise
        finally:
            tts_manager.clear()

    async def _handle_live2d_param_preview(
        self, websocket: WebSocket, client_uid: str, data: WSMessage
    ) -> None:
        """Forward live parameter preview to all overlay clients."""
        parameters = data.get("parameters")
        if not isinstance(parameters, dict):
            return
        ttl_ms = int(data.get("ttl_ms") or 1500)
        forwarded = await self._forward_to_client_kind("overlay", {
            "type": "live2d-param-preview",
            "parameters": parameters,
            "ttl_ms": ttl_ms,
        })
        await websocket.send_text(
            json.dumps(
                {
                    "type": "live2d-param-preview-ack",
                    "forwarded": forwarded,
                    "ttl_ms": ttl_ms,
                }
            )
        )

    async def _handle_live2d_param_preview_result(
        self, websocket: WebSocket, client_uid: str, data: WSMessage
    ) -> None:
        """Forward overlay preview diagnostics back to console clients."""
        await self._forward_to_client_kind("console", {
            "type": "live2d-param-preview-result",
            "source_uid": client_uid,
            "ok": bool(data.get("ok")),
            "detail": str(data.get("detail") or ""),
            "probe": data.get("probe") if isinstance(data.get("probe"), dict) else {},
        })

    async def _handle_live2d_gesture_preview(
        self, websocket: WebSocket, client_uid: str, data: WSMessage
    ) -> None:
        """Forward a procedural gesture preview to all overlay clients."""
        gesture = data.get("gesture")
        if not isinstance(gesture, dict):
            return
        name = str(data.get("name") or "")
        forwarded = await self._forward_to_client_kind("overlay", {
            "type": "live2d-gesture-preview",
            "name": name,
            "gesture": gesture,
        })
        await websocket.send_text(
            json.dumps(
                {
                    "type": "live2d-gesture-preview-ack",
                    "forwarded": forwarded,
                    "name": name,
                }
            )
        )

    async def _handle_live2d_gesture_preview_result(
        self, websocket: WebSocket, client_uid: str, data: WSMessage
    ) -> None:
        """Forward overlay gesture preview diagnostics back to console clients."""
        await self._forward_to_client_kind("console", {
            "type": "live2d-gesture-preview-result",
            "source_uid": client_uid,
            "ok": bool(data.get("ok")),
            "name": str(data.get("name") or ""),
            "detail": str(data.get("detail") or ""),
            "probe": data.get("probe") if isinstance(data.get("probe"), dict) else {},
        })

    async def _forward_to_client_kind(self, client_kind: str, payload: dict) -> int:
        """Best-effort forward a websocket payload to clients of one registered kind."""
        message = json.dumps(
            payload
        )
        forwarded = 0
        for uid, client_ws in list(self.client_connections.items()):
            if self.client_kinds.get(uid) == client_kind:
                try:
                    await client_ws.send_text(message)
                    forwarded += 1
                except Exception:
                    pass
        return forwarded

    async def broadcast_model_conf_update(self, model_info: dict) -> None:
        """Broadcast set-model-and-conf to all connected clients."""
        message = json.dumps({
            "type": "set-model-and-conf",
            "model_info": model_info,
        })
        for client_ws in list(self.client_connections.values()):
            try:
                await client_ws.send_text(message)
            except Exception:
                pass

    async def _emit_rikka_result_to_client(
        self,
        websocket: WebSocket,
        context: ServiceContext,
        event_data: dict[str, Any],
        validation_ok: bool,
        validation_errors: list[str],
        response: RikkaResponse,
        applied_memory: list[dict[str, Any]],
        planner_status: dict[str, Any],
        speak: bool,
        flow_id: str | None = None,
    ) -> None:
        """Emit validated event/response payloads to one Live2D client."""
        if flow_id is None:
            flow_id = event_data.get("id")
        actions = rikka_response_to_actions(
            response,
            context.live2d_model,
            enable_expression_actions=live2d_expressions_enabled(self.rikka_settings),
        )
        self._apply_rikka_mood_to_output(
            response=response,
            live2d_model=context.live2d_model,
            actions=actions,
        )
        action_payload = actions.to_dict()
        await websocket.send_text(
            json.dumps(
                {
                    "type": "rikka-live-event",
                    "event": event_data,
                    "flow": {"id": flow_id} if flow_id else {},
                }
            )
        )
        self._record_flow(flow_id, "live2d", "running", "sent event to frontend")
        await websocket.send_text(
            json.dumps(
                {
                    "type": "rikka-response",
                    "validation": {
                        "ok": validation_ok,
                        "errors": validation_errors,
                    },
                    "response": response.model_dump(mode="json"),
                    "memory_applied": applied_memory,
                    "planner": planner_status,
                    "actions": action_payload,
                    "speak": speak,
                    "flow": {"id": flow_id} if flow_id else {},
                }
            )
        )
        self._record_flow(
            flow_id,
            "live2d",
            "ok",
            "structured response sent to frontend",
        )
        if speak:
            await self._speak_rikka_response(websocket, context, response, flow_id)
        else:
            self._record_flow(flow_id, "complete", "ok", "speak disabled")

    def rikka_client_status(self) -> dict[str, Any]:
        """Return privacy-safe status for connected Live2D clients."""
        return {
            "connected_clients": len(self.client_connections),
            "client_uids": list(self.client_connections.keys()),
        }

    async def emit_preplanned_rikka_result(
        self,
        result_payload: dict[str, Any],
        speak: bool = True,
    ) -> dict[str, Any]:
        """Broadcast a preplanned Rikka result to connected Live2D clients."""
        flow_id = (result_payload.get("flow") or {}).get("id") or (
            result_payload.get("event") or {}
        ).get("id")
        if not self.client_connections:
            self._record_flow(flow_id, "delivery", "error", "no Live2D clients connected")
            return {
                "ok": False,
                "delivered_clients": 0,
                "failed_clients": [],
                "reason": "no Live2D clients connected",
            }

        response = RikkaResponse.model_validate(result_payload["response"])
        event_data = result_payload.get("event") or {}
        self._register_rikka_mood_for_event(response, event_data)
        failed_clients: list[dict[str, str]] = []
        delivered_clients = 0

        for client_uid, websocket in list(self.client_connections.items()):
            context = self.client_contexts.get(client_uid, self.default_context_cache)
            try:
                await self._emit_rikka_result_to_client(
                    websocket=websocket,
                    context=context,
                    event_data=result_payload["event"],
                    validation_ok=result_payload["validation"]["ok"],
                    validation_errors=result_payload["validation"]["errors"],
                    response=response,
                    applied_memory=result_payload.get("memory_applied", []),
                    planner_status=result_payload.get("planner", {}),
                    speak=speak,
                    flow_id=flow_id,
                )
                delivered_clients += 1
            except Exception as exc:
                logger.error(f"Failed to emit Rikka debug result to {client_uid}: {exc}")
                failed_clients.append({"client_uid": client_uid, "error": str(exc)})

        return {
            "ok": delivered_clients > 0,
            "delivered_clients": delivered_clients,
            "failed_clients": failed_clients,
            "reason": "" if delivered_clients else "all Live2D client deliveries failed",
        }

    def _register_rikka_mood_for_event(
        self,
        response: RikkaResponse,
        event_data: dict[str, Any],
    ) -> None:
        if (event_data or {}).get("source") == "bilibili":
            return
        try:
            settings = self.rikka_settings.snapshot()
            apply_rikka_mood_effects(
                emotion=response.emotion,
                settings=settings.mood,
                register=True,
                enable_idle_expression=False,
            )
        except Exception as exc:
            logger.warning(f"Failed to register Rikka mood for event response: {exc}")

    def _apply_rikka_mood_to_output(
        self,
        response: RikkaResponse,
        live2d_model: Any,
        actions: Actions,
    ) -> dict[str, Any] | None:
        try:
            settings = self.rikka_settings.snapshot()
            return apply_rikka_mood_effects(
                emotion=response.emotion,
                settings=settings.mood,
                live2d_model=live2d_model,
                actions=actions,
                register=False,
                enable_idle_expression=live2d_expressions_enabled(self.rikka_settings),
            )
        except Exception as exc:
            logger.warning(f"Failed to apply Rikka mood output effects: {exc}")
            return None

    def _record_flow(
        self,
        flow_id: str | None,
        stage: str,
        status: str,
        detail: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        monitor = getattr(self, "rikka_flow_monitor", None)
        if monitor:
            monitor.record(
                flow_id,
                stage,
                status,
                detail=detail,
                metadata=metadata,
            )

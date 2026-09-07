import asyncio
import json
import uuid
from typing import Any, Dict, Optional, Callable

import numpy as np
from fastapi import WebSocket
from loguru import logger

from ..chat_group import ChatGroupManager
from ..chat_history_manager import store_message
from ..rikka.capture import get_default_capture_service
from ..rikka.screen_context import latest_screen_images, screen_context_metadata
from ..rikka.settings import get_default_settings_store
from ..service_context import ServiceContext
from .group_conversation import process_group_conversation
from .single_conversation import process_single_conversation
from .conversation_utils import EMOJI_LIST
from .types import GroupConversationState
from prompts import prompt_loader


async def handle_conversation_trigger(
    msg_type: str,
    data: dict,
    client_uid: str,
    context: ServiceContext,
    websocket: WebSocket,
    client_contexts: Dict[str, ServiceContext],
    client_connections: Dict[str, WebSocket],
    chat_group_manager: ChatGroupManager,
    received_data_buffers: Dict[str, np.ndarray],
    current_conversation_tasks: Dict[str, Optional[asyncio.Task]],
    broadcast_to_group: Callable,
    flow_monitor: Any = None,
) -> None:
    """Handle triggers that start a conversation"""
    metadata = None

    if msg_type == "ai-speak-signal":
        proactive_kind = str(data.get("kind") or "idle_speech")
        user_input = str(data.get("text") or "").strip()
        try:
            if not user_input:
                prompt_name = "proactive_speak_prompt"
                prompt_file = context.system_config.tool_prompts.get(prompt_name)
                if prompt_file:
                    user_input = prompt_loader.load_util(prompt_file)
                else:
                    logger.warning(
                        "Proactive speak prompt not configured, using default"
                    )
                    user_input = "Please say something."
        except Exception as e:
            logger.error(f"Error loading proactive speak prompt: {e}")
            user_input = "Please say something."

        # Add metadata to indicate this is a proactive speak request
        # that should be skipped in both memory and history
        metadata = {
            "proactive_speak": True,
            "proactive_kind": proactive_kind,
            "skip_memory": True,  # Skip storing in AI's internal memory
            "skip_history": True,  # Skip storing in local conversation history
        }
        if isinstance(data.get("metadata"), dict):
            metadata = {**metadata, **data["metadata"]}

        await websocket.send_text(
            json.dumps(
                {
                    "type": "full-text",
                    "text": "AI wants to speak something...",
                }
            )
        )
    elif msg_type == "text-input":
        user_input = data.get("text", "")
        if isinstance(data.get("metadata"), dict):
            metadata = {**(metadata or {}), **data["metadata"]}
    else:  # mic-audio-end
        user_input = received_data_buffers[client_uid]
        received_data_buffers[client_uid] = np.array([])
        if flow_monitor is not None:
            flow_id = f"mic-{uuid.uuid4().hex[:12]}"
            flow_monitor.start(
                flow_id,
                {
                    "id": flow_id,
                    "source": "mic",
                    "type": "mic_audio",
                    "text": "",
                    "actor": {"display_name": "microphone"},
                },
            )
            flow_monitor.record(
                flow_id,
                "normalize",
                "running",
                detail="transcribing microphone audio",
                metadata={"sample_count": int(len(user_input))},
            )
            metadata = {
                **(metadata or {}),
                "rikka_flow_id": flow_id,
            }

    images = data.get("images")
    settings = get_default_settings_store().snapshot()
    # After proactive speech, open a wake-free follow-up window. The scheduler
    # may bind this to the microphone owner instead of the visual response client.
    if (metadata or {}).get("proactive_speak"):
        followup_ms = settings.proactive.proactive_followup_window_ms
        if followup_ms > 0:
            metadata = {
                **(metadata or {}),
                "wake_client_uid": (
                    (metadata or {}).get("wake_client_uid") or client_uid
                ),
                "wake_window_after_playback_ms": followup_ms,
            }
    capture_service = get_default_capture_service()
    if images:
        capture_service.record_attachment_status(
            "skipped",
            "explicit images supplied by websocket payload",
        )
    elif settings.keyframe_upload_enabled and settings.capture.attach_to_user_turns:
        screen_images = latest_screen_images(capture_service)
        capture_attempt = None
        if not screen_images:
            capture_attempt = capture_service.capture_keyframe(force=False)
            screen_images = latest_screen_images(capture_service)
        if screen_images:
            latest_frame = capture_service.latest_frame()
            images = screen_images
            metadata = {
                **(metadata or {}),
                **screen_context_metadata(latest_frame),
            }
            capture_service.record_attachment_status(
                "attached",
                "latest screen keyframe attached to user turn",
                captured_at_ms=latest_frame.captured_at_ms if latest_frame else None,
                window_title=latest_frame.window.title if latest_frame else "",
            )
        else:
            capture_service.record_attachment_status(
                "skipped",
                "no latest screen keyframe available",
                capture_status=(
                    capture_attempt.get("status") if capture_attempt else None
                ),
                capture_reason=(
                    capture_attempt.get("reason") if capture_attempt else None
                ),
            )
    else:
        capture_service.record_attachment_status(
            "skipped",
            "keyframe upload or attach_to_user_turns is disabled",
        )
    if flow_monitor is not None and not (metadata or {}).get("rikka_flow_id"):
        flow_id = f"conv-{uuid.uuid4().hex[:12]}"
        if msg_type == "ai-speak-signal":
            source = "proactive"
            event_type = f"proactive.{(metadata or {}).get('proactive_kind') or 'speak'}"
            actor = {"display_name": "Rikka proactive"}
        else:
            source = "user"
            event_type = "text_input"
            actor = {"display_name": getattr(context.character_config, "human_name", "")}
        flow_monitor.start(
            flow_id,
            {
                "id": flow_id,
                "source": source,
                "type": event_type,
                "text": user_input if isinstance(user_input, str) else "",
                "actor": actor,
                "payload": {
                    "client_uid": client_uid,
                    "has_images": bool(images),
                },
            },
        )
        metadata = {
            **(metadata or {}),
            "rikka_flow_id": flow_id,
        }
    session_emoji = np.random.choice(EMOJI_LIST)

    group = chat_group_manager.get_client_group(client_uid)
    if group and len(group.members) > 1:
        # Use group_id as task key for group conversations
        task_key = group.group_id
        if (
            task_key not in current_conversation_tasks
            or current_conversation_tasks[task_key].done()
        ):
            logger.info(f"Starting new group conversation for {task_key}")

            current_conversation_tasks[task_key] = asyncio.create_task(
                process_group_conversation(
                    client_contexts=client_contexts,
                    client_connections=client_connections,
                    broadcast_func=broadcast_to_group,
                    group_members=group.members,
                    initiator_client_uid=client_uid,
                    user_input=user_input,
                    images=images,
                    session_emoji=session_emoji,
                    metadata=metadata,
                )
            )
    else:
        # Use client_uid as task key for individual conversations
        current_conversation_tasks[client_uid] = asyncio.create_task(
            process_single_conversation(
                context=context,
                websocket_send=websocket.send_text,
                client_uid=client_uid,
                user_input=user_input,
                images=images,
                session_emoji=session_emoji,
                metadata=metadata,
                flow_monitor=flow_monitor,
                flow_id=(metadata or {}).get("rikka_flow_id"),
            )
        )


async def handle_individual_interrupt(
    client_uid: str,
    current_conversation_tasks: Dict[str, Optional[asyncio.Task]],
    context: ServiceContext,
    heard_response: str,
):
    if client_uid in current_conversation_tasks:
        task = current_conversation_tasks[client_uid]
        if task and not task.done():
            task.cancel()
            logger.info("🛑 Conversation task was successfully interrupted")

        try:
            context.agent_engine.handle_interrupt(heard_response)
        except Exception as e:
            logger.error(f"Error handling interrupt: {e}")

        if context.history_uid:
            store_message(
                conf_uid=context.character_config.conf_uid,
                history_uid=context.history_uid,
                role="ai",
                content=heard_response,
                name=context.character_config.character_name,
                avatar=context.character_config.avatar,
            )
            store_message(
                conf_uid=context.character_config.conf_uid,
                history_uid=context.history_uid,
                role="system",
                content="[Interrupted by user]",
            )


async def handle_group_interrupt(
    group_id: str,
    heard_response: str,
    current_conversation_tasks: Dict[str, Optional[asyncio.Task]],
    chat_group_manager: ChatGroupManager,
    client_contexts: Dict[str, ServiceContext],
    broadcast_to_group: Callable,
) -> None:
    """Handles interruption for a group conversation"""
    task = current_conversation_tasks.get(group_id)
    if not task or task.done():
        return

    # Get state and speaker info before cancellation
    state = GroupConversationState.get_state(group_id)
    current_speaker_uid = state.current_speaker_uid if state else None

    # Get context from current speaker
    context = None
    group = chat_group_manager.get_group_by_id(group_id)
    if current_speaker_uid:
        context = client_contexts.get(current_speaker_uid)
        logger.info(f"Found current speaker context for {current_speaker_uid}")
    if not context and group and group.members:
        logger.warning(f"No context found for group {group_id}, using first member")
        context = client_contexts.get(next(iter(group.members)))

    # Now cancel the task
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        logger.info(f"🛑 Group conversation {group_id} cancelled successfully.")

    current_conversation_tasks.pop(group_id, None)
    GroupConversationState.remove_state(group_id)  # Clean up state after we've used it

    # Store messages with speaker info
    if context and group:
        for member_uid in group.members:
            if member_uid in client_contexts:
                try:
                    member_ctx = client_contexts[member_uid]
                    member_ctx.agent_engine.handle_interrupt(heard_response)
                    store_message(
                        conf_uid=member_ctx.character_config.conf_uid,
                        history_uid=member_ctx.history_uid,
                        role="ai",
                        content=heard_response,
                        name=context.character_config.character_name,
                        avatar=context.character_config.avatar,
                    )
                    store_message(
                        conf_uid=member_ctx.character_config.conf_uid,
                        history_uid=member_ctx.history_uid,
                        role="system",
                        content="[Interrupted by user]",
                    )
                except Exception as e:
                    logger.error(f"Error handling interrupt for {member_uid}: {e}")

    await broadcast_to_group(
        list(group.members),
        {
            "type": "interrupt-signal",
            "text": "conversation-interrupted",
        },
    )

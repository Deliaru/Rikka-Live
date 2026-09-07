from typing import Union, List, Dict, Any, Optional
import asyncio
import json
from loguru import logger
import numpy as np

from .conversation_utils import (
    create_batch_input,
    process_agent_output,
    send_conversation_start_signals,
    process_user_input,
    finalize_conversation_turn,
    send_conversation_end_signal,
    cleanup_conversation,
    EMOJI_LIST,
)
from .types import WebSocketSend
from .tts_manager import TTSTaskManager
from ..chat_history_manager import store_message
from ..rikka.proactive import get_default_proactive_coordinator
from ..rikka.settings import get_default_settings_store, live2d_thinking_state_enabled
from ..rikka.wake_gate import get_default_wake_gate
from ..service_context import ServiceContext

# Import necessary types from agent outputs
from ..agent.output_types import SentenceOutput, AudioOutput


RIKKA_VALIDATION_DIAGNOSTIC_FIELDS = (
    "failure_kind",
    "raw_response_length",
    "raw_response_hash",
    "raw_response_excerpt",
    "raw_response_text",
    "raw_response_text_truncated",
    "raw_response_truncated",
    "repaired",
    "repair_notes",
    "fallback_reason_code",
    "fallback_spoken_preview",
    "fallback_spoken_truncated",
    "fallback_subtitle_preview",
    "fallback_subtitle_truncated",
    "attached_image_count",
    "provider_error",
    "provider_endpoint",
    "provider_status_code",
    "provider_error_detail",
    "provider_error_message",
)


def _rikka_validation_flow_metadata(
    output_item: dict[str, Any],
    validation_errors: list[Any],
) -> dict[str, Any]:
    metadata = {
        "ok": bool(output_item.get("ok")),
        "fallback": bool(output_item.get("fallback")),
        "silent": bool(output_item.get("silent")),
        "error_count": int(output_item.get("error_count") or len(validation_errors)),
        "errors": validation_errors,
    }
    for key in RIKKA_VALIDATION_DIAGNOSTIC_FIELDS:
        if key in output_item:
            metadata[key] = output_item.get(key)
    return metadata


async def process_single_conversation(
    context: ServiceContext,
    websocket_send: WebSocketSend,
    client_uid: str,
    user_input: Union[str, np.ndarray],
    images: Optional[List[Dict[str, Any]]] = None,
    session_emoji: str = np.random.choice(EMOJI_LIST),
    metadata: Optional[Dict[str, Any]] = None,
    flow_monitor: Any = None,
    flow_id: str | None = None,
) -> str:
    """Process a single-user conversation turn

    Args:
        context: Service context containing all configurations and engines
        websocket_send: WebSocket send function
        client_uid: Client unique identifier
        user_input: Text or audio input from user
        images: Optional list of image data
        session_emoji: Emoji identifier for the conversation
        metadata: Optional metadata for special processing flags

    Returns:
        str: Complete response text
    """
    # Create TTSTaskManager for this conversation
    tts_manager = TTSTaskManager()
    full_response = ""  # Initialize full_response here
    agent_error: Exception | None = None
    planner_reported_error = False
    flow_monitor = flow_monitor or (metadata or {}).get("rikka_flow_monitor")
    flow_id = flow_id or (metadata or {}).get("rikka_flow_id")
    wake_window_after_playback_ms: int | None = (
        int((metadata or {}).get("wake_window_after_playback_ms") or 0) or None
    )
    wake_client_uid = str((metadata or {}).get("wake_client_uid") or client_uid)

    try:
        # Process user input
        input_text = await process_user_input(
            user_input, context.asr_engine, websocket_send
        )
        if flow_monitor and flow_id and isinstance(user_input, np.ndarray):
            flow_monitor.record(
                flow_id,
                "normalize",
                "ok",
                detail="microphone transcript ready",
                metadata={"has_text": bool(input_text.strip())},
            )
        settings = get_default_settings_store().snapshot()
        if isinstance(user_input, np.ndarray):
            decision = get_default_wake_gate().evaluate(
                client_uid,
                input_text,
                settings.audio,
            )
            await websocket_send(
                json.dumps({"type": "wake-gate", **decision.to_dict()})
            )
            if flow_monitor and flow_id:
                flow_monitor.record(
                    flow_id,
                    "validate",
                    "ok" if decision.should_process else "skipped",
                    detail=decision.reason,
                    metadata=decision.to_flow_metadata(),
                )
            if not decision.should_process:
                if flow_monitor and flow_id:
                    flow_monitor.record(
                        flow_id,
                        "complete",
                        "skipped",
                        detail="wake gate did not accept microphone turn",
                    )
                await send_conversation_end_signal(websocket_send, None)
                return ""
            if decision.woke and decision.reason == "wake_phrase_matched":
                wake_window_after_playback_ms = settings.audio.wake_active_window_ms
            input_text = decision.text

        get_default_proactive_coordinator().mark_user_activity()

        # Send initial signals only after wake-gated microphone input is accepted.
        await send_conversation_start_signals(
            websocket_send, thinking_enabled=live2d_thinking_state_enabled()
        )
        if flow_monitor and flow_id:
            flow_monitor.record(
                flow_id,
                "planner",
                "running",
                detail="conversation chain started",
            )
        logger.info(f"New Conversation Chain {session_emoji} started!")

        # Create batch input
        batch_input = create_batch_input(
            input_text=input_text,
            images=images,
            from_name=context.character_config.human_name,
            metadata=metadata,
        )

        # Store user message (check if we should skip storing to history)
        skip_history = metadata and metadata.get("skip_history", False)
        if context.history_uid and not skip_history:
            store_message(
                conf_uid=context.character_config.conf_uid,
                history_uid=context.history_uid,
                role="human",
                content=input_text,
                name=context.character_config.human_name,
            )

        if skip_history:
            logger.debug("Skipping storing user input to history (proactive speak)")

        logger.info(f"User input: {input_text}")
        if images:
            logger.info(f"With {len(images)} images")

        try:
            # agent.chat yields Union[SentenceOutput, Dict[str, Any]]
            agent_output_stream = context.agent_engine.chat(batch_input)

            async for output_item in agent_output_stream:
                if (
                    isinstance(output_item, dict)
                    and output_item.get("type") == "tool_call_status"
                ):
                    # Handle tool status event: send WebSocket message
                    output_item["name"] = context.character_config.character_name
                    logger.debug(f"Sending tool status update: {output_item}")

                    await websocket_send(json.dumps(output_item))
                    if flow_monitor and flow_id:
                        tool_status = str(output_item.get("status") or "")
                        metadata = {
                            "tool_name": output_item.get("tool_name"),
                            "tool_kind": output_item.get("tool_kind"),
                            "status": tool_status,
                        }
                        for key in (
                            "ok",
                            "duration_ms",
                            "result_kind",
                            "result_summary",
                        ):
                            if key in output_item:
                                metadata[key] = output_item.get(key)
                        flow_monitor.record(
                            flow_id,
                            "planner",
                            "error" if tool_status == "error" else "running",
                            detail=(
                                f"tool {output_item.get('tool_name')}: {tool_status}"
                            ),
                            metadata=metadata,
                        )

                elif (
                    isinstance(output_item, dict)
                    and output_item.get("type") == "rikka_validation_status"
                ):
                    if flow_monitor and flow_id:
                        validation_ok = bool(output_item.get("ok"))
                        silent = bool(output_item.get("silent"))
                        validation_errors = output_item.get("errors") or []
                        validation_metadata = _rikka_validation_flow_metadata(
                            output_item,
                            validation_errors,
                        )
                        if not validation_ok and not silent:
                            planner_reported_error = True
                            provider_error = bool(output_item.get("provider_error"))
                            provider_status = output_item.get("provider_status_code")
                            provider_endpoint = output_item.get("provider_endpoint")
                            provider_detail = output_item.get("provider_error_detail")
                            planner_detail = (
                                f"LLM {provider_endpoint or 'provider'} call failed"
                                f"{f' with HTTP {provider_status}' if provider_status else ''}: "
                                f"{provider_detail or 'provider error'}"
                                if provider_error
                                else "LLM response invalid; fallback used"
                            )
                            flow_monitor.record(
                                flow_id,
                                "planner",
                                "error",
                                detail=planner_detail,
                                metadata=validation_metadata,
                            )
                        flow_monitor.record(
                            flow_id,
                            "validate",
                            (
                                "ok"
                                if validation_ok
                                else ("skipped" if silent else "error")
                            ),
                            detail=(
                                "Rikka response validated"
                                if validation_ok
                                else (
                                    "empty proactive response skipped"
                                    if silent
                                    else "Rikka response validation failed; fallback used"
                                )
                            ),
                            metadata=validation_metadata,
                        )

                elif isinstance(output_item, (SentenceOutput, AudioOutput)):
                    # Handle SentenceOutput or AudioOutput
                    response_part = await process_agent_output(
                        output=output_item,
                        character_config=context.character_config,
                        live2d_model=context.live2d_model,
                        tts_engine=context.tts_engine,
                        websocket_send=websocket_send,  # Pass websocket_send for audio/tts messages
                        tts_manager=tts_manager,
                        translate_engine=context.translate_engine,
                        flow_id=flow_id,
                    )
                    # Ensure response_part is treated as a string before concatenation
                    response_part_str = (
                        str(response_part) if response_part is not None else ""
                    )
                    full_response += response_part_str  # Accumulate text response
                else:
                    logger.warning(
                        f"Received unexpected item type from agent chat stream: {type(output_item)}"
                    )
                    logger.debug(f"Unexpected item content: {output_item}")

        except Exception as e:
            agent_error = e
            if flow_monitor and flow_id:
                flow_monitor.record(
                    flow_id,
                    "planner",
                    "error",
                    detail=str(e),
                )
            logger.exception(
                f"Error processing agent response stream: {e}"
            )  # Log with stack trace
            await websocket_send(
                json.dumps(
                    {
                        "type": "error",
                        "message": f"Error processing agent response: {str(e)}",
                    }
                )
            )
            # full_response will contain partial response before error
        # --- End processing agent response ---
        if (
            flow_monitor
            and flow_id
            and agent_error is None
            and not planner_reported_error
        ):
            flow_monitor.record(
                flow_id,
                "planner",
                "ok",
                detail="agent response stream completed",
                metadata={"has_response": bool(full_response.strip())},
            )

        playback_completion = await finalize_conversation_turn(
            tts_manager=tts_manager,
            websocket_send=websocket_send,
            client_uid=client_uid,
            flow_id=flow_id,
        )
        playback_completed_with_audio = (
            isinstance(playback_completion, dict)
            and playback_completion.get("status") == "ok"
            and playback_completion.get("has_audio") is True
        )
        if (
            wake_window_after_playback_ms is not None
            and agent_error is None
            and playback_completed_with_audio
        ):
            active_until = get_default_wake_gate().activate(
                wake_client_uid,
                wake_window_after_playback_ms,
            )
            await websocket_send(
                json.dumps(
                    {
                        "type": "wake-gate",
                        "active": True,
                        "should_process": True,
                        "woke": False,
                        "reason": "wake_window_started",
                        "text": "",
                        "active_until_ms": active_until,
                    }
                )
            )
        if flow_monitor and flow_id and tts_manager.task_list:
            flow_monitor.record(flow_id, "tts", "ok", detail="speech synthesized")
        if flow_monitor and flow_id:
            flow_monitor.record(
                flow_id,
                "complete",
                "error" if agent_error else "ok",
                detail=(
                    "conversation failed before response"
                    if agent_error
                    else "microphone conversation completed"
                ),
            )

        if context.history_uid and full_response:  # Check full_response before storing
            store_message(
                conf_uid=context.character_config.conf_uid,
                history_uid=context.history_uid,
                role="ai",
                content=full_response,
                name=context.character_config.character_name,
                avatar=context.character_config.avatar,
            )
            logger.info(f"AI response: {full_response}")

        return full_response  # Return accumulated full_response

    except asyncio.CancelledError:
        logger.info(f"🤡👍 Conversation {session_emoji} cancelled because interrupted.")
        raise
    except Exception as e:
        logger.error(f"Error in conversation chain: {e}")
        await websocket_send(
            json.dumps({"type": "error", "message": f"Conversation error: {str(e)}"})
        )
        raise
    finally:
        cleanup_conversation(tts_manager, session_emoji)

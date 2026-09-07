import asyncio
import json
import re
import uuid
from datetime import datetime
from typing import Any, List, Optional, Dict
from loguru import logger

from ..agent.output_types import DisplayText, Actions
from ..live2d_model import Live2dModel
from ..tts.tts_interface import TTSInterface
from ..utils.audio_tail_cleanup import process_tts_audio_tail
from ..utils.stream_audio import prepare_audio_payload
from .types import WebSocketSend


class TTSTaskManager:
    """Manages TTS tasks and ensures ordered delivery to frontend while allowing parallel TTS generation"""

    def __init__(self) -> None:
        self.task_list: List[asyncio.Task] = []
        self._lock = asyncio.Lock()
        # Queue to store ordered payloads
        self._payload_queue: asyncio.Queue[Dict] = asyncio.Queue()
        # Task to handle sending payloads in order
        self._sender_task: Optional[asyncio.Task] = None
        # Counter for maintaining order
        self._sequence_counter = 0
        self._next_sequence_to_send = 0

    async def speak(
        self,
        tts_text: str,
        display_text: DisplayText,
        actions: Optional[Actions],
        live2d_model: Live2dModel,
        tts_engine: TTSInterface,
        websocket_send: WebSocketSend,
        tts_meta: Optional[Dict[str, Any]] = None,
        flow_id: str | None = None,
    ) -> None:
        """
        Queue a TTS task while maintaining order of delivery.

        Args:
            tts_text: Text to synthesize
            display_text: Text to display in UI
            actions: Live2D model actions
            live2d_model: Live2D model instance
            tts_engine: TTS engine instance
            websocket_send: WebSocket send function
        """
        if len(re.sub(r'[\s.,!?，。！？\'"』」）】\s]+', "", tts_text)) == 0:
            logger.debug("Empty TTS text, sending silent display payload")
            # Get current sequence number for silent payload
            current_sequence = self._sequence_counter
            self._sequence_counter += 1

            # Start sender task if not running
            if not self._sender_task or self._sender_task.done():
                self._sender_task = asyncio.create_task(
                    self._process_payload_queue(websocket_send)
                )

            await self._send_silent_payload(
                display_text,
                actions,
                current_sequence,
                tts_engine,
                tts_meta,
                flow_id,
            )
            return

        logger.debug(
            f"🏃Queuing TTS task for: '''{tts_text}''' (by {display_text.name})"
        )

        # Get current sequence number
        current_sequence = self._sequence_counter
        self._sequence_counter += 1

        # Start sender task if not running
        if not self._sender_task or self._sender_task.done():
            self._sender_task = asyncio.create_task(
                self._process_payload_queue(websocket_send)
            )

        # Create and queue the TTS task
        task = asyncio.create_task(
            self._process_tts(
                tts_text=tts_text,
                display_text=display_text,
                actions=actions,
                live2d_model=live2d_model,
                tts_engine=tts_engine,
                sequence_number=current_sequence,
                tts_meta=tts_meta,
                flow_id=flow_id,
            )
        )
        self.task_list.append(task)

    async def _process_payload_queue(self, websocket_send: WebSocketSend) -> None:
        """
        Process and send payloads in correct order.
        Runs continuously until all payloads are processed.
        """
        buffered_payloads: Dict[int, Dict] = {}

        while True:
            try:
                # Get payload from queue
                payload, sequence_number = await self._payload_queue.get()
                buffered_payloads[sequence_number] = payload

                # Send payloads in order
                while self._next_sequence_to_send in buffered_payloads:
                    next_payload = buffered_payloads.pop(self._next_sequence_to_send)
                    interval_ms = int(
                        next_payload.pop("_rikka_sentence_interval_ms", 0) or 0
                    )
                    if self._next_sequence_to_send > 0 and interval_ms > 0:
                        await asyncio.sleep(interval_ms / 1000)
                    await websocket_send(json.dumps(next_payload))
                    self._next_sequence_to_send += 1

                self._payload_queue.task_done()

            except asyncio.CancelledError:
                break

    async def wait_for_payloads(self) -> None:
        """Wait until queued payloads have been handed to the websocket sender."""
        if self._sender_task and not self._sender_task.done():
            await self._payload_queue.join()

    async def _send_silent_payload(
        self,
        display_text: DisplayText,
        actions: Optional[Actions],
        sequence_number: int,
        tts_engine: TTSInterface | None = None,
        tts_meta: Optional[Dict[str, Any]] = None,
        flow_id: str | None = None,
    ) -> None:
        """Queue a silent audio payload"""
        audio_payload = prepare_audio_payload(
            audio_path=None,
            display_text=display_text,
            actions=actions,
            flow_id=flow_id,
        )
        self._attach_sentence_interval(audio_payload, tts_engine)
        self._attach_tts_meta(audio_payload, tts_meta)
        await self._payload_queue.put((audio_payload, sequence_number))

    async def _process_tts(
        self,
        tts_text: str,
        display_text: DisplayText,
        actions: Optional[Actions],
        live2d_model: Live2dModel,
        tts_engine: TTSInterface,
        sequence_number: int,
        tts_meta: Optional[Dict[str, Any]] = None,
        flow_id: str | None = None,
    ) -> None:
        """Process TTS generation and queue the result for ordered delivery"""
        audio_file_path = None
        try:
            tts_kwargs: dict[str, Any] = {}
            if tts_meta and getattr(tts_engine, "accepts_rikka_emotion_kwargs", False):
                if tts_meta.get("tts_style"):
                    tts_kwargs["tts_style"] = tts_meta["tts_style"]
                if tts_meta.get("emotion_vec"):
                    tts_kwargs["emotion_vec"] = tts_meta["emotion_vec"]
            audio_file_path = await self._generate_audio(
                tts_engine,
                tts_text,
                **tts_kwargs,
            )
            # Opt-in generated-audio tail cleanup (no-op when disabled).
            # Runs before payload prep so the cleaned file is what gets base64'd.
            cleanup_result = process_tts_audio_tail(audio_file_path)
            if cleanup_result.reason != "disabled":
                logger.debug(
                    "tts tail cleanup {}: trimmed={}ms before={}ms after={}ms "
                    "threshold_db={}".format(
                        cleanup_result.reason,
                        cleanup_result.trimmed_ms,
                        cleanup_result.before_ms,
                        cleanup_result.after_ms,
                        cleanup_result.threshold_db,
                    )
                )
            payload = prepare_audio_payload(
                audio_path=audio_file_path,
                display_text=display_text,
                actions=actions,
                flow_id=flow_id,
            )
            # Attach privacy-safe diagnostics only when the stage actually ran,
            # so payloads are byte-compatible with the unprocessed path when
            # cleanup is disabled.
            if cleanup_result.reason != "disabled":
                payload["post_process"] = {
                    "applied": cleanup_result.applied,
                    "trimmed_ms": cleanup_result.trimmed_ms,
                    "fade_ms": cleanup_result.fade_ms,
                    "reason": cleanup_result.reason,
                }
            self._attach_sentence_interval(payload, tts_engine)
            self._attach_tts_meta(payload, tts_meta)
            # Queue the payload with its sequence number
            await self._payload_queue.put((payload, sequence_number))

        except Exception as e:
            logger.error(f"Error preparing audio payload: {e}")
            # Queue silent payload for error case
            payload = prepare_audio_payload(
                audio_path=None,
                display_text=display_text,
                actions=actions,
                flow_id=flow_id,
            )
            self._attach_sentence_interval(payload, tts_engine)
            self._attach_tts_meta(payload, tts_meta)
            await self._payload_queue.put((payload, sequence_number))

        finally:
            if audio_file_path:
                tts_engine.remove_file(audio_file_path)
                logger.debug("Audio cache file cleaned.")

    async def _generate_audio(
        self,
        tts_engine: TTSInterface,
        text: str,
        **kwargs: Any,
    ) -> str:
        """Generate audio file from text"""
        logger.debug(f"🏃Generating audio for '''{text}'''...")
        return await tts_engine.async_generate_audio(
            text=text,
            file_name_no_ext=f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}",
            **kwargs,
        )

    def _attach_sentence_interval(
        self,
        payload: Dict,
        tts_engine: TTSInterface | None,
    ) -> None:
        interval_ms = int(getattr(tts_engine, "sentence_interval_ms", 0) or 0)
        if interval_ms > 0:
            payload["_rikka_sentence_interval_ms"] = interval_ms

    def _attach_tts_meta(
        self,
        payload: Dict,
        tts_meta: Optional[Dict[str, Any]],
    ) -> None:
        pre_silence_ms = int((tts_meta or {}).get("pre_silence_ms") or 0)
        if pre_silence_ms > 0:
            payload["pre_silence_ms"] = pre_silence_ms

    def clear(self) -> None:
        """Clear all pending tasks and reset state"""
        self.task_list.clear()
        if self._sender_task:
            self._sender_task.cancel()
        self._sequence_counter = 0
        self._next_sequence_to_send = 0
        # Create a new queue to clear any pending items
        self._payload_queue = asyncio.Queue()

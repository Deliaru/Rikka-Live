import asyncio
import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import numpy as np

from open_llm_vtuber.asr.asr_interface import StreamingASRResult
from open_llm_vtuber.rikka.settings import AudioInteractionSettings
from open_llm_vtuber.websocket_handler import WebSocketHandler


class FakeWebSocket:
    def __init__(self):
        self.messages = []

    async def send_text(self, message):
        self.messages.append(json.loads(message))

    async def send_json(self, message):
        self.messages.append(message)


class FakeFlowMonitor:
    def __init__(self):
        self.started = []
        self.records = []

    def start(self, flow_id, event):
        self.started.append({"flow_id": flow_id, "event": event})

    def record(self, flow_id, stage, status="ok", *, detail="", metadata=None):
        self.records.append(
            {
                "flow_id": flow_id,
                "stage": stage,
                "status": status,
                "detail": detail,
                "metadata": metadata or {},
            }
        )


class MicOwnerProtocolTests(unittest.TestCase):
    def make_handler(self, asr_disabled=False):
        asr = SimpleNamespace(SAMPLE_RATE=16000, is_disabled=asr_disabled)
        handler = WebSocketHandler.__new__(WebSocketHandler)
        handler.default_context_cache = SimpleNamespace(asr_engine=asr)
        handler.client_contexts = {
            "console": SimpleNamespace(asr_engine=asr),
            "overlay": SimpleNamespace(asr_engine=asr),
        }
        handler.client_connections = {
            "console": FakeWebSocket(),
            "overlay": FakeWebSocket(),
        }
        handler.received_data_buffers = {
            "console": np.array([], dtype=np.float32),
            "overlay": np.array([], dtype=np.float32),
        }
        handler.mic_clients = {}
        handler.client_kinds = {}
        handler.active_mic_owner_uid = None
        handler.active_mic_owner_since_ms = None
        handler.playback_guard_by_client = {}
        handler.streaming_asr_sessions = {}
        handler.rikka_settings = SimpleNamespace(
            snapshot=lambda: SimpleNamespace(
                audio=AudioInteractionSettings(wake_gate_enabled=True)
            )
        )
        handler.chat_group_manager = SimpleNamespace()
        handler.current_conversation_tasks = {}
        handler.broadcast_to_group = AsyncMock()
        handler.rikka_flow_monitor = FakeFlowMonitor()
        return handler

    def test_console_has_default_priority_over_overlay(self):
        async def run():
            handler = self.make_handler()
            await handler._handle_client_capabilities(
                handler.client_connections["overlay"],
                "overlay",
                {
                    "type": "client-capabilities",
                    "client_kind": "overlay",
                    "always_on_enabled": True,
                    "mic_permission": "granted",
                    "listening": True,
                },
            )
            await handler._handle_client_capabilities(
                handler.client_connections["console"],
                "console",
                {
                    "type": "client-capabilities",
                    "client_kind": "console",
                    "always_on_enabled": True,
                    "mic_permission": "granted",
                    "listening": True,
                },
            )
            return handler.active_mic_owner_uid

        self.assertEqual(asyncio.run(run()), "console")

    def test_overlay_explicit_owner_can_override_console(self):
        async def run():
            handler = self.make_handler()
            await handler._handle_client_capabilities(
                handler.client_connections["console"],
                "console",
                {
                    "type": "client-capabilities",
                    "client_kind": "console",
                    "always_on_enabled": True,
                    "mic_permission": "granted",
                    "listening": True,
                },
            )
            await handler._handle_client_capabilities(
                handler.client_connections["overlay"],
                "overlay",
                {
                    "type": "mic-owner-request",
                    "client_kind": "overlay",
                    "mic_permission": "granted",
                    "listening": True,
                },
            )
            return handler.active_mic_owner_uid

        self.assertEqual(asyncio.run(run()), "overlay")

    def test_streaming_partial_emits_wake_preview_without_conversation(self):
        class FakeStreamingSession:
            async def accept_audio(self, _chunk):
                return StreamingASRResult(partial="六花，晚上好")

        class FakeASR:
            SAMPLE_RATE = 16000
            is_disabled = False

            def streaming_status(self):
                return "streaming_ready"

            def create_streaming_session(self):
                return FakeStreamingSession()

        async def run():
            handler = self.make_handler()
            handler.client_contexts["console"].asr_engine = FakeASR()
            await handler._handle_client_capabilities(
                handler.client_connections["console"],
                "console",
                {
                    "type": "client-capabilities",
                    "client_kind": "console",
                    "always_on_enabled": True,
                    "mic_permission": "granted",
                    "listening": True,
                },
            )
            await handler._handle_client_capabilities(
                handler.client_connections["overlay"],
                "overlay",
                {
                    "type": "client-capabilities",
                    "client_kind": "overlay",
                    "always_on_enabled": False,
                    "mic_permission": "unknown",
                    "listening": False,
                },
            )
            with patch(
                "open_llm_vtuber.websocket_handler.handle_conversation_trigger",
                new=AsyncMock(),
            ) as trigger:
                await handler._handle_audio_data(
                    handler.client_connections["console"],
                    "console",
                    {
                        "type": "mic-audio-data",
                        "audio": [0.1] * 160,
                        "sample_rate": 16000,
                    },
                )
                return handler.client_connections["console"].messages, trigger.await_count

        messages, trigger_count = asyncio.run(run())
        self.assertEqual(trigger_count, 0)
        self.assertTrue(
            any(message.get("type") == "asr-streaming-partial" for message in messages)
        )
        wake_messages = [message for message in messages if message.get("type") == "wake-gate"]
        self.assertTrue(any(message.get("source") == "partial" for message in wake_messages))
        self.assertTrue(any(message.get("reason") == "wake_phrase_matched" for message in wake_messages))
        self.assertTrue(any(message.get("match_kind") == "canonical" for message in wake_messages))

    def test_streaming_final_accepted_triggers_conversation_once(self):
        class FakeStreamingSession:
            async def accept_audio(self, _chunk):
                return StreamingASRResult(final="六花，继续解释一下", endpoint=True)

        class FakeASR:
            SAMPLE_RATE = 16000
            is_disabled = False

            def streaming_status(self):
                return "streaming_ready"

            def create_streaming_session(self):
                return FakeStreamingSession()

        async def run():
            handler = self.make_handler()
            handler.client_contexts["console"].asr_engine = FakeASR()
            await handler._handle_client_capabilities(
                handler.client_connections["console"],
                "console",
                {
                    "type": "client-capabilities",
                    "client_kind": "console",
                    "always_on_enabled": True,
                    "mic_permission": "granted",
                    "listening": True,
                },
            )
            await handler._handle_client_capabilities(
                handler.client_connections["overlay"],
                "overlay",
                {
                    "type": "client-capabilities",
                    "client_kind": "overlay",
                    "always_on_enabled": False,
                    "mic_permission": "unknown",
                    "listening": False,
                },
            )
            with patch(
                "open_llm_vtuber.websocket_handler.handle_conversation_trigger",
                new=AsyncMock(),
            ) as trigger:
                await handler._handle_audio_data(
                    handler.client_connections["console"],
                    "console",
                    {
                        "type": "mic-audio-data",
                        "audio": [0.1] * 160,
                        "sample_rate": 16000,
                    },
                )
                return (
                    handler.client_connections["console"].messages,
                    trigger,
                    handler.rikka_flow_monitor.records,
                )

        messages, trigger, records = asyncio.run(run())
        self.assertEqual(trigger.await_count, 1)
        _, kwargs = trigger.await_args
        self.assertEqual(kwargs["msg_type"], "text-input")
        self.assertEqual(kwargs["client_uid"], "overlay")
        self.assertEqual(kwargs["data"]["text"], "继续解释一下")
        self.assertTrue(kwargs["data"]["metadata"]["rikka_flow_id"].startswith("mic-"))
        self.assertEqual(kwargs["data"]["metadata"]["wake_client_uid"], "console")
        self.assertTrue(
            any(
                message.get("type") == "wake-gate"
                and message.get("source") == "final"
                and message.get("should_process") is True
                and message.get("match_kind") == "canonical"
                for message in messages
            )
        )
        self.assertTrue(
            any(
                record["stage"] == "validate"
                and record["metadata"].get("match_kind") == "canonical"
                for record in records
            )
        )

    def test_streaming_final_accepts_asr_confusion_alias(self):
        class FakeStreamingSession:
            async def accept_audio(self, _chunk):
                return StreamingASRResult(final="柳华，继续解释一下", endpoint=True)

        class FakeASR:
            SAMPLE_RATE = 16000
            is_disabled = False

            def streaming_status(self):
                return "streaming_ready"

            def create_streaming_session(self):
                return FakeStreamingSession()

        async def run():
            handler = self.make_handler()
            handler.client_contexts["console"].asr_engine = FakeASR()
            await handler._handle_client_capabilities(
                handler.client_connections["console"],
                "console",
                {
                    "type": "client-capabilities",
                    "client_kind": "console",
                    "always_on_enabled": True,
                    "mic_permission": "granted",
                    "listening": True,
                },
            )
            await handler._handle_client_capabilities(
                handler.client_connections["overlay"],
                "overlay",
                {
                    "type": "client-capabilities",
                    "client_kind": "overlay",
                    "always_on_enabled": False,
                    "mic_permission": "unknown",
                    "listening": False,
                },
            )
            with patch(
                "open_llm_vtuber.websocket_handler.handle_conversation_trigger",
                new=AsyncMock(),
            ) as trigger:
                await handler._handle_audio_data(
                    handler.client_connections["console"],
                    "console",
                    {
                        "type": "mic-audio-data",
                        "audio": [0.1] * 160,
                        "sample_rate": 16000,
                    },
                )
                return (
                    handler.client_connections["console"].messages,
                    trigger,
                    handler.rikka_flow_monitor.records,
                )

        messages, trigger, records = asyncio.run(run())
        self.assertEqual(trigger.await_count, 1)
        _, kwargs = trigger.await_args
        self.assertEqual(kwargs["data"]["text"], "继续解释一下")
        self.assertTrue(
            any(
                message.get("type") == "wake-gate"
                and message.get("source") == "final"
                and message.get("match_kind") == "asr_confusion"
                and message.get("matched_phrase") == "柳华"
                for message in messages
            )
        )
        self.assertTrue(
            any(
                record["stage"] == "validate"
                and record["metadata"].get("match_kind") == "asr_confusion"
                for record in records
            )
        )

    def test_console_streaming_final_targets_overlay_response_client(self):
        async def run():
            handler = self.make_handler()
            await handler._handle_client_capabilities(
                handler.client_connections["console"],
                "console",
                {
                    "type": "client-capabilities",
                    "client_kind": "console",
                    "always_on_enabled": True,
                    "mic_permission": "granted",
                    "listening": True,
                },
            )
            await handler._handle_client_capabilities(
                handler.client_connections["overlay"],
                "overlay",
                {
                    "type": "client-capabilities",
                    "client_kind": "overlay",
                    "always_on_enabled": False,
                    "mic_permission": "unknown",
                    "listening": False,
                },
            )
            with patch(
                "open_llm_vtuber.websocket_handler.handle_conversation_trigger",
                new=AsyncMock(),
            ) as trigger:
                await handler._handle_streaming_final(
                    handler.client_connections["console"],
                    "console",
                    "六花，继续解释一下",
                )
                return (
                    handler.client_connections["console"].messages,
                    handler.client_connections["overlay"].messages,
                    trigger,
                )

        console_messages, overlay_messages, trigger = asyncio.run(run())
        self.assertEqual(trigger.await_count, 1)
        _, kwargs = trigger.await_args
        self.assertEqual(kwargs["client_uid"], "overlay")
        self.assertIs(kwargs["websocket"], kwargs["client_connections"]["overlay"])
        self.assertEqual(kwargs["data"]["text"], "继续解释一下")
        self.assertTrue(kwargs["data"]["metadata"]["rikka_flow_id"].startswith("mic-"))
        self.assertEqual(kwargs["data"]["metadata"]["wake_client_uid"], "console")
        self.assertTrue(
            any(message.get("type") == "asr-response-target" for message in console_messages)
        )
        self.assertTrue(
            any(message.get("type") == "wake-gate" for message in overlay_messages)
        )

    def test_console_streaming_final_without_overlay_reports_no_response_target(self):
        async def run():
            handler = self.make_handler()
            handler.client_connections.pop("overlay")
            handler.client_contexts.pop("overlay")
            await handler._handle_client_capabilities(
                handler.client_connections["console"],
                "console",
                {
                    "type": "client-capabilities",
                    "client_kind": "console",
                    "always_on_enabled": True,
                    "mic_permission": "granted",
                    "listening": True,
                },
            )
            with patch(
                "open_llm_vtuber.websocket_handler.handle_conversation_trigger",
                new=AsyncMock(),
            ) as trigger:
                await handler._handle_streaming_final(
                    handler.client_connections["console"],
                    "console",
                    "六花，继续解释一下",
                )
                return handler.client_connections["console"].messages, trigger

        messages, trigger = asyncio.run(run())
        self.assertEqual(trigger.await_count, 0)
        self.assertTrue(
            any(
                message.get("type") == "error"
                and "no Overlay/Live2D" in message.get("message", "")
                for message in messages
            )
        )

    def test_non_owner_audio_chunk_is_ignored(self):
        async def run():
            handler = self.make_handler()
            await handler._handle_client_capabilities(
                handler.client_connections["console"],
                "console",
                {
                    "type": "client-capabilities",
                    "client_kind": "console",
                    "always_on_enabled": True,
                    "mic_permission": "granted",
                    "listening": True,
                },
            )
            await handler._handle_client_capabilities(
                handler.client_connections["overlay"],
                "overlay",
                {
                    "type": "client-capabilities",
                    "client_kind": "overlay",
                    "always_on_enabled": True,
                    "mic_permission": "granted",
                    "listening": True,
                },
            )
            await handler._handle_audio_data(
                handler.client_connections["overlay"],
                "overlay",
                {"type": "mic-audio-data", "audio": [0.1, 0.2], "sample_rate": 16000},
            )
            return handler.received_data_buffers["overlay"], handler.client_connections["overlay"].messages

        buffer, messages = asyncio.run(run())
        self.assertEqual(len(buffer), 0)
        self.assertTrue(
            any(message.get("reason") == "non_owner_audio_ignored" for message in messages)
        )

    def test_disabled_asr_does_not_assign_owner(self):
        async def run():
            handler = self.make_handler(asr_disabled=True)
            await handler._handle_client_capabilities(
                handler.client_connections["console"],
                "console",
                {
                    "type": "client-capabilities",
                    "client_kind": "console",
                    "always_on_enabled": True,
                    "mic_permission": "granted",
                    "listening": True,
                },
            )
            return handler.active_mic_owner_uid, handler.client_connections["console"].messages[-1]

        owner, message = asyncio.run(run())
        self.assertIsNone(owner)
        self.assertEqual(message["streaming_status"], "asr_disabled")

    def test_owner_release_promotes_next_eligible_client(self):
        async def run():
            handler = self.make_handler()
            await handler._handle_client_capabilities(
                handler.client_connections["console"],
                "console",
                {
                    "type": "client-capabilities",
                    "client_kind": "console",
                    "always_on_enabled": True,
                    "mic_permission": "granted",
                    "listening": True,
                },
            )
            await handler._handle_client_capabilities(
                handler.client_connections["overlay"],
                "overlay",
                {
                    "type": "client-capabilities",
                    "client_kind": "overlay",
                    "always_on_enabled": True,
                    "mic_permission": "granted",
                    "listening": True,
                },
            )
            await handler._handle_mic_owner_release(
                handler.client_connections["console"],
                "console",
                {"type": "mic-owner-release"},
            )
            return handler.active_mic_owner_uid

        self.assertEqual(asyncio.run(run()), "overlay")


if __name__ == "__main__":
    unittest.main()

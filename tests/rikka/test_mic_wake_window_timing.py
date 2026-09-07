import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

from open_llm_vtuber.conversations.single_conversation import process_single_conversation
from open_llm_vtuber.rikka.settings import AudioInteractionSettings
from open_llm_vtuber.rikka.wake_gate import WakeGate


class FakeASR:
    async def async_transcribe_np(self, _audio):
        return "六花，晚上好"


class FakeAliasASR:
    async def async_transcribe_np(self, _audio):
        return "柳华，晚上好"


class FakeAgent:
    async def chat(self, _batch_input):
        if False:
            yield None


class FakeFlowMonitor:
    def __init__(self):
        self.records = []

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


class MicWakeWindowTimingTests(unittest.IsolatedAsyncioTestCase):
    async def test_followup_window_starts_after_playback_finalize(self):
        now = 1000
        gate = WakeGate(clock_ms=lambda: now)
        flow = FakeFlowMonitor()
        settings = SimpleNamespace(
            audio=AudioInteractionSettings(
                wake_gate_enabled=True,
                wake_active_window_ms=18000,
            )
        )
        sent_messages: list[dict] = []

        async def websocket_send(message: str) -> None:
            sent_messages.append(json.loads(message))

        async def finalize_after_playback(**_kwargs) -> dict:
            self.assertFalse(gate.status("client")["active"])
            return {"type": "frontend-playback-complete", "status": "ok", "has_audio": True}

        context = SimpleNamespace(
            asr_engine=FakeASR(),
            agent_engine=FakeAgent(),
            character_config=SimpleNamespace(
                human_name="Deliaru",
                character_name="弥生月六花",
                avatar="",
                conf_uid="rikka_live_001",
            ),
            history_uid=None,
            live2d_model=None,
            tts_engine=None,
            translate_engine=None,
        )

        with (
            patch(
                "open_llm_vtuber.conversations.single_conversation."
                "get_default_wake_gate",
                return_value=gate,
            ),
            patch(
                "open_llm_vtuber.conversations.single_conversation."
                "get_default_settings_store",
                return_value=SimpleNamespace(snapshot=lambda: settings),
            ),
            patch(
                "open_llm_vtuber.conversations.single_conversation."
                "get_default_proactive_coordinator",
                return_value=SimpleNamespace(mark_user_activity=lambda: None),
            ),
            patch(
                "open_llm_vtuber.conversations.single_conversation."
                "finalize_conversation_turn",
                side_effect=finalize_after_playback,
            ),
        ):
            await process_single_conversation(
                context=context,
                websocket_send=websocket_send,
                client_uid="client",
                user_input=np.array([0.0], dtype=np.float32),
                flow_monitor=flow,
                flow_id="mic-flow",
            )

        wake_messages = [
            message for message in sent_messages if message.get("type") == "wake-gate"
        ]
        self.assertEqual(wake_messages[0]["reason"], "wake_phrase_matched")
        self.assertEqual(wake_messages[0]["match_kind"], "canonical")
        self.assertFalse(wake_messages[0]["active"])
        self.assertEqual(wake_messages[-1]["reason"], "wake_window_started")
        self.assertTrue(wake_messages[-1]["active"])
        self.assertTrue(gate.status("client")["active"])
        validate_records = [
            record for record in flow.records if record["stage"] == "validate"
        ]
        self.assertTrue(
            any(
                record["metadata"].get("match_kind") == "canonical"
                for record in validate_records
            )
        )
        planner_records = [
            record for record in flow.records if record["stage"] == "planner"
        ]
        self.assertEqual(
            [record["status"] for record in planner_records],
            ["running", "ok"],
        )

    async def test_non_streaming_asr_confusion_alias_starts_followup_after_playback(self):
        gate = WakeGate(clock_ms=lambda: 1000)
        flow = FakeFlowMonitor()
        settings = SimpleNamespace(
            audio=AudioInteractionSettings(
                wake_gate_enabled=True,
                wake_active_window_ms=18000,
            )
        )
        sent_messages: list[dict] = []

        async def websocket_send(message: str) -> None:
            sent_messages.append(json.loads(message))

        async def finalize_after_playback(**_kwargs) -> dict:
            self.assertFalse(gate.status("client")["active"])
            return {"type": "frontend-playback-complete", "status": "ok", "has_audio": True}

        context = SimpleNamespace(
            asr_engine=FakeAliasASR(),
            agent_engine=FakeAgent(),
            character_config=SimpleNamespace(
                human_name="Deliaru",
                character_name="弥生月六花",
                avatar="",
                conf_uid="rikka_live_001",
            ),
            history_uid=None,
            live2d_model=None,
            tts_engine=None,
            translate_engine=None,
        )

        with (
            patch(
                "open_llm_vtuber.conversations.single_conversation."
                "get_default_wake_gate",
                return_value=gate,
            ),
            patch(
                "open_llm_vtuber.conversations.single_conversation."
                "get_default_settings_store",
                return_value=SimpleNamespace(snapshot=lambda: settings),
            ),
            patch(
                "open_llm_vtuber.conversations.single_conversation."
                "get_default_proactive_coordinator",
                return_value=SimpleNamespace(mark_user_activity=lambda: None),
            ),
            patch(
                "open_llm_vtuber.conversations.single_conversation."
                "finalize_conversation_turn",
                side_effect=finalize_after_playback,
            ),
        ):
            await process_single_conversation(
                context=context,
                websocket_send=websocket_send,
                client_uid="client",
                user_input=np.array([0.0], dtype=np.float32),
                flow_monitor=flow,
                flow_id="mic-flow",
            )

        wake_messages = [
            message for message in sent_messages if message.get("type") == "wake-gate"
        ]
        self.assertEqual(wake_messages[0]["match_kind"], "asr_confusion")
        self.assertEqual(wake_messages[0]["matched_phrase"], "柳华")
        self.assertEqual(wake_messages[0]["text"], "晚上好")
        self.assertEqual(wake_messages[-1]["reason"], "wake_window_started")
        self.assertTrue(gate.status("client")["active"])
        self.assertTrue(
            any(
                record["stage"] == "validate"
                and record["metadata"].get("match_kind") == "asr_confusion"
                for record in flow.records
            )
        )

    async def test_streaming_metadata_window_starts_for_mic_source_client(self):
        now = 1000
        gate = WakeGate(clock_ms=lambda: now)
        settings = SimpleNamespace(audio=AudioInteractionSettings())
        sent_messages: list[dict] = []

        async def websocket_send(message: str) -> None:
            sent_messages.append(json.loads(message))

        async def finalize_after_playback(**_kwargs) -> dict:
            self.assertFalse(gate.status("console")["active"])
            self.assertFalse(gate.status("overlay")["active"])
            return {"type": "frontend-playback-complete", "status": "ok", "has_audio": True}

        context = SimpleNamespace(
            asr_engine=FakeASR(),
            agent_engine=FakeAgent(),
            character_config=SimpleNamespace(
                human_name="Deliaru",
                character_name="弥生月六花",
                avatar="",
                conf_uid="rikka_live_001",
            ),
            history_uid=None,
            live2d_model=None,
            tts_engine=None,
            translate_engine=None,
        )

        with (
            patch(
                "open_llm_vtuber.conversations.single_conversation."
                "get_default_wake_gate",
                return_value=gate,
            ),
            patch(
                "open_llm_vtuber.conversations.single_conversation."
                "get_default_settings_store",
                return_value=SimpleNamespace(snapshot=lambda: settings),
            ),
            patch(
                "open_llm_vtuber.conversations.single_conversation."
                "get_default_proactive_coordinator",
                return_value=SimpleNamespace(mark_user_activity=lambda: None),
            ),
            patch(
                "open_llm_vtuber.conversations.single_conversation."
                "finalize_conversation_turn",
                side_effect=finalize_after_playback,
            ),
        ):
            await process_single_conversation(
                context=context,
                websocket_send=websocket_send,
                client_uid="overlay",
                user_input="晚上好",
                metadata={
                    "wake_client_uid": "console",
                    "wake_window_after_playback_ms": 18000,
                },
            )

        wake_messages = [
            message for message in sent_messages if message.get("type") == "wake-gate"
        ]
        self.assertEqual(wake_messages[-1]["reason"], "wake_window_started")
        self.assertTrue(gate.status("console")["active"])
        self.assertFalse(gate.status("overlay")["active"])

    async def test_streaming_metadata_window_waits_for_successful_audio_playback(self):
        gate = WakeGate(clock_ms=lambda: 1000)
        settings = SimpleNamespace(audio=AudioInteractionSettings())
        sent_messages: list[dict] = []

        async def websocket_send(message: str) -> None:
            sent_messages.append(json.loads(message))

        async def playback_rejected(**_kwargs) -> dict:
            return {
                "type": "frontend-playback-complete",
                "status": "error",
                "has_audio": True,
            }

        context = SimpleNamespace(
            asr_engine=FakeASR(),
            agent_engine=FakeAgent(),
            character_config=SimpleNamespace(
                human_name="Deliaru",
                character_name="弥生月六花",
                avatar="",
                conf_uid="rikka_live_001",
            ),
            history_uid=None,
            live2d_model=None,
            tts_engine=None,
            translate_engine=None,
        )

        with (
            patch(
                "open_llm_vtuber.conversations.single_conversation."
                "get_default_wake_gate",
                return_value=gate,
            ),
            patch(
                "open_llm_vtuber.conversations.single_conversation."
                "get_default_settings_store",
                return_value=SimpleNamespace(snapshot=lambda: settings),
            ),
            patch(
                "open_llm_vtuber.conversations.single_conversation."
                "get_default_proactive_coordinator",
                return_value=SimpleNamespace(mark_user_activity=lambda: None),
            ),
            patch(
                "open_llm_vtuber.conversations.single_conversation."
                "finalize_conversation_turn",
                side_effect=playback_rejected,
            ),
        ):
            await process_single_conversation(
                context=context,
                websocket_send=websocket_send,
                client_uid="overlay",
                user_input="晚上好",
                metadata={
                    "wake_client_uid": "console",
                    "wake_window_after_playback_ms": 18000,
                },
            )

        self.assertFalse(gate.status("console")["active"])
        self.assertFalse(
            any(
                message.get("reason") == "wake_window_started"
                for message in sent_messages
            )
        )


if __name__ == "__main__":
    unittest.main()

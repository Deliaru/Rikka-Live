import json
import unittest
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from open_llm_vtuber.agent.output_types import Actions, DisplayText
from open_llm_vtuber.conversations.conversation_utils import finalize_conversation_turn
from open_llm_vtuber.conversations.tts_manager import TTSTaskManager


class TTSTaskManagerTests(unittest.IsolatedAsyncioTestCase):
    async def test_silent_payload_can_be_drained_before_clear(self):
        manager = TTSTaskManager()
        sent_messages: list[str] = []

        async def send_message(message: str) -> None:
            sent_messages.append(message)

        await manager.speak(
            tts_text="。",
            display_text=DisplayText(text="表情映射测试。", name="Rikka"),
            actions=Actions(expressions=[7]),
            live2d_model=None,
            tts_engine=None,
            websocket_send=send_message,
        )
        await manager.wait_for_payloads()
        manager.clear()

        self.assertEqual(len(sent_messages), 1)
        payload = json.loads(sent_messages[0])
        self.assertEqual(payload["type"], "audio")
        self.assertIsNone(payload["audio"])
        self.assertEqual(payload["actions"]["expressions"], [7])

    async def test_silent_payload_can_carry_pre_silence_metadata(self):
        manager = TTSTaskManager()
        sent_messages: list[str] = []

        async def send_message(message: str) -> None:
            sent_messages.append(message)

        await manager.speak(
            tts_text="。",
            display_text=DisplayText(text="稍后显示。", name="Rikka"),
            actions=Actions(),
            live2d_model=None,
            tts_engine=None,
            websocket_send=send_message,
            tts_meta={"pre_silence_ms": 800},
        )
        await manager.wait_for_payloads()
        manager.clear()

        payload = json.loads(sent_messages[0])
        self.assertEqual(payload["pre_silence_ms"], 800)

    async def test_emotion_kwargs_only_pass_to_marked_tts_engine(self):
        class MarkedEngine:
            accepts_rikka_emotion_kwargs = True

            def __init__(self):
                self.kwargs = None
                self.sentence_interval_ms = 0

            async def async_generate_audio(self, text, file_name_no_ext=None, **kwargs):
                self.kwargs = kwargs
                return "cache/test.wav"

            def remove_file(self, _path):
                return None

        manager = TTSTaskManager()
        sent_messages: list[str] = []
        engine = MarkedEngine()

        async def send_message(message: str) -> None:
            sent_messages.append(message)

        await manager.speak(
            tts_text="你好",
            display_text=DisplayText(text="你好", name="Rikka"),
            actions=Actions(),
            live2d_model=None,
            tts_engine=engine,
            websocket_send=send_message,
            tts_meta={"emotion_vec": {"happy": 0.12}},
        )
        await asyncio.gather(*manager.task_list)
        await manager.wait_for_payloads()
        manager.clear()

        self.assertEqual(engine.kwargs, {"emotion_vec": {"happy": 0.12}})

    async def test_emotion_kwargs_not_passed_to_unmarked_tts_engine(self):
        class UnmarkedEngine:
            def __init__(self):
                self.called = False
                self.sentence_interval_ms = 0

            async def async_generate_audio(self, text, file_name_no_ext=None):
                self.called = True
                return "cache/test.wav"

            def remove_file(self, _path):
                return None

        manager = TTSTaskManager()
        sent_messages: list[str] = []
        engine = UnmarkedEngine()

        async def send_message(message: str) -> None:
            sent_messages.append(message)

        await manager.speak(
            tts_text="你好",
            display_text=DisplayText(text="你好", name="Rikka"),
            actions=Actions(),
            live2d_model=None,
            tts_engine=engine,
            websocket_send=send_message,
            tts_meta={"emotion_vec": {"happy": 0.12}},
        )
        await asyncio.gather(*manager.task_list)
        await manager.wait_for_payloads()
        manager.clear()

        self.assertTrue(engine.called)

    async def test_finalize_drains_payloads_and_sends_single_synth_complete(self):
        sent_messages: list[str] = []

        async def send_message(message: str) -> None:
            sent_messages.append(message)

        completed_task = asyncio.create_task(asyncio.sleep(0))
        manager = SimpleNamespace(
            task_list=[completed_task],
            wait_for_payloads=AsyncMock(),
        )

        completion = {"type": "frontend-playback-complete", "status": "ok", "has_audio": True}

        with patch(
            "open_llm_vtuber.conversations.conversation_utils."
            "message_handler.wait_for_response",
            new=AsyncMock(return_value=completion),
        ):
            result = await finalize_conversation_turn(
                tts_manager=manager,
                websocket_send=send_message,
                client_uid="client",
            )

        self.assertEqual(result, completion)
        manager.wait_for_payloads.assert_awaited_once()
        payloads = [json.loads(message) for message in sent_messages]
        self.assertEqual(
            [payload for payload in payloads if payload.get("type") == "backend-synth-complete"],
            [{"type": "backend-synth-complete"}],
        )
        self.assertEqual(payloads[-1], {"type": "control", "text": "conversation-chain-end"})


if __name__ == "__main__":
    unittest.main()

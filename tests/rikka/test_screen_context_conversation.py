import asyncio
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import numpy as np

from open_llm_vtuber.agent.agents.basic_memory_agent import BasicMemoryAgent
from open_llm_vtuber.agent.input_types import (
    BatchInput,
    ImageData,
    ImageSource,
    TextData,
    TextSource,
)
from open_llm_vtuber.chat_group import ChatGroupManager
from open_llm_vtuber.conversations.conversation_handler import (
    handle_conversation_trigger,
)
from open_llm_vtuber.rikka.capture import WindowCaptureService
from open_llm_vtuber.rikka.settings import RikkaSettingsStore


class FakeWebSocket:
    async def send_text(self, _text):
        return None


class FakeFlowMonitor:
    def __init__(self):
        self.started = []
        self.records = []

    def start(self, flow_id, event):
        self.started.append((flow_id, event))
        return {"id": flow_id}

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


class ScreenContextConversationTests(unittest.TestCase):
    def test_text_turn_attaches_latest_screen_keyframe(self):
        async def run():
            tmp_dir = tempfile.TemporaryDirectory()
            self.addCleanup(tmp_dir.cleanup)
            store = RikkaSettingsStore(Path(tmp_dir.name) / "settings.json")
            store.update({"keyframe_upload_enabled": True})
            capture = WindowCaptureService(settings_store=store)
            capture.ingest_keyframe(
                "ZmFrZS1pbWFnZQ==",
                reason="unit_test_screen",
                mime_type="image/jpeg",
            )
            task_map = {}
            single = AsyncMock(return_value="ok")
            with (
                patch(
                    "open_llm_vtuber.conversations.conversation_handler."
                    "get_default_settings_store",
                    return_value=store,
                ),
                patch(
                    "open_llm_vtuber.conversations.conversation_handler."
                    "get_default_capture_service",
                    return_value=capture,
                ),
                patch(
                    "open_llm_vtuber.conversations.conversation_handler."
                    "process_single_conversation",
                    single,
                ),
            ):
                await handle_conversation_trigger(
                    msg_type="text-input",
                    data={"type": "text-input", "text": "看看现在画面"},
                    client_uid="client",
                    context=SimpleNamespace(),
                    websocket=FakeWebSocket(),
                    client_contexts={"client": SimpleNamespace()},
                    client_connections={"client": FakeWebSocket()},
                    chat_group_manager=ChatGroupManager(),
                    received_data_buffers={"client": np.array([])},
                    current_conversation_tasks=task_map,
                    broadcast_to_group=AsyncMock(),
                )
                await task_map["client"]

            kwargs = single.await_args.kwargs
            self.assertEqual(kwargs["images"][0]["source"], "screen")
            self.assertTrue(kwargs["images"][0]["data"].startswith("data:image/jpeg"))
            self.assertEqual(kwargs["metadata"]["screen_context"], "attached")
            self.assertTrue(kwargs["metadata"]["raw_media_attached"])

        asyncio.run(run())

    def test_mic_turn_creates_privacy_safe_debug_flow(self):
        async def run():
            tmp_dir = tempfile.TemporaryDirectory()
            self.addCleanup(tmp_dir.cleanup)
            store = RikkaSettingsStore(Path(tmp_dir.name) / "settings.json")
            store.update({"keyframe_upload_enabled": False})
            capture = WindowCaptureService(settings_store=store)
            flow = FakeFlowMonitor()
            task_map = {}
            single = AsyncMock(return_value="ok")
            with (
                patch(
                    "open_llm_vtuber.conversations.conversation_handler."
                    "get_default_settings_store",
                    return_value=store,
                ),
                patch(
                    "open_llm_vtuber.conversations.conversation_handler."
                    "get_default_capture_service",
                    return_value=capture,
                ),
                patch(
                    "open_llm_vtuber.conversations.conversation_handler."
                    "process_single_conversation",
                    single,
                ),
            ):
                await handle_conversation_trigger(
                    msg_type="mic-audio-end",
                    data={"type": "mic-audio-end"},
                    client_uid="client",
                    context=SimpleNamespace(),
                    websocket=FakeWebSocket(),
                    client_contexts={"client": SimpleNamespace()},
                    client_connections={"client": FakeWebSocket()},
                    chat_group_manager=ChatGroupManager(),
                    received_data_buffers={
                        "client": np.array([0.1, 0.2], dtype=np.float32)
                    },
                    current_conversation_tasks=task_map,
                    broadcast_to_group=AsyncMock(),
                    flow_monitor=flow,
                )
                await task_map["client"]

            kwargs = single.await_args.kwargs
            self.assertTrue(flow.started[0][0].startswith("mic-"))
            self.assertEqual(flow.started[0][1]["source"], "mic")
            self.assertEqual(flow.records[0]["stage"], "normalize")
            self.assertEqual(flow.records[0]["metadata"]["sample_count"], 2)
            self.assertEqual(kwargs["flow_id"], flow.started[0][0])
            self.assertIs(kwargs["flow_monitor"], flow)
            self.assertEqual(
                kwargs["metadata"]["rikka_flow_id"],
                flow.started[0][0],
            )
            self.assertNotIn("rikka_flow_monitor", kwargs["metadata"])

        asyncio.run(run())

    def test_basic_memory_agent_converts_screen_data_url_to_image_message(self):
        agent = BasicMemoryAgent(
            llm=SimpleNamespace(),
            system="system",
            live2d_model=SimpleNamespace(),
        )
        messages = agent._to_messages(
            BatchInput(
                texts=[
                    TextData(
                        source=TextSource.INPUT,
                        content="看看画面",
                        from_name="host",
                    )
                ],
                images=[
                    ImageData(
                        source=ImageSource.SCREEN,
                        data="data:image/jpeg;base64,ZmFrZQ==",
                        mime_type="image/jpeg",
                    )
                ],
            )
        )

        content = messages[-1]["content"]
        self.assertEqual(content[0]["type"], "text")
        self.assertEqual(content[1]["type"], "image_url")
        self.assertEqual(
            content[1]["image_url"]["url"],
            "data:image/jpeg;base64,ZmFrZQ==",
        )


if __name__ == "__main__":
    unittest.main()

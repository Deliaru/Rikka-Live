import asyncio
import base64
import tempfile
import unittest
from contextlib import suppress
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from PIL import Image

from open_llm_vtuber.rikka.capture import (
    CapturedFrame,
    WindowCaptureService,
    WindowInfo,
)
from open_llm_vtuber.rikka.proactive import ProactiveCoordinator
from open_llm_vtuber.rikka.settings import RikkaSettingsStore
from open_llm_vtuber.websocket_handler import MicClientState, WebSocketHandler


class FakeEnumerator:
    is_available = True

    def unavailable_reason(self):
        return ""

    def list_windows(self):
        return [
            WindowInfo(
                handle=42,
                title="Minecraft 1.21",
                process_name="javaw.exe",
                bounds=(0, 0, 800, 600),
            )
        ]

    def capture_window(self, window, settings):
        return CapturedFrame(
            data_base64="ZmFrZS1mcmFtZQ==",
            mime_type="image/jpeg",
            captured_at_ms=123456,
            window=window,
            width=800,
            height=600,
        )


def image_b64(color):
    image = Image.new("RGB", (32, 18), color)
    out = BytesIO()
    image.save(out, format="JPEG")
    return base64.b64encode(out.getvalue()).decode("ascii")


class MutableFrameEnumerator(FakeEnumerator):
    def __init__(self):
        self.frame_b64 = image_b64((0, 0, 0))

    def capture_window(self, window, settings):
        return CapturedFrame(
            data_base64=self.frame_b64,
            mime_type="image/jpeg",
            captured_at_ms=123456,
            window=window,
            width=32,
            height=18,
        )


class FakeWebSocket:
    async def send_text(self, _text):
        return None


class ProactiveSchedulerTests(unittest.TestCase):
    def make_handler(self, clock_ms=lambda: 500000):
        tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(tmp_dir.cleanup)
        store = RikkaSettingsStore(Path(tmp_dir.name) / "settings.json")
        capture = WindowCaptureService(
            settings_store=store,
            enumerator=FakeEnumerator(),
        )
        proactive = ProactiveCoordinator(clock_ms=clock_ms)
        proactive.last_user_activity_ms = 0
        handler = WebSocketHandler(
            default_context_cache=None,
            settings_store=store,
            capture_service=capture,
            proactive_coordinator=proactive,
        )
        handler.client_connections["client"] = FakeWebSocket()
        handler.client_contexts["client"] = SimpleNamespace()
        return handler, store, capture, proactive

    def make_handler_with_enumerator(self, enumerator, clock_ms=lambda: 500000):
        tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(tmp_dir.cleanup)
        store = RikkaSettingsStore(Path(tmp_dir.name) / "settings.json")
        capture = WindowCaptureService(
            settings_store=store,
            enumerator=enumerator,
        )
        proactive = ProactiveCoordinator(clock_ms=clock_ms)
        proactive.last_user_activity_ms = 0
        handler = WebSocketHandler(
            default_context_cache=None,
            settings_store=store,
            capture_service=capture,
            proactive_coordinator=proactive,
        )
        handler.client_connections["client"] = FakeWebSocket()
        handler.client_contexts["client"] = SimpleNamespace()
        return handler, store, capture, proactive

    def test_scheduler_triggers_screen_comment_with_keyframe(self):
        async def run():
            handler, store, capture, proactive = self.make_handler()
            store.update(
                {
                    "screen_capture_enabled": True,
                    "keyframe_upload_enabled": True,
                    "capture": {
                        "enabled": True,
                        "window_title_allowlist": ["Minecraft"],
                    },
                    "proactive": {
                        "screen_comments_enabled": True,
                        "screen_comment_cooldown_ms": 10000,
                        "min_user_idle_ms": 5000,
                    },
                }
            )
            trigger = AsyncMock()
            handler.rikka_flow_monitor = object()
            with patch(
                "open_llm_vtuber.websocket_handler.handle_conversation_trigger",
                trigger,
            ):
                result = await handler.tick_proactive_once()

            self.assertTrue(result["triggered"])
            self.assertEqual(result["kind"], "screen_comment")
            self.assertIsNotNone(capture.latest_frame())
            self.assertEqual(proactive.last_screen_comment_ms, 500000)
            trigger.assert_awaited_once()
            data = trigger.await_args.kwargs["data"]
            self.assertEqual(data["kind"], "screen_comment")
            self.assertIn("游戏画面", data["text"])
            self.assertEqual(data["metadata"]["wake_client_uid"], "client")
            self.assertIs(trigger.await_args.kwargs["flow_monitor"], handler.rikka_flow_monitor)

        asyncio.run(run())

    def test_scheduler_binds_proactive_followup_to_active_mic_owner(self):
        async def run():
            handler, store, _capture, proactive = self.make_handler()
            handler.client_connections.clear()
            handler.client_contexts.clear()
            handler.client_connections["console"] = FakeWebSocket()
            handler.client_connections["overlay"] = FakeWebSocket()
            handler.client_contexts["console"] = SimpleNamespace()
            handler.client_contexts["overlay"] = SimpleNamespace()
            handler.mic_clients["console"] = MicClientState(
                "console",
                client_kind="console",
                always_on_enabled=True,
                mic_permission="granted",
                listening=True,
            )
            handler.mic_clients["overlay"] = MicClientState(
                "overlay",
                client_kind="overlay",
                always_on_enabled=False,
                mic_permission="unknown",
                listening=False,
            )
            handler.active_mic_owner_uid = "console"
            store.update(
                {
                    "screen_capture_enabled": True,
                    "keyframe_upload_enabled": True,
                    "capture": {
                        "enabled": True,
                        "window_title_allowlist": ["Minecraft"],
                    },
                    "proactive": {
                        "screen_comments_enabled": True,
                        "screen_comment_cooldown_ms": 10000,
                        "min_user_idle_ms": 5000,
                    },
                }
            )
            trigger = AsyncMock()
            with patch(
                "open_llm_vtuber.websocket_handler.handle_conversation_trigger",
                trigger,
            ):
                result = await handler.tick_proactive_once()

            self.assertTrue(result["triggered"])
            self.assertEqual(result["kind"], "screen_comment")
            self.assertEqual(proactive.last_screen_comment_ms, 500000)
            trigger.assert_awaited_once()
            self.assertEqual(trigger.await_args.kwargs["client_uid"], "overlay")
            data = trigger.await_args.kwargs["data"]
            self.assertEqual(data["metadata"]["wake_client_uid"], "console")

        asyncio.run(run())

    def test_scheduler_triggers_idle_speech_without_screen_context(self):
        async def run():
            handler, store, _capture, proactive = self.make_handler(
                clock_ms=lambda: 1000000
            )
            store.update(
                {
                    "proactive": {
                        "idle_speech_enabled": True,
                        "idle_speech_cooldown_ms": 60000,
                        "min_user_idle_ms": 5000,
                    }
                }
            )
            trigger = AsyncMock()
            handler.rikka_flow_monitor = object()
            with patch(
                "open_llm_vtuber.websocket_handler.handle_conversation_trigger",
                trigger,
            ):
                result = await handler.tick_proactive_once()

            self.assertTrue(result["triggered"])
            self.assertEqual(result["kind"], "idle_speech")
            self.assertEqual(proactive.last_idle_speech_ms, 1000000)
            data = trigger.await_args.kwargs["data"]
            self.assertEqual(data["kind"], "idle_speech")
            self.assertIn("暂时没有说话", data["text"])
            self.assertEqual(data["metadata"]["wake_client_uid"], "client")
            self.assertIs(trigger.await_args.kwargs["flow_monitor"], handler.rikka_flow_monitor)

        asyncio.run(run())

    def test_scheduler_does_not_interrupt_active_conversation(self):
        async def run():
            handler, store, _capture, _proactive = self.make_handler()
            store.update(
                {
                    "proactive": {
                        "idle_speech_enabled": True,
                        "idle_speech_cooldown_ms": 60000,
                        "min_user_idle_ms": 5000,
                    }
                }
            )
            task = asyncio.create_task(asyncio.sleep(10))
            handler.current_conversation_tasks["client"] = task
            trigger = AsyncMock()
            try:
                with patch(
                    "open_llm_vtuber.websocket_handler.handle_conversation_trigger",
                    trigger,
                ):
                    result = await handler.tick_proactive_once()
            finally:
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task

            self.assertFalse(result["triggered"])
            self.assertEqual(
                result["decisions"]["idle_speech"]["reason"],
                "conversation is active",
            )
            trigger.assert_not_awaited()

        asyncio.run(run())

    def test_screen_comment_waits_for_significant_change_after_baseline(self):
        async def run():
            now = 500000
            enumerator = MutableFrameEnumerator()
            handler, store, _capture, proactive = self.make_handler_with_enumerator(
                enumerator,
                clock_ms=lambda: now,
            )
            store.update(
                {
                    "screen_capture_enabled": True,
                    "keyframe_upload_enabled": True,
                    "capture": {
                        "enabled": True,
                        "window_title_allowlist": ["Minecraft"],
                    },
                    "proactive": {
                        "screen_comments_enabled": True,
                        "screen_comment_cooldown_ms": 10000,
                        "min_user_idle_ms": 5000,
                    },
                }
            )
            trigger = AsyncMock()
            with patch(
                "open_llm_vtuber.websocket_handler.handle_conversation_trigger",
                trigger,
            ):
                first = await handler.tick_proactive_once()
                now += 20000
                second = await handler.tick_proactive_once()
                enumerator.frame_b64 = image_b64((255, 255, 255))
                now += 20000
                third = await handler.tick_proactive_once()

            self.assertTrue(first["triggered"])
            self.assertFalse(second["triggered"])
            self.assertEqual(
                second["decisions"]["screen_comment"]["reason"],
                "screen unchanged",
            )
            self.assertEqual(proactive._count_since(proactive.screen_comment_times, 0), 2)
            self.assertTrue(third["triggered"])
            self.assertEqual(trigger.await_count, 2)

        asyncio.run(run())

    def test_scheduler_does_not_target_console_only_client(self):
        async def run():
            handler, store, _capture, proactive = self.make_handler()
            handler.mic_clients["client"] = MicClientState(
                client_uid="client",
                client_kind="console",
            )
            handler.client_kinds["client"] = "console"
            store.update(
                {
                    "proactive": {
                        "idle_speech_enabled": True,
                        "idle_speech_cooldown_ms": 60000,
                        "min_user_idle_ms": 5000,
                    }
                }
            )
            trigger = AsyncMock()
            with patch(
                "open_llm_vtuber.websocket_handler.handle_conversation_trigger",
                trigger,
            ):
                result = await handler.tick_proactive_once()

            self.assertFalse(result["triggered"])
            self.assertEqual(
                result["decisions"]["idle_speech"]["reason"],
                "no Live2D client connected",
            )
            trigger.assert_not_awaited()
            self.assertEqual(proactive.idle_speech_times, [])

        asyncio.run(run())

    def test_scheduler_ignores_stale_console_task_and_targets_overlay(self):
        async def run():
            handler, store, _capture, _proactive = self.make_handler(
                clock_ms=lambda: 1000000
            )
            handler.mic_clients["client"] = MicClientState(
                client_uid="client",
                client_kind="console",
            )
            handler.client_kinds["client"] = "console"
            handler.client_connections["overlay"] = FakeWebSocket()
            handler.client_contexts["overlay"] = SimpleNamespace()
            handler.mic_clients["overlay"] = MicClientState(
                client_uid="overlay",
                client_kind="overlay",
            )
            handler.client_kinds["overlay"] = "overlay"
            handler.current_conversation_tasks["client"] = asyncio.create_task(
                asyncio.sleep(10)
            )
            store.update(
                {
                    "proactive": {
                        "idle_speech_enabled": True,
                        "idle_speech_cooldown_ms": 60000,
                        "min_user_idle_ms": 5000,
                    }
                }
            )
            trigger = AsyncMock()
            try:
                with patch(
                    "open_llm_vtuber.websocket_handler.handle_conversation_trigger",
                    trigger,
                ):
                    result = await handler.tick_proactive_once()
            finally:
                handler.current_conversation_tasks["client"].cancel()
                with suppress(asyncio.CancelledError):
                    await handler.current_conversation_tasks["client"]

            self.assertTrue(result["triggered"])
            self.assertEqual(result["client_uid"], "overlay")
            self.assertEqual(trigger.await_args.kwargs["client_uid"], "overlay")

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()

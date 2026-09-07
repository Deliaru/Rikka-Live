import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from open_llm_vtuber.rikka.core import normalize_live_event
from open_llm_vtuber.rikka.routes import extract_debug_event_envelope
from open_llm_vtuber.rikka.schemas import RikkaResponse
from open_llm_vtuber.rikka.settings import RikkaSettingsStore
import open_llm_vtuber.websocket_handler as websocket_handler_module
from open_llm_vtuber.websocket_handler import (
    WebSocketHandler,
    extract_rikka_live_event_message,
)


class RikkaWebSocketEventTests(unittest.TestCase):
    def test_rikka_live_event_extracts_inner_event_and_speak_flag(self):
        response_candidate = {
            "spoken_text": "收到。",
            "subtitle_text": "收到。",
            "emotion": "soft_smile",
            "motion": "nod",
            "gaze": "chat",
            "priority": "normal",
            "interruptible": True,
            "reason_code": "reply_chat",
        }
        event_payload, candidate_response, speak = extract_rikka_live_event_message(
            {
                "type": "rikka-live-event",
                "speak": True,
                "candidate_response": response_candidate,
                "event": {
                    "type": "chat.message",
                    "source": "debug",
                    "text": "六花，WebSocket 事件测试。",
                    "actor": {
                        "platform": "bilibili",
                        "user_id": "viewer",
                        "display_name": "viewer",
                    },
                },
            }
        )

        event = normalize_live_event(event_payload)
        self.assertEqual(event.type, "chat.message")
        self.assertTrue(speak)
        self.assertEqual(candidate_response, response_candidate)
        self.assertNotIn("speak", event_payload)
        self.assertNotIn("candidate_response", event_payload)

    def test_rikka_live_event_can_take_candidate_from_inner_event(self):
        event_payload, candidate_response, speak = extract_rikka_live_event_message(
            {
                "type": "rikka-live-event",
                "event": {
                    "type": "chat.message",
                    "source": "debug",
                    "text": "六花，候选响应测试。",
                    "candidate_response": {
                        "spoken_text": "候选收到。",
                        "subtitle_text": "候选收到。",
                        "emotion": "neutral",
                        "motion": "idle",
                        "gaze": "camera",
                        "priority": "normal",
                        "interruptible": True,
                        "reason_code": "reply_chat",
                    },
                },
            }
        )

        self.assertFalse(speak)
        self.assertEqual(candidate_response["spoken_text"], "候选收到。")
        self.assertNotIn("candidate_response", event_payload)

    def test_rikka_live_event_requires_event_object(self):
        with self.assertRaises(ValueError):
            extract_rikka_live_event_message({"type": "rikka-live-event"})

    def test_debug_event_envelope_removes_control_fields(self):
        response_candidate = {
            "spoken_text": "收到。",
            "subtitle_text": "收到。",
            "emotion": "neutral",
            "motion": "idle",
            "gaze": "camera",
            "priority": "normal",
            "interruptible": True,
            "reason_code": "reply_chat",
        }
        event_payload, candidate_response, speak = extract_debug_event_envelope(
            {
                "speak": True,
                "candidate_response": response_candidate,
                "event": {
                    "type": "chat.message",
                    "source": "debug",
                    "text": "六花，HTTP 调试事件测试。",
                },
            }
        )

        event = normalize_live_event(event_payload)
        self.assertEqual(event.type, "chat.message")
        self.assertTrue(speak)
        self.assertEqual(candidate_response, response_candidate)
        self.assertNotIn("speak", event_payload)
        self.assertNotIn("candidate_response", event_payload)

    def test_emit_preplanned_result_reports_no_live2d_clients(self):
        async def run():
            handler = WebSocketHandler(default_context_cache=None)
            return await handler.emit_preplanned_rikka_result(
                {
                    "event": {
                        "type": "chat.message",
                        "source": "debug",
                        "text": "无人连接测试。",
                    },
                    "validation": {"ok": True, "errors": []},
                    "response": {
                        "spoken_text": "无人连接。",
                        "subtitle_text": "无人连接。",
                        "emotion": "neutral",
                        "motion": "idle",
                        "gaze": "camera",
                        "priority": "normal",
                        "interruptible": True,
                        "reason_code": "reply_chat",
                    },
                    "memory_applied": [],
                    "planner": {},
                }
            )

        result = asyncio.run(run())

        self.assertFalse(result["ok"])
        self.assertEqual(result["delivered_clients"], 0)
        self.assertEqual(result["reason"], "no Live2D clients connected")

    def test_rikka_response_payload_includes_motion_and_gaze_actions(self):
        class FakeWebSocket:
            def __init__(self):
                self.messages = []

            async def send_text(self, text):
                self.messages.append(json.loads(text))

        async def run():
            websocket = FakeWebSocket()
            handler = WebSocketHandler(default_context_cache=None)
            context = SimpleNamespace(
                live2d_model=SimpleNamespace(
                    model_info={
                        "motionMap": {
                            "nod": {
                                "group": "",
                                "index": 16,
                                "priority": "normal",
                                "cooldown_ms": 1800,
                            }
                        },
                        "gazeMap": {
                            "chat": {
                                "parameters": {
                                    "ParamAngleX": -5,
                                    "ParamEyeBallX": -0.25,
                                },
                                "hold_ms": 1400,
                            }
                        },
                    }
                )
            )
            await handler._emit_rikka_result_to_client(
                websocket=websocket,
                context=context,
                event_data={
                    "id": "flow-response-actions",
                    "type": "chat.message",
                    "source": "debug",
                    "text": "动作意图测试。",
                },
                validation_ok=True,
                validation_errors=[],
                response=RikkaResponse.model_validate(
                    {
                        "spoken_text": "收到。",
                        "subtitle_text": "收到。",
                        "emotion": "soft_smile",
                        "motion": "nod",
                        "gaze": "chat",
                        "priority": "normal",
                        "interruptible": True,
                        "reason_code": "reply_chat",
                    }
                ),
                applied_memory=[],
                planner_status={},
                speak=False,
            )
            return websocket.messages

        messages = asyncio.run(run())
        response_payload = next(item for item in messages if item["type"] == "rikka-response")

        self.assertFalse(response_payload["speak"])
        self.assertNotIn("expressions", response_payload["actions"])
        self.assertEqual(response_payload["actions"]["motions"][0]["name"], "nod")
        self.assertEqual(response_payload["actions"]["gaze"]["name"], "chat")

    def test_response_payload_expressions_follow_live2d_settings_gate(self):
        class FakeWebSocket:
            def __init__(self):
                self.messages = []

            async def send_text(self, text):
                self.messages.append(json.loads(text))

        preset_context = SimpleNamespace(
            live2d_model=SimpleNamespace(
                model_info={
                    "expressionPresets": {
                        "neutral": {"label": "平静", "parameters": {}},
                        "soft_smile": {
                            "label": "浅笑",
                            "parameters": {"ParamMouthForm": 0.15},
                            "fade_ms": 400,
                        },
                    },
                }
            )
        )
        response = RikkaResponse.model_validate(
            {
                "spoken_text": "收到。",
                "subtitle_text": "收到。",
                "emotion": "soft_smile",
                "motion": "idle",
                "gaze": "camera",
                "priority": "normal",
                "interruptible": True,
                "reason_code": "reply_chat",
            }
        )

        async def emit(handler):
            websocket = FakeWebSocket()
            await handler._emit_rikka_result_to_client(
                websocket=websocket,
                context=preset_context,
                event_data={
                    "id": "flow-expressions-gate",
                    "type": "chat.message",
                    "source": "debug",
                    "text": "表情开关测试。",
                },
                validation_ok=True,
                validation_errors=[],
                response=response,
                applied_memory=[],
                planner_status={},
                speak=False,
            )
            return next(
                item
                for item in websocket.messages
                if item["type"] == "rikka-response"
            )

        async def run():
            with tempfile.TemporaryDirectory() as tmp_dir:
                store = RikkaSettingsStore(Path(tmp_dir) / "settings.json")
                handler = WebSocketHandler(
                    default_context_cache=None,
                    settings_store=store,
                )
                enabled_payload = await emit(handler)
                store.update({"live2d": {"expressions_enabled": False}})
                disabled_payload = await emit(handler)
                return enabled_payload, disabled_payload

        enabled_payload, disabled_payload = asyncio.run(run())

        expression = enabled_payload["actions"]["expressions"][0]
        self.assertEqual(expression["name"], "soft_smile")
        self.assertEqual(expression["preset"]["fade_ms"], 400)
        self.assertEqual(
            expression["preset"]["parameters"], {"ParamMouthForm": 0.15}
        )
        self.assertNotIn("expressions", disabled_payload["actions"])

    def test_speaking_display_text_uses_spoken_text_not_short_subtitle(self):
        class FakeWebSocket:
            def __init__(self):
                self.messages = []

            async def send_text(self, text):
                self.messages.append(json.loads(text))

        class FakeTTSTaskManager:
            last_call = None

            def __init__(self):
                self.task_list = []

            async def speak(
                self,
                tts_text,
                display_text,
                actions,
                live2d_model,
                tts_engine,
                websocket_send,
                tts_meta=None,
            ):
                FakeTTSTaskManager.last_call = {
                    "tts_text": tts_text,
                    "display_text": display_text,
                    "tts_meta": tts_meta,
                }

            async def wait_for_payloads(self):
                return None

            def clear(self):
                return None

        async def run():
            original_manager = websocket_handler_module.TTSTaskManager
            websocket_handler_module.TTSTaskManager = FakeTTSTaskManager
            try:
                websocket = FakeWebSocket()
                handler = WebSocketHandler(default_context_cache=None)
                context = SimpleNamespace(
                    character_config=SimpleNamespace(
                        character_name="Rikka",
                        avatar="",
                    ),
                    live2d_model=SimpleNamespace(model_info={}),
                    tts_engine=SimpleNamespace(),
                )
                response = RikkaResponse.model_validate(
                    {
                        "spoken_text": "完整播报文本，会被 TTS 念出来。",
                        "subtitle_text": "短字幕。",
                        "emotion": "soft_smile",
                        "motion": "idle",
                        "gaze": "camera",
                        "priority": "normal",
                        "interruptible": True,
                        "reason_code": "host_note",
                    }
                )
                await handler._speak_rikka_response(websocket, context, response, "flow-spoken")
            finally:
                websocket_handler_module.TTSTaskManager = original_manager

        asyncio.run(run())

        self.assertEqual(
            FakeTTSTaskManager.last_call["tts_text"],
            "完整播报文本，会被 TTS 念出来。",
        )
        self.assertEqual(
            FakeTTSTaskManager.last_call["display_text"].text,
            "完整播报文本，会被 TTS 念出来。",
        )

    def test_preplanned_debug_result_registers_mood_once_before_broadcast(self):
        class FakeWebSocket:
            async def send_text(self, _text):
                return None

        calls = []

        def fake_apply_mood_effects(**kwargs):
            calls.append(kwargs)
            if kwargs.get("register"):
                return None
            return {"emotion_vec": {"happy": 0.13}}

        async def run():
            handler = WebSocketHandler(default_context_cache=None)
            context = SimpleNamespace(
                character_config=SimpleNamespace(character_name="Rikka", avatar=""),
                live2d_model=SimpleNamespace(model_info={}),
                tts_engine=SimpleNamespace(),
            )
            handler.client_connections = {
                "one": FakeWebSocket(),
                "two": FakeWebSocket(),
            }
            handler.client_contexts = {"one": context, "two": context}
            with patch(
                "open_llm_vtuber.websocket_handler.apply_rikka_mood_effects",
                side_effect=fake_apply_mood_effects,
            ):
                await handler.emit_preplanned_rikka_result(
                    {
                        "event": {
                            "id": "flow-mood-debug",
                            "type": "system.test_event",
                            "source": "debug",
                            "text": "六花，你真棒",
                        },
                        "validation": {"ok": True, "errors": []},
                        "response": {
                            "spoken_text": "谢谢你。",
                            "subtitle_text": "谢谢你。",
                            "emotion": "soft_smile",
                            "motion": "idle",
                            "gaze": "camera",
                            "priority": "normal",
                            "interruptible": True,
                            "reason_code": "reply_chat",
                        },
                        "memory_applied": [],
                        "planner": {},
                    },
                    speak=False,
                )

        asyncio.run(run())

        register_calls = [call for call in calls if call.get("register")]
        self.assertEqual(len(register_calls), 1)
        self.assertEqual(register_calls[0]["emotion"], "soft_smile")

    def test_preplanned_bilibili_result_does_not_register_mood(self):
        class FakeWebSocket:
            async def send_text(self, _text):
                return None

        calls = []

        def fake_apply_mood_effects(**kwargs):
            calls.append(kwargs)
            return None

        async def run():
            handler = WebSocketHandler(default_context_cache=None)
            context = SimpleNamespace(
                character_config=SimpleNamespace(character_name="Rikka", avatar=""),
                live2d_model=SimpleNamespace(model_info={}),
                tts_engine=SimpleNamespace(),
            )
            handler.client_connections = {"one": FakeWebSocket()}
            handler.client_contexts = {"one": context}
            with patch(
                "open_llm_vtuber.websocket_handler.apply_rikka_mood_effects",
                side_effect=fake_apply_mood_effects,
            ):
                await handler.emit_preplanned_rikka_result(
                    {
                        "event": {
                            "id": "flow-mood-bilibili",
                            "type": "chat.message",
                            "source": "bilibili",
                            "text": "六花真棒",
                        },
                        "validation": {"ok": True, "errors": []},
                        "response": {
                            "spoken_text": "谢谢。",
                            "subtitle_text": "谢谢。",
                            "emotion": "soft_smile",
                            "motion": "idle",
                            "gaze": "chat",
                            "priority": "normal",
                            "interruptible": True,
                            "reason_code": "reply_chat",
                        },
                        "memory_applied": [],
                        "planner": {},
                    },
                    speak=False,
                )

        asyncio.run(run())

        self.assertFalse([call for call in calls if call.get("register")])


if __name__ == "__main__":
    unittest.main()

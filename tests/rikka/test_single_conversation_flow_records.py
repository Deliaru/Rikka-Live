import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from open_llm_vtuber.conversations.single_conversation import process_single_conversation
from open_llm_vtuber.rikka.settings import AudioInteractionSettings, ProactiveSettings


async def _noop_send(_message: str) -> None:
    return None



class ToolStatusAgent:
    async def chat(self, _batch_input):
        yield {
            "type": "tool_call_status",
            "tool_name": "look_at_screen",
            "tool_kind": "native",
            "status": "running",
            "content": "capture requested",
        }
        yield {
            "type": "tool_call_status",
            "tool_name": "look_at_screen",
            "tool_kind": "native",
            "status": "completed",
            "content": "captured image",
            "ok": True,
            "duration_ms": 42,
            "result_kind": "image",
            "result_summary": "captured image",
        }


class EmptyAgent:
    async def chat(self, _batch_input):
        if False:
            yield None


class ValidationFailureAgent:
    async def chat(self, _batch_input):
        yield {
            "type": "rikka_validation_status",
            "ok": False,
            "fallback": True,
            "silent": False,
            "failure_kind": "missing_json",
            "raw_response_length": 32,
            "raw_response_hash": "0123456789abcdef",
            "raw_response_excerpt": "plain text",
            "raw_response_truncated": False,
            "fallback_reason_code": "safety_fallback",
            "fallback_spoken_preview": "嗯...我听到了。",
            "fallback_subtitle_preview": "嗯...我听到了。",
            "attached_image_count": 1,
            "errors": ["Extra data: line 1 column 42 (char 41)"],
        }


class ValidationRepairAgent:
    async def chat(self, _batch_input):
        yield {
            "type": "rikka_validation_status",
            "ok": True,
            "fallback": False,
            "silent": False,
            "failure_kind": "schema_repaired",
            "repaired": True,
            "repair_notes": ["subtitle_text defaulted from spoken_text"],
            "raw_response_length": 120,
            "raw_response_hash": "fedcba9876543210",
            "raw_response_excerpt": '{"spoken_text":"收到。"}',
            "raw_response_text": '{"spoken_text":"收到。"}',
            "raw_response_text_truncated": False,
            "raw_response_truncated": False,
            "attached_image_count": 0,
            "errors": [],
        }

        from open_llm_vtuber.agent.output_types import (
            Actions,
            DisplayText,
            SentenceOutput,
        )

        yield SentenceOutput(
            display_text=DisplayText(text="收到。"),
            tts_text="收到。",
            actions=Actions(),
        )


class ProviderErrorAgent:
    async def chat(self, _batch_input):
        yield {
            "type": "rikka_validation_status",
            "ok": False,
            "fallback": True,
            "silent": False,
            "provider_error": True,
            "provider_endpoint": "responses",
            "provider_status_code": 502,
            "provider_error_detail": (
                '{"error":{"message":"Upstream service temporarily unavailable",'
                '"type":"upstream_error"}}'
            ),
            "errors": ["provider returned HTTP 502"],
        }


class OneSentenceAgent:
    async def chat(self, _batch_input):
        from open_llm_vtuber.agent.output_types import (
            Actions,
            DisplayText,
            SentenceOutput,
        )

        yield SentenceOutput(
            display_text=DisplayText(text="嗯...我听到了。"),
            tts_text="嗯...我听到了。",
            actions=Actions(),
        )


class SilentValidationFailureAgent:
    async def chat(self, _batch_input):
        yield {
            "type": "rikka_validation_status",
            "ok": False,
            "fallback": True,
            "silent": True,
            "errors": ["spoken_text cannot be empty after cleaning"],
        }


class FakeFlowMonitor:
    def __init__(self):
        self.records = []
        self.started = []

    def start(self, flow_id, event):
        self.started.append({"flow_id": flow_id, "event": event})
        self.record(flow_id, "event", "ok", detail="event received")
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


class SingleConversationFlowRecordTests(unittest.IsolatedAsyncioTestCase):
    def make_context(self, agent):
        return SimpleNamespace(
            asr_engine=None,
            agent_engine=agent,
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

    async def run_conversation(self, agent):
        flow = FakeFlowMonitor()
        sent_messages = []

        async def websocket_send(message: str) -> None:
            sent_messages.append(json.loads(message))

        with (
            patch(
                "open_llm_vtuber.conversations.single_conversation."
                "get_default_settings_store",
                return_value=SimpleNamespace(
                    snapshot=lambda: SimpleNamespace(audio=AudioInteractionSettings())
                ),
            ),
            patch(
                "open_llm_vtuber.conversations.single_conversation."
                "get_default_proactive_coordinator",
                return_value=SimpleNamespace(mark_user_activity=lambda: None),
            ),
            patch(
                "open_llm_vtuber.conversations.single_conversation."
                "finalize_conversation_turn",
                return_value={"type": "frontend-playback-complete", "status": "ok"},
            ),
        ):
            await process_single_conversation(
                context=self.make_context(agent),
                websocket_send=websocket_send,
                client_uid="client",
                user_input="帮我看看屏幕",
                flow_monitor=flow,
                flow_id="tool-flow",
            )
        return flow, sent_messages

    async def test_tool_status_records_privacy_safe_planner_flow(self):
        flow, sent_messages = await self.run_conversation(ToolStatusAgent())

        self.assertTrue(
            any(message.get("type") == "tool_call_status" for message in sent_messages)
        )
        tool_records = [
            record
            for record in flow.records
            if record["stage"] == "planner"
            and record["metadata"].get("tool_name") == "look_at_screen"
        ]
        self.assertEqual(len(tool_records), 2)
        self.assertEqual(tool_records[0]["status"], "running")
        self.assertEqual(tool_records[0]["metadata"]["status"], "running")
        self.assertEqual(tool_records[0]["metadata"]["tool_kind"], "native")
        self.assertEqual(tool_records[1]["metadata"]["status"], "completed")
        self.assertTrue(tool_records[1]["metadata"]["ok"])
        self.assertEqual(tool_records[1]["metadata"]["duration_ms"], 42)
        self.assertEqual(tool_records[1]["metadata"]["result_kind"], "image")
        self.assertEqual(tool_records[1]["metadata"]["result_summary"], "captured image")
        self.assertNotIn("content", tool_records[0]["metadata"])

    async def test_empty_agent_preserves_planner_running_ok_shape(self):
        flow, _sent_messages = await self.run_conversation(EmptyAgent())

        planner_records = [
            record for record in flow.records if record["stage"] == "planner"
        ]
        self.assertEqual(
            [record["status"] for record in planner_records],
            ["running", "ok"],
        )

    async def test_validation_failure_records_flow_validate_stage(self):
        flow, _sent_messages = await self.run_conversation(ValidationFailureAgent())

        planner_records = [
            record for record in flow.records if record["stage"] == "planner"
        ]
        self.assertEqual(
            [record["status"] for record in planner_records],
            ["running", "error"],
        )
        self.assertEqual(
            planner_records[-1]["detail"],
            "LLM response invalid; fallback used",
        )
        self.assertTrue(planner_records[-1]["metadata"]["fallback"])
        self.assertEqual(planner_records[-1]["metadata"]["failure_kind"], "missing_json")
        self.assertEqual(
            planner_records[-1]["metadata"]["raw_response_hash"],
            "0123456789abcdef",
        )
        self.assertEqual(planner_records[-1]["metadata"]["attached_image_count"], 1)

        validate_records = [
            record for record in flow.records if record["stage"] == "validate"
        ]
        self.assertEqual(len(validate_records), 1)
        self.assertEqual(validate_records[0]["status"], "error")
        self.assertTrue(validate_records[0]["metadata"]["fallback"])
        self.assertEqual(validate_records[0]["metadata"]["error_count"], 1)
        self.assertEqual(
            validate_records[0]["metadata"]["fallback_spoken_preview"],
            "嗯...我听到了。",
        )

    async def test_validation_repair_records_ok_flow_validate_stage(self):
        flow, _sent_messages = await self.run_conversation(ValidationRepairAgent())

        planner_records = [
            record for record in flow.records if record["stage"] == "planner"
        ]
        self.assertEqual(
            [record["status"] for record in planner_records],
            ["running", "ok"],
        )

        validate_records = [
            record for record in flow.records if record["stage"] == "validate"
        ]
        self.assertEqual(len(validate_records), 1)
        self.assertEqual(validate_records[0]["status"], "ok")
        self.assertTrue(validate_records[0]["metadata"]["repaired"])
        self.assertFalse(validate_records[0]["metadata"]["fallback"])
        self.assertEqual(
            validate_records[0]["metadata"]["repair_notes"],
            ["subtitle_text defaulted from spoken_text"],
        )
        self.assertIn("spoken_text", validate_records[0]["metadata"]["raw_response_text"])

    async def test_provider_error_records_llm_call_failure_in_planner_stage(self):
        flow, _sent_messages = await self.run_conversation(ProviderErrorAgent())

        planner_records = [
            record for record in flow.records if record["stage"] == "planner"
        ]
        self.assertEqual(
            planner_records[-1]["detail"],
            'LLM responses call failed with HTTP 502: {"error":{"message":"Upstream service temporarily unavailable","type":"upstream_error"}}',
        )
        self.assertTrue(planner_records[-1]["metadata"]["provider_error"])
        self.assertEqual(planner_records[-1]["metadata"]["provider_endpoint"], "responses")
        self.assertEqual(planner_records[-1]["metadata"]["provider_status_code"], 502)

    async def test_silent_validation_failure_records_skipped_flow_validate_stage(self):
        flow, _sent_messages = await self.run_conversation(
            SilentValidationFailureAgent()
        )

        validate_records = [
            record for record in flow.records if record["stage"] == "validate"
        ]
        self.assertEqual(len(validate_records), 1)
        self.assertEqual(validate_records[0]["status"], "skipped")
        self.assertTrue(validate_records[0]["metadata"]["silent"])

    async def test_text_input_conversation_starts_privacy_safe_flow_event(self):
        from open_llm_vtuber.conversations.conversation_handler import (
            handle_conversation_trigger,
        )

        flow = FakeFlowMonitor()
        sent_messages = []

        async def websocket_send(message: str) -> None:
            sent_messages.append(json.loads(message))

        with (
            patch(
                "open_llm_vtuber.conversations.conversation_handler."
                "get_default_settings_store",
                return_value=SimpleNamespace(
                    snapshot=lambda: SimpleNamespace(
                        keyframe_upload_enabled=False,
                        capture=SimpleNamespace(attach_to_user_turns=False),
                    )
                ),
            ),
            patch(
                "open_llm_vtuber.conversations.single_conversation."
                "get_default_settings_store",
                return_value=SimpleNamespace(
                    snapshot=lambda: SimpleNamespace(audio=AudioInteractionSettings())
                ),
            ),
            patch(
                "open_llm_vtuber.conversations.single_conversation."
                "get_default_proactive_coordinator",
                return_value=SimpleNamespace(mark_user_activity=lambda: None),
            ),
            patch(
                "open_llm_vtuber.conversations.single_conversation."
                "finalize_conversation_turn",
                return_value={"type": "frontend-playback-complete", "status": "ok"},
            ),
        ):
            tasks = {}
            await handle_conversation_trigger(
                msg_type="text-input",
                data={"type": "text-input", "text": "六花，为什么 fallback？"},
                client_uid="client",
                context=self.make_context(ValidationFailureAgent()),
                websocket=SimpleNamespace(send_text=websocket_send),
                client_contexts={},
                client_connections={},
                chat_group_manager=SimpleNamespace(get_client_group=lambda _uid: None),
                received_data_buffers={},
                current_conversation_tasks=tasks,
                broadcast_to_group=lambda *_args, **_kwargs: None,
                flow_monitor=flow,
            )
            await tasks["client"]

        self.assertEqual(flow.started[0]["event"]["source"], "user")
        self.assertEqual(flow.started[0]["event"]["type"], "text_input")
        self.assertEqual(flow.started[0]["event"]["text"], "六花，为什么 fallback？")
        self.assertFalse(flow.started[0]["event"]["payload"]["has_images"])

    async def test_proactive_conversation_starts_privacy_safe_flow_event(self):
        from open_llm_vtuber.conversations.conversation_handler import (
            handle_conversation_trigger,
        )

        flow = FakeFlowMonitor()
        sent_messages = []

        async def websocket_send(message: str) -> None:
            sent_messages.append(json.loads(message))

        with (
            patch(
                "open_llm_vtuber.conversations.conversation_handler."
                "get_default_settings_store",
                return_value=SimpleNamespace(
                    snapshot=lambda: SimpleNamespace(
                        keyframe_upload_enabled=False,
                        capture=SimpleNamespace(attach_to_user_turns=False),
                        proactive=ProactiveSettings(proactive_followup_window_ms=18000),
                    )
                ),
            ),
            patch(
                "open_llm_vtuber.conversations.single_conversation."
                "get_default_settings_store",
                return_value=SimpleNamespace(
                    snapshot=lambda: SimpleNamespace(audio=AudioInteractionSettings())
                ),
            ),
            patch(
                "open_llm_vtuber.conversations.single_conversation."
                "get_default_proactive_coordinator",
                return_value=SimpleNamespace(mark_user_activity=lambda: None),
            ),
            patch(
                "open_llm_vtuber.conversations.single_conversation."
                "finalize_conversation_turn",
                return_value={"type": "frontend-playback-complete", "status": "ok"},
            ),
        ):
            tasks = {}
            await handle_conversation_trigger(
                msg_type="ai-speak-signal",
                data={
                    "type": "ai-speak-signal",
                    "kind": "screen_comment",
                    "text": "请根据最近一张游戏画面，用低打扰的陪播语气说一句。",
                },
                client_uid="client",
                context=self.make_context(ValidationFailureAgent()),
                websocket=SimpleNamespace(send_text=websocket_send),
                client_contexts={},
                client_connections={},
                chat_group_manager=SimpleNamespace(get_client_group=lambda _uid: None),
                received_data_buffers={},
                current_conversation_tasks=tasks,
                broadcast_to_group=lambda *_args, **_kwargs: None,
                flow_monitor=flow,
            )
            await tasks["client"]

        self.assertEqual(flow.started[0]["event"]["source"], "proactive")
        self.assertEqual(flow.started[0]["event"]["type"], "proactive.screen_comment")
        self.assertEqual(flow.started[0]["event"]["actor"]["display_name"], "Rikka proactive")
        self.assertTrue(flow.started[0]["event"]["payload"]["client_uid"])

    async def test_proactive_speak_fills_wake_followup_metadata_when_enabled(self):
        from open_llm_vtuber.conversations.conversation_handler import (
            handle_conversation_trigger,
        )

        captured = AsyncMock(return_value="ok")
        tasks: dict = {}
        with (
            patch(
                "open_llm_vtuber.conversations.conversation_handler."
                "get_default_settings_store",
                return_value=SimpleNamespace(
                    snapshot=lambda: SimpleNamespace(
                        keyframe_upload_enabled=False,
                        capture=SimpleNamespace(attach_to_user_turns=False),
                        proactive=ProactiveSettings(proactive_followup_window_ms=18000),
                    )
                ),
            ),
            patch(
                "open_llm_vtuber.conversations.conversation_handler."
                "process_single_conversation",
                captured,
            ),
        ):
            await handle_conversation_trigger(
                msg_type="ai-speak-signal",
                data={"type": "ai-speak-signal", "kind": "idle_speech", "text": "..."},
                client_uid="client",
                context=self.make_context(ValidationFailureAgent()),
                websocket=SimpleNamespace(send_text=_noop_send),
                client_contexts={},
                client_connections={},
                chat_group_manager=SimpleNamespace(get_client_group=lambda _uid: None),
                received_data_buffers={},
                current_conversation_tasks=tasks,
                broadcast_to_group=lambda *_args, **_kwargs: None,
                flow_monitor=FakeFlowMonitor(),
            )
            await tasks["client"]

        metadata = captured.await_args.kwargs["metadata"]
        self.assertEqual(metadata["wake_client_uid"], "client")
        self.assertEqual(metadata["wake_window_after_playback_ms"], 18000)

    async def test_proactive_speak_preserves_upstream_wake_client_metadata(self):
        from open_llm_vtuber.conversations.conversation_handler import (
            handle_conversation_trigger,
        )

        captured = AsyncMock(return_value="ok")
        tasks: dict = {}
        with (
            patch(
                "open_llm_vtuber.conversations.conversation_handler."
                "get_default_settings_store",
                return_value=SimpleNamespace(
                    snapshot=lambda: SimpleNamespace(
                        keyframe_upload_enabled=False,
                        capture=SimpleNamespace(attach_to_user_turns=False),
                        proactive=ProactiveSettings(proactive_followup_window_ms=18000),
                    )
                ),
            ),
            patch(
                "open_llm_vtuber.conversations.conversation_handler."
                "process_single_conversation",
                captured,
            ),
        ):
            await handle_conversation_trigger(
                msg_type="ai-speak-signal",
                data={
                    "type": "ai-speak-signal",
                    "kind": "screen_comment",
                    "text": "...",
                    "metadata": {"wake_client_uid": "console"},
                },
                client_uid="overlay",
                context=self.make_context(ValidationFailureAgent()),
                websocket=SimpleNamespace(send_text=_noop_send),
                client_contexts={},
                client_connections={},
                chat_group_manager=SimpleNamespace(get_client_group=lambda _uid: None),
                received_data_buffers={},
                current_conversation_tasks=tasks,
                broadcast_to_group=lambda *_args, **_kwargs: None,
                flow_monitor=FakeFlowMonitor(),
            )
            await tasks["overlay"]

        metadata = captured.await_args.kwargs["metadata"]
        self.assertEqual(metadata["wake_client_uid"], "console")
        self.assertEqual(metadata["wake_window_after_playback_ms"], 18000)
        self.assertTrue(metadata["proactive_speak"])
        self.assertTrue(metadata["skip_memory"])
        self.assertTrue(metadata["skip_history"])

    async def test_proactive_speak_omits_wake_followup_metadata_when_disabled(self):
        from open_llm_vtuber.conversations.conversation_handler import (
            handle_conversation_trigger,
        )

        captured = AsyncMock(return_value="ok")
        tasks: dict = {}
        with (
            patch(
                "open_llm_vtuber.conversations.conversation_handler."
                "get_default_settings_store",
                return_value=SimpleNamespace(
                    snapshot=lambda: SimpleNamespace(
                        keyframe_upload_enabled=False,
                        capture=SimpleNamespace(attach_to_user_turns=False),
                        proactive=ProactiveSettings(proactive_followup_window_ms=0),
                    )
                ),
            ),
            patch(
                "open_llm_vtuber.conversations.conversation_handler."
                "process_single_conversation",
                captured,
            ),
        ):
            await handle_conversation_trigger(
                msg_type="ai-speak-signal",
                data={"type": "ai-speak-signal", "kind": "idle_speech", "text": "..."},
                client_uid="client",
                context=self.make_context(ValidationFailureAgent()),
                websocket=SimpleNamespace(send_text=_noop_send),
                client_contexts={},
                client_connections={},
                chat_group_manager=SimpleNamespace(get_client_group=lambda _uid: None),
                received_data_buffers={},
                current_conversation_tasks=tasks,
                broadcast_to_group=lambda *_args, **_kwargs: None,
                flow_monitor=FakeFlowMonitor(),
            )
            await tasks["client"]

        metadata = captured.await_args.kwargs["metadata"]
        self.assertNotIn("wake_client_uid", metadata)
        self.assertNotIn("wake_window_after_playback_ms", metadata)

    async def test_audio_payloads_carry_conversation_flow_id(self):
        sent_messages = []

        async def websocket_send(message: str) -> None:
            sent_messages.append(json.loads(message))

        async def fake_generate_audio(_engine, _text, **_kwargs):
            return "fake.wav"

        with (
            patch.object(
                __import__(
                    "open_llm_vtuber.conversations.tts_manager",
                    fromlist=["TTSTaskManager"],
                ).TTSTaskManager,
                "_generate_audio",
                fake_generate_audio,
            ),
            patch(
                "open_llm_vtuber.conversations.tts_manager.prepare_audio_payload",
                return_value={
                    "type": "audio",
                    "audio": None,
                    "volumes": [],
                    "display_text": {"text": "嗯...我听到了。"},
                    "actions": None,
                },
            ) as prepare_payload,
            patch(
                "open_llm_vtuber.conversations.single_conversation."
                "get_default_settings_store",
                return_value=SimpleNamespace(
                    snapshot=lambda: SimpleNamespace(audio=AudioInteractionSettings())
                ),
            ),
            patch(
                "open_llm_vtuber.conversations.single_conversation."
                "get_default_proactive_coordinator",
                return_value=SimpleNamespace(mark_user_activity=lambda: None),
            ),
            patch(
                "open_llm_vtuber.conversations.conversation_utils.message_handler.wait_for_response",
                return_value={
                    "type": "frontend-playback-complete",
                    "status": "ok",
                    "has_audio": True,
                },
            ),
        ):
            await process_single_conversation(
                context=self.make_context(OneSentenceAgent()),
                websocket_send=websocket_send,
                client_uid="client",
                user_input="测试 flow id",
                flow_id="conv-flow",
            )

        self.assertEqual(prepare_payload.call_args.kwargs["flow_id"], "conv-flow")
        complete_messages = [
            message
            for message in sent_messages
            if message.get("type") == "backend-synth-complete"
        ]
        self.assertEqual(
            complete_messages,
            [{"type": "backend-synth-complete", "flow": {"id": "conv-flow"}}],
        )


if __name__ == "__main__":
    unittest.main()

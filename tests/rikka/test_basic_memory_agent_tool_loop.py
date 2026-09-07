import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from open_llm_vtuber.agent.agents.basic_memory_agent import BasicMemoryAgent
from open_llm_vtuber.agent.input_types import (
    BatchInput,
    ImageData,
    ImageSource,
    TextData,
    TextSource,
)
from open_llm_vtuber.agent.output_types import SentenceOutput
from open_llm_vtuber.config_manager import TTSPreprocessorConfig, TranslatorConfig
from open_llm_vtuber.rikka.agent_tools import RikkaToolResult, RikkaToolRunner


class ScriptedLLM:
    def __init__(self, scripts):
        self.scripts = list(scripts)
        self.calls = []

    async def chat_completion(self, messages, system, tools=None):
        self.calls.append({"messages": [*messages], "system": system, "tools": tools})
        for chunk in self.scripts.pop(0):
            yield chunk


class FakeSettingsStore:
    def __init__(self, tools_enabled=True, filler_enabled=True, max_tool_rounds=3):
        self.agent = SimpleNamespace(
            tools_enabled=tools_enabled,
            look_at_screen_enabled=True,
            get_time_enabled=True,
            web_search_enabled=True,
            filler_enabled=filler_enabled,
            result_pre_silence_ms=1000,
            max_tool_rounds=max_tool_rounds,
            web_search_timeout_seconds=1,
        )
        self.mood = SimpleNamespace(
            enabled=True,
            tts_adjustment_enabled=True,
            half_life_minutes=10,
        )
        self.inner_life = SimpleNamespace(
            enabled=True,
            rotation_minutes=18,
            activities=[],
        )
        self.identity = SimpleNamespace(
            host_display_name="Deliaru",
            audience_display_name="\u5f39\u5e55",
        )

    def snapshot(self):
        return SimpleNamespace(
            agent=self.agent,
            mood=self.mood,
            inner_life=self.inner_life,
            identity=self.identity,
        )


class FakeMemoryStore:
    def __init__(self):
        self.writes = []

    def summary(self):
        return "preference:tea=喜欢热茶"

    def apply_writes(self, writes):
        self.writes.extend(writes)
        return list(writes)


class FakeRunner:
    def available_tools(self):
        return [SimpleNamespace(name="look_at_screen")]

    def tool_protocol_block(self):
        return "【可用工具】look_at_screen"

    def filler_text(self, tool_names):
        return "我看看哦……"

    async def run_iter(self, calls):
        yield {
            "type": "tool_call_status",
            "tool_name": "look_at_screen",
            "status": "running",
        }
        yield (
            "results",
            [
                RikkaToolResult(
                    tool="look_at_screen",
                    ok=True,
                    text="[look_at_screen] ok",
                    image_data_url="data:image/jpeg;base64,abc123",
                )
            ],
        )


class EmptyRunner(FakeRunner):
    def available_tools(self):
        return []

    def tool_protocol_block(self):
        return ""


class FailingSearchRunner(FakeRunner):
    def available_tools(self):
        return [SimpleNamespace(name="web_search")]

    def tool_protocol_block(self):
        return "【可用工具】web_search"

    def filler_text(self, tool_names):
        return "稍等哦，我去查查。"

    async def run_iter(self, calls):
        yield {
            "type": "tool_call_status",
            "tool_name": "web_search",
            "status": "running",
        }
        yield {
            "type": "tool_call_status",
            "tool_name": "web_search",
            "status": "error",
            "ok": False,
            "result_kind": "error",
            "result_summary": "我想查来着，但网络好像不太给力，先凭印象说啦。",
        }
        yield (
            "results",
            [
                RikkaToolResult(
                    tool="web_search",
                    ok=False,
                    text="[web_search] 搜索失败：TimeoutError。",
                    spoken_error="我想查来着，但网络好像不太给力，先凭印象说啦。",
                )
            ],
        )


def rikka_json(text="看到了哦", memory_writes=None):
    return json.dumps(
        {
            "spoken_text": text,
            "subtitle_text": text,
            "emotion": "curious",
            "motion": "thinking",
            "gaze": "camera",
            "priority": "normal",
            "interruptible": True,
            "reason_code": "reply_chat",
            "memory_writes": memory_writes or [],
        },
        ensure_ascii=False,
    )


def tts_config():
    return TTSPreprocessorConfig(
        remove_special_char=True,
        translator_config=TranslatorConfig(
            translate_audio=False,
            translate_provider="deeplx",
        ),
    )


class BasicMemoryAgentToolLoopTests(unittest.IsolatedAsyncioTestCase):
    async def collect(self, agent):
        batch = BatchInput(
            texts=[TextData(source=TextSource.INPUT, content="帮我看看屏幕")]
        )
        outputs = []
        async for item in agent.chat(batch):
            outputs.append(item)
        return outputs

    async def collect_with_image(self, agent):
        batch = BatchInput(
            texts=[TextData(source=TextSource.INPUT, content="帮我看看屏幕")],
            images=[
                ImageData(
                    source=ImageSource.SCREEN,
                    data="data:image/jpeg;base64," + ("a" * 160),
                    mime_type="image/jpeg",
                )
            ],
        )
        outputs = []
        async for item in agent.chat(batch):
            outputs.append(item)
        return outputs

    async def collect_proactive(self, agent):
        batch = BatchInput(
            texts=[TextData(source=TextSource.INPUT, content="只有值得回应才说一句")],
            metadata={"proactive_speak": True, "skip_memory": True},
        )
        outputs = []
        async for item in agent.chat(batch):
            outputs.append(item)
        return outputs

    async def test_tool_request_yields_filler_status_and_final_response(self):
        llm = ScriptedLLM(
            [
                ['{"type":"tool_request","calls":[{"tool":"look_at_screen","args":{}}]}'],
                [rikka_json("屏幕上是测试窗口")],
            ]
        )
        memory = FakeMemoryStore()
        agent = BasicMemoryAgent(
            llm=llm,
            system="Return JSON with spoken_text subtitle_text reason_code",
            live2d_model=None,
            tts_preprocessor_config=tts_config(),
        )
        with patch(
            "open_llm_vtuber.agent.agents.basic_memory_agent.get_default_tool_runner",
            return_value=FakeRunner(),
        ), patch(
            "open_llm_vtuber.agent.agents.basic_memory_agent.get_default_settings_store",
            return_value=FakeSettingsStore(),
        ), patch(
            "open_llm_vtuber.agent.agents.basic_memory_agent.get_default_memory_store",
            return_value=memory,
        ):
            outputs = await self.collect(agent)

        self.assertIsInstance(outputs[0], SentenceOutput)
        self.assertEqual(outputs[0].tts_text, "我看看哦……")
        self.assertEqual(outputs[1]["type"], "tool_call_status")
        self.assertIsInstance(outputs[2], SentenceOutput)
        self.assertEqual(outputs[2].tts_meta["pre_silence_ms"], 1000)
        self.assertIn("【可用工具】", llm.calls[0]["system"])
        self.assertIn("preference:tea=喜欢热茶", llm.calls[0]["system"])
        self.assertIn("\u4e3b\u64ad\u300cDeliaru\u300d", llm.calls[0]["system"])
        self.assertIn("\u79f0\u547c\u4e3b\u64ad\u4e3a\u300cDeliaru\u300d", llm.calls[0]["system"])
        self.assertIn("\u7238\u7238\u3001\u7236\u4eb2\u6216\u4e3b\u4eba", llm.calls[0]["system"])
        self.assertIn("source=bilibili", llm.calls[0]["system"])
        self.assertIn("\u300c\u5f39\u5e55\u300d", llm.calls[0]["system"])
        self.assertEqual(llm.calls[1]["messages"][-1]["content"][1]["type"], "image_url")

    async def test_enabled_real_runner_adds_full_tool_protocol_to_llm_system(self):
        llm = ScriptedLLM([[rikka_json("普通回答")]])
        memory = FakeMemoryStore()
        settings = FakeSettingsStore(tools_enabled=True)
        runner = RikkaToolRunner(
            settings_store=settings,
            capture_service=SimpleNamespace(),
        )
        agent = BasicMemoryAgent(
            llm=llm,
            system="Return JSON with spoken_text subtitle_text reason_code",
            live2d_model=None,
            tts_preprocessor_config=tts_config(),
        )
        with patch(
            "open_llm_vtuber.agent.agents.basic_memory_agent.get_default_tool_runner",
            return_value=runner,
        ), patch(
            "open_llm_vtuber.agent.agents.basic_memory_agent.get_default_settings_store",
            return_value=settings,
        ), patch(
            "open_llm_vtuber.agent.agents.basic_memory_agent.get_default_memory_store",
            return_value=memory,
        ):
            outputs = await self.collect(agent)

        self.assertEqual(len(outputs), 1)
        self.assertIsInstance(outputs[0], SentenceOutput)
        system = llm.calls[0]["system"]
        self.assertIn("【可用工具】", system)
        self.assertIn('"type":"tool_request"', system)
        self.assertIn("不要回答“我没有外部搜索入口/不能联网”", system)
        self.assertIn("用户明确要求你搜索", system)
        self.assertIn("look_at_screen", system)
        self.assertIn("get_time", system)
        self.assertIn("web_search", system)
        self.assertIn("preference:tea=喜欢热茶", system)

    async def test_simple_rikka_path_injects_memory_when_tools_disabled(self):
        llm = ScriptedLLM([[rikka_json("普通回答")]])
        memory = FakeMemoryStore()
        agent = BasicMemoryAgent(
            llm=llm,
            system="Return JSON with spoken_text subtitle_text reason_code",
            live2d_model=None,
            tts_preprocessor_config=tts_config(),
        )

        with patch(
            "open_llm_vtuber.agent.agents.basic_memory_agent.get_default_tool_runner",
            return_value=EmptyRunner(),
        ), patch(
            "open_llm_vtuber.agent.agents.basic_memory_agent.get_default_settings_store",
            return_value=FakeSettingsStore(tools_enabled=False),
        ), patch(
            "open_llm_vtuber.agent.agents.basic_memory_agent.get_default_memory_store",
            return_value=memory,
        ):
            outputs = await self.collect(agent)

        self.assertEqual(len(outputs), 1)
        self.assertIsInstance(outputs[0], SentenceOutput)
        self.assertIn("preference:tea=喜欢热茶", llm.calls[0]["system"])
        self.assertNotIn("【可用工具】", llm.calls[0]["system"])

    async def test_memory_writes_are_applied_after_validation(self):
        llm = ScriptedLLM(
            [
                [
                    rikka_json(
                        "记住啦",
                        [
                            {
                                "kind": "preference",
                                "key": "drink",
                                "value": "喜欢热茶",
                            }
                        ],
                    )
                ]
            ]
        )
        memory = FakeMemoryStore()
        agent = BasicMemoryAgent(
            llm=llm,
            system="Return JSON with spoken_text subtitle_text reason_code",
            live2d_model=None,
            tts_preprocessor_config=tts_config(),
        )

        with patch(
            "open_llm_vtuber.agent.agents.basic_memory_agent.get_default_tool_runner",
            return_value=EmptyRunner(),
        ), patch(
            "open_llm_vtuber.agent.agents.basic_memory_agent.get_default_settings_store",
            return_value=FakeSettingsStore(tools_enabled=False),
        ), patch(
            "open_llm_vtuber.agent.agents.basic_memory_agent.get_default_memory_store",
            return_value=memory,
        ):
            await self.collect(agent)

        self.assertEqual(len(memory.writes), 1)
        self.assertEqual(memory.writes[0].key, "drink")

    async def test_filler_disabled_skips_filler_and_pre_silence(self):
        llm = ScriptedLLM(
            [
                ['{"type":"tool_request","calls":[{"tool":"look_at_screen","args":{}}]}'],
                [rikka_json("屏幕上是测试窗口")],
            ]
        )
        memory = FakeMemoryStore()
        agent = BasicMemoryAgent(
            llm=llm,
            system="Return JSON with spoken_text subtitle_text reason_code",
            live2d_model=None,
            tts_preprocessor_config=tts_config(),
        )
        with patch(
            "open_llm_vtuber.agent.agents.basic_memory_agent.get_default_tool_runner",
            return_value=FakeRunner(),
        ), patch(
            "open_llm_vtuber.agent.agents.basic_memory_agent.get_default_settings_store",
            return_value=FakeSettingsStore(filler_enabled=False),
        ), patch(
            "open_llm_vtuber.agent.agents.basic_memory_agent.get_default_memory_store",
            return_value=memory,
        ):
            outputs = await self.collect(agent)

        self.assertEqual(outputs[0]["type"], "tool_call_status")
        self.assertIsInstance(outputs[1], SentenceOutput)
        self.assertIsNone(outputs[1].tts_meta)

    async def test_tool_round_limit_adds_final_note(self):
        llm = ScriptedLLM(
            [
                ['{"type":"tool_request","calls":[{"tool":"look_at_screen","args":{}}]}'],
                ['{"type":"tool_request","calls":[{"tool":"look_at_screen","args":{}}]}'],
            ]
        )
        memory = FakeMemoryStore()
        agent = BasicMemoryAgent(
            llm=llm,
            system="Return JSON with spoken_text subtitle_text reason_code",
            live2d_model=None,
            tts_preprocessor_config=tts_config(),
        )
        with patch(
            "open_llm_vtuber.agent.agents.basic_memory_agent.get_default_tool_runner",
            return_value=FakeRunner(),
        ), patch(
            "open_llm_vtuber.agent.agents.basic_memory_agent.get_default_settings_store",
            return_value=FakeSettingsStore(max_tool_rounds=1),
        ), patch(
            "open_llm_vtuber.agent.agents.basic_memory_agent.get_default_memory_store",
            return_value=memory,
        ):
            outputs = await self.collect(agent)

        self.assertIn("工具轮已用尽", llm.calls[1]["system"])
        self.assertIsInstance(outputs[-1], SentenceOutput)

    async def test_tool_failure_invalid_final_uses_tool_spoken_error(self):
        llm = ScriptedLLM(
            [
                ['{"type":"tool_request","calls":[{"tool":"web_search","args":{"query":"Rikka"}}]}'],
                ["搜索好像失败了，我先凭印象说。"],
            ]
        )
        memory = FakeMemoryStore()
        agent = BasicMemoryAgent(
            llm=llm,
            system="Return JSON with spoken_text subtitle_text reason_code",
            live2d_model=None,
            tts_preprocessor_config=tts_config(),
        )
        with patch(
            "open_llm_vtuber.agent.agents.basic_memory_agent.get_default_tool_runner",
            return_value=FailingSearchRunner(),
        ), patch(
            "open_llm_vtuber.agent.agents.basic_memory_agent.get_default_settings_store",
            return_value=FakeSettingsStore(),
        ), patch(
            "open_llm_vtuber.agent.agents.basic_memory_agent.get_default_memory_store",
            return_value=memory,
        ):
            outputs = await self.collect(agent)

        self.assertIsInstance(outputs[-1], SentenceOutput)
        self.assertEqual(
            outputs[-1].tts_text,
            "我想查来着，但网络好像不太给力，先凭印象说啦。",
        )

    async def test_proactive_empty_response_skips_audible_fallback(self):
        llm = ScriptedLLM(
            [
                [
                    json.dumps(
                        {
                            "spoken_text": "",
                            "subtitle_text": "",
                            "emotion": "quiet",
                            "motion": "idle",
                            "gaze": "camera",
                            "priority": "low",
                            "interruptible": True,
                            "reason_code": "idle_fill",
                        }
                    )
                ]
            ]
        )
        agent = BasicMemoryAgent(
            llm=llm,
            system="Return JSON with spoken_text subtitle_text reason_code",
            live2d_model=None,
            tts_preprocessor_config=tts_config(),
        )

        with patch(
            "open_llm_vtuber.agent.agents.basic_memory_agent.get_default_tool_runner",
            return_value=EmptyRunner(),
        ), patch(
            "open_llm_vtuber.agent.agents.basic_memory_agent.get_default_settings_store",
            return_value=FakeSettingsStore(tools_enabled=False),
        ), patch(
            "open_llm_vtuber.agent.agents.basic_memory_agent.get_default_memory_store",
            return_value=FakeMemoryStore(),
        ):
            outputs = await self.collect_proactive(agent)

        self.assertEqual(len(outputs), 1)
        self.assertEqual(outputs[0]["type"], "rikka_validation_status")
        self.assertFalse(outputs[0]["ok"])
        self.assertTrue(outputs[0]["silent"])
        self.assertEqual(outputs[0]["failure_kind"], "empty_proactive_response")

    async def test_non_proactive_empty_response_still_uses_fallback(self):
        llm = ScriptedLLM(
            [
                [
                    json.dumps(
                        {
                            "spoken_text": "",
                            "subtitle_text": "",
                            "emotion": "quiet",
                            "motion": "idle",
                            "gaze": "camera",
                            "priority": "low",
                            "interruptible": True,
                            "reason_code": "idle_fill",
                        }
                    )
                ]
            ]
        )
        agent = BasicMemoryAgent(
            llm=llm,
            system="Return JSON with spoken_text subtitle_text reason_code",
            live2d_model=None,
            tts_preprocessor_config=tts_config(),
        )

        with patch(
            "open_llm_vtuber.agent.agents.basic_memory_agent.get_default_tool_runner",
            return_value=EmptyRunner(),
        ), patch(
            "open_llm_vtuber.agent.agents.basic_memory_agent.get_default_settings_store",
            return_value=FakeSettingsStore(tools_enabled=False),
        ), patch(
            "open_llm_vtuber.agent.agents.basic_memory_agent.get_default_memory_store",
            return_value=FakeMemoryStore(),
        ):
            outputs = await self.collect(agent)

        self.assertEqual(outputs[0]["type"], "rikka_validation_status")
        self.assertIsInstance(outputs[1], SentenceOutput)
        self.assertEqual(outputs[1].tts_text, "嗯...我听到了。先把这段回响轻轻放好。")
        self.assertEqual(outputs[0]["failure_kind"], "schema_error")
        self.assertEqual(outputs[0]["fallback_reason_code"], "safety_fallback")

    async def test_incomplete_json_is_repaired_and_diagnosed_without_fallback(self):
        llm = ScriptedLLM(
            [
                [
                    json.dumps(
                        {
                            "spoken_text": "嗯…这些整齐的文字，看起来很复杂呢。[quiet]",
                            "emotion": "quiet",
                            "motion": "look_close",
                            "gaze": "game",
                            "priority": "low",
                            "interruptible": True,
                            "reason_code": "game_comment",
                            "memory_writes": [],
                        },
                        ensure_ascii=False,
                    )
                ]
            ]
        )
        agent = BasicMemoryAgent(
            llm=llm,
            system="Return JSON with spoken_text subtitle_text reason_code",
            live2d_model=None,
            tts_preprocessor_config=tts_config(),
        )

        with patch(
            "open_llm_vtuber.agent.agents.basic_memory_agent.get_default_tool_runner",
            return_value=EmptyRunner(),
        ), patch(
            "open_llm_vtuber.agent.agents.basic_memory_agent.get_default_settings_store",
            return_value=FakeSettingsStore(tools_enabled=False),
        ), patch(
            "open_llm_vtuber.agent.agents.basic_memory_agent.get_default_memory_store",
            return_value=FakeMemoryStore(),
        ):
            outputs = await self.collect(agent)

        event = outputs[0]
        self.assertEqual(event["type"], "rikka_validation_status")
        self.assertTrue(event["ok"])
        self.assertTrue(event["repaired"])
        self.assertFalse(event["fallback"])
        self.assertEqual(event["failure_kind"], "schema_repaired")
        self.assertIn("subtitle_text defaulted from spoken_text", event["repair_notes"])
        self.assertIn("spoken_text", event["raw_response_text"])
        self.assertIn("这些整齐的文字", event["raw_response_text"])
        self.assertIsInstance(outputs[1], SentenceOutput)
        self.assertEqual(outputs[1].tts_text, "嗯…这些整齐的文字，看起来很复杂呢。")

    async def test_malformed_response_with_spoken_text_is_repaired_without_fallback(self):
        llm = ScriptedLLM(
            [
                [
                    '前面乱掉了 "spoken_text": "先按这句话说。[quiet]" '
                    '"motion": "backflip" 后面也不是 JSON'
                ]
            ]
        )
        agent = BasicMemoryAgent(
            llm=llm,
            system="Return JSON with spoken_text subtitle_text reason_code",
            live2d_model=None,
            tts_preprocessor_config=tts_config(),
        )

        with patch(
            "open_llm_vtuber.agent.agents.basic_memory_agent.get_default_tool_runner",
            return_value=EmptyRunner(),
        ), patch(
            "open_llm_vtuber.agent.agents.basic_memory_agent.get_default_settings_store",
            return_value=FakeSettingsStore(tools_enabled=False),
        ), patch(
            "open_llm_vtuber.agent.agents.basic_memory_agent.get_default_memory_store",
            return_value=FakeMemoryStore(),
        ):
            outputs = await self.collect(agent)

        event = outputs[0]
        self.assertEqual(event["type"], "rikka_validation_status")
        self.assertTrue(event["ok"])
        self.assertTrue(event["repaired"])
        self.assertFalse(event["fallback"])
        self.assertEqual(event["failure_kind"], "schema_repaired")
        self.assertIn(
            "spoken_text extracted from malformed response",
            event["repair_notes"],
        )
        self.assertIsInstance(outputs[1], SentenceOutput)
        self.assertEqual(outputs[1].tts_text, "先按这句话说。")

    async def test_plain_text_response_is_repaired_without_fallback(self):
        llm = ScriptedLLM(
            [
                [
                    "(轻轻歪头) Deliaru，你在研究什么有趣的东西吗？"
                    "看起来好厉害的样子。"
                ]
            ]
        )
        agent = BasicMemoryAgent(
            llm=llm,
            system="Return JSON with spoken_text subtitle_text reason_code",
            live2d_model=None,
            tts_preprocessor_config=tts_config(),
        )

        with patch(
            "open_llm_vtuber.agent.agents.basic_memory_agent.get_default_tool_runner",
            return_value=EmptyRunner(),
        ), patch(
            "open_llm_vtuber.agent.agents.basic_memory_agent.get_default_settings_store",
            return_value=FakeSettingsStore(tools_enabled=False),
        ), patch(
            "open_llm_vtuber.agent.agents.basic_memory_agent.get_default_memory_store",
            return_value=FakeMemoryStore(),
        ):
            outputs = await self.collect(agent)

        event = outputs[0]
        self.assertEqual(event["type"], "rikka_validation_status")
        self.assertTrue(event["ok"])
        self.assertTrue(event["repaired"])
        self.assertFalse(event["fallback"])
        self.assertEqual(event["failure_kind"], "schema_repaired")
        self.assertIn("plain text used as spoken_text", event["repair_notes"])
        self.assertIsInstance(outputs[1], SentenceOutput)
        self.assertEqual(
            outputs[1].tts_text,
            "Deliaru，你在研究什么有趣的东西吗？看起来好厉害的样子。",
        )

    async def test_invalid_rikka_response_event_includes_safe_diagnostics(self):
        llm = ScriptedLLM(
            [
                [
                    "plain text sk-secret-demo-1234567890 "
                    + "data:image/png;base64,"
                    + ("a" * 160)
                ]
            ]
        )
        agent = BasicMemoryAgent(
            llm=llm,
            system="Return JSON with spoken_text subtitle_text reason_code",
            live2d_model=None,
            tts_preprocessor_config=tts_config(),
        )

        with patch(
            "open_llm_vtuber.agent.agents.basic_memory_agent.get_default_tool_runner",
            return_value=EmptyRunner(),
        ), patch(
            "open_llm_vtuber.agent.agents.basic_memory_agent.get_default_settings_store",
            return_value=FakeSettingsStore(tools_enabled=False),
        ), patch(
            "open_llm_vtuber.agent.agents.basic_memory_agent.get_default_memory_store",
            return_value=FakeMemoryStore(),
        ):
            outputs = await self.collect_with_image(agent)

        event = outputs[0]
        self.assertEqual(event["type"], "rikka_validation_status")
        self.assertEqual(event["failure_kind"], "missing_json")
        self.assertEqual(event["attached_image_count"], 1)
        self.assertEqual(len(event["raw_response_hash"]), 16)
        self.assertIn("plain text", event["raw_response_excerpt"])
        self.assertIn("plain text", event["raw_response_text"])
        self.assertNotIn("sk-secret-demo", event["raw_response_excerpt"])
        self.assertNotIn("sk-secret-demo", event["raw_response_text"])
        self.assertNotIn("data:image", event["raw_response_excerpt"])
        self.assertNotIn("data:image", event["raw_response_text"])
        self.assertEqual(event["fallback_reason_code"], "safety_fallback")
        self.assertIn("我听到了", event["fallback_spoken_preview"])

    async def test_non_text_llm_delta_is_preserved_for_diagnostics(self):
        llm = ScriptedLLM(
            [
                [
                    {
                        "type": "raw_delta",
                        "source": "chat",
                        "data": {
                            "delta": {
                                "reasoning_content": "我先想一下，但没有输出 JSON。"
                            },
                            "finish_reason": "stop",
                        },
                    }
                ]
            ]
        )
        agent = BasicMemoryAgent(
            llm=llm,
            system="Return JSON with spoken_text subtitle_text reason_code",
            live2d_model=None,
            tts_preprocessor_config=tts_config(),
        )

        with patch(
            "open_llm_vtuber.agent.agents.basic_memory_agent.get_default_tool_runner",
            return_value=EmptyRunner(),
        ), patch(
            "open_llm_vtuber.agent.agents.basic_memory_agent.get_default_settings_store",
            return_value=FakeSettingsStore(tools_enabled=False),
        ), patch(
            "open_llm_vtuber.agent.agents.basic_memory_agent.get_default_memory_store",
            return_value=FakeMemoryStore(),
        ):
            outputs = await self.collect(agent)

        event = outputs[0]
        self.assertEqual(event["type"], "rikka_validation_status")
        self.assertFalse(event["ok"])
        self.assertEqual(event["failure_kind"], "missing_json")
        self.assertGreater(event["raw_response_length"], 0)
        self.assertNotEqual(event["raw_response_hash"], "e3b0c44298fc1c14")
        self.assertIn("raw_delta", event["raw_response_text"])
        self.assertIn("reasoning_content", event["raw_response_text"])
        self.assertIsInstance(outputs[1], SentenceOutput)
        self.assertEqual(outputs[1].tts_text, "嗯...我听到了。先把这段回响轻轻放好。")

    async def test_provider_error_event_keeps_provider_kind_distinct(self):
        llm = ScriptedLLM(
            [
                [
                    "Error calling the responses endpoint: provider returned HTTP 502. "
                    "Detail: upstream failed with Authorization=Bearer secret-token-1234567890."
                ]
            ]
        )
        agent = BasicMemoryAgent(
            llm=llm,
            system="Return JSON with spoken_text subtitle_text reason_code",
            live2d_model=None,
            tts_preprocessor_config=tts_config(),
        )

        with patch(
            "open_llm_vtuber.agent.agents.basic_memory_agent.get_default_tool_runner",
            return_value=EmptyRunner(),
        ), patch(
            "open_llm_vtuber.agent.agents.basic_memory_agent.get_default_settings_store",
            return_value=FakeSettingsStore(tools_enabled=False),
        ), patch(
            "open_llm_vtuber.agent.agents.basic_memory_agent.get_default_memory_store",
            return_value=FakeMemoryStore(),
        ):
            outputs = await self.collect(agent)

        event = outputs[0]
        self.assertEqual(event["failure_kind"], "provider_error")
        self.assertTrue(event["provider_error"])
        self.assertEqual(event["provider_endpoint"], "responses")
        self.assertEqual(event["provider_status_code"], 502)
        self.assertNotIn("secret-token", event["provider_error_detail"])

    async def test_mood_and_inner_life_are_injected_and_registered(self):
        class FakeMood:
            def __init__(self):
                self.registered = []

            def prompt_block(self, _settings):
                return "【当前心情】心情不错。"

            def register_emotion(self, emotion, _settings):
                self.registered.append(emotion)

            def tts_overrides(self, _settings):
                return {"happy": 0.13}

        class FakeInnerLife:
            def prompt_block(self, _settings):
                return "【你现在正在做的事】看屏幕。"

        llm = ScriptedLLM([[rikka_json("普通回答")]])
        mood = FakeMood()
        agent = BasicMemoryAgent(
            llm=llm,
            system="Return JSON with spoken_text subtitle_text reason_code",
            live2d_model=None,
            tts_preprocessor_config=tts_config(),
        )
        def fake_apply_mood_effects(**kwargs):
            mood.register_emotion(kwargs["emotion"], kwargs["settings"])
            return {"emotion_vec": {"happy": 0.13}}

        with patch(
            "open_llm_vtuber.agent.agents.basic_memory_agent.get_default_tool_runner",
            return_value=EmptyRunner(),
        ), patch(
            "open_llm_vtuber.agent.agents.basic_memory_agent.get_default_settings_store",
            return_value=FakeSettingsStore(tools_enabled=False),
        ), patch(
            "open_llm_vtuber.agent.agents.basic_memory_agent.get_default_memory_store",
            return_value=FakeMemoryStore(),
        ), patch(
            "open_llm_vtuber.agent.agents.basic_memory_agent.get_default_mood_state",
            return_value=mood,
        ), patch(
            "open_llm_vtuber.agent.agents.basic_memory_agent.get_default_inner_life",
            return_value=FakeInnerLife(),
        ), patch(
            "open_llm_vtuber.agent.agents.basic_memory_agent.apply_rikka_mood_effects",
            side_effect=fake_apply_mood_effects,
        ):
            outputs = await self.collect(agent)

        self.assertIn("【当前心情】", llm.calls[0]["system"])
        self.assertIn("【你现在正在做的事】", llm.calls[0]["system"])
        self.assertEqual(mood.registered, ["curious"])
        self.assertEqual(outputs[0].tts_meta["emotion_vec"], {"happy": 0.13})

    async def test_mood_idle_expression_reuses_existing_preset(self):
        llm = ScriptedLLM([[rikka_json("开心啦").replace('"curious"', '"happy"')]])
        agent = BasicMemoryAgent(
            llm=llm,
            system="Return JSON with spoken_text subtitle_text reason_code",
            live2d_model=SimpleNamespace(
                model_info={
                    "expressionPresets": {
                        "neutral": {"parameters": {}},
                        "soft_smile": {
                            "parameters": {
                                "ParamMouthForm": 0.15,
                                "ParamEyeLSmile": 0.25,
                            },
                            "fade_ms": 400,
                        },
                    }
                },
            ),
            tts_preprocessor_config=tts_config(),
        )
        with patch(
            "open_llm_vtuber.agent.agents.basic_memory_agent.get_default_tool_runner",
            return_value=EmptyRunner(),
        ), patch(
            "open_llm_vtuber.agent.agents.basic_memory_agent.get_default_settings_store",
            return_value=FakeSettingsStore(tools_enabled=False),
        ), patch(
            "open_llm_vtuber.agent.agents.basic_memory_agent.get_default_memory_store",
            return_value=FakeMemoryStore(),
        ):
            outputs = await self.collect(agent)

        action_payload = outputs[0].actions.to_dict()
        self.assertEqual(action_payload["mood_idle_expression"]["name"], "soft_smile")
        self.assertEqual(
            action_payload["mood_idle_expression"]["preset"]["parameters"][
                "ParamMouthForm"
            ],
            0.15,
        )


if __name__ == "__main__":
    unittest.main()

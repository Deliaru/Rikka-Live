import asyncio
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from open_llm_vtuber.rikka.memory import MemoryStore
from open_llm_vtuber.rikka.planner import RikkaStructuredPlanner
from open_llm_vtuber.rikka.schemas import LiveEvent, MemoryWrite


class FakeAsyncLLM:
    def __init__(self, chunks):
        self.chunks = chunks
        self.calls = []

    async def chat_completion(self, messages, system=None, tools=None):
        self.calls.append({"messages": messages, "system": system, "tools": tools})
        for chunk in self.chunks:
            yield chunk


class SlowAsyncLLM:
    def __init__(self):
        self.calls = 0

    async def chat_completion(self, messages, system=None, tools=None):
        self.calls += 1
        await asyncio.sleep(0.05)
        yield "{}"


class ErrorTextAsyncLLM:
    def __init__(self, text):
        self.text = text
        self.calls = 0

    async def chat_completion(self, messages, system=None, tools=None):
        self.calls += 1
        yield self.text


class RikkaStructuredPlannerTest(unittest.TestCase):
    def _event(self):
        return LiveEvent.model_validate(
            {
                "type": "chat.message",
                "source": "debug",
                "actor": {"display_name": "alice"},
                "text": "六花晚上好",
            }
        )

    def test_llm_json_response_is_validated(self):
        async def run():
            llm = FakeAsyncLLM(
                [
                    '{"spoken_text":"晚上好，alice。今晚也轻轻开始吧。",',
                    '"subtitle_text":"晚上好，alice。","emotion":"soft_smile",',
                    '"motion":"nod","gaze":"chat","priority":"normal",',
                    '"interruptible":true,"reason_code":"reply_chat"}',
                ]
            )
            planner = RikkaStructuredPlanner(
                llm=llm,
                system_prompt="system",
                provider_name="fake",
                model_name="fake-model",
            )
            result = await planner.plan(self._event())
            return result, planner.status()

        result, status = asyncio.run(run())

        self.assertTrue(result.ok)
        self.assertEqual(result.response.reason_code, "reply_chat")
        self.assertEqual(status["mode"], "llm_structured")
        self.assertTrue(status["available"])

    def test_invalid_llm_output_falls_back(self):
        async def run():
            planner = RikkaStructuredPlanner(
                llm=FakeAsyncLLM(["<thinking>secret</thinking>not json"]),
                system_prompt="system",
            )
            result = await planner.plan(self._event())
            return result, planner.status()

        result, status = asyncio.run(run())

        self.assertFalse(result.ok)
        self.assertEqual(result.response.reason_code, "safety_fallback")
        self.assertEqual(status["mode"], "fallback")
        self.assertNotIn("<thinking>", result.response.spoken_text)
        self.assertTrue(status["last_error"])
        self.assertEqual(status["last_error_kind"], "validation")

    def test_provider_error_text_is_not_silent_fallback(self):
        async def run():
            planner = RikkaStructuredPlanner(
                llm=ErrorTextAsyncLLM(
                    "Error calling the chat endpoint: Rate limit exceeded."
                ),
                system_prompt="system",
            )
            result = await planner.plan(self._event())
            return result, planner.status()

        result, status = asyncio.run(run())

        self.assertFalse(result.ok)
        self.assertEqual(result.response.reason_code, "reply_chat")
        self.assertEqual(status["mode"], "fallback")
        self.assertEqual(status["last_error_kind"], "provider_error")
        self.assertIn("Rate limit exceeded", status["last_error"])
        self.assertGreater(status["retry_after_ms"], 0)

    def test_timeout_falls_back_with_observable_error(self):
        async def run():
            planner = RikkaStructuredPlanner(
                llm=SlowAsyncLLM(),
                system_prompt="system",
                timeout_seconds=0.01,
            )
            result = await planner.plan(self._event())
            return result, planner.status()

        result, status = asyncio.run(run())

        self.assertFalse(result.ok)
        self.assertEqual(result.response.reason_code, "reply_chat")
        self.assertEqual(status["mode"], "fallback")
        self.assertIn("timed out", status["last_error"])
        self.assertEqual(status["last_error_kind"], "timeout")
        self.assertGreater(status["retry_after_ms"], 0)

    def test_failure_cooldown_skips_next_llm_call(self):
        async def run():
            llm = SlowAsyncLLM()
            planner = RikkaStructuredPlanner(
                llm=llm,
                system_prompt="system",
                timeout_seconds=0.01,
                failure_cooldown_seconds=1.0,
            )
            first = await planner.plan(self._event())
            second = await planner.plan(self._event())
            return first, second, planner.status(), llm.calls

        first, second, status, calls = asyncio.run(run())

        self.assertFalse(first.ok)
        self.assertFalse(second.ok)
        self.assertEqual(first.response.reason_code, "reply_chat")
        self.assertEqual(second.response.reason_code, "reply_chat")
        self.assertEqual(calls, 1)
        self.assertEqual(status["mode"], "fallback")
        self.assertIn("fallback cooldown", status["last_error"])
        self.assertEqual(status["last_error_kind"], "cooldown")

    def test_candidate_response_bypasses_llm_call(self):
        async def run():
            llm = FakeAsyncLLM(["not used"])
            planner = RikkaStructuredPlanner(llm=llm, system_prompt="system")
            result = await planner.plan(
                self._event(),
                candidate_response={
                    "spoken_text": "候选响应已接收。",
                    "subtitle_text": "候选响应已接收。",
                    "emotion": "neutral",
                    "motion": "idle",
                    "gaze": "camera",
                    "priority": "low",
                    "interruptible": True,
                    "reason_code": "idle_fill",
                },
            )
            return result, planner.status(), llm.calls

        result, status, calls = asyncio.run(run())

        self.assertTrue(result.ok)
        self.assertEqual(result.response.reason_code, "idle_fill")
        self.assertEqual(status["mode"], "candidate_response")
        self.assertEqual(calls, [])

    def test_event_and_memory_summary_are_sent_to_llm(self):
        async def run():
            with tempfile.TemporaryDirectory() as tmp_dir:
                memory = MemoryStore(Path(tmp_dir) / "memory.json")
                memory.upsert(
                    MemoryWrite(
                        kind="viewer_note",
                        key="alice",
                        value="喜欢安静陪播",
                    )
                )
                llm = FakeAsyncLLM(
                    [
                        '{"spoken_text":"记得的。","subtitle_text":"记得的。",'
                        '"emotion":"soft_smile","motion":"nod","gaze":"chat",'
                        '"priority":"normal","interruptible":true,'
                        '"reason_code":"memory_recall"}'
                    ]
                )
                planner = RikkaStructuredPlanner(
                    memory_store=memory,
                    llm=llm,
                    system_prompt="system",
                )
                await planner.plan(self._event())
                return llm.calls[0]["messages"][0]["content"]

        prompt = asyncio.run(run())

        self.assertIn("viewer_note:alice=喜欢安静陪播", prompt)
        self.assertIn('"type": "chat.message"', prompt)

    def test_identity_block_is_injected_into_planner_system_prompt(self):
        async def run():
            llm = FakeAsyncLLM(
                [
                    '{"spoken_text":"收到。","subtitle_text":"收到。",'
                    '"emotion":"soft_smile","motion":"nod","gaze":"chat",'
                    '"priority":"normal","interruptible":true,'
                    '"reason_code":"reply_chat"}'
                ]
            )
            planner = RikkaStructuredPlanner(llm=llm, system_prompt="base system")
            fake_store = SimpleNamespace(
                snapshot=lambda: SimpleNamespace(
                    identity=SimpleNamespace(
                        host_display_name="\u4e3b\u64ad\u7532",
                        audience_display_name="\u89c2\u4f17\u5e2d",
                    )
                )
            )
            with patch(
                "open_llm_vtuber.rikka.planner.get_default_settings_store",
                return_value=fake_store,
            ):
                await planner.plan(self._event())
            return llm.calls[0]["system"]

        system = asyncio.run(run())

        self.assertIn("base system", system)
        self.assertIn("\u4e3b\u64ad\u300c\u4e3b\u64ad\u7532\u300d", system)
        self.assertIn(
            "\u79f0\u547c\u4e3b\u64ad\u4e3a\u300c\u4e3b\u64ad\u7532\u300d",
            system,
        )
        self.assertIn("\u7238\u7238\u3001\u7236\u4eb2\u6216\u4e3b\u4eba", system)
        self.assertIn("source=bilibili", system)
        self.assertIn("\u300c\u89c2\u4f17\u5e2d\u300d", system)


if __name__ == "__main__":
    unittest.main()

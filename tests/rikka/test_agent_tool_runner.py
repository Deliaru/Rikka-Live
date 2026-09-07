import asyncio
import unittest
from types import SimpleNamespace

from open_llm_vtuber.rikka.agent_tools import (
    RikkaToolRunner,
    build_tool_result_content,
    parse_tool_request,
)


class FakeSettingsStore:
    def __init__(self, tools_enabled=True):
        self.agent = SimpleNamespace(
            tools_enabled=tools_enabled,
            look_at_screen_enabled=True,
            get_time_enabled=True,
            web_search_enabled=True,
            filler_enabled=True,
            result_pre_silence_ms=1000,
            max_tool_rounds=3,
            web_search_timeout_seconds=1,
        )

    def snapshot(self):
        return SimpleNamespace(agent=self.agent)


class FakeFrame:
    width = 640
    height = 360
    window = SimpleNamespace(title="Unit Test Window")

    def data_url(self):
        return "data:image/jpeg;base64,abc123"


class FakeCapture:
    def __init__(self, status):
        self.status = status

    def capture_keyframe(self, force=False):
        return self.status

    def latest_frame(self):
        return FakeFrame() if self.status.get("status") == "captured" else None


class FakeTool:
    name = "search"


class FakeMcpClient:
    def __init__(self):
        self.list_tools_calls = 0
        self.call_tool_calls = 0
        self.close_calls = 0

    async def list_tools(self, server_name):
        self.list_tools_calls += 1
        return [FakeTool()]

    async def call_tool(self, server_name, tool_name, tool_args):
        self.call_tool_calls += 1
        return {
            "content_items": [
                {"type": "text", "text": "result " * 400},
            ]
        }

    async def aclose(self):
        self.close_calls += 1


class SlowMcpClient(FakeMcpClient):
    async def call_tool(self, server_name, tool_name, tool_args):
        self.call_tool_calls += 1
        await asyncio.sleep(2)
        return {"content_items": [{"type": "text", "text": "late"}]}


class SlowListFastCallMcpClient(FakeMcpClient):
    async def list_tools(self, server_name):
        self.list_tools_calls += 1
        await asyncio.sleep(2)
        return [FakeTool()]


class CloseErrorMcpClient(FakeMcpClient):
    async def aclose(self):
        self.close_calls += 1
        raise RuntimeError("close failed")


class RikkaToolRunnerTests(unittest.IsolatedAsyncioTestCase):
    def test_parse_tool_request(self):
        request = parse_tool_request(
            '{"type":"tool_request","calls":[{"tool":"get_time","args":{}}]}'
        )
        self.assertIsNotNone(request)
        self.assertEqual(request.calls[0]["tool"], "get_time")
        self.assertIsNone(parse_tool_request('{"spoken_text":"hi"}'))
        self.assertIsNone(parse_tool_request("not json"))

    def test_available_tools_respects_master_switch(self):
        runner = RikkaToolRunner(
            settings_store=FakeSettingsStore(tools_enabled=False),
            capture_service=FakeCapture({"status": "disabled"}),
        )
        self.assertEqual(runner.available_tools(), [])

    async def test_look_at_screen_disabled_returns_spoken_error(self):
        runner = RikkaToolRunner(
            settings_store=FakeSettingsStore(),
            capture_service=FakeCapture({"status": "disabled", "reason": "off"}),
        )

        events = []
        async for event in runner.run_iter([{"tool": "look_at_screen", "args": {}}]):
            events.append(event)

        results = events[-1][1]
        self.assertFalse(results[0].ok)
        self.assertIn("权限", results[0].spoken_error)
        self.assertNotIn("data:image", str(events[:-1]))

    async def test_look_at_screen_captured_adds_image_only_to_result_content(self):
        runner = RikkaToolRunner(
            settings_store=FakeSettingsStore(),
            capture_service=FakeCapture({"status": "captured"}),
        )

        events = []
        async for event in runner.run_iter([{"tool": "look_at_screen", "args": {}}]):
            events.append(event)

        results = events[-1][1]
        self.assertTrue(results[0].ok)
        self.assertEqual(results[0].image_data_url, "data:image/jpeg;base64,abc123")
        self.assertEqual(events[-2]["tool_kind"], "native")
        self.assertTrue(events[-2]["ok"])
        self.assertEqual(events[-2]["result_kind"], "image")
        self.assertEqual(events[-2]["result_summary"], "captured image")
        self.assertIn("duration_ms", events[-2])
        content = build_tool_result_content(results)
        self.assertEqual(content[1]["type"], "image_url")
        self.assertNotIn("data:image", str(events[:-1]))

    async def test_get_time_returns_local_time_text(self):
        runner = RikkaToolRunner(
            settings_store=FakeSettingsStore(),
            capture_service=FakeCapture({"status": "disabled"}),
        )

        events = []
        async for event in runner.run_iter([{"tool": "get_time", "args": {}}]):
            events.append(event)

        self.assertIn("现在是", events[-1][1][0].text)

    async def test_web_search_uses_fake_mcp_and_truncates(self):
        client = FakeMcpClient()
        runner = RikkaToolRunner(
            settings_store=FakeSettingsStore(),
            capture_service=FakeCapture({"status": "disabled"}),
            mcp_client_factory=lambda: client,
        )

        events = []
        async for event in runner.run_iter(
            [{"tool": "web_search", "args": {"query": "Rikka"}}]
        ):
            events.append(event)

        result = events[-1][1][0]
        self.assertTrue(result.ok)
        self.assertLessEqual(len(result.text), 1600)
        self.assertEqual(events[-2]["tool_kind"], "mcp")
        self.assertEqual(events[-2]["result_kind"], "text")
        self.assertEqual(events[-2]["result_summary"], "search results received")
        self.assertTrue(runner.status()["mcp"]["mcp_tool_verified"])
        self.assertEqual(client.list_tools_calls, 0)
        self.assertEqual(client.call_tool_calls, 1)

    async def test_web_search_does_not_spend_timeout_on_list_tools(self):
        client = SlowListFastCallMcpClient()
        runner = RikkaToolRunner(
            settings_store=FakeSettingsStore(),
            capture_service=FakeCapture({"status": "disabled"}),
            mcp_client_factory=lambda: client,
        )

        events = []
        async for event in runner.run_iter(
            [{"tool": "web_search", "args": {"query": "Rikka"}}]
        ):
            events.append(event)

        self.assertTrue(events[-1][1][0].ok)
        self.assertEqual(client.list_tools_calls, 0)
        self.assertEqual(client.call_tool_calls, 1)

    async def test_web_search_timeout_degrades(self):
        client = SlowMcpClient()
        runner = RikkaToolRunner(
            settings_store=FakeSettingsStore(),
            capture_service=FakeCapture({"status": "disabled"}),
            mcp_client_factory=lambda: client,
        )

        events = []
        async for event in runner.run_iter(
            [{"tool": "web_search", "args": {"query": "Rikka"}}]
        ):
            events.append(event)

        result = events[-1][1][0]
        self.assertFalse(result.ok)
        self.assertIn("网络", result.spoken_error)
        self.assertEqual(runner.status()["last_error"], "TimeoutError")
        self.assertEqual(client.close_calls, 1)
        self.assertIsNone(runner._mcp_client)

    async def test_aclose_swallows_mcp_close_errors(self):
        client = CloseErrorMcpClient()
        runner = RikkaToolRunner(
            settings_store=FakeSettingsStore(),
            capture_service=FakeCapture({"status": "disabled"}),
            mcp_client_factory=lambda: client,
        )
        await runner._mcp()

        await runner.aclose()

        self.assertEqual(client.close_calls, 1)
        self.assertIsNone(runner._mcp_client)


if __name__ == "__main__":
    unittest.main()

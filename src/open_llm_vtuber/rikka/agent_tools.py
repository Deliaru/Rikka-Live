"""Self-directed tool calling for the Rikka conversation agent.

The ddg-search MCP server is expected to expose a `search` tool accepting
`query` and `max_results`. Runtime status reports `mcp_tool_verified` after a
successful tool listing confirms that name.
"""

from __future__ import annotations

import asyncio
import json
import random
import shutil
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, AsyncIterator, Literal
from uuid import uuid4

from loguru import logger

from .capture import get_default_capture_service
from .core import _extract_json_object
from .settings import get_default_settings_store

TOOL_REQUEST_TYPE = "tool_request"
MAX_CALLS_PER_ROUND = 2
WEB_SEARCH_RESULT_CHAR_LIMIT = 1500


def _now_ms() -> int:
    return int(time.time() * 1000)


def _utc_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def _describe_exception(exc: BaseException) -> str:
    message = str(exc).strip()
    if message:
        return f"{type(exc).__name__}: {message}"
    return type(exc).__name__


@dataclass(frozen=True)
class RikkaToolSpec:
    name: str
    description: str
    args_hint: str
    kind: Literal["native", "mcp"]
    mcp_server: str = ""
    mcp_tool: str = ""
    filler: bool = True


@dataclass
class RikkaToolResult:
    tool: str
    ok: bool
    text: str
    image_data_url: str | None = None
    spoken_error: str | None = None
    duration_ms: int = 0


@dataclass
class RikkaToolRequest:
    calls: list[dict[str, Any]]


FILLER_TEMPLATES = {
    "look_at_screen": ["我看看哦……", "稍等，我瞄一眼屏幕。", "让我看一下你的屏幕哈。"],
    "web_search": ["这个我查一下哈……", "唔，等我搜搜看。", "稍等哦，我去查查。"],
}

TOOL_SPECS = {
    "look_at_screen": RikkaToolSpec(
        name="look_at_screen",
        description="截取主播侧屏幕上白名单窗口的当前画面。被问屏幕上是什么或帮忙看看游戏时使用。",
        args_hint="{}",
        kind="native",
    ),
    "get_time": RikkaToolSpec(
        name="get_time",
        description="获取现在的本地日期和时间。",
        args_hint="{}",
        kind="native",
        filler=False,
    ),
    "web_search": RikkaToolSpec(
        name="web_search",
        description="搜索互联网，获取你不知道或可能过时的信息。",
        args_hint='{"query": "搜索词"}',
        kind="mcp",
        mcp_server="ddg-search",
        mcp_tool="search",
    ),
}


def parse_tool_request(raw: str) -> RikkaToolRequest | None:
    try:
        extracted = _extract_json_object(raw)
    except (ValueError, json.JSONDecodeError, TypeError):
        return None
    if extracted is None or extracted.get("type") != TOOL_REQUEST_TYPE:
        return None
    calls = extracted.get("calls")
    if not isinstance(calls, list) or not calls:
        return None
    normalized_calls: list[dict[str, Any]] = []
    for call in calls[:MAX_CALLS_PER_ROUND]:
        if not isinstance(call, dict):
            continue
        tool = call.get("tool")
        args = call.get("args", {})
        if isinstance(tool, str):
            normalized_calls.append({"tool": tool, "args": args if isinstance(args, dict) else {}})
    return RikkaToolRequest(calls=normalized_calls) if normalized_calls else None


def build_tool_result_content(results: list[RikkaToolResult]) -> list[dict[str, Any]]:
    text = "\n\n".join(result.text for result in results if result.text)
    content: list[dict[str, Any]] = [
        {"type": "text", "text": f"[工具结果]\n{text}" if text else "[工具结果]\n（没有结果）"}
    ]
    for result in results:
        if result.image_data_url:
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": result.image_data_url, "detail": "auto"},
                }
            )
    return content


class RikkaToolRunner:
    """Runs privacy-gated Rikka tools for the direct conversation path."""

    def __init__(
        self,
        settings_store=None,
        capture_service=None,
        clock_ms=_now_ms,
        mcp_client_factory=None,
    ) -> None:
        self.settings_store = settings_store or get_default_settings_store()
        self.capture_service = capture_service or get_default_capture_service()
        self.clock_ms = clock_ms
        self.mcp_client_factory = mcp_client_factory
        self._mcp_client = None
        self._mcp_tool_verified = False
        self._last_filler = ""
        self._last_tool: dict[str, Any] | None = None
        self._last_error = ""

    def _settings(self):
        return self.settings_store.snapshot().agent

    def available_tools(self) -> list[RikkaToolSpec]:
        settings = self._settings()
        if not settings.tools_enabled:
            return []
        specs: list[RikkaToolSpec] = []
        if settings.look_at_screen_enabled:
            specs.append(TOOL_SPECS["look_at_screen"])
        if settings.get_time_enabled:
            specs.append(TOOL_SPECS["get_time"])
        if settings.web_search_enabled:
            specs.append(TOOL_SPECS["web_search"])
        return specs

    def tool_protocol_block(self) -> str:
        specs = self.available_tools()
        if not specs:
            return ""
        max_rounds = self._settings().max_tool_rounds
        lines = [
            "【可用工具】",
            "这些工具已经由后端接好，出现在本列表就表示当前可请求；不要回答“我没有外部搜索入口/不能联网”。",
            "如果用户明确要求你搜索、查询今天/最新/近期事实，或问题依赖你可能不知道的外部信息，先请求合适工具；否则照常输出 RikkaResponse JSON。",
            "请求工具时，只输出一个 JSON 对象（不要 Markdown、不要解释）：",
            '{"type":"tool_request","calls":[{"tool":"<工具名>","args":{...}}]}',
            "工具结果会以 [工具结果] 开头的消息回给你，之后你必须输出最终 RikkaResponse JSON。",
            f"最多请求 {max_rounds} 轮工具，单轮最多 2 个；闲聊不要调用工具。",
            "工具列表：",
        ]
        for spec in specs:
            lines.append(f"- {spec.name}：{spec.description} args: {spec.args_hint}")
        return "\n".join(lines)

    def filler_text(self, tool_names: list[str]) -> str | None:
        for name in tool_names:
            spec = TOOL_SPECS.get(name)
            templates = FILLER_TEMPLATES.get(name, [])
            if not spec or not spec.filler or not templates:
                continue
            choice = random.choice(templates)
            if len(templates) > 1 and choice == self._last_filler:
                choice = random.choice([item for item in templates if item != choice])
            self._last_filler = choice
            return choice
        return None

    async def run_iter(
        self, calls: list[dict[str, Any]]
    ) -> AsyncIterator[dict[str, Any] | tuple[str, list[RikkaToolResult]]]:
        results: list[RikkaToolResult] = []
        allowed = {spec.name for spec in self.available_tools()}
        for call in calls[:MAX_CALLS_PER_ROUND]:
            tool_name = call.get("tool")
            args = call.get("args") if isinstance(call.get("args"), dict) else {}
            tool_id = f"rikka_{uuid4().hex[:8]}"
            if tool_name not in allowed:
                result = RikkaToolResult(
                    tool=str(tool_name or "unknown"),
                    ok=False,
                    text=f"[{tool_name}] 工具不可用。请直接向用户说明这个能力现在不可用。",
                    spoken_error="这个功能现在还不能用哦。",
                )
                yield self._status_event(tool_id, result.tool, "error", "工具不可用")
                results.append(result)
                continue

            yield self._status_event(
                tool_id,
                tool_name,
                "running",
                self._status_content(tool_name, args),
            )
            start = self.clock_ms()
            try:
                result = await self._run_one(tool_name, args)
            except Exception as exc:
                logger.warning(f"Rikka tool {tool_name} failed: {exc}")
                result = RikkaToolResult(
                    tool=tool_name,
                    ok=False,
                    text=f"[{tool_name}] 工具调用失败。请口头说明暂时用不了，不要泄露内部错误。",
                    spoken_error="我试了一下，但这个工具现在好像用不了。",
                )
                self._last_error = _describe_exception(exc)[:200]
            result.duration_ms = max(0, self.clock_ms() - start)
            status = "completed" if result.ok else "error"
            yield self._status_event(
                tool_id,
                tool_name,
                status,
                self._result_status_content(result),
                result=result,
            )
            self._last_tool = {
                "name": tool_name,
                "status": status,
                "duration_ms": result.duration_ms,
                "at_ms": self.clock_ms(),
            }
            results.append(result)
        yield ("results", results)

    async def _run_one(self, tool_name: str, args: dict[str, Any]) -> RikkaToolResult:
        if tool_name == "look_at_screen":
            return await self._look_at_screen()
        if tool_name == "get_time":
            return await self._get_time()
        if tool_name == "web_search":
            return await self._web_search(args)
        return RikkaToolResult(
            tool=tool_name,
            ok=False,
            text=f"[{tool_name}] 未知工具。",
            spoken_error="这个功能现在还不能用哦。",
        )

    async def _look_at_screen(self) -> RikkaToolResult:
        status = self.capture_service.capture_keyframe(force=True)
        frame = self.capture_service.latest_frame()
        if status.get("status") == "captured" and frame is not None:
            title = getattr(getattr(frame, "window", None), "title", "") or "未知窗口"
            return RikkaToolResult(
                tool="look_at_screen",
                ok=True,
                text=f"[look_at_screen] 已截取窗口「{title}」当前画面（{frame.width}x{frame.height}），画面内容见图片。",
                image_data_url=frame.data_url(),
            )
        code = str(status.get("status") or "error")
        reason = str(status.get("reason") or "")
        spoken_error = {
            "disabled": "我现在还没有看屏幕的权限哦，要在控制台里打开才行。",
            "blocked": "我现在还没有看屏幕的权限哦，要在控制台里打开才行。",
            "waiting_for_target": "唔……我没找到能看的窗口。要把窗口加进白名单我才看得到。",
            "unavailable": "我试着看了一下，但好像出了点小状况，先不看啦。",
            "error": "我试着看了一下，但好像出了点小状况，先不看啦。",
        }.get(code, "我现在看不到屏幕哦。")
        return RikkaToolResult(
            tool="look_at_screen",
            ok=False,
            text=f"[look_at_screen] 截图失败：{code}/{reason}。请向用户口头说明你现在看不到屏幕，原因大意：{spoken_error}",
            spoken_error=spoken_error,
        )

    async def _get_time(self) -> RikkaToolResult:
        now = datetime.now()
        weekdays = "一二三四五六日"
        text = (
            f"[get_time] 现在是 {now.year}年{now.month}月{now.day}日 "
            f"星期{weekdays[now.weekday()]} {now:%H:%M}（本机时间）"
        )
        return RikkaToolResult(tool="get_time", ok=True, text=text)

    async def _mcp(self):
        if self._mcp_client is not None:
            return self._mcp_client
        if self.mcp_client_factory is not None:
            self._mcp_client = self.mcp_client_factory()
            return self._mcp_client
        from ..mcpp.mcp_client import MCPClient
        from ..mcpp.server_registry import ServerRegistry

        self._mcp_client = MCPClient(ServerRegistry())
        return self._mcp_client

    async def _reset_mcp_client(self) -> None:
        client = self._mcp_client
        self._mcp_client = None
        if client is None or not hasattr(client, "aclose"):
            return
        try:
            await client.aclose()
        except Exception as exc:
            logger.warning(f"Failed to close Rikka MCP client after tool error: {exc}")

    async def _web_search(self, args: dict[str, Any]) -> RikkaToolResult:
        query = str(args.get("query") or "").strip()
        if not query:
            return RikkaToolResult(
                tool="web_search",
                ok=False,
                text="[web_search] 缺少搜索词。请直接询问用户要查什么。",
                spoken_error="你想让我查什么呀？",
            )
        timeout = self._settings().web_search_timeout_seconds
        try:
            client = await self._mcp()
            result = await asyncio.wait_for(
                client.call_tool("ddg-search", "search", {"query": query, "max_results": 5}),
                timeout=timeout,
            )
        except Exception as exc:
            self._mcp_tool_verified = False
            self._last_error = _describe_exception(exc)[:200]
            await self._reset_mcp_client()
            return RikkaToolResult(
                tool="web_search",
                ok=False,
                text=(
                    f"[web_search] 搜索「{query}」失败：{self._last_error}。"
                    "请向用户口头说明网络或搜索工具暂时不可用，可凭已有知识谨慎回答。"
                ),
                spoken_error="我想查来着，但网络好像不太给力，先凭印象说啦。",
            )
        self._mcp_tool_verified = True
        chunks: list[str] = []
        for item in result.get("content_items", []):
            if item.get("type") in {"text", "error"} and item.get("text"):
                chunks.append(str(item["text"]))
        text = "\n".join(chunks).strip()[:WEB_SEARCH_RESULT_CHAR_LIMIT]
        if not text:
            text = "没有找到可用的搜索结果。"
        return RikkaToolResult(
            tool="web_search",
            ok=True,
            text=f"[web_search] 搜索「{query}」的结果：\n{text}",
        )

    def _status_event(
        self,
        tool_id: str,
        tool_name: str,
        status: str,
        content: str,
        *,
        result: RikkaToolResult | None = None,
    ) -> dict[str, Any]:
        spec = TOOL_SPECS.get(tool_name)
        event = {
            "type": "tool_call_status",
            "tool_id": tool_id,
            "tool_name": tool_name,
            "tool_kind": spec.kind if spec else "unknown",
            "status": status,
            "content": content[:120],
            "timestamp": _utc_iso(),
        }
        if result is not None:
            event.update(
                {
                    "ok": result.ok,
                    "duration_ms": result.duration_ms,
                    "result_kind": self._result_kind(result),
                    "result_summary": content[:120],
                }
            )
        return event

    def _status_content(self, tool_name: str, args: dict[str, Any]) -> str:
        if tool_name == "web_search":
            return f"query={str(args.get('query') or '')[:60]}"
        if tool_name == "look_at_screen":
            return "capture requested"
        return tool_name

    def _result_kind(self, result: RikkaToolResult) -> str:
        if not result.ok:
            return "error"
        if result.image_data_url:
            return "image"
        return "text"

    def _result_status_content(self, result: RikkaToolResult) -> str:
        if not result.ok:
            return result.spoken_error or "tool failed"
        if result.tool == "look_at_screen":
            return "captured image" if result.image_data_url else "capture completed"
        if result.tool == "web_search":
            return "search results received"
        if result.tool == "get_time":
            return "local time returned"
        return "tool completed"

    def status(self) -> dict[str, Any]:
        settings = self._settings()
        return {
            "enabled": settings.tools_enabled,
            "tools": {
                "look_at_screen": settings.look_at_screen_enabled,
                "get_time": settings.get_time_enabled,
                "web_search": settings.web_search_enabled,
            },
            "filler_enabled": settings.filler_enabled,
            "result_pre_silence_ms": settings.result_pre_silence_ms,
            "mcp": {
                "uvx_available": shutil.which("uvx") is not None,
                "ddg_search_session": "ready" if self._mcp_client is not None else "not_started",
                "mcp_tool_verified": self._mcp_tool_verified,
            },
            "last_tool": self._last_tool,
            "last_error": self._last_error,
        }

    async def aclose(self) -> None:
        if self._mcp_client is not None:
            try:
                await self._mcp_client.aclose()
            except Exception as exc:
                logger.warning(f"Failed to close Rikka MCP client: {exc}")
            self._mcp_client = None


_DEFAULT_RUNNER: RikkaToolRunner | None = None


def get_default_tool_runner() -> RikkaToolRunner:
    global _DEFAULT_RUNNER
    if _DEFAULT_RUNNER is None:
        _DEFAULT_RUNNER = RikkaToolRunner()
    return _DEFAULT_RUNNER


def configure_default_tool_runner(settings_store=None, capture_service=None) -> RikkaToolRunner:
    """Bind the default runner to the app-level settings and capture services."""
    runner = get_default_tool_runner()
    if settings_store is not None:
        runner.settings_store = settings_store
    if capture_service is not None:
        runner.capture_service = capture_service
    return runner

"""Bilibili live session control for the Rikka co-streaming console."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Any

from loguru import logger

from ..live.bilibili_live import (
    BLIVEDM_AVAILABLE,
    BiliBiliLivePlatform,
    build_bilibili_danmaku_event,
    get_blivedm_status,
)


RikkaEventConsumer = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]
RikkaResultEmitter = Callable[[dict[str, Any], bool], Awaitable[dict[str, Any]]]

DANMAKU_REPLY_TYPES = {"chat.message"}
HIGH_PRIORITY_EVENT_TYPES = {
    "chat.gift",
    "chat.guard",
    "chat.super_chat",
    "chat.follow",
}
CONTROL_PRIORITY_SOURCES = {"host", "screen", "system"}
CONTROL_PRIORITY_TYPES = {
    "host.note",
    "game.roi_changed",
    "game.result_detected",
    "system.test_event",
}
DANMAKU_BUSY_REASON = "Bilibili danmaku reply blocked while another turn is processing"
DANMAKU_COOLDOWN_REASON = "Bilibili danmaku reply cooldown"


def _now_ms() -> int:
    return int(time.time() * 1000)


def normalize_room_ids(room_ids: list[int] | int | None) -> list[int]:
    """Normalize user/config room IDs into a de-duplicated positive integer list."""
    if room_ids is None:
        return []
    if isinstance(room_ids, int):
        raw_items = [room_ids]
    else:
        raw_items = room_ids

    normalized: list[int] = []
    seen: set[int] = set()
    for item in raw_items:
        try:
            room_id = int(item)
        except (TypeError, ValueError):
            continue
        if room_id <= 0 or room_id in seen:
            continue
        normalized.append(room_id)
        seen.add(room_id)
    return normalized


class BilibiliLiveManager:
    """Owns one in-process Bilibili danmaku session for local demo control."""

    def __init__(
        self,
        event_consumer: RikkaEventConsumer,
        result_emitter: RikkaResultEmitter | None = None,
    ):
        self._event_consumer = event_consumer
        self._result_emitter = result_emitter
        self._lock = asyncio.Lock()
        self._platform: BiliBiliLivePlatform | None = None
        self._task: asyncio.Task | None = None
        self._room_ids: list[int] = []
        self._use_proxy = False
        self._proxy_url: str | None = None
        self._speak = True
        self._started_at_ms: int | None = None
        self._stopped_at_ms: int | None = None
        self._last_event_at_ms: int | None = None
        self._last_error: str = ""
        self._last_result: dict[str, Any] | None = None
        self._last_delivery: dict[str, Any] | None = None
        self._last_delivery_at_ms: int | None = None
        self._last_danmaku_reply_started_at_ms: int | None = None
        self._blocked_events = 0
        self._last_blocked_at_ms: int | None = None
        self._last_blocked_reason = ""
        self._last_blocked_event_type = ""
        self._last_blocked_event_kind: str | None = None
        self._last_blocked_event_priority = 0
        self._last_connect_attempt_at_ms: int | None = None
        self._connected_at_ms: int | None = None
        self._processing_events = 0
        self._last_processing_started_at_ms: int | None = None
        self._last_processing_finished_at_ms: int | None = None
        self._last_processing_stage = ""
        self._last_processing_event_kind: str | None = None
        self._last_processing_event_type = ""
        self._received_events = 0
        self._received_real_events = 0
        self._received_test_events = 0
        self._last_event_kind: str | None = None
        self._last_real_event_at_ms: int | None = None
        self._last_test_event_at_ms: int | None = None
        self._connect_timeout_seconds = 3.0
        self._delivery_min_interval_ms = 12000

    def status(self) -> dict[str, Any]:
        running = bool(self._task and not self._task.done())
        platform_room_id = self._platform.active_room_id if self._platform else None
        active_room_id = platform_room_id if running else None
        proxy_connected = bool(self._platform and self._platform.is_connected)
        platform_connected_at_ms = (
            getattr(self._platform, "connected_at_ms", None) if self._platform else None
        )
        if running and active_room_id and self._connected_at_ms is None:
            self._connected_at_ms = platform_connected_at_ms or _now_ms()
        connected_at_ms = platform_connected_at_ms or self._connected_at_ms
        last_packet_at_ms = (
            getattr(self._platform, "last_packet_at_ms", None) if self._platform else None
        )
        last_packet_type = (
            getattr(self._platform, "last_packet_type", "") if self._platform else ""
        )
        last_heartbeat_at_ms = (
            getattr(self._platform, "last_heartbeat_at_ms", None)
            if self._platform
            else None
        )
        last_heartbeat_popularity = (
            getattr(self._platform, "last_heartbeat_popularity", None)
            if self._platform
            else None
        )
        received_packets = (
            getattr(self._platform, "received_packets", 0) if self._platform else 0
        )
        platform_error = (
            getattr(self._platform, "last_error", "") if self._platform else ""
        )
        if platform_error and not self._last_error:
            self._last_error = platform_error
        state = self._derive_state(running, active_room_id)
        elapsed_ms = None
        if self._started_at_ms:
            elapsed_until_ms = (
                self._stopped_at_ms if not running and self._stopped_at_ms else _now_ms()
            )
            elapsed_ms = max(0, elapsed_until_ms - self._started_at_ms)
        return {
            "available": BLIVEDM_AVAILABLE,
            "state": state,
            "running": running,
            "connected": state == "connected",
            "proxy_connected": proxy_connected,
            "room_ids": self._room_ids,
            "active_room_id": active_room_id,
            "last_active_room_id": platform_room_id,
            "use_proxy": self._use_proxy,
            "proxy_url": self._proxy_url,
            "speak": self._speak,
            "started_at_ms": self._started_at_ms,
            "stopped_at_ms": self._stopped_at_ms,
            "elapsed_ms": elapsed_ms,
            "last_event_at_ms": self._last_event_at_ms,
            "received_events": self._received_events,
            "received_real_events": self._received_real_events,
            "received_test_events": self._received_test_events,
            "last_event_kind": self._last_event_kind,
            "last_real_event_at_ms": self._last_real_event_at_ms,
            "last_test_event_at_ms": self._last_test_event_at_ms,
            "last_error": self._last_error,
            "last_result": self._last_result,
            "last_delivery": self._last_delivery,
            "last_delivery_at_ms": self._last_delivery_at_ms,
            "last_danmaku_reply_started_at_ms": self._last_danmaku_reply_started_at_ms,
            "danmaku_reply_min_interval_ms": self._delivery_min_interval_ms,
            "danmaku_reply_cooldown_remaining_ms": self._danmaku_cooldown_remaining_ms(),
            "blocked_events": self._blocked_events,
            "last_blocked_at_ms": self._last_blocked_at_ms,
            "last_blocked_reason": self._last_blocked_reason,
            "last_blocked_event_type": self._last_blocked_event_type,
            "last_blocked_event_kind": self._last_blocked_event_kind,
            "last_blocked_event_priority": self._last_blocked_event_priority,
            "last_connect_attempt_at_ms": self._last_connect_attempt_at_ms,
            "connected_at_ms": connected_at_ms,
            "processing_events": self._processing_events,
            "last_processing_started_at_ms": self._last_processing_started_at_ms,
            "last_processing_finished_at_ms": self._last_processing_finished_at_ms,
            "last_processing_stage": self._last_processing_stage,
            "last_processing_event_kind": self._last_processing_event_kind,
            "last_processing_event_type": self._last_processing_event_type,
            "last_processing_duration_ms": self._processing_duration_ms(),
            "last_packet_at_ms": last_packet_at_ms,
            "last_packet_type": last_packet_type,
            "last_heartbeat_at_ms": last_heartbeat_at_ms,
            "last_heartbeat_popularity": last_heartbeat_popularity,
            "received_packets": received_packets,
            "state_detail": self._state_detail(
                state=state,
                active_room_id=active_room_id,
                last_packet_at_ms=last_packet_at_ms,
                last_packet_type=last_packet_type,
                last_heartbeat_at_ms=last_heartbeat_at_ms,
                received_packets=received_packets,
            ),
            "delivery_min_interval_ms": self._delivery_min_interval_ms,
            "library": get_blivedm_status(),
        }

    def _derive_state(self, running: bool, active_room_id: int | None) -> str:
        if running and active_room_id:
            return "connected"
        if running:
            return "starting"
        if self._last_error:
            return "failed"
        if self._started_at_ms and self._stopped_at_ms:
            return "stopped"
        return "idle"

    def _state_detail(
        self,
        *,
        state: str,
        active_room_id: int | None,
        last_packet_at_ms: int | None,
        last_packet_type: str,
        last_heartbeat_at_ms: int | None,
        received_packets: int,
    ) -> str:
        if state == "idle":
            return "connector idle; click connect to start real danmaku intake"
        if state == "failed":
            return self._last_error or "connector failed before room became active"
        if state == "stopped":
            return "connector stopped"
        if state == "starting":
            return "network task created; waiting for room client to become active"
        if state == "connected":
            if self._processing_events > 0:
                return (
                    f"processing {self._processing_events} event(s); "
                    f"stage {self._last_processing_stage or 'planner'}"
                )
            if self._last_blocked_reason:
                return f"last danmaku blocked: {self._last_blocked_reason}"
            if self._received_real_events > 0:
                return f"received {self._received_real_events} real event(s)"
            if last_packet_type and last_packet_type != "heartbeat":
                return f"received {last_packet_type} packet; waiting for planner/delivery"
            if last_heartbeat_at_ms:
                return "heartbeat received; waiting for real danmaku"
            if received_packets:
                return "received Bilibili packets; waiting for real danmaku"
            return f"room {active_room_id or '?'} active; waiting for Bilibili packets"
        return state

    def _processing_duration_ms(self) -> int | None:
        if not self._last_processing_started_at_ms:
            return None
        end_ms = (
            _now_ms()
            if self._processing_events > 0
            else self._last_processing_finished_at_ms
        )
        if not end_ms:
            return None
        return max(0, end_ms - self._last_processing_started_at_ms)

    def _danmaku_cooldown_remaining_ms(self, now_ms: int | None = None) -> int:
        if not self._last_danmaku_reply_started_at_ms:
            return 0
        now = now_ms or _now_ms()
        elapsed = now - self._last_danmaku_reply_started_at_ms
        return max(0, self._delivery_min_interval_ms - elapsed)

    def _event_priority(self, event: dict[str, Any]) -> int:
        event_type = str(event.get("type") or "")
        source = str(event.get("source") or "")
        if source in CONTROL_PRIORITY_SOURCES or event_type in CONTROL_PRIORITY_TYPES:
            return 100
        if event_type in HIGH_PRIORITY_EVENT_TYPES:
            return 80
        if event_type in DANMAKU_REPLY_TYPES:
            return 10
        return 50

    def _is_danmaku_reply_event(self, event: dict[str, Any]) -> bool:
        return str(event.get("type") or "") in DANMAKU_REPLY_TYPES

    def _blocked_delivery_for_event(
        self,
        event: dict[str, Any],
        now_ms: int,
    ) -> dict[str, Any] | None:
        if not self._is_danmaku_reply_event(event):
            return None

        if self._processing_events > 0:
            return {
                "ok": False,
                "delivered_clients": 0,
                "failed_clients": [],
                "reason": DANMAKU_BUSY_REASON,
                "retry_after_ms": 1000,
                "blocked": True,
                "blocked_by": self._last_processing_event_type or "active_turn",
            }

        retry_after_ms = self._danmaku_cooldown_remaining_ms(now_ms)
        if retry_after_ms > 0:
            return {
                "ok": False,
                "delivered_clients": 0,
                "failed_clients": [],
                "reason": DANMAKU_COOLDOWN_REASON,
                "retry_after_ms": retry_after_ms,
                "blocked": True,
                "blocked_by": "danmaku_reply_cooldown",
            }
        return None

    def _blocked_result(
        self,
        event: dict[str, Any],
        *,
        kind: str,
        priority: int,
        delivery: dict[str, Any],
        now_ms: int,
    ) -> dict[str, Any]:
        self._blocked_events += 1
        self._last_blocked_at_ms = now_ms
        self._last_blocked_reason = str(delivery.get("reason") or "")
        self._last_blocked_event_type = str(event.get("type") or "")
        self._last_blocked_event_kind = kind
        self._last_blocked_event_priority = priority
        self._last_delivery = delivery
        if self._processing_events <= 0:
            self._last_processing_started_at_ms = now_ms
            self._last_processing_finished_at_ms = now_ms
            self._last_processing_stage = "blocked"
            self._last_processing_event_kind = kind
            self._last_processing_event_type = self._last_blocked_event_type

        result = {
            "event": event,
            "blocked": True,
            "delivery": delivery,
            "scheduler": {
                "event_priority": priority,
                "reason": delivery.get("reason"),
                "retry_after_ms": delivery.get("retry_after_ms", 0),
            },
        }
        self._last_result = result
        return result

    async def connect(
        self,
        room_ids: list[int],
        sessdata: str = "",
        use_proxy: bool = False,
        proxy_url: str | None = None,
        speak: bool = True,
    ) -> dict[str, Any]:
        room_ids = normalize_room_ids(room_ids)
        if not room_ids:
            raise ValueError("At least one positive Bilibili room ID is required.")
        if not BLIVEDM_AVAILABLE:
            raise RuntimeError("Bilibili danmaku library is not available.")

        async with self._lock:
            if self._task and not self._task.done():
                raise RuntimeError("Bilibili connector is already running.")

            self._room_ids = room_ids
            self._use_proxy = use_proxy
            self._proxy_url = proxy_url if use_proxy else None
            self._speak = speak
            self._started_at_ms = _now_ms()
            self._stopped_at_ms = None
            self._last_connect_attempt_at_ms = self._started_at_ms
            self._connected_at_ms = None
            self._last_error = ""
            self._last_result = None
            self._last_delivery = None
            self._last_delivery_at_ms = None
            self._last_danmaku_reply_started_at_ms = None
            self._blocked_events = 0
            self._last_blocked_at_ms = None
            self._last_blocked_reason = ""
            self._last_blocked_event_type = ""
            self._last_blocked_event_kind = None
            self._last_blocked_event_priority = 0
            self._received_events = 0
            self._received_real_events = 0
            self._received_test_events = 0
            self._last_event_kind = None
            self._last_real_event_at_ms = None
            self._last_test_event_at_ms = None
            self._processing_events = 0
            self._last_processing_started_at_ms = None
            self._last_processing_finished_at_ms = None
            self._last_processing_stage = ""
            self._last_processing_event_kind = None
            self._last_processing_event_type = ""

            self._platform = BiliBiliLivePlatform(
                room_ids=room_ids,
                sessdata=sessdata,
                proxy_url=self._proxy_url,
                event_handler=self._handle_event,
                speak=speak,
            )
            self._task = asyncio.create_task(self._run_platform())
            await self._wait_until_started()
            return self.status()

    async def disconnect(self) -> dict[str, Any]:
        async with self._lock:
            platform = self._platform
            task = self._task
            if platform:
                await platform.disconnect()
            if task and not task.done():
                try:
                    await asyncio.wait_for(task, timeout=5)
                except TimeoutError:
                    task.cancel()
                except asyncio.CancelledError:
                    pass
            self._stopped_at_ms = _now_ms()
            return self.status()

    async def publish_test_event(
        self,
        text: str = "六花，B站测试弹幕来了。",
        user_name: str = "B站观众",
        user_id: str = "debug-bilibili",
        room_id: str = "0",
    ) -> dict[str, Any]:
        event = build_bilibili_danmaku_event(
            danmaku_text=text,
            user_name=user_name,
            user_id=user_id,
            room_id=room_id,
        )
        event.setdefault("payload", {})["debug_test_event"] = True
        result = await self._handle_event(event, event_kind="test")
        return {
            "event": event,
            "result": result,
            "status": self.status(),
        }

    async def _run_platform(self) -> None:
        try:
            if not self._platform:
                return
            await self._platform.run()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self._last_error = str(exc)
            logger.error(f"Bilibili connector failed: {exc}")
        finally:
            platform_error = (
                getattr(self._platform, "last_error", "") if self._platform else ""
            )
            if platform_error and not self._last_error:
                self._last_error = platform_error
            self._stopped_at_ms = _now_ms()

    async def _wait_until_started(self) -> None:
        """Wait briefly for the network client to either start or fail."""
        if not self._task:
            return
        deadline = time.monotonic() + self._connect_timeout_seconds
        while time.monotonic() < deadline:
            if self._task.done():
                return
            if self._platform and self._platform.active_room_id:
                return
            await asyncio.sleep(0.05)

    async def _handle_event(
        self,
        event: dict[str, Any],
        event_kind: str = "real",
    ) -> dict[str, Any]:
        self._received_events += 1
        now_ms = _now_ms()
        kind = "test" if event_kind == "test" else "real"
        self._last_event_kind = kind
        self._last_event_at_ms = now_ms
        if kind == "test":
            self._received_test_events += 1
            self._last_test_event_at_ms = now_ms
        else:
            self._received_real_events += 1
            self._last_real_event_at_ms = now_ms
        priority = self._event_priority(event)
        blocked_delivery = self._blocked_delivery_for_event(event, now_ms)
        if blocked_delivery:
            return self._blocked_result(
                event,
                kind=kind,
                priority=priority,
                delivery=blocked_delivery,
                now_ms=now_ms,
            )
        if self._is_danmaku_reply_event(event):
            self._last_danmaku_reply_started_at_ms = now_ms
        self._processing_events += 1
        self._last_processing_started_at_ms = now_ms
        self._last_processing_finished_at_ms = None
        self._last_processing_stage = "planner"
        self._last_processing_event_kind = kind
        self._last_processing_event_type = str(event.get("type") or "")
        try:
            self._last_result = await self._event_consumer(event)
            self._last_processing_stage = "delivery"
            self._last_delivery = await self._maybe_emit_result(self._last_result, event)
            if self._last_delivery and isinstance(self._last_result, dict):
                self._last_result["delivery"] = self._last_delivery
        except Exception as exc:
            self._last_processing_stage = "error"
            self._last_error = str(exc)
            logger.error(f"Failed to process Bilibili LiveEvent: {exc}")
            raise
        finally:
            self._processing_events = max(0, self._processing_events - 1)
            self._last_processing_finished_at_ms = _now_ms()
            if self._processing_events <= 0 and self._last_processing_stage != "error":
                self._last_processing_stage = "complete"
        return self._last_result

    async def _maybe_emit_result(
        self,
        result: dict[str, Any],
        _event: dict[str, Any],
    ) -> dict[str, Any] | None:
        if not self._result_emitter:
            return None
        if not self._speak:
            return {
                "ok": False,
                "delivered_clients": 0,
                "failed_clients": [],
                "reason": "Bilibili speak is disabled",
            }
        delivery = await self._result_emitter(result, True)
        if delivery.get("ok"):
            self._last_delivery_at_ms = _now_ms()
        return delivery

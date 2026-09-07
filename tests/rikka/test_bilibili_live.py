import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from open_llm_vtuber.live.bilibili_live import (
    build_bilibili_danmaku_event,
    build_bilibili_gift_event,
)
from open_llm_vtuber.rikka.bilibili import BilibiliLiveManager, normalize_room_ids
from open_llm_vtuber.rikka.core import normalize_live_event, plan_rikka_response


async def consume_event(event_payload):
    event = normalize_live_event(event_payload)
    result = plan_rikka_response(event)
    return {
        "event": event.model_dump(mode="json"),
        "response": result.response.model_dump(mode="json"),
    }


class BilibiliLiveTest(unittest.TestCase):
    def test_room_ids_are_normalized(self):
        self.assertEqual(normalize_room_ids([0, "12", 12, -1, "bad", 34]), [12, 34])

    def test_danmaku_event_matches_live_event_schema(self):
        payload = build_bilibili_danmaku_event(
            danmaku_text="六花晚上好",
            user_name="alice",
            user_id=42,
            room_id=123,
        )

        event = normalize_live_event(payload)

        self.assertEqual(event.type, "chat.message")
        self.assertEqual(event.source, "bilibili")
        self.assertEqual(event.actor.display_name, "alice")
        self.assertEqual(event.room_id, "123")

    def test_gift_event_matches_live_event_schema(self):
        payload = build_bilibili_gift_event(
            SimpleNamespace(
                gift_name="小花",
                num=2,
                uname="alice",
                uid=42,
                medal_name="月光",
                price=1000,
                coin_type="gold",
            ),
            room_id=123,
        )

        event = normalize_live_event(payload)

        self.assertEqual(event.type, "chat.gift")
        self.assertEqual(event.source, "bilibili")
        self.assertEqual(event.actor.medal, "月光")
        self.assertIn("小花", event.text)

    def test_test_event_runs_through_rikka_pipeline(self):
        async def run():
            manager = BilibiliLiveManager(consume_event)
            return await manager.publish_test_event(
                text="六花，测试弹幕来啦",
                user_name="alice",
                user_id="42",
                room_id="123",
            )

        result = asyncio.run(run())

        self.assertEqual(result["event"]["source"], "bilibili")
        self.assertTrue(result["event"]["payload"]["debug_test_event"])
        self.assertEqual(result["result"]["response"]["reason_code"], "reply_chat")
        self.assertEqual(result["status"]["received_events"], 1)
        self.assertEqual(result["status"]["received_real_events"], 0)
        self.assertEqual(result["status"]["received_test_events"], 1)
        self.assertEqual(result["status"]["last_event_kind"], "test")

    def test_real_event_count_is_separate_from_test_events(self):
        async def run():
            manager = BilibiliLiveManager(consume_event)
            event = build_bilibili_danmaku_event(
                danmaku_text="真实弹幕计数测试",
                user_name="alice",
                user_id="42",
                room_id="123",
            )
            result = await manager._handle_event(event)
            return result, manager.status()

        result, status = asyncio.run(run())

        self.assertEqual(result["event"]["source"], "bilibili")
        self.assertEqual(status["received_events"], 1)
        self.assertEqual(status["received_real_events"], 1)
        self.assertEqual(status["received_test_events"], 0)
        self.assertEqual(status["last_event_kind"], "real")

    def test_status_reports_in_flight_event_processing(self):
        async def run():
            started = asyncio.Event()
            release = asyncio.Event()

            async def slow_consume(event_payload):
                started.set()
                await release.wait()
                return await consume_event(event_payload)

            manager = BilibiliLiveManager(slow_consume)
            event = build_bilibili_danmaku_event(
                danmaku_text="处理状态测试",
                user_name="alice",
                user_id="42",
                room_id="123",
            )
            task = asyncio.create_task(manager._handle_event(event))
            await asyncio.wait_for(started.wait(), timeout=1)
            in_flight = manager.status()
            release.set()
            result = await task
            done = manager.status()
            return in_flight, result, done

        in_flight, result, done = asyncio.run(run())

        self.assertEqual(in_flight["processing_events"], 1)
        self.assertEqual(in_flight["last_processing_stage"], "planner")
        self.assertEqual(in_flight["last_processing_event_kind"], "real")
        self.assertEqual(in_flight["last_processing_event_type"], "chat.message")
        self.assertIsNotNone(in_flight["last_processing_duration_ms"])
        self.assertEqual(result["response"]["reason_code"], "reply_chat")
        self.assertEqual(done["processing_events"], 0)
        self.assertEqual(done["last_processing_stage"], "complete")

    def test_test_event_emits_result_and_throttles_delivery(self):
        deliveries = []

        async def emit_result(result, speak):
            deliveries.append((result, speak))
            return {
                "ok": True,
                "delivered_clients": 1,
                "failed_clients": [],
                "reason": "",
            }

        async def run():
            manager = BilibiliLiveManager(consume_event, result_emitter=emit_result)
            first = await manager.publish_test_event(
                text="六花，第一条弹幕。",
                user_name="alice",
                user_id="42",
                room_id="123",
            )
            second = await manager.publish_test_event(
                text="六花，第二条弹幕。",
                user_name="bob",
                user_id="43",
                room_id="123",
            )
            return first, second, manager.status()

        first, second, status = asyncio.run(run())

        self.assertEqual(len(deliveries), 1)
        self.assertTrue(deliveries[0][1])
        self.assertTrue(first["result"]["delivery"]["ok"])
        self.assertFalse(second["result"]["delivery"]["ok"])
        self.assertEqual(
            second["result"]["delivery"]["reason"],
            "Bilibili danmaku reply cooldown",
        )
        self.assertTrue(second["result"]["blocked"])
        self.assertEqual(status["blocked_events"], 1)
        self.assertEqual(status["received_events"], 2)
        self.assertEqual(status["received_test_events"], 2)
        self.assertEqual(status["received_real_events"], 0)

    def test_busy_danmaku_is_blocked_before_planner(self):
        calls = []

        async def run():
            started = asyncio.Event()
            release = asyncio.Event()

            async def slow_consume(event_payload):
                calls.append(event_payload["text"])
                started.set()
                await release.wait()
                return await consume_event(event_payload)

            manager = BilibiliLiveManager(slow_consume)
            first = build_bilibili_danmaku_event(
                danmaku_text="第一条真实弹幕",
                user_name="alice",
                user_id="42",
                room_id="123",
            )
            second = build_bilibili_danmaku_event(
                danmaku_text="第二条真实弹幕",
                user_name="bob",
                user_id="43",
                room_id="123",
            )
            first_task = asyncio.create_task(manager._handle_event(first))
            await asyncio.wait_for(started.wait(), timeout=1)
            blocked = await manager._handle_event(second)
            in_flight = manager.status()
            release.set()
            processed = await first_task
            done = manager.status()
            return blocked, in_flight, processed, done

        blocked, in_flight, processed, done = asyncio.run(run())

        self.assertEqual(calls, ["第一条真实弹幕"])
        self.assertTrue(blocked["blocked"])
        self.assertEqual(
            blocked["delivery"]["reason"],
            "Bilibili danmaku reply blocked while another turn is processing",
        )
        self.assertEqual(in_flight["processing_events"], 1)
        self.assertEqual(in_flight["blocked_events"], 1)
        self.assertEqual(processed["response"]["reason_code"], "reply_chat")
        self.assertEqual(done["received_real_events"], 2)
        self.assertEqual(done["blocked_events"], 1)

    def test_high_priority_event_bypasses_danmaku_cooldown(self):
        deliveries = []

        async def emit_result(result, speak):
            deliveries.append((result, speak))
            return {
                "ok": True,
                "delivered_clients": 1,
                "failed_clients": [],
                "reason": "",
            }

        async def run():
            manager = BilibiliLiveManager(consume_event, result_emitter=emit_result)
            first = build_bilibili_danmaku_event(
                danmaku_text="先回一条普通弹幕",
                user_name="alice",
                user_id="42",
                room_id="123",
            )
            gift = build_bilibili_gift_event(
                SimpleNamespace(
                    gift_name="小花",
                    num=1,
                    uname="bob",
                    uid=43,
                    medal_name="月光",
                    price=1000,
                    coin_type="gold",
                ),
                room_id=123,
            )
            first_result = await manager._handle_event(first)
            gift_result = await manager._handle_event(gift)
            return first_result, gift_result, manager.status()

        first_result, gift_result, status = asyncio.run(run())

        self.assertTrue(first_result["delivery"]["ok"])
        self.assertTrue(gift_result["delivery"]["ok"])
        self.assertEqual(gift_result["response"]["reason_code"], "thank_gift")
        self.assertEqual(len(deliveries), 2)
        self.assertEqual(status["blocked_events"], 0)

    def test_connect_reports_connected_after_platform_starts(self):
        class FakePlatform:
            def __init__(self, room_ids, **kwargs):
                self.room_ids = room_ids
                self._active_room_id = None
                self._running = False
                self._stop = asyncio.Event()
                self.last_error = ""
                self.is_connected = False
                self.connected_at_ms = 123456
                self.last_packet_at_ms = 123789
                self.last_packet_type = "heartbeat"
                self.last_heartbeat_at_ms = 123789
                self.last_heartbeat_popularity = 42
                self.received_packets = 1

            @property
            def active_room_id(self):
                return self._active_room_id

            async def run(self):
                self._running = True
                self._active_room_id = self.room_ids[0]
                await self._stop.wait()

            async def disconnect(self):
                self._running = False
                self._stop.set()

        async def run():
            with (
                patch("open_llm_vtuber.rikka.bilibili.BLIVEDM_AVAILABLE", True),
                patch("open_llm_vtuber.rikka.bilibili.BiliBiliLivePlatform", FakePlatform),
            ):
                manager = BilibiliLiveManager(consume_event)
                status = await manager.connect([123])
                disconnected = await manager.disconnect()
                return status, disconnected

        status, disconnected = asyncio.run(run())

        self.assertEqual(status["state"], "connected")
        self.assertTrue(status["connected"])
        self.assertEqual(status["active_room_id"], 123)
        self.assertEqual(status["connected_at_ms"], 123456)
        self.assertEqual(status["last_packet_type"], "heartbeat")
        self.assertEqual(status["last_heartbeat_popularity"], 42)
        self.assertEqual(status["received_packets"], 1)
        self.assertIn("heartbeat", status["state_detail"])
        self.assertEqual(disconnected["state"], "stopped")
        self.assertIsNone(disconnected["active_room_id"])
        self.assertEqual(disconnected["last_active_room_id"], 123)
        self.assertLess(disconnected["elapsed_ms"], 5000)

    def test_connect_reports_failed_when_platform_exits_with_error(self):
        class FailingPlatform:
            active_room_id = None
            is_connected = False
            last_error = "room handshake failed"

            def __init__(self, *args, **kwargs):
                pass

            async def run(self):
                return None

            async def disconnect(self):
                return None

        async def run():
            with (
                patch("open_llm_vtuber.rikka.bilibili.BLIVEDM_AVAILABLE", True),
                patch(
                    "open_llm_vtuber.rikka.bilibili.BiliBiliLivePlatform",
                    FailingPlatform,
                ),
            ):
                manager = BilibiliLiveManager(consume_event)
                return await manager.connect([123])

        status = asyncio.run(run())

        self.assertEqual(status["state"], "failed")
        self.assertFalse(status["connected"])
        self.assertEqual(status["last_error"], "room handshake failed")


if __name__ == "__main__":
    unittest.main()

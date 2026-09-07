import tempfile
import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from open_llm_vtuber.rikka.capture import (
    CaptureDependencyError,
    CapturedFrame,
    WindowCaptureService,
    WindowInfo,
)
from open_llm_vtuber.rikka.pointer import GlobalPointerTracker
from open_llm_vtuber.rikka.routes import init_rikka_routes
from open_llm_vtuber.rikka.settings import (
    AudioInteractionSettings,
    RikkaSettingsStore,
)
from open_llm_vtuber.rikka.wake_gate import WakeGate


class FakeEnumerator:
    def __init__(self, windows=None, available=True):
        self._windows = windows or []
        self.is_available = available

    def unavailable_reason(self):
        return "" if self.is_available else "not windows"

    def list_windows(self):
        return self._windows

    def capture_window(self, window, settings):
        return CapturedFrame(
            data_base64="ZmFrZQ==",
            mime_type="image/jpeg",
            captured_at_ms=1234,
            window=window,
            width=640,
            height=360,
        )


class MissingDependencyEnumerator(FakeEnumerator):
    def capture_window(self, window, settings):
        raise CaptureDependencyError("mss and pillow are required for capture")


class CaptureRouteTests(unittest.TestCase):
    def make_client(self, enumerator):
        tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(tmp_dir.cleanup)
        store = RikkaSettingsStore(Path(tmp_dir.name) / "settings.json")
        capture = WindowCaptureService(settings_store=store, enumerator=enumerator)
        app = FastAPI()
        app.include_router(
            init_rikka_routes(
                None,
                settings_store=store,
                capture_service=capture,
            )
        )
        return TestClient(app), store, capture

    def test_capture_disabled_by_default(self):
        client, _, _ = self.make_client(FakeEnumerator())

        response = client.get("/rikka/capture/status")

        self.assertEqual(response.status_code, 200)
        payload = response.json()["capture"]
        self.assertFalse(payload["enabled"])
        self.assertEqual(payload["status"], "disabled")

    def test_whitelist_capture_waits_when_target_missing(self):
        client, store, _ = self.make_client(
            FakeEnumerator(
                [
                    WindowInfo(
                        handle=1,
                        title="Browser",
                        process_name="browser.exe",
                        bounds=(0, 0, 800, 600),
                    )
                ]
            )
        )
        store.update(
            {
                "screen_capture_enabled": True,
                "keyframe_upload_enabled": True,
                "capture": {
                    "enabled": True,
                    "window_title_allowlist": ["Minecraft"],
                },
            }
        )

        response = client.post("/rikka/capture/keyframe")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["capture"]["status"], "waiting_for_target")

    def test_whitelist_capture_stores_latest_frame_transiently(self):
        client, store, _ = self.make_client(
            FakeEnumerator(
                [
                    WindowInfo(
                        handle=2,
                        title="Minecraft 1.21",
                        process_name="javaw.exe",
                        bounds=(0, 0, 800, 600),
                    )
                ]
            )
        )
        store.update(
            {
                "screen_capture_enabled": True,
                "keyframe_upload_enabled": True,
                "capture": {
                    "enabled": True,
                    "window_title_allowlist": ["Minecraft"],
                },
            }
        )

        response = client.post("/rikka/capture/keyframe")

        self.assertEqual(response.status_code, 200)
        capture = response.json()["capture"]
        self.assertEqual(capture["status"], "captured")
        self.assertFalse(capture["raw_media_persisted"])
        self.assertEqual(capture["latest_frame"]["window"]["title"], "Minecraft 1.21")

    def test_foreground_capture_requires_explicit_debug_opt_in(self):
        client, store, _ = self.make_client(
            FakeEnumerator(
                [
                    WindowInfo(
                        handle=3,
                        title="Secret Foreground",
                        bounds=(0, 0, 800, 600),
                        is_foreground=True,
                    )
                ]
            )
        )
        store.update(
            {
                "screen_capture_enabled": True,
                "keyframe_upload_enabled": True,
                "capture": {
                    "enabled": True,
                    "mode": "foreground_debug",
                },
            }
        )

        response = client.post("/rikka/capture/keyframe")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["capture"]["status"], "blocked")

    def test_non_windows_capture_reports_unavailable(self):
        client, _, _ = self.make_client(FakeEnumerator(available=False))

        response = client.get("/rikka/capture/status")

        self.assertEqual(response.status_code, 200)
        payload = response.json()["capture"]
        self.assertFalse(payload["available"])
        self.assertEqual(payload["status"], "unavailable")

    def test_missing_capture_dependency_reports_unavailable(self):
        client, store, _ = self.make_client(
            MissingDependencyEnumerator(
                [
                    WindowInfo(
                        handle=4,
                        title="Minecraft",
                        process_name="javaw.exe",
                        bounds=(0, 0, 800, 600),
                    )
                ]
            )
        )
        store.update(
            {
                "screen_capture_enabled": True,
                "keyframe_upload_enabled": True,
                "capture": {
                    "enabled": True,
                    "window_title_allowlist": ["Minecraft"],
                },
            }
        )

        response = client.post("/rikka/capture/keyframe")

        self.assertEqual(response.status_code, 200)
        capture = response.json()["capture"]
        self.assertEqual(capture["status"], "unavailable")
        self.assertIn("mss and pillow", capture["reason"])


class WakeGateTests(unittest.TestCase):
    def test_wake_gate_suppresses_without_phrase(self):
        gate = WakeGate(clock_ms=lambda: 1000)
        settings = AudioInteractionSettings(wake_gate_enabled=True)

        decision = gate.evaluate("client", "今天天气不错", settings)

        self.assertFalse(decision.should_process)
        self.assertEqual(decision.reason, "wake_phrase_missing")

    def test_wake_gate_strips_phrase_without_opening_followup_window(self):
        now = 1000
        gate = WakeGate(clock_ms=lambda: now)
        settings = AudioInteractionSettings(wake_gate_enabled=True)

        decision = gate.evaluate("client", "六花，看看现在的画面", settings)

        self.assertTrue(decision.should_process)
        self.assertEqual(decision.text, "看看现在的画面")
        self.assertTrue(decision.woke)
        self.assertFalse(decision.active)
        self.assertEqual(decision.match_kind, "canonical")
        self.assertEqual(decision.matched_phrase, "六花")
        self.assertFalse(gate.status("client")["active"])

        active_until = gate.activate("client", settings.wake_active_window_ms)

        self.assertEqual(active_until, now + settings.wake_active_window_ms)
        self.assertTrue(gate.status("client")["active"])

    def test_wake_gate_strips_phrase_across_asr_pause_punctuation(self):
        gate = WakeGate(clock_ms=lambda: 1000)
        settings = AudioInteractionSettings(wake_gate_enabled=True)

        decision = gate.evaluate("client", "六。花，晚上好", settings)

        self.assertTrue(decision.should_process)
        self.assertEqual(decision.text, "晚上好")
        self.assertTrue(decision.woke)
        self.assertFalse(decision.active)

    def test_wake_gate_repairs_spaced_cjk_asr_text(self):
        gate = WakeGate(clock_ms=lambda: 1000)
        settings = AudioInteractionSettings(wake_gate_enabled=True)

        decision = gate.evaluate("client", "六 花 晚 上 好", settings)

        self.assertTrue(decision.should_process)
        self.assertEqual(decision.text, "晚上好")

    def test_wake_gate_tolerates_asr_pause_fillers_inside_phrase(self):
        gate = WakeGate(clock_ms=lambda: 1000)
        settings = AudioInteractionSettings(wake_gate_enabled=True)

        decision = gate.evaluate("client", "六……嗯……花，晚上好", settings)

        self.assertTrue(decision.should_process)
        self.assertEqual(decision.text, "晚上好")
        self.assertEqual(decision.reason, "wake_phrase_matched")

    def test_wake_gate_only_strips_invocation_wake_phrase(self):
        gate = WakeGate(clock_ms=lambda: 1000)
        settings = AudioInteractionSettings(wake_gate_enabled=True)

        decision = gate.evaluate("client", "六花，六花这个名字是什么意思", settings)

        self.assertTrue(decision.should_process)
        self.assertEqual(decision.text, "六花这个名字是什么意思")

    def test_wake_gate_does_not_trigger_on_mid_sentence_name_mention(self):
        gate = WakeGate(clock_ms=lambda: 1000)
        settings = AudioInteractionSettings(wake_gate_enabled=True)

        decision = gate.evaluate("client", "我想问六花这个名字是什么意思", settings)

        self.assertFalse(decision.should_process)
        self.assertEqual(decision.reason, "wake_phrase_missing")
        self.assertNotIn("match_kind", decision.to_dict())

    def test_wake_gate_accepts_configured_asr_confusion_aliases(self):
        gate = WakeGate(clock_ms=lambda: 1000)
        settings = AudioInteractionSettings(wake_gate_enabled=True)

        first = gate.evaluate("client", "柳华，看看画面", settings)
        second = gate.evaluate("client", "有花，继续解释一下", settings)

        self.assertTrue(first.should_process)
        self.assertEqual(first.text, "看看画面")
        self.assertEqual(first.match_kind, "asr_confusion")
        self.assertEqual(first.matched_phrase, "柳华")
        self.assertTrue(second.should_process)
        self.assertEqual(second.text, "继续解释一下")
        self.assertEqual(second.match_kind, "asr_confusion")
        self.assertEqual(second.matched_phrase, "有花")

    def test_wake_gate_rejects_unconfigured_asr_confusion_alias(self):
        gate = WakeGate(clock_ms=lambda: 1000)
        settings = AudioInteractionSettings(
            wake_gate_enabled=True,
            wake_asr_confusions=[],
        )

        decision = gate.evaluate("client", "柳华，看看画面", settings)

        self.assertFalse(decision.should_process)
        self.assertEqual(decision.reason, "wake_phrase_missing")
        self.assertIsNone(decision.match_kind)

    def test_asr_confusion_wake_only_opens_window(self):
        times = [1000, 2000]
        gate = WakeGate(clock_ms=lambda: times[0])
        settings = AudioInteractionSettings(wake_gate_enabled=True)

        first = gate.evaluate("client", "柳华", settings)
        times[0] = times[1]
        second = gate.evaluate("client", "继续解释一下", settings)

        self.assertFalse(first.should_process)
        self.assertEqual(first.reason, "wake_only")
        self.assertTrue(first.active)
        self.assertEqual(first.match_kind, "asr_confusion")
        self.assertTrue(second.should_process)
        self.assertEqual(second.reason, "wake_window_active")

    def test_wake_gate_does_not_trigger_on_mid_sentence_alias_mention(self):
        gate = WakeGate(clock_ms=lambda: 1000)
        settings = AudioInteractionSettings(wake_gate_enabled=True)

        decision = gate.evaluate("client", "我刚才听成柳华了", settings)

        self.assertFalse(decision.should_process)
        self.assertEqual(decision.reason, "wake_phrase_missing")
        self.assertIsNone(decision.match_kind)

    def test_partial_asr_confusion_preview_does_not_open_window(self):
        gate = WakeGate(clock_ms=lambda: 1000)
        settings = AudioInteractionSettings(wake_gate_enabled=True)

        preview = gate.preview("柳华，看看画面", settings)
        follow_up = gate.evaluate("client", "继续解释一下", settings)

        self.assertFalse(preview.should_process)
        self.assertTrue(preview.woke)
        self.assertEqual(preview.text, "看看画面")
        self.assertEqual(preview.match_kind, "asr_confusion")
        self.assertFalse(follow_up.should_process)
        self.assertEqual(follow_up.reason, "wake_phrase_missing")

    def test_wake_only_opens_window_for_next_turn(self):
        times = [1000, 2000]
        gate = WakeGate(clock_ms=lambda: times[0])
        settings = AudioInteractionSettings(wake_gate_enabled=True)

        first = gate.evaluate("client", "Rikka", settings)
        times[0] = times[1]
        second = gate.evaluate("client", "继续解释一下", settings)

        self.assertFalse(first.should_process)
        self.assertEqual(first.reason, "wake_only")
        self.assertTrue(second.should_process)
        self.assertEqual(second.reason, "wake_window_active")

    def test_partial_wake_preview_does_not_open_window(self):
        gate = WakeGate(clock_ms=lambda: 1000)
        settings = AudioInteractionSettings(wake_gate_enabled=True)

        preview = gate.preview("Rikka", settings)
        follow_up = gate.evaluate("client", "继续解释一下", settings)

        self.assertEqual(preview.reason, "wake_only")
        self.assertTrue(preview.woke)
        self.assertFalse(follow_up.should_process)
        self.assertEqual(follow_up.reason, "wake_phrase_missing")


class OverlayPointerRouteTests(unittest.TestCase):
    def make_client(self, pointer):
        tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(tmp_dir.cleanup)
        store = RikkaSettingsStore(Path(tmp_dir.name) / "settings.json")
        app = FastAPI()
        app.include_router(
            init_rikka_routes(
                None,
                settings_store=store,
                pointer_tracker=pointer,
            )
        )
        return TestClient(app), store

    def test_global_pointer_status_normalizes_primary_screen_position(self):
        pointer = GlobalPointerTracker(
            pointer_reader=lambda: ((1920, 1080), (0, 0, 2560, 1440)),
            platform_name="Windows",
            clock_ms=lambda: 1234,
        )
        client, _ = self.make_client(pointer)

        response = client.get("/rikka/overlay/pointer")

        self.assertEqual(response.status_code, 200)
        payload = response.json()["pointer"]
        self.assertEqual(payload["status"], "tracked")
        self.assertEqual(payload["coordinate_space"], "primary_screen")
        self.assertEqual(payload["x"], 1920)
        self.assertEqual(payload["y"], 1080)
        self.assertEqual(payload["primary_x"], 1920)
        self.assertEqual(payload["primary_y"], 1080)
        self.assertAlmostEqual(payload["normalized_x"], 0.5)
        self.assertAlmostEqual(payload["normalized_y"], -0.5)
        self.assertEqual(payload["bounds"]["width"], 2560)
        self.assertEqual(payload["bounds"]["height"], 1440)
        self.assertEqual(payload["captured_at_ms"], 1234)

    def test_global_pointer_status_respects_overlay_setting(self):
        pointer = GlobalPointerTracker(
            pointer_reader=lambda: ((50, 50), (0, 0, 100, 100)),
            platform_name="Windows",
        )
        client, store = self.make_client(pointer)
        store.update({"overlay": {"global_pointer_tracking_enabled": False}})

        response = client.get("/rikka/overlay/pointer")

        self.assertEqual(response.status_code, 200)
        payload = response.json()["pointer"]
        self.assertEqual(payload["status"], "disabled")
        self.assertFalse(payload["enabled"])

    def test_global_pointer_status_reports_non_windows_unavailable(self):
        pointer = GlobalPointerTracker(platform_name="Linux")
        client, _ = self.make_client(pointer)

        response = client.get("/rikka/overlay/pointer")

        self.assertEqual(response.status_code, 200)
        payload = response.json()["pointer"]
        self.assertFalse(payload["available"])
        self.assertEqual(payload["status"], "unavailable")


if __name__ == "__main__":
    unittest.main()

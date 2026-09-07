import tempfile
import unittest
import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from open_llm_vtuber.rikka.capture import WindowCaptureService
from open_llm_vtuber.rikka.routes import init_rikka_routes
from open_llm_vtuber.rikka.settings import (
    RikkaSettingsStore,
    live2d_expressions_enabled,
)


class RikkaSettingsAndMultimodalTests(unittest.TestCase):
    def make_client(self):
        tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(tmp_dir.cleanup)
        store = RikkaSettingsStore(Path(tmp_dir.name) / "settings.json")
        capture = WindowCaptureService(settings_store=store)
        app = FastAPI()
        app.include_router(
            init_rikka_routes(None, settings_store=store, capture_service=capture)
        )
        return TestClient(app), store

    def test_settings_default_to_local_privacy_first(self):
        client, _ = self.make_client()

        response = client.get("/rikka/settings")

        self.assertEqual(response.status_code, 200)
        settings = response.json()["settings"]
        self.assertFalse(settings["screen_capture_enabled"])
        self.assertFalse(settings["keyframe_upload_enabled"])
        self.assertFalse(settings["debug_media_logging_enabled"])
        self.assertFalse(settings["capture"]["enabled"])
        self.assertEqual(settings["capture"]["mode"], "whitelist")
        self.assertFalse(settings["proactive"]["screen_comments_enabled"])
        self.assertEqual(settings["proactive"]["scheduler_interval_ms"], 15000)
        self.assertFalse(settings["audio"]["wake_gate_enabled"])
        self.assertTrue(settings["audio"]["mic_conversation_enabled"])
        self.assertTrue(settings["overlay"]["subtitle_visible"])
        self.assertTrue(settings["overlay"]["asr_hud_visible"])
        self.assertEqual(settings["overlay"]["dock_layout_mode"], "corner")
        self.assertIsNone(settings["overlay"]["dock_left_px"])
        self.assertIsNone(settings["overlay"]["dock_top_px"])
        self.assertEqual(settings["overlay"]["pointer_tracking_mode"], "natural_layered")
        self.assertEqual(settings["overlay"]["pointer_tracking_intensity"], 1.0)
        self.assertEqual(settings["overlay"]["pointer_tracking_smoothness"], 0.65)
        self.assertEqual(settings["overlay"]["pointer_tracking_deadzone"], 0.05)
        self.assertEqual(settings["overlay"]["subtitle_layout_mode"], "anchor")
        self.assertEqual(settings["overlay"]["subtitle_width_px"], 520)
        self.assertFalse(settings["agent"]["tools_enabled"])
        self.assertTrue(settings["agent"]["look_at_screen_enabled"])
        self.assertTrue(settings["agent"]["get_time_enabled"])
        self.assertTrue(settings["agent"]["web_search_enabled"])
        self.assertEqual(settings["agent"]["result_pre_silence_ms"], 1000)
        self.assertEqual(settings["memory"]["summary_per_kind"], 5)
        self.assertEqual(settings["memory"]["per_kind_cap"], 50)
        self.assertTrue(settings["mood"]["enabled"])
        self.assertTrue(settings["mood"]["tts_adjustment_enabled"])
        self.assertEqual(settings["mood"]["half_life_minutes"], 10.0)
        self.assertTrue(settings["inner_life"]["enabled"])
        self.assertEqual(settings["inner_life"]["rotation_minutes"], 18.0)
        self.assertEqual(settings["inner_life"]["activities"], [])
        self.assertEqual(settings["identity"]["host_display_name"], "Deliaru")
        self.assertEqual(settings["identity"]["audience_display_name"], "\u5f39\u5e55")
        self.assertTrue(settings["proactive"]["screen_change_gate_enabled"])
        self.assertEqual(settings["proactive"]["screen_change_threshold"], 0.12)

    def test_settings_patch_persists_and_reset_restores_defaults(self):
        client, store = self.make_client()

        response = client.patch(
            "/rikka/settings",
            json={
                "screen_capture_enabled": True,
                "keyframe_upload_enabled": True,
                "debug_media_logging_enabled": True,
                "multimodal_provider": "vision_debug",
                "capture": {
                    "enabled": True,
                    "window_title_allowlist": ["Minecraft"],
                },
                "proactive": {
                    "screen_comments_enabled": True,
                    "screen_change_threshold": 0.25,
                },
                "audio": {
                    "wake_gate_enabled": True,
                    "wake_active_window_ms": 12000,
                },
                "overlay": {
                    "asr_hud_visible": False,
                    "dock_layout_mode": "free",
                    "dock_left_px": 300,
                    "dock_top_px": 180,
                    "pointer_tracking_mode": "classic_lapp",
                    "pointer_tracking_intensity": 0.75,
                    "pointer_tracking_smoothness": 0.2,
                    "pointer_tracking_deadzone": 0.08,
                    "subtitle_layout_mode": "free",
                    "subtitle_anchor": "bottom_right",
                    "subtitle_left_px": 120,
                    "subtitle_top_px": 240,
                    "subtitle_width_px": 640,
                },
                "agent": {
                    "tools_enabled": True,
                    "result_pre_silence_ms": 800,
                },
                "memory": {
                    "summary_per_kind": 6,
                    "per_kind_cap": 60,
                },
                "mood": {
                    "enabled": False,
                    "half_life_minutes": 20,
                },
                "inner_life": {
                    "activities": ["watch screen", "<b>"],
                },
                "identity": {
                    "host_display_name": "\u4e3b\u64ad\u7532",
                    "audience_display_name": "\u5c0f\u5f39\u5e55",
                },
            },
        )

        self.assertEqual(response.status_code, 200)
        settings = response.json()["settings"]
        self.assertTrue(settings["screen_capture_enabled"])
        self.assertTrue(settings["keyframe_upload_enabled"])
        self.assertTrue(settings["debug_media_logging_enabled"])
        self.assertEqual(settings["multimodal_provider"], "vision_debug")
        self.assertTrue(settings["capture"]["enabled"])
        self.assertEqual(settings["capture"]["window_title_allowlist"], ["Minecraft"])
        self.assertTrue(settings["proactive"]["screen_comments_enabled"])
        self.assertTrue(settings["audio"]["wake_gate_enabled"])
        self.assertEqual(settings["audio"]["wake_active_window_ms"], 12000)
        self.assertEqual(settings["overlay"]["pointer_tracking_mode"], "classic_lapp")
        self.assertFalse(settings["overlay"]["asr_hud_visible"])
        self.assertEqual(settings["overlay"]["dock_layout_mode"], "free")
        self.assertEqual(settings["overlay"]["dock_left_px"], 300)
        self.assertEqual(settings["overlay"]["dock_top_px"], 180)
        self.assertEqual(settings["overlay"]["pointer_tracking_intensity"], 0.75)
        self.assertEqual(settings["overlay"]["pointer_tracking_smoothness"], 0.2)
        self.assertEqual(settings["overlay"]["pointer_tracking_deadzone"], 0.08)
        self.assertEqual(settings["overlay"]["subtitle_anchor"], "bottom_right")
        self.assertEqual(settings["overlay"]["subtitle_layout_mode"], "free")
        self.assertEqual(settings["overlay"]["subtitle_left_px"], 120)
        self.assertEqual(settings["overlay"]["subtitle_top_px"], 240)
        self.assertEqual(settings["overlay"]["subtitle_width_px"], 640)
        self.assertTrue(settings["agent"]["tools_enabled"])
        self.assertEqual(settings["agent"]["result_pre_silence_ms"], 800)
        self.assertEqual(settings["memory"]["summary_per_kind"], 6)
        self.assertEqual(settings["memory"]["per_kind_cap"], 60)
        self.assertEqual(settings["proactive"]["screen_change_threshold"], 0.25)
        self.assertFalse(settings["mood"]["enabled"])
        self.assertEqual(settings["mood"]["half_life_minutes"], 20.0)
        self.assertEqual(settings["inner_life"]["activities"], ["watch screen", "<b>"])
        self.assertEqual(settings["identity"]["host_display_name"], "\u4e3b\u64ad\u7532")
        self.assertEqual(settings["identity"]["audience_display_name"], "\u5c0f\u5f39\u5e55")
        providers = response.json()["providers"]["privacy"]
        self.assertEqual(providers["capture"]["window_title_allowlist"], ["Minecraft"])
        self.assertEqual(providers["audio"]["wake_active_window_ms"], 12000)
        self.assertEqual(providers["overlay"]["pointer_tracking_mode"], "classic_lapp")
        self.assertFalse(providers["overlay"]["asr_hud_visible"])
        self.assertEqual(providers["overlay"]["dock_layout_mode"], "free")
        self.assertEqual(providers["overlay"]["dock_left_px"], 300)
        self.assertEqual(providers["overlay"]["dock_top_px"], 180)
        self.assertEqual(providers["overlay"]["pointer_tracking_intensity"], 0.75)
        self.assertEqual(providers["overlay"]["pointer_tracking_smoothness"], 0.2)
        self.assertEqual(providers["overlay"]["pointer_tracking_deadzone"], 0.08)
        self.assertEqual(providers["overlay"]["subtitle_anchor"], "bottom_right")
        self.assertEqual(providers["overlay"]["subtitle_layout_mode"], "free")
        self.assertEqual(providers["identity"]["host_display_name"], "\u4e3b\u64ad\u7532")
        self.assertEqual(providers["identity"]["audience_display_name"], "\u5c0f\u5f39\u5e55")
        reloaded = RikkaSettingsStore(store.path)
        self.assertTrue(reloaded.snapshot().screen_capture_enabled)
        self.assertTrue(reloaded.snapshot().capture.enabled)
        self.assertEqual(reloaded.snapshot().identity.host_display_name, "\u4e3b\u64ad\u7532")

        reset = client.post("/rikka/settings/reset")

        self.assertEqual(reset.status_code, 200)
        reset_settings = reset.json()["settings"]
        self.assertFalse(reset_settings["screen_capture_enabled"])
        self.assertFalse(reset_settings["keyframe_upload_enabled"])
        self.assertFalse(reset_settings["debug_media_logging_enabled"])
        self.assertFalse(reset_settings["capture"]["enabled"])
        self.assertFalse(reset_settings["agent"]["tools_enabled"])
        self.assertTrue(reset_settings["overlay"]["asr_hud_visible"])
        self.assertEqual(reset_settings["overlay"]["dock_layout_mode"], "corner")
        self.assertTrue(reset_settings["mood"]["enabled"])
        self.assertEqual(reset_settings["identity"]["host_display_name"], "Deliaru")

    def test_liveliness_status_and_reset_are_privacy_safe(self):
        client, _ = self.make_client()

        response = client.get("/rikka/liveliness/status")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("mood", payload)
        self.assertIn("inner_life", payload)
        self.assertIn("screen_change", payload)
        self.assertNotIn("data:image", json.dumps(payload))

        reset = client.post("/rikka/liveliness/reset")

        self.assertEqual(reset.status_code, 200)
        self.assertEqual(reset.json()["mood"]["valence"], 0.0)

    def test_agent_settings_reject_unknown_fields(self):
        client, _ = self.make_client()

        response = client.patch(
            "/rikka/settings",
            json={"agent": {"tools_enabled": True, "unknown_field": 1}},
        )

        self.assertEqual(response.status_code, 422)

    def test_identity_settings_reject_unknown_fields(self):
        client, _ = self.make_client()

        response = client.patch(
            "/rikka/settings",
            json={"identity": {"host_display_name": "Deliaru", "unknown_field": 1}},
        )

        self.assertEqual(response.status_code, 422)

    def test_agent_status_is_privacy_safe(self):
        client, _ = self.make_client()
        update = client.patch(
            "/rikka/settings",
            json={"agent": {"tools_enabled": True, "web_search_enabled": False}},
        )
        self.assertEqual(update.status_code, 200)

        response = client.get("/rikka/agent/status")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["enabled"])
        self.assertFalse(payload["tools"]["web_search"])
        self.assertIn("uvx_available", payload["mcp"])
        self.assertNotIn("data:image", json.dumps(payload))

    def test_overlay_status_exposes_pointer_tracking_settings(self):
        client, _store = self.make_client()

        response = client.patch(
            "/rikka/settings",
            json={
                "overlay": {
                    "asr_hud_visible": False,
                    "dock_layout_mode": "free",
                    "dock_left_px": 188,
                    "dock_top_px": 92,
                    "pointer_tracking_mode": "off",
                    "pointer_tracking_intensity": 0.35,
                    "pointer_tracking_smoothness": 0.9,
                    "pointer_tracking_deadzone": 0.12,
                },
            },
        )
        self.assertEqual(response.status_code, 200)

        status = client.get("/rikka/overlay/status")

        self.assertEqual(status.status_code, 200)
        overlay = status.json()["settings"]
        self.assertFalse(overlay["asr_hud_visible"])
        self.assertEqual(overlay["dock_layout_mode"], "free")
        self.assertEqual(overlay["dock_left_px"], 188)
        self.assertEqual(overlay["dock_top_px"], 92)
        self.assertEqual(overlay["pointer_tracking_mode"], "off")
        self.assertEqual(overlay["pointer_tracking_intensity"], 0.35)
        self.assertEqual(overlay["pointer_tracking_smoothness"], 0.9)
        self.assertEqual(overlay["pointer_tracking_deadzone"], 0.12)

    def test_live2d_gates_default_on_and_are_patchable(self):
        client, store = self.make_client()

        response = client.get("/rikka/settings")

        self.assertEqual(response.status_code, 200)
        live2d = response.json()["settings"]["live2d"]
        self.assertTrue(live2d["expressions_enabled"])
        self.assertTrue(live2d["thinking_state_enabled"])
        self.assertTrue(live2d_expressions_enabled(store))

        patched = client.patch(
            "/rikka/settings",
            json={"live2d": {"expressions_enabled": False}},
        )

        self.assertEqual(patched.status_code, 200)
        patched_live2d = patched.json()["settings"]["live2d"]
        self.assertFalse(patched_live2d["expressions_enabled"])
        self.assertTrue(patched_live2d["thinking_state_enabled"])
        self.assertFalse(live2d_expressions_enabled(store))
        reloaded = RikkaSettingsStore(store.path)
        self.assertFalse(reloaded.snapshot().live2d.expressions_enabled)

    def test_nested_settings_reject_unknown_fields(self):
        client, _ = self.make_client()

        response = client.patch(
            "/rikka/settings",
            json={"capture": {"enabled": True, "surprise_me": True}},
        )

        self.assertEqual(response.status_code, 422)

    def test_settings_repair_mojibake_wake_phrases(self):
        tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(tmp_dir.cleanup)
        path = Path(tmp_dir.name) / "settings.json"
        mojibake_alias = "柳华".encode("utf-8").decode("latin1")
        path.write_text(
            json.dumps(
                {
                    "audio": {
                        "wake_phrases": ["å­è±", "Rikka", "ãã£ã"],
                        "wake_asr_confusions": [mojibake_alias, "有花"],
                    },
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        store = RikkaSettingsStore(path)

        self.assertEqual(store.snapshot().audio.wake_phrases, ["六花", "Rikka", "りっか"])
        self.assertEqual(store.snapshot().audio.wake_asr_confusions, ["柳华", "有花"])
        self.assertIn("六花", path.read_text(encoding="utf-8"))
        self.assertIn("柳华", path.read_text(encoding="utf-8"))

        store.update({"audio": {"wake_phrases": ["å­è±"]}})

        self.assertEqual(store.snapshot().audio.wake_phrases, ["六花"])

        store.update({"audio": {"wake_asr_confusions": [mojibake_alias]}})

        self.assertEqual(store.snapshot().audio.wake_asr_confusions, ["柳华"])

    def test_settings_round_trips_wake_asr_confusions(self):
        client, store = self.make_client()

        response = client.get("/rikka/settings")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["settings"]["audio"]["wake_asr_confusions"],
            ["柳华", "有花"],
        )

        patched = client.patch(
            "/rikka/settings",
            json={"audio": {"wake_asr_confusions": ["柳华", "有花", "油画"]}},
        )

        self.assertEqual(patched.status_code, 200)
        self.assertEqual(
            patched.json()["settings"]["audio"]["wake_asr_confusions"],
            ["柳华", "有花", "油画"],
        )
        self.assertEqual(
            store.snapshot().audio.wake_asr_confusions,
            ["柳华", "有花", "油画"],
        )
        self.assertIn("柳华", store.path.read_text(encoding="utf-8"))

        unknown = client.patch(
            "/rikka/settings",
            json={"audio": {"wake_aliases": ["柳华"]}},
        )

        self.assertEqual(unknown.status_code, 422)

    def test_multimodal_keyframe_is_blocked_until_enabled(self):
        client, _ = self.make_client()

        response = client.post(
            "/rikka/multimodal/keyframe",
            json={"reason": "unit_test", "keyframe_base64": "raw-image"},
        )

        self.assertEqual(response.status_code, 403)

    def test_multimodal_keyframe_enabled_returns_privacy_safe_stub(self):
        client, _ = self.make_client()
        update = client.patch(
            "/rikka/settings",
            json={
                "keyframe_upload_enabled": True,
                "multimodal_provider": "cloud_fallback_stub",
            },
        )
        self.assertEqual(update.status_code, 200)
        self.assertTrue(
            update.json()["providers"]["privacy"]["keyframe_upload_enabled"]
        )

        response = client.post(
            "/rikka/multimodal/keyframe",
            json={
                "reason": "unit_test",
                "event_id": "event-1",
                "keyframe_base64": "raw-image",
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "queued_stub")
        self.assertEqual(payload["provider"], "cloud_fallback_stub")
        self.assertTrue(payload["keyframe_supplied"])
        self.assertIsNotNone(payload["latest_frame"])
        self.assertIsNone(payload["no_frame_reason"])
        self.assertTrue(payload["provider_configured"])
        self.assertTrue(payload["normal_user_turn_is_e2e_test"])
        self.assertFalse(payload["raw_media_persisted"])

    def test_multimodal_smoke_without_frame_reports_no_frame_reason(self):
        client, _ = self.make_client()
        update = client.patch(
            "/rikka/settings",
            json={
                "keyframe_upload_enabled": True,
                "multimodal_provider": "not_configured",
            },
        )
        self.assertEqual(update.status_code, 200)

        response = client.post("/rikka/multimodal/keyframe", json={})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertFalse(payload["keyframe_supplied"])
        self.assertIsNone(payload["latest_frame"])
        self.assertEqual(payload["no_frame_reason"], "capture_disabled")
        self.assertFalse(payload["provider_configured"])
        self.assertTrue(payload["normal_user_turn_is_e2e_test"])

    def test_multimodal_smoke_reports_no_latest_frame_when_capture_is_ready_but_empty(self):
        client, _ = self.make_client()
        update = client.patch(
            "/rikka/settings",
            json={
                "screen_capture_enabled": True,
                "keyframe_upload_enabled": True,
                "multimodal_provider": "openai_compatible_llm",
                "capture": {
                    "enabled": True,
                    "attach_to_user_turns": True,
                },
            },
        )
        self.assertEqual(update.status_code, 200)

        response = client.post("/rikka/multimodal/keyframe", json={})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIsNone(payload["latest_frame"])
        self.assertEqual(payload["no_frame_reason"], "no_latest_frame")
        self.assertTrue(payload["provider_configured"])


if __name__ == "__main__":
    unittest.main()

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from open_llm_vtuber.rikka.core import (
    normalize_live_event,
    plan_rikka_response,
    validate_rikka_response,
)


class RikkaResponseValidationTest(unittest.TestCase):
    def test_valid_response_is_accepted(self):
        result = validate_rikka_response(
            {
                "spoken_text": "我听到了这条弹幕，像很轻的雨点。",
                "subtitle_text": "我听到了这条弹幕。",
                "emotion": "soft_smile",
                "motion": "nod",
                "gaze": "chat",
                "priority": "normal",
                "interruptible": True,
                "reason_code": "reply_chat",
            }
        )

        self.assertTrue(result.ok)
        self.assertEqual(result.response.reason_code, "reply_chat")

    def test_invalid_json_falls_back(self):
        result = validate_rikka_response(",,,")

        self.assertFalse(result.ok)
        self.assertEqual(result.response.reason_code, "safety_fallback")
        self.assertNotIn("<thinking>", result.response.spoken_text)

    def test_trailing_text_after_json_is_ignored(self):
        result = validate_rikka_response(
            rikka_payload_text("前半句。") + "\n补充说明：上面是最终 JSON。"
        )

        self.assertTrue(result.ok)
        self.assertEqual(result.response.spoken_text, "前半句。")

    def test_multiple_json_objects_uses_first_complete_object(self):
        result = validate_rikka_response(
            rikka_payload_text("第一句。") + "\n" + rikka_payload_text("第二句。")
        )

        self.assertTrue(result.ok)
        self.assertEqual(result.response.spoken_text, "第一句。")

    def test_screen_gaze_is_normalized_to_game(self):
        result = validate_rikka_response(
            {
                "spoken_text": "我看着屏幕这边。",
                "subtitle_text": "我看着屏幕这边。",
                "emotion": "curious",
                "motion": "thinking",
                "gaze": "screen",
                "priority": "normal",
                "interruptible": True,
                "reason_code": "reply_chat",
            }
        )

        self.assertTrue(result.ok)
        self.assertEqual(result.response.gaze, "game")

    def test_missing_subtitle_text_defaults_from_cleaned_spoken_text(self):
        result = validate_rikka_response(
            {
                "spoken_text": "嗯…看起来很复杂呢。[quiet]",
                "emotion": "quiet",
                "motion": "look_close",
                "gaze": "game",
                "priority": "low",
                "interruptible": True,
                "reason_code": "game_comment",
                "memory_writes": [],
            }
        )

        self.assertTrue(result.ok)
        self.assertTrue(result.repaired)
        self.assertIn("subtitle_text defaulted from spoken_text", result.repair_notes)
        self.assertEqual(result.response.spoken_text, "嗯…看起来很复杂呢。")
        self.assertEqual(result.response.subtitle_text, "嗯…看起来很复杂呢。")

    def test_incomplete_json_defaults_safe_optional_response_fields(self):
        result = validate_rikka_response({"spoken_text": "收到。"})

        self.assertTrue(result.ok)
        self.assertTrue(result.repaired)
        self.assertEqual(result.response.subtitle_text, "收到。")
        self.assertEqual(result.response.emotion, "neutral")
        self.assertEqual(result.response.motion, "idle")
        self.assertEqual(result.response.reason_code, "idle_fill")

    def test_malformed_response_with_spoken_text_is_repaired(self):
        result = validate_rikka_response(
            '模型乱说了一点，但还是给了 "spoken_text": "嗯…我看到了。[quiet]" '
            "后面格式全没了"
        )

        self.assertTrue(result.ok)
        self.assertTrue(result.repaired)
        self.assertIn(
            "spoken_text extracted from malformed response",
            result.repair_notes,
        )
        self.assertEqual(result.response.spoken_text, "嗯…我看到了。")
        self.assertEqual(result.response.subtitle_text, "嗯…我看到了。")
        self.assertEqual(result.response.motion, "idle")
        self.assertEqual(result.response.reason_code, "idle_fill")

    def test_malformed_response_with_single_quoted_spoken_text_is_repaired(self):
        result = validate_rikka_response(
            "broken payload spoken_text: '收到啦，先按这个说。' motion: backflip"
        )

        self.assertTrue(result.ok)
        self.assertTrue(result.repaired)
        self.assertEqual(result.response.spoken_text, "收到啦，先按这个说。")

    def test_plain_text_response_is_repaired_as_spoken_text(self):
        result = validate_rikka_response(
            "(轻轻歪头) Deliaru，你在研究什么有趣的东西吗？看起来好厉害的样子。"
        )

        self.assertTrue(result.ok)
        self.assertTrue(result.repaired)
        self.assertIn("plain text used as spoken_text", result.repair_notes)
        self.assertEqual(
            result.response.spoken_text,
            "Deliaru，你在研究什么有趣的东西吗？看起来好厉害的样子。",
        )
        self.assertEqual(result.response.subtitle_text, result.response.spoken_text)
        self.assertEqual(result.response.motion, "idle")
        self.assertEqual(result.response.reason_code, "idle_fill")

    def test_provider_error_text_is_not_repaired_as_plain_text(self):
        result = validate_rikka_response(
            "Error calling the responses endpoint: provider returned HTTP 502. "
            "Detail: upstream failed."
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.response.reason_code, "safety_fallback")

    def test_hidden_thinking_only_plain_text_still_falls_back(self):
        result = validate_rikka_response("<thinking>secret only</thinking>")

        self.assertFalse(result.ok)
        self.assertEqual(result.response.reason_code, "safety_fallback")

    def test_hidden_thinking_is_removed(self):
        result = validate_rikka_response(
            """
            {
              "spoken_text": "<thinking>secret</thinking>嗯，我看到了。",
              "subtitle_text": "<think>secret</think>嗯，我看到了。",
              "emotion": "quiet",
              "motion": "thinking",
              "gaze": "chat",
              "priority": "normal",
              "interruptible": true,
              "reason_code": "reply_chat"
            }
            """
        )

        self.assertTrue(result.ok)
        self.assertEqual(result.response.spoken_text, "嗯，我看到了。")
        self.assertEqual(result.response.subtitle_text, "嗯，我看到了。")

    def test_leading_stage_direction_is_removed_from_public_output(self):
        result = validate_rikka_response(
            {
                "spoken_text": "[joy]嗯，收到啦。",
                "subtitle_text": "（开心）收到。",
                "emotion": "soft_smile",
                "motion": "nod",
                "gaze": "chat",
                "priority": "normal",
                "interruptible": True,
                "reason_code": "reply_chat",
            }
        )

        self.assertTrue(result.ok)
        self.assertEqual(result.response.spoken_text, "嗯，收到啦。")
        self.assertEqual(result.response.subtitle_text, "收到。")

    def test_inline_action_tags_are_removed_from_public_output(self):
        result = validate_rikka_response(
            {
                "spoken_text": "晚上好呀。[soft_smile] 今天的声音很安静。",
                "subtitle_text": "晚上好呀。[nod] 今天的声音很安静。",
                "emotion": "soft_smile",
                "motion": "nod",
                "gaze": "chat",
                "priority": "normal",
                "interruptible": True,
                "reason_code": "reply_chat",
            }
        )

        self.assertTrue(result.ok)
        self.assertEqual(result.response.spoken_text, "晚上好呀。 今天的声音很安静。")
        self.assertEqual(result.response.subtitle_text, "晚上好呀。 今天的声音很安静。")

    def test_overlong_subtitle_is_repaired(self):
        long_text = "这一条字幕会很长" * 20
        result = validate_rikka_response(
            {
                "spoken_text": long_text,
                "subtitle_text": long_text,
                "emotion": "neutral",
                "motion": "idle",
                "gaze": "camera",
                "priority": "low",
                "interruptible": True,
                "reason_code": "idle_fill",
            }
        )

        self.assertTrue(result.ok)
        self.assertLessEqual(len(result.response.subtitle_text), 80)

    def test_unknown_emotion_is_lowercased_and_accepted(self):
        result = validate_rikka_response(
            {
                "spoken_text": "看到啦。",
                "subtitle_text": "看到啦。",
                "emotion": "Starry_Eyes",
                "motion": "idle",
                "gaze": "camera",
                "priority": "normal",
                "interruptible": True,
                "reason_code": "reply_chat",
            }
        )

        self.assertTrue(result.ok)
        self.assertEqual(result.response.emotion, "starry_eyes")

    def test_empty_emotion_falls_back_to_neutral(self):
        result = validate_rikka_response(
            {
                "spoken_text": "嗯。",
                "subtitle_text": "嗯。",
                "emotion": "  ",
                "motion": "idle",
                "gaze": "camera",
                "priority": "normal",
                "interruptible": True,
                "reason_code": "reply_chat",
            }
        )

        self.assertTrue(result.ok)
        self.assertEqual(result.response.emotion, "neutral")

    def test_invalid_motion_with_spoken_text_defaults_to_repaired_response(self):
        result = validate_rikka_response(
            {
                "spoken_text": "嗯。",
                "subtitle_text": "嗯。",
                "emotion": "neutral",
                "motion": "backflip",
                "gaze": "camera",
                "priority": "normal",
                "interruptible": True,
                "reason_code": "reply_chat",
            }
        )

        self.assertTrue(result.ok)
        self.assertTrue(result.repaired)
        self.assertEqual(result.response.motion, "idle")
        self.assertEqual(result.response.spoken_text, "嗯。")
        self.assertEqual(result.response.reason_code, "idle_fill")

    def test_memory_writes_shape_drift_is_repaired_before_validation(self):
        result = validate_rikka_response(
            {
                "spoken_text": "记住啦，炒蛋这件事我放好了。",
                "subtitle_text": "记住啦，炒蛋这件事我放好了。",
                "emotion": "soft_smile",
                "motion": "nod",
                "gaze": "camera",
                "priority": "normal",
                "interruptible": True,
                "reason_code": "reply_chat",
                "memory_writes": [
                    {
                        "key": "user_preference_food",
                        "value": "喜欢吃炒蛋",
                        "source_event_id": "debug-event",
                    }
                ],
            }
        )

        self.assertTrue(result.ok)
        self.assertEqual(len(result.response.memory_writes), 1)
        self.assertEqual(result.response.memory_writes[0].kind, "preference")
        self.assertEqual(result.response.memory_writes[0].key, "user_preference_food")

    def test_debug_event_generates_response(self):
        event = normalize_live_event(
            {
                "type": "chat.message",
                "source": "debug",
                "actor": {"display_name": "viewer"},
                "text": "六花晚上好",
            }
        )
        result = plan_rikka_response(event)

        self.assertTrue(result.ok)
        self.assertEqual(result.response.reason_code, "reply_chat")
        self.assertIn("viewer", result.response.spoken_text)

    def test_fallback_uses_configured_identity_defaults_by_source(self):
        fake_store = SimpleNamespace(
            snapshot=lambda: SimpleNamespace(
                identity=SimpleNamespace(
                    host_display_name="\u4e3b\u64ad\u7532",
                    audience_display_name="\u89c2\u4f17\u5e2d",
                )
            )
        )
        with patch(
            "open_llm_vtuber.rikka.core.get_default_settings_store",
            return_value=fake_store,
        ):
            debug_event = normalize_live_event(
                {
                    "type": "chat.message",
                    "source": "debug",
                    "text": "测试",
                }
            )
            bilibili_event = normalize_live_event(
                {
                    "type": "chat.message",
                    "source": "bilibili",
                    "text": "测试",
                }
            )
            host_event = normalize_live_event(
                {
                    "type": "host.note",
                    "source": "host",
                    "text": "测试",
                }
            )
            debug_result = plan_rikka_response(debug_event)
            bilibili_result = plan_rikka_response(bilibili_event)
            host_result = plan_rikka_response(host_event)

        self.assertIn("\u4e3b\u64ad\u7532", debug_result.response.spoken_text)
        self.assertIn("\u89c2\u4f17\u5e2d", bilibili_result.response.spoken_text)
        self.assertIn("\u4e3b\u64ad\u7532", host_result.response.spoken_text)

    def test_debug_actor_platform_is_allowed(self):
        event = normalize_live_event(
            {
                "type": "host.note",
                "source": "debug",
                "actor": {
                    "platform": "debug",
                    "user_id": "local-debugger",
                    "display_name": "debugger",
                },
                "text": "切到调试事件。",
            }
        )

        self.assertEqual(event.actor.platform, "debug")


def rikka_payload_text(text: str) -> str:
    return (
        "{"
        f'"spoken_text": "{text}",'
        f'"subtitle_text": "{text}",'
        '"emotion": "curious",'
        '"motion": "thinking",'
        '"gaze": "camera",'
        '"priority": "normal",'
        '"interruptible": true,'
        '"reason_code": "reply_chat"'
        "}"
    )


if __name__ == "__main__":
    unittest.main()

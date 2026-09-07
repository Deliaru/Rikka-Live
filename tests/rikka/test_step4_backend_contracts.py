"""Step 4 validation: dynamic emotion vocabulary + preset resolution + settings."""

import unittest

from open_llm_vtuber.rikka.persona import build_emotion_vocabulary
from open_llm_vtuber.rikka.presentation import (
    resolve_rikka_expression,
    resolve_rikka_motion,
    rikka_response_to_actions,
)
from open_llm_vtuber.rikka.schemas import RikkaResponse
from open_llm_vtuber.rikka.settings import Live2DSettings, RikkaSettings


class DummyLive2DModel:
    def __init__(self, emo_map=None, model_info=None):
        self.emo_map = emo_map or {}
        self.model_info = model_info or {}


PRESET_MODEL_INFO = {
    "expressionPresets": {
        "neutral": {"label": "平静", "parameters": {}, "fade_ms": 300},
        "soft_smile": {
            "label": "浅笑",
            "parameters": {"ParamEyeLSmile": 0.35, "ParamMouthForm": 0.15},
            "fade_ms": 400,
            "hold_after_speech_ms": 2500,
        },
        "curious": {"label": "好奇", "parameters": {"ParamBrowLY": 0.2}},
    },
    "gestureMap": {
        "nod": {
            "kind": "nod",
            "amplitude": 1.0,
            "duration_ms": 900,
            "cooldown_ms": 1800,
        },
        "thinking": {"kind": "think_pose", "amplitude": 0.9, "duration_ms": 1800},
    },
}

LEGACY_MODEL_INFO = {
    "motionMap": {
        "nod": {"group": "", "index": 16, "priority": "normal", "cooldown_ms": 1200},
    },
}


class Step4BackendContractsTest(unittest.TestCase):
    def test_emotion_relaxed_to_str_with_fallback(self):
        """schemas.py: emotion is str with lowercase + neutral fallback."""
        response = RikkaResponse.model_validate(
            {
                "spoken_text": "测试。",
                "subtitle_text": "测试。",
                "emotion": "Unknown_Emotion",
                "motion": "idle",
                "gaze": "camera",
                "priority": "normal",
                "interruptible": True,
                "reason_code": "reply_chat",
            }
        )
        self.assertEqual(response.emotion, "unknown_emotion")

        empty_response = RikkaResponse.model_validate(
            {
                "spoken_text": "测试。",
                "subtitle_text": "测试。",
                "emotion": "  ",
                "motion": "idle",
                "gaze": "camera",
                "priority": "normal",
                "interruptible": True,
                "reason_code": "reply_chat",
            }
        )
        self.assertEqual(empty_response.emotion, "neutral")

    def test_unknown_emotion_falls_back_to_neutral_at_resolution(self):
        """presentation.py: unknown emotion → neutral preset fallback."""
        model = DummyLive2DModel(model_info=PRESET_MODEL_INFO)
        expression = resolve_rikka_expression(model, "starry_eyes")
        self.assertIsNotNone(expression)
        self.assertEqual(expression["name"], "neutral")
        self.assertEqual(expression["preset"]["label"], "平静")

    def test_preset_resolution_returns_inline_preset(self):
        """presentation.py: resolve_rikka_expression returns {"name", "preset"}."""
        model = DummyLive2DModel(model_info=PRESET_MODEL_INFO)
        expression = resolve_rikka_expression(model, "soft_smile")
        self.assertEqual(expression["name"], "soft_smile")
        self.assertEqual(expression["preset"]["label"], "浅笑")
        self.assertEqual(expression["preset"]["fade_ms"], 400)
        self.assertEqual(expression["preset"]["hold_after_speech_ms"], 2500)
        self.assertIn("ParamEyeLSmile", expression["preset"]["parameters"])

    def test_legacy_emotionmap_branch_still_works(self):
        """presentation.py: models without expressionPresets use legacy emo_map."""
        model = DummyLive2DModel(emo_map={"soft_smile": 7})
        expression = resolve_rikka_expression(model, "soft_smile")
        self.assertEqual(expression, 7)

    def test_gesture_map_returns_envelope_payload_with_cooldown(self):
        """presentation.py: resolve_rikka_motion from gestureMap."""
        model = DummyLive2DModel(model_info=PRESET_MODEL_INFO)
        motion = resolve_rikka_motion(model, "nod")
        self.assertEqual(motion["name"], "nod")
        self.assertEqual(motion["kind"], "nod")
        self.assertEqual(motion["amplitude"], 1.0)
        self.assertEqual(motion["duration_ms"], 900)
        self.assertEqual(motion["cooldown_ms"], 1800)

    def test_gesture_map_missing_fields_use_defaults(self):
        """presentation.py: gestureMap fills missing fields with defaults."""
        model = DummyLive2DModel(model_info=PRESET_MODEL_INFO)
        motion = resolve_rikka_motion(model, "thinking")
        self.assertEqual(motion["kind"], "think_pose")
        self.assertEqual(motion["duration_ms"], 1800)
        self.assertEqual(motion["cooldown_ms"], 1200)

    def test_legacy_motionmap_branch_still_works(self):
        """presentation.py: models without gestureMap use legacy motionMap."""
        model = DummyLive2DModel(model_info=LEGACY_MODEL_INFO)
        motion = resolve_rikka_motion(model, "nod")
        self.assertEqual(motion["name"], "nod")
        self.assertEqual(motion["group"], "")
        self.assertEqual(motion["index"], 16)
        self.assertIn("cooldown_ms", motion)

    def test_enable_expression_actions_defaults_to_true(self):
        """presentation.py: enable_expression_actions defaults to True."""
        model = DummyLive2DModel(emo_map={"soft_smile": 7})
        response = RikkaResponse.model_validate(
            {
                "spoken_text": "测试。",
                "subtitle_text": "测试。",
                "emotion": "soft_smile",
                "motion": "idle",
                "gaze": "camera",
                "priority": "normal",
                "interruptible": True,
                "reason_code": "reply_chat",
            }
        )
        actions = rikka_response_to_actions(response, model)
        self.assertIsNotNone(actions.expressions)

    def test_settings_gate_can_disable_expressions(self):
        """settings.py: live2d.expressions_enabled gates expression actions."""
        settings = RikkaSettings()
        self.assertTrue(settings.live2d.expressions_enabled)

        disabled_settings = RikkaSettings(
            live2d=Live2DSettings(expressions_enabled=False)
        )
        self.assertFalse(disabled_settings.live2d.expressions_enabled)

    def test_dynamic_vocabulary_built_from_presets(self):
        """persona.py: dynamic emotion vocabulary from configured presets."""
        vocabulary = build_emotion_vocabulary(PRESET_MODEL_INFO)
        self.assertIsNotNone(vocabulary)
        self.assertIn("neutral（平静）", vocabulary)
        self.assertIn("soft_smile（浅笑）", vocabulary)
        self.assertIn("curious（好奇）", vocabulary)

    def test_dynamic_vocabulary_returns_none_when_missing(self):
        """persona.py: no expressionPresets → None (static fallback)."""
        self.assertIsNone(build_emotion_vocabulary(None))
        self.assertIsNone(build_emotion_vocabulary({}))
        self.assertIsNone(build_emotion_vocabulary({"expressionPresets": {}}))


if __name__ == "__main__":
    unittest.main()

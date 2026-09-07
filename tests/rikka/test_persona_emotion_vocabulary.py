import os
import tempfile
import unittest
from pathlib import Path

from open_llm_vtuber.rikka.persona import (
    DEFAULT_RESPONSE_PROMPT,
    apply_emotion_vocabulary,
    build_emotion_vocabulary,
    build_rikka_system_prompt,
)


PRESET_MODEL_INFO = {
    "expressionPresets": {
        "neutral": {"label": "平静", "parameters": {}},
        "soft_smile": {"label": "浅笑", "parameters": {"ParamMouthForm": 0.15}},
        "starlight": {"parameters": {"ParamEyeLSmile": 0.2}},
    },
}


class RikkaEmotionVocabularyTests(unittest.TestCase):
    def test_missing_config_returns_none(self):
        self.assertIsNone(build_emotion_vocabulary(None))
        self.assertIsNone(build_emotion_vocabulary({}))
        self.assertIsNone(build_emotion_vocabulary({"expressionPresets": []}))
        self.assertIsNone(build_emotion_vocabulary({"expressionPresets": {}}))

    def test_vocabulary_uses_preset_names_and_labels(self):
        vocabulary = build_emotion_vocabulary(PRESET_MODEL_INFO)

        self.assertEqual(
            vocabulary,
            "neutral（平静）, soft_smile（浅笑）, starlight。",
        )

    def test_static_prompt_line_is_replaced_with_configured_presets(self):
        prompt = apply_emotion_vocabulary(DEFAULT_RESPONSE_PROMPT, PRESET_MODEL_INFO)

        self.assertIn("starlight", prompt)
        self.assertIn("soft_smile（浅笑）", prompt)
        self.assertNotIn("teasing", prompt)
        self.assertIn("motion 可选：", prompt)

    def test_prompt_without_marker_gets_vocabulary_appended(self):
        prompt = apply_emotion_vocabulary("自定义输出协议。", PRESET_MODEL_INFO)

        self.assertTrue(prompt.startswith("自定义输出协议。"))
        self.assertIn("emotion 可选：\nneutral（平静）", prompt)

    def test_missing_config_keeps_static_prompt(self):
        prompt = apply_emotion_vocabulary(DEFAULT_RESPONSE_PROMPT, None)

        self.assertEqual(prompt, DEFAULT_RESPONSE_PROMPT)
        self.assertIn("teasing, quiet。", prompt)

    def test_system_prompt_uses_dynamic_vocabulary_when_configured(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            persona_path = Path(tmp_dir) / "prompt.txt"
            persona_path.write_text("你是弥生月六花。", encoding="utf-8")
            response_path = Path(tmp_dir) / "response.txt"
            response_path.write_text(DEFAULT_RESPONSE_PROMPT, encoding="utf-8")
            os.environ["RIKKA_PERSONA_PATH"] = str(persona_path)
            os.environ["RIKKA_RESPONSE_PROMPT_PATH"] = str(response_path)
            try:
                dynamic_prompt = build_rikka_system_prompt(PRESET_MODEL_INFO)
                static_prompt = build_rikka_system_prompt()
            finally:
                os.environ.pop("RIKKA_PERSONA_PATH", None)
                os.environ.pop("RIKKA_RESPONSE_PROMPT_PATH", None)

        self.assertIn("你是弥生月六花。", dynamic_prompt)
        self.assertIn("starlight", dynamic_prompt)
        self.assertNotIn("worried", dynamic_prompt)
        self.assertIn("teasing, quiet。", static_prompt)
        self.assertNotIn("starlight", static_prompt)


if __name__ == "__main__":
    unittest.main()

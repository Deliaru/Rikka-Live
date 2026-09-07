import base64
import os
import unittest
from types import SimpleNamespace

from open_llm_vtuber.config_manager.tts import XiaomiMimoTTSConfig
from open_llm_vtuber.tts.xiaomi_mimo_tts import (
    PRESET_MODEL,
    VOICE_CLONE_MODEL,
    VOICE_DESIGN_MODEL,
    TTSEngine,
)


class FakeMimoClient:
    def __init__(self, audio_bytes: bytes = b"fake-audio"):
        self.last_request = None
        self.chat = SimpleNamespace(
            completions=SimpleNamespace(create=self._create)
        )
        self._audio_data = base64.b64encode(audio_bytes).decode("utf-8")

    def _create(self, **kwargs):
        self.last_request = kwargs
        message = SimpleNamespace(audio={"data": self._audio_data})
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class XiaomiMimoTTSTests(unittest.TestCase):
    def tearDown(self):
        for name in (
            "mimo_preset_test.wav",
            "mimo_clone_test.wav",
            "mimo_design_test.wav",
        ):
            path = os.path.join("cache", name)
            if os.path.exists(path):
                os.remove(path)

    def test_preset_model_uses_configured_voice(self):
        engine = TTSEngine(
            api_key="test-key",
            model=PRESET_MODEL,
            voice="冰糖",
        )
        fake_client = FakeMimoClient()
        engine.client = fake_client

        output_path = engine.generate_audio("六花试音。", "mimo_preset_test")

        self.assertEqual(output_path, os.path.join("cache", "mimo_preset_test.wav"))
        self.assertTrue(os.path.exists(output_path))
        self.assertEqual(fake_client.last_request["model"], PRESET_MODEL)
        self.assertEqual(fake_client.last_request["audio"]["voice"], "冰糖")
        self.assertEqual(
            fake_client.last_request["messages"][1],
            {"role": "assistant", "content": "六花试音。"},
        )

    def test_voice_clone_model_uses_reference_audio_data_uri(self):
        reference_audio = base64.b64encode(b"voice-sample").decode("utf-8")
        engine = TTSEngine(
            api_key="test-key",
            model=VOICE_CLONE_MODEL,
            voice_audio_base64=reference_audio,
            voice_mime_type="audio/wav",
        )
        fake_client = FakeMimoClient()
        engine.client = fake_client

        engine.generate_audio("六花复刻试音。", "mimo_clone_test")

        voice = fake_client.last_request["audio"]["voice"]
        self.assertTrue(voice.startswith("data:audio/wav;base64,"))
        self.assertIn(reference_audio, voice)

    def test_voice_design_model_uses_user_prompt_without_voice_field(self):
        voice_prompt = "A silver-haired virtual singer with a bright Chinese voice."
        engine = TTSEngine(
            api_key="test-key",
            model=VOICE_DESIGN_MODEL,
            voice_design_prompt=voice_prompt,
            optimize_text_preview=True,
        )
        fake_client = FakeMimoClient()
        engine.client = fake_client

        engine.generate_audio("六花文本设计试音。", "mimo_design_test")

        self.assertEqual(
            fake_client.last_request["messages"][0],
            {"role": "user", "content": voice_prompt},
        )
        self.assertNotIn("voice", fake_client.last_request["audio"])
        self.assertTrue(fake_client.last_request["audio"]["optimize_text_preview"])

    def test_config_defaults_to_preset_model(self):
        config = XiaomiMimoTTSConfig.model_validate({})

        self.assertEqual(config.model, PRESET_MODEL)
        self.assertEqual(config.voice, "mimo_default")
        self.assertEqual(config.audio_format, "wav")
        self.assertEqual(config.timeout_seconds, 45.0)

    def test_engine_passes_timeout_to_openai_client(self):
        engine = TTSEngine(
            api_key="test-key",
            model=PRESET_MODEL,
            timeout_seconds=12.5,
        )

        self.assertEqual(engine.timeout_seconds, 12.5)


if __name__ == "__main__":
    unittest.main()

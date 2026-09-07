import base64
import os
import unittest
from unittest.mock import patch

from open_llm_vtuber.config_manager.tts import IndexTTS2Config
from open_llm_vtuber.tts.indextts2_tts import TTSEngine
from open_llm_vtuber.tts.tts_factory import TTSFactory


class FakeResponse:
    def __init__(
        self,
        content: bytes = b"fake-wav",
        content_type: str = "audio/wav",
        payload: dict | None = None,
    ):
        self.content = content
        self.headers = {"content-type": content_type}
        self._payload = payload or {}

    def json(self):
        return self._payload

    def raise_for_status(self):
        return None


class IndexTTS2TTSTests(unittest.TestCase):
    def tearDown(self):
        for name in ("indextts2_bytes_test.wav", "indextts2_json_test.wav"):
            path = os.path.join("cache", name)
            if os.path.exists(path):
                os.remove(path)

    def test_config_defaults_to_cloud_modelverse_service(self):
        config = IndexTTS2Config.model_validate({})

        self.assertEqual(config.mode, "cloud")
        self.assertEqual(config.base_url, "https://api.modelverse.cn/v1")
        self.assertEqual(config.model, "IndexTeam/IndexTTS-2")
        self.assertEqual(config.voice_id, "")
        self.assertEqual(config.default_tts_style, "default")
        self.assertEqual(config.quiet_companion_emo_alpha, 1.0)
        self.assertEqual(
            config.quiet_companion_emo_vec,
            [0.10, 0, 0, 0, 0, 0.20, 0, 0.10],
        )
        self.assertEqual(config.api_url, "http://127.0.0.1:7861/tts")
        self.assertEqual(config.audio_format, "wav")
        self.assertEqual(config.emo_audio_path, "")
        self.assertEqual(config.emo_alpha, 0.6)
        self.assertFalse(config.use_emo_text)
        self.assertFalse(config.use_random)
        self.assertEqual(config.timeout_seconds, 180.0)
        self.assertFalse(config.sentence_split_enabled)
        self.assertEqual(config.sentence_split_method, "regex")
        self.assertEqual(config.max_text_tokens_per_segment, 80)
        self.assertEqual(config.sentence_interval_ms, 0)

    def test_factory_creates_indextts2_engine(self):
        engine = TTSFactory.get_tts_engine(
            "indextts2_tts",
            mode="local",
            api_url="http://127.0.0.1:7861/tts",
            speaker_audio_path="private/voice/rikka_voice_clone.wav",
            timeout_seconds=12,
        )

        self.assertIsInstance(engine, TTSEngine)
        self.assertEqual(engine.timeout_seconds, 12)

    def test_provider_posts_reference_audio_and_writes_audio_bytes(self):
        engine = TTSEngine(
            mode="local",
            api_url="http://127.0.0.1:7861/tts",
            speaker_audio_path="private/voice/rikka_voice_clone.wav",
        )

        with patch(
            "open_llm_vtuber.tts.indextts2_tts.requests.post",
            return_value=FakeResponse(content=b"wav-bytes"),
        ) as post:
            output_path = engine.generate_audio("六花试音。", "indextts2_bytes_test")

        self.assertEqual(output_path, os.path.join("cache", "indextts2_bytes_test.wav"))
        self.assertTrue(os.path.exists(output_path))
        with open(output_path, "rb") as output_file:
            self.assertEqual(output_file.read(), b"wav-bytes")
        payload = post.call_args.kwargs["json"]
        self.assertEqual(payload["text"], "六花试音。")
        self.assertTrue(payload["speaker_audio_path"].endswith("rikka_voice_clone.wav"))

    def test_provider_posts_emotion_controls(self):
        engine = TTSEngine(
            mode="local",
            api_url="http://127.0.0.1:7861/tts",
            speaker_audio_path="private/voice/rikka_voice_clone.wav",
            emo_audio_path="private/voice/rikka_emo_cute.wav",
            emo_alpha=0.82,
            use_emo_text=True,
            emo_text="可爱、明亮、稍微夹一点。",
            use_random=False,
            max_text_tokens_per_segment=64,
        )

        with patch(
            "open_llm_vtuber.tts.indextts2_tts.requests.post",
            return_value=FakeResponse(content=b"wav-bytes"),
        ) as post:
            output_path = engine.generate_audio("情绪参数测试。", "indextts2_bytes_test")

        self.assertEqual(output_path, os.path.join("cache", "indextts2_bytes_test.wav"))
        payload = post.call_args.kwargs["json"]
        self.assertTrue(payload["emo_audio_path"].endswith("rikka_emo_cute.wav"))
        self.assertEqual(payload["emo_alpha"], 0.82)
        self.assertTrue(payload["use_emo_text"])
        self.assertEqual(payload["emo_text"], "可爱、明亮、稍微夹一点。")
        self.assertFalse(payload["use_random"])
        self.assertFalse(payload["sentence_split_enabled"])
        self.assertEqual(payload["sentence_split_method"], "regex")
        self.assertEqual(payload["max_text_tokens_per_segment"], 64)

    def test_provider_accepts_json_base64_audio(self):
        engine = TTSEngine(mode="local", api_url="http://127.0.0.1:7861/tts")
        audio_base64 = base64.b64encode(b"json-wav").decode("utf-8")

        with patch(
            "open_llm_vtuber.tts.indextts2_tts.requests.post",
            return_value=FakeResponse(
                content_type="application/json",
                payload={"audio_base64": audio_base64},
            ),
        ):
            output_path = engine.generate_audio("JSON 音频。", "indextts2_json_test")

        self.assertEqual(output_path, os.path.join("cache", "indextts2_json_test.wav"))
        with open(output_path, "rb") as output_file:
            self.assertEqual(output_file.read(), b"json-wav")

    def test_cloud_default_payload_only_uses_model_input_and_voice(self):
        engine = TTSEngine(
            api_key="mv-secret",
            voice_id="uspeech:test-voice",
        )

        payload = engine._build_cloud_payload(
            "[joy]收到啦。谢谢小明的加油……",
        )

        self.assertEqual(
            payload,
            {
                "model": "IndexTeam/IndexTTS-2",
                "input": "收到啦。谢谢小明的加油……",
                "voice": "uspeech:test-voice",
            },
        )
        self.assertNotIn("sample_rate", payload)
        self.assertNotIn("speed", payload)
        self.assertNotIn("emo_text", payload)
        self.assertNotIn("max_text_tokens_per_sentence", payload)
        self.assertNotIn("max_text_tokens_per_segment", payload)
        self.assertNotIn("interval_silence", payload)

    def test_cloud_sentence_controls_are_explicit_opt_in(self):
        engine = TTSEngine(
            api_key="mv-secret",
            voice_id="uspeech:test-voice",
            sentence_split_enabled=True,
            max_text_tokens_per_segment=48,
            sentence_interval_ms=350,
        )

        payload = engine._build_cloud_payload("第一句。第二句。")

        self.assertEqual(payload["max_text_tokens_per_segment"], 48)
        self.assertEqual(payload["interval_silence"], 0.35)

    def test_cloud_quiet_companion_payload_uses_fixed_baseline_vector(self):
        engine = TTSEngine(
            api_key="mv-secret",
            voice_id="uspeech:test-voice",
        )

        payload = engine._build_cloud_payload(
            "今晚轻轻陪你。",
            tts_style="quiet_companion",
        )

        self.assertEqual(payload["emo_control_method"], 2)
        self.assertEqual(payload["emo_alpha"], 1.0)
        self.assertEqual(payload["emo_vec"], [0.10, 0, 0, 0, 0, 0.20, 0, 0.10])
        self.assertFalse(payload["emo_random"])

    def test_cloud_quiet_companion_payload_uses_configured_vector(self):
        engine = TTSEngine(
            api_key="mv-secret",
            voice_id="uspeech:test-voice",
            quiet_companion_emo_alpha=0.9,
            quiet_companion_emo_vec=[0.12, 0, 0.04, 0, 0, 0.18, 0.03, 0.08],
        )

        payload = engine._build_cloud_payload(
            "今晚轻轻陪你。",
            tts_style="quiet_companion",
        )

        self.assertEqual(payload["emo_alpha"], 0.9)
        self.assertEqual(payload["emo_vec"], [0.12, 0, 0.04, 0, 0, 0.18, 0.03, 0.08])

    def test_cloud_emotion_adjustments_are_bounded(self):
        engine = TTSEngine(
            api_key="mv-secret",
            voice_id="uspeech:test-voice",
        )

        payload = engine._build_cloud_payload(
            "有一点开心，也有一点惊讶。",
            tts_style="quiet_companion",
            emotion_vec={
                "happy": 0.5,
                "angry": 0.1,
                "fear": 0.1,
                "sad": 0.3,
                "melancholy": 0,
                "surprise": 0.25,
                "calm": 0,
            },
        )

        self.assertEqual(payload["emo_vec"], [0.15, 0, 0.19, 0, 0, 0.20, 0.19, 0.10])

    def test_cloud_generation_posts_modelverse_payload_and_writes_wav(self):
        engine = TTSEngine(
            api_key="mv-secret",
            voice_id="uspeech:test-voice",
            timeout_seconds=12,
        )

        with patch(
            "open_llm_vtuber.tts.indextts2_tts.requests.post",
            return_value=FakeResponse(content=b"cloud-wav"),
        ) as post:
            output_path = engine.generate_audio("云端试音。", "indextts2_bytes_test")

        self.assertEqual(output_path, os.path.join("cache", "indextts2_bytes_test.wav"))
        self.assertTrue(os.path.exists(output_path))
        self.assertEqual(
            post.call_args.args[0],
            "https://api.modelverse.cn/v1/audio/speech",
        )
        self.assertEqual(
            post.call_args.kwargs["json"],
            {
                "model": "IndexTeam/IndexTTS-2",
                "input": "云端试音。",
                "voice": "uspeech:test-voice",
            },
        )
        self.assertEqual(
            post.call_args.kwargs["headers"]["Authorization"],
            "Bearer mv-secret",
        )
        with open(output_path, "rb") as output_file:
            self.assertEqual(output_file.read(), b"cloud-wav")

    def test_cloud_missing_key_or_voice_returns_none_without_request(self):
        with patch("open_llm_vtuber.tts.indextts2_tts.requests.post") as post:
            self.assertIsNone(TTSEngine(voice_id="uspeech:test").generate_audio("试音"))
            self.assertIsNone(TTSEngine(api_key="mv-secret").generate_audio("试音"))

        post.assert_not_called()

    def test_cloud_config_strips_forbidden_production_fields(self):
        config = IndexTTS2Config.model_validate(
            {
                "mode": "cloud",
                "sample_rate": 44100,
                "speed": 0.9,
                "emo_weight": 0.5,
                "stream": True,
            }
        )

        dumped = config.model_dump()
        self.assertNotIn("sample_rate", dumped)
        self.assertNotIn("speed", dumped)
        self.assertNotIn("emo_weight", dumped)
        self.assertNotIn("stream", dumped)


if __name__ == "__main__":
    unittest.main()

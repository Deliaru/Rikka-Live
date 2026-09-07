import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import yaml
from fastapi import FastAPI
from fastapi.testclient import TestClient

from open_llm_vtuber.rikka.debug_console import (
    DebugConfigUpdate,
    error_snapshot,
    log_snapshot,
    patch_debug_config,
    snapshot_debug_config,
)
from open_llm_vtuber.rikka.routes import init_rikka_routes
from open_llm_vtuber.rikka.settings import RikkaSettingsStore
from open_llm_vtuber.utils.log_redaction import redact_debug_text


APP_ROOT = Path(__file__).resolve().parents[2]


def write_demo_config(path: Path) -> None:
    path.write_text(
        yaml.safe_dump(
            {
                "character_config": {
                    "agent_config": {
                        "agent_settings": {
                            "basic_memory_agent": {
                                "llm_provider": "openai_compatible_llm",
                            }
                        },
                        "llm_configs": {
                            "openai_compatible_llm": {
                                "base_url": "http://127.0.0.1:8317/v1",
                                "llm_api_key": "sk-secret-demo",
                                "model": "gpt-5.5",
                                "api_mode": "chat",
                            }
                        },
                    },
                    "asr_config": {
                        "asr_model": "none",
                    },
                    "tts_config": {
                        "tts_model": "xiaomi_mimo_tts",
                        "xiaomi_mimo_tts": {
                            "api_key": "mimo-secret-demo",
                            "base_url": "https://api.xiaomimimo.com/v1",
                            "model": "mimo-v2.5-tts-voiceclone",
                            "voice": "冰糖",
                            "voice_audio_path": "private/voice/rikka_voice_clone.wav",
                            "timeout_seconds": 45,
                        },
                        "indextts2_tts": {
                            "mode": "cloud",
                            "api_key": "modelverse-secret-demo",
                            "base_url": "https://api.modelverse.cn/v1",
                            "model": "IndexTeam/IndexTTS-2",
                            "voice_id": "uspeech:secret-demo",
                            "default_tts_style": "default",
                            "quiet_companion_emo_alpha": 1.0,
                            "quiet_companion_emo_vec": [0.10, 0, 0, 0, 0, 0.20, 0, 0.10],
                            "api_url": "http://127.0.0.1:7861/tts",
                            "speaker_audio_path": "private/voice/rikka_voice_clone.wav",
                            "emo_audio_path": "private/voice/rikka_emo_cute.wav",
                            "emo_alpha": 0.82,
                            "use_emo_text": True,
                            "emo_text": "可爱、明亮、稍微夹一点。",
                            "use_random": False,
                            "timeout_seconds": 180,
                            "sentence_split_enabled": False,
                            "sentence_split_method": "regex",
                            "max_text_tokens_per_segment": 80,
                            "sentence_interval_ms": 0,
                        },
                    },
                },
                "live_config": {
                    "bilibili_live": {
                        "room_ids": [21013446],
                        "sessdata": "sess-secret-demo",
                    },
                }
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )


class ErrorTextAsyncLLM:
    async def chat_completion(self, messages, system=None, tools=None):
        yield "Error calling the chat endpoint: Rate limit exceeded."


class RikkaDebugConsoleTests(unittest.TestCase):
    def make_client(self):
        tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(tmp_dir.cleanup)
        root = Path(tmp_dir.name)
        config_path = root / "conf.yaml"
        log_dir = root / "logs"
        log_dir.mkdir()
        write_demo_config(config_path)
        (log_dir / "server.err.log").write_text(
            "INFO boot\nERROR planner failed cleanly\nTraceback demo\n",
            encoding="utf-8",
        )
        settings_store = RikkaSettingsStore(root / "settings.json")
        app = FastAPI()
        app.include_router(
            init_rikka_routes(
                None,
                settings_store=settings_store,
                config_path=config_path,
                log_dir=log_dir,
            )
        )
        return TestClient(app), config_path

    def test_debug_config_patch_hot_applies_when_context_can_reload(self):
        tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(tmp_dir.cleanup)
        root = Path(tmp_dir.name)
        config_path = root / "conf.yaml"
        log_dir = root / "logs"
        log_dir.mkdir()
        config_path.write_text(
            (APP_ROOT / "config_templates/conf.default.yaml").read_text(
                encoding="utf-8"
            ),
            encoding="utf-8",
        )

        class ReloadableContext:
            config = None
            system_config = None
            character_config = None

            async def load_from_config(self, config):
                self.config = config
                self.system_config = config.system_config
                self.character_config = config.character_config

        context = ReloadableContext()
        app = FastAPI()
        app.include_router(
            init_rikka_routes(
                context,
                settings_store=RikkaSettingsStore(root / "settings.json"),
                config_path=config_path,
                log_dir=log_dir,
            )
        )
        client = TestClient(app)

        response = client.patch(
            "/rikka/debug/config",
            json={"llm": {"model": "hot-applied-model"}},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertFalse(payload["config"]["restart_required"])
        self.assertEqual(payload["config"]["runtime_apply"]["status"], "applied")
        self.assertEqual(
            context.character_config.agent_config.llm_configs.openai_compatible_llm.model,
            "hot-applied-model",
        )

    def test_debug_config_exposes_and_updates_rikka_prompts(self):
        tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(tmp_dir.cleanup)
        root = Path(tmp_dir.name)
        config_path = root / "conf.yaml"
        persona_path = root / "persona.txt"
        response_path = root / "response.txt"
        write_demo_config(config_path)
        persona_path.write_text("旧角色提示词", encoding="utf-8")
        response_path.write_text("旧回应提示词", encoding="utf-8")

        with patch.dict(
            "os.environ",
            {
                "RIKKA_PERSONA_PATH": str(persona_path),
                "RIKKA_RESPONSE_PROMPT_PATH": str(response_path),
            },
        ):
            snapshot = snapshot_debug_config(config_path)
            self.assertEqual(snapshot["prompts"]["persona"]["text"], "旧角色提示词")
            self.assertEqual(snapshot["prompts"]["response"]["text"], "旧回应提示词")

            updated = patch_debug_config(
                DebugConfigUpdate.model_validate(
                    {
                    "prompts": {
                        "persona": {"text": "新角色提示词"},
                        "response": {"text": "新回应提示词"},
                    }
                    }
                ),
                config_path,
            )

        self.assertTrue(updated["restart_required"])
        self.assertEqual(persona_path.read_text(encoding="utf-8"), "新角色提示词")
        self.assertEqual(response_path.read_text(encoding="utf-8"), "新回应提示词")

    def test_debug_config_masks_secrets(self):
        client, _ = self.make_client()

        response = client.get("/rikka/debug/config")

        self.assertEqual(response.status_code, 200)
        config = response.json()["config"]
        self.assertTrue(config["llm"]["api_key_configured"])
        self.assertEqual(config["llm"]["api_mode"], "chat")
        self.assertNotIn("sk-secret-demo", str(config))
        self.assertTrue(config["tts"]["xiaomi_mimo_tts"]["api_key_configured"])
        self.assertNotIn("mimo-secret-demo", str(config))
        self.assertTrue(config["tts"]["indextts2_tts"]["api_key_configured"])
        self.assertTrue(config["tts"]["indextts2_tts"]["voice_id_configured"])
        self.assertNotIn("modelverse-secret-demo", str(config))
        self.assertNotIn("uspeech:secret-demo", str(config))
        self.assertEqual(config["tts"]["indextts2_tts"]["mode"], "cloud")
        self.assertEqual(
            config["tts"]["indextts2_tts"]["base_url"],
            "https://api.modelverse.cn/v1",
        )
        self.assertEqual(
            config["tts"]["indextts2_tts"]["emo_audio_path"],
            "private/voice/rikka_emo_cute.wav",
        )
        self.assertEqual(config["tts"]["indextts2_tts"]["emo_alpha"], 0.82)
        self.assertTrue(config["tts"]["indextts2_tts"]["use_emo_text"])
        self.assertEqual(
            config["tts"]["indextts2_tts"]["quiet_companion_emo_vec"],
            [0.10, 0, 0, 0, 0, 0.20, 0, 0.10],
        )
        self.assertFalse(config["tts"]["indextts2_tts"]["sentence_split_enabled"])
        self.assertEqual(config["tts"]["indextts2_tts"]["sentence_split_method"], "regex")
        self.assertEqual(config["tts"]["indextts2_tts"]["sentence_interval_ms"], 0)
        self.assertEqual(config["asr"]["provider"], "none")
        self.assertEqual(
            config["asr"]["available_providers"],
            ["none", "sherpa_onnx_asr"],
        )
        self.assertFalse(config["asr"]["sherpa_onnx_asr"]["ready"])
        self.assertEqual(
            config["asr"]["sherpa_onnx_asr"]["reason"],
            "sherpa_onnx_asr config block is missing",
        )
        self.assertEqual(config["live"]["bilibili_live"]["room_ids"], [21013446])
        self.assertTrue(config["live"]["bilibili_live"]["sessdata_configured"])
        self.assertNotIn("sess-secret-demo", str(config))

    def test_debug_config_reports_sherpa_model_readiness(self):
        tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(tmp_dir.cleanup)
        root = Path(tmp_dir.name)
        config_path = root / "conf.yaml"
        model_dir = root / "models" / "sherpa"
        model_dir.mkdir(parents=True)
        (model_dir / "model.onnx").write_bytes(b"fake")
        (model_dir / "tokens.txt").write_text("a 1\n", encoding="utf-8")
        config_path.write_text(
            yaml.safe_dump(
                {
                    "character_config": {
                        "asr_config": {
                            "asr_model": "sherpa_onnx_asr",
                            "sherpa_onnx_asr": {
                                "model_type": "sense_voice",
                                "sense_voice": "./models/sherpa/model.onnx",
                                "tokens": "./models/sherpa/tokens.txt",
                                "sample_rate": 16000,
                                "provider": "cpu",
                            },
                        }
                    }
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )

        response = snapshot_debug_config(config_path)

        sherpa = response["asr"]["sherpa_onnx_asr"]
        self.assertTrue(sherpa["ready"])
        self.assertEqual(sherpa["reason"], "ready")
        self.assertEqual(sherpa["missing_files"], [])

    def test_debug_config_reports_missing_sherpa_model_files(self):
        tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(tmp_dir.cleanup)
        root = Path(tmp_dir.name)
        config_path = root / "conf.yaml"
        config_path.write_text(
            yaml.safe_dump(
                {
                    "character_config": {
                        "asr_config": {
                            "asr_model": "sherpa_onnx_asr",
                            "sherpa_onnx_asr": {
                                "model_type": "sense_voice",
                                "sense_voice": "./models/sherpa/model.onnx",
                                "tokens": "./models/sherpa/tokens.txt",
                            },
                        }
                    }
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )

        response = snapshot_debug_config(config_path)

        sherpa = response["asr"]["sherpa_onnx_asr"]
        self.assertFalse(sherpa["ready"])
        self.assertEqual(sherpa["reason"], "sherpa_onnx model files are missing")
        self.assertEqual(
            {item["field"] for item in sherpa["missing_files"]},
            {"sense_voice", "tokens"},
        )

    def test_debug_config_patch_updates_demo_subset(self):
        client, config_path = self.make_client()

        response = client.patch(
            "/rikka/debug/config",
            json={
                "llm": {
                    "base_url": "http://127.0.0.1:9000/v1",
                    "model": "local-test",
                    "api_mode": "responses",
                    "api_key": "new-secret",
                },
                "tts": {
                    "provider": "indextts2_tts",
                    "indextts2_tts": {
                        "mode": "cloud",
                        "api_key": "new-modelverse-secret",
                        "base_url": "https://api.modelverse.cn/v1",
                        "model": "IndexTeam/IndexTTS-2",
                        "voice_id": "uspeech:new-demo",
                        "default_tts_style": "quiet_companion",
                        "quiet_companion_emo_alpha": 0.92,
                        "quiet_companion_emo_vec": [
                            0.12,
                            0,
                            0.04,
                            0,
                            0,
                            0.18,
                            0.03,
                            0.08,
                        ],
                        "api_url": "http://127.0.0.1:7861/tts",
                        "emo_audio_path": "private/voice/rikka_emo_cute.wav",
                        "emo_alpha": 0.9,
                        "use_emo_text": True,
                        "emo_text": "更可爱一点，但保持自然。",
                        "use_random": False,
                        "timeout_seconds": 240,
                        "sentence_split_enabled": True,
                        "sentence_split_method": "regex",
                        "max_text_tokens_per_segment": 48,
                        "sentence_interval_ms": 350,
                    },
                },
                "asr": {
                    "provider": "none",
                },
                "live": {
                    "bilibili_live": {
                        "room_ids": [21013446, 0, 21013446, 67890],
                        "sessdata": "new-sess-secret",
                    },
                },
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()["config"]
        self.assertTrue(payload["restart_required"])
        self.assertEqual(payload["llm"]["model"], "local-test")
        self.assertEqual(payload["tts"]["provider"], "indextts2_tts")
        data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        llm = data["character_config"]["agent_config"]["llm_configs"][
            "openai_compatible_llm"
        ]
        self.assertEqual(llm["llm_api_key"], "new-secret")
        self.assertEqual(llm["api_mode"], "responses")
        self.assertEqual(
            data["character_config"]["tts_config"]["tts_model"],
            "indextts2_tts",
        )
        indextts2 = data["character_config"]["tts_config"]["indextts2_tts"]
        self.assertEqual(indextts2["mode"], "cloud")
        self.assertEqual(indextts2["api_key"], "new-modelverse-secret")
        self.assertEqual(indextts2["model"], "IndexTeam/IndexTTS-2")
        self.assertEqual(indextts2["voice_id"], "uspeech:new-demo")
        self.assertEqual(indextts2["default_tts_style"], "quiet_companion")
        self.assertEqual(indextts2["quiet_companion_emo_alpha"], 0.92)
        self.assertEqual(
            indextts2["quiet_companion_emo_vec"],
            [0.12, 0, 0.04, 0, 0, 0.18, 0.03, 0.08],
        )
        self.assertEqual(indextts2["emo_audio_path"], "private/voice/rikka_emo_cute.wav")
        self.assertEqual(indextts2["emo_alpha"], 0.9)
        self.assertTrue(indextts2["use_emo_text"])
        self.assertEqual(indextts2["emo_text"], "更可爱一点，但保持自然。")
        self.assertFalse(indextts2["use_random"])
        self.assertTrue(indextts2["sentence_split_enabled"])
        self.assertEqual(indextts2["sentence_split_method"], "regex")
        self.assertEqual(indextts2["max_text_tokens_per_segment"], 48)
        self.assertEqual(indextts2["sentence_interval_ms"], 350)
        self.assertEqual(data["character_config"]["asr_config"]["asr_model"], "none")
        self.assertEqual(
            data["live_config"]["bilibili_live"]["room_ids"],
            [21013446, 67890],
        )
        self.assertEqual(
            data["live_config"]["bilibili_live"]["sessdata"],
            "new-sess-secret",
        )

    def test_debug_config_patch_allows_only_sherpa_onnx_asr_for_asr(self):
        client, config_path = self.make_client()

        response = client.patch(
            "/rikka/debug/config",
            json={"asr": {"provider": "sherpa_onnx_asr"}},
        )

        self.assertEqual(response.status_code, 200)
        data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        self.assertEqual(
            data["character_config"]["asr_config"]["asr_model"],
            "sherpa_onnx_asr",
        )

    def test_debug_config_patch_rejects_invalid_asr_provider_alias(self):
        client, config_path = self.make_client()

        response = client.patch(
            "/rikka/debug/config",
            json={"asr": {"provider": "voice_magic"}},
        )

        self.assertEqual(response.status_code, 422)
        data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        self.assertEqual(data["character_config"]["asr_config"]["asr_model"], "none")

    def test_debug_config_patch_rejects_invalid_llm_provider_alias(self):
        client, config_path = self.make_client()

        response = client.patch(
            "/rikka/debug/config",
            json={"llm": {"provider": "mimo"}},
        )

        self.assertEqual(response.status_code, 422)
        data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        provider = data["character_config"]["agent_config"]["agent_settings"][
            "basic_memory_agent"
        ]["llm_provider"]
        self.assertEqual(provider, "openai_compatible_llm")

    def test_debug_config_patch_rejects_invalid_emotion_vector(self):
        client, _ = self.make_client()

        response = client.patch(
            "/rikka/debug/config",
            json={
                "tts": {
                    "indextts2_tts": {
                        "quiet_companion_emo_vec": [1, 1, 1, 1, 1, 1, 1, 1],
                    },
                },
            },
        )

        self.assertEqual(response.status_code, 422)

    def test_runtime_tts_patch_updates_loaded_indextts2_provider(self):
        tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(tmp_dir.cleanup)
        root = Path(tmp_dir.name)
        config_path = root / "conf.yaml"
        log_dir = root / "logs"
        log_dir.mkdir()
        write_demo_config(config_path)

        runtime_config = SimpleNamespace(
            mode="local",
            api_key="",
            base_url="https://api.modelverse.cn/v1",
            model="IndexTeam/IndexTTS-2",
            voice_id="",
            default_tts_style="default",
            quiet_companion_emo_alpha=1.0,
            quiet_companion_emo_vec=[0.10, 0, 0, 0, 0, 0.20, 0, 0.10],
            api_url="http://127.0.0.1:7861/tts",
            speaker_audio_path="private/voice/rikka_voice_clone.wav",
            emo_audio_path="private/voice/rikka_emo_cute.wav",
            emo_alpha=0.6,
            use_emo_text=False,
            emo_text="",
            use_random=False,
            audio_format="wav",
            timeout_seconds=180.0,
            sentence_split_enabled=False,
            sentence_split_method="regex",
            max_text_tokens_per_segment=80,
            sentence_interval_ms=0,
        )
        runtime_engine = SimpleNamespace(
            mode=runtime_config.mode,
            api_key=runtime_config.api_key,
            base_url=runtime_config.base_url,
            model=runtime_config.model,
            voice_id=runtime_config.voice_id,
            default_tts_style=runtime_config.default_tts_style,
            quiet_companion_emo_alpha=runtime_config.quiet_companion_emo_alpha,
            quiet_companion_emo_vec=list(runtime_config.quiet_companion_emo_vec),
            api_url=runtime_config.api_url,
            speaker_audio_path=runtime_config.speaker_audio_path,
            emo_audio_path=runtime_config.emo_audio_path,
            emo_alpha=runtime_config.emo_alpha,
            use_emo_text=runtime_config.use_emo_text,
            emo_text=runtime_config.emo_text,
            use_random=runtime_config.use_random,
            timeout_seconds=runtime_config.timeout_seconds,
            sentence_split_enabled=runtime_config.sentence_split_enabled,
            sentence_split_method=runtime_config.sentence_split_method,
            max_text_tokens_per_segment=runtime_config.max_text_tokens_per_segment,
            sentence_interval_ms=runtime_config.sentence_interval_ms,
        )
        context = SimpleNamespace(
            character_config=SimpleNamespace(
                tts_config=SimpleNamespace(
                    tts_model="indextts2_tts",
                    indextts2_tts=runtime_config,
                ),
                agent_config=None,
            ),
            tts_engine=runtime_engine,
        )
        app = FastAPI()
        app.include_router(
            init_rikka_routes(
                context,
                settings_store=RikkaSettingsStore(root / "settings.json"),
                config_path=config_path,
                log_dir=log_dir,
            )
        )
        client = TestClient(app)

        response = client.patch(
            "/rikka/debug/runtime-tts",
            json={
                "indextts2_tts": {
                    "emo_alpha": 1.5,
                    "use_emo_text": True,
                    "emo_text": "更夹一点，但保持自然。",
                    "quiet_companion_emo_alpha": 0.85,
                    "quiet_companion_emo_vec": [
                        0.11,
                        0,
                        0.03,
                        0,
                        0,
                        0.19,
                        0.02,
                        0.09,
                    ],
                    "use_random": False,
                    "timeout_seconds": 0,
                    "sentence_split_enabled": True,
                    "sentence_split_method": "pysbd",
                    "max_text_tokens_per_segment": 4,
                    "sentence_interval_ms": 3600,
                }
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertFalse(payload["restart_required"])
        self.assertEqual(payload["applied"]["emo_alpha"], 1.0)
        self.assertEqual(payload["applied"]["quiet_companion_emo_alpha"], 0.85)
        self.assertEqual(
            payload["applied"]["quiet_companion_emo_vec"],
            [0.11, 0, 0.03, 0, 0, 0.19, 0.02, 0.09],
        )
        self.assertEqual(payload["applied"]["timeout_seconds"], 1.0)
        self.assertTrue(payload["applied"]["sentence_split_enabled"])
        self.assertEqual(payload["applied"]["sentence_split_method"], "pysbd")
        self.assertEqual(payload["applied"]["max_text_tokens_per_segment"], 10)
        self.assertEqual(payload["applied"]["sentence_interval_ms"], 3000)
        self.assertEqual(runtime_config.emo_alpha, 1.0)
        self.assertTrue(runtime_config.use_emo_text)
        self.assertEqual(runtime_config.emo_text, "更夹一点，但保持自然。")
        self.assertEqual(runtime_config.quiet_companion_emo_alpha, 0.85)
        self.assertEqual(
            runtime_config.quiet_companion_emo_vec,
            [0.11, 0, 0.03, 0, 0, 0.19, 0.02, 0.09],
        )
        self.assertEqual(runtime_engine.emo_alpha, 1.0)
        self.assertEqual(runtime_engine.quiet_companion_emo_alpha, 0.85)
        self.assertEqual(runtime_engine.timeout_seconds, 1.0)
        self.assertTrue(runtime_engine.sentence_split_enabled)
        self.assertEqual(runtime_engine.sentence_split_method, "pysbd")
        self.assertEqual(runtime_engine.max_text_tokens_per_segment, 10)
        self.assertEqual(runtime_engine.sentence_interval_ms, 3000)
        self.assertEqual(payload["providers"]["tts"]["emo_alpha"], 1.0)

    def test_flow_and_frontend_action_routes_report_pipeline_state(self):
        client, _ = self.make_client()

        planned = client.post(
            "/rikka/debug/event",
            json={
                "type": "chat.message",
                "source": "debug",
                "text": "六花，调试流程图测试。",
            },
        )

        self.assertEqual(planned.status_code, 200)
        flow_id = planned.json()["flow"]["id"]
        flow = client.get("/rikka/debug/flow")
        self.assertEqual(flow.status_code, 200)
        snapshot = flow.json()
        self.assertIn("diagnostics", snapshot)
        self.assertEqual(snapshot["diagnostics"]["blocker"], "bilibili_idle")
        self.assertEqual(snapshot["diagnostics"]["bilibili"]["state"], "idle")
        self.assertEqual(snapshot["diagnostics"]["live2d"]["connected_clients"], 0)
        self.assertEqual(snapshot["active"]["id"], flow_id)
        self.assertEqual(snapshot["active"]["stages"]["normalize"]["status"], "ok")
        self.assertEqual(snapshot["active"]["stages"]["planner"]["status"], "ok")
        self.assertEqual(snapshot["active"]["stages"]["validate"]["status"], "ok")
        self.assertIsInstance(snapshot["active"]["stages"]["planner"]["duration_ms"], int)
        self.assertIsInstance(snapshot["active"]["stages"]["planner"]["elapsed_ms"], int)
        self.assertIsInstance(snapshot["active"]["timeline"][-1]["duration_ms"], int)
        self.assertIsInstance(snapshot["active"]["timeline"][-1]["elapsed_ms"], int)

        action = client.post(
            "/rikka/debug/frontend-action",
            json={
                "flow_id": flow_id,
                "kind": "motion",
                "status": "ok",
                "detail": "motion applied",
                "metadata": {"group": "TapBody", "index": 0},
            },
        )

        self.assertEqual(action.status_code, 200)
        updated = client.get("/rikka/debug/flow").json()
        self.assertEqual(updated["frontend_actions"][0]["kind"], "motion")
        self.assertEqual(updated["active"]["stages"]["actions"]["status"], "ok")
        self.assertEqual(updated["active"]["stages"]["live2d"]["status"], "ok")

    def test_recent_events_include_flow_started_events_once(self):
        client, _ = self.make_client()

        planned = client.post(
            "/rikka/debug/event",
            json={
                "type": "chat.message",
                "source": "debug",
                "text": "六花，Recent Events 测试。",
            },
        )

        self.assertEqual(planned.status_code, 200)
        flow_id = planned.json()["flow"]["id"]
        events = client.get("/rikka/events").json()["events"]
        matching = [event for event in events if event["id"] == flow_id]

        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0]["type"], "chat.message")
        self.assertEqual(matching[0]["source"], "debug")
        self.assertEqual(matching[0]["text"], "六花，Recent Events 测试。")
        self.assertFalse(matching[0]["privacy"]["contains_raw_media"])

    def test_flow_console_renders_stage_durations(self):
        render_js = (APP_ROOT / "web_tool/rikka/render.js").read_text(
            encoding="utf-8"
        )

        self.assertIn("function formatDurationMs", render_js)
        self.assertIn("function displayDurationMs", render_js)
        self.assertIn("function validationDiagnosticsFromFlow", render_js)
        self.assertIn("function renderValidationDiagnostics", render_js)
        self.assertIn("raw_response_excerpt", render_js)
        self.assertIn("raw_response_text", render_js)
        self.assertIn("repair_notes", render_js)
        self.assertIn("fallback_spoken_preview", render_js)
        self.assertIn("attached_image_count", render_js)
        self.assertIn("validation-diagnostics", render_js)
        self.assertIn("diagnosticRow", render_js)
        self.assertIn("diagnostic-value", render_js)
        self.assertNotIn("kvList(list, rows)", render_js)
        self.assertIn('item?.status === "running"', render_js)
        self.assertIn("Date.now() - Number(item.at_ms)", render_js)
        self.assertIn("displayDurationMs(stage)", render_js)
        self.assertIn("displayDurationMs(entry)", render_js)
        self.assertIn("item?.duration_ms", render_js)
        self.assertIn("耗时", render_js)

    def test_recent_events_render_groups_by_flow_id(self):
        render_js = (APP_ROOT / "web_tool/rikka/render.js").read_text(
            encoding="utf-8"
        )
        styles = (APP_ROOT / "web_tool/rikka/styles/components.css").read_text(
            encoding="utf-8"
        )

        self.assertIn("function groupRecentEvents", render_js)
        self.assertIn("eventFlowId(event)", render_js)
        self.assertIn("payload?.flow_id", render_js)
        self.assertIn("group.items.length > 1 ? \"details\" : \"div\"", render_js)
        self.assertIn("groupPrimaryEvent(group)", render_js)
        self.assertIn("replay.dataset.eventIndex = String(primary.index)", render_js)
        self.assertIn("state.expandedEventGroups.has(group.key)", render_js)
        self.assertIn("state.expandedEventGroups.add(group.key)", render_js)
        self.assertIn(".validation-diagnostics", styles)
        self.assertIn("grid-column: 1 / -1", styles)
        self.assertIn(".diagnostic-row.long .diagnostic-value", styles)
        self.assertIn("white-space: pre-wrap", styles)
        self.assertIn(".event-group-items", styles)
        self.assertIn(".event-child", styles)

    def test_frontend_actions_without_flow_id_attach_to_latest_flow(self):
        from open_llm_vtuber.rikka.flow import RikkaFlowMonitor

        flow = RikkaFlowMonitor()
        flow.start(
            "conv-latest",
            {
                "id": "conv-latest",
                "source": "proactive",
                "type": "proactive.idle_speech",
                "text": "idle",
            },
        )

        action = flow.record_frontend_action(
            {
                "kind": "audio",
                "status": "ok",
                "detail": "audio playback started",
                "metadata": {},
            }
        )

        self.assertEqual(action["flow_id"], "conv-latest")
        self.assertTrue(action["metadata"]["inferred_flow_id"])
        self.assertEqual(flow.snapshot()["frontend_actions"][0]["flow_id"], "conv-latest")

    def test_flow_error_status_survives_later_complete_stage(self):
        from open_llm_vtuber.rikka.flow import RikkaFlowMonitor

        flow = RikkaFlowMonitor()
        flow.start(
            "conv-error",
            {
                "id": "conv-error",
                "source": "proactive",
                "type": "proactive.screen_comment",
                "text": "screen",
            },
        )

        flow.record("conv-error", "planner", "error", detail="provider 502")
        flow.record("conv-error", "tts", "ok", detail="fallback synthesized")
        flow.record("conv-error", "complete", "ok", detail="fallback completed")

        snapshot = flow.snapshot()
        self.assertEqual(snapshot["active"]["status"], "error")
        self.assertEqual(snapshot["active"]["current_stage"], "planner")
        self.assertEqual(snapshot["active"]["stages"]["planner"]["status"], "error")
        self.assertEqual(snapshot["active"]["stages"]["complete"]["status"], "ok")

    def test_flow_metadata_keeps_redacted_raw_response_text_for_diagnostics(self):
        from open_llm_vtuber.rikka.flow import RikkaFlowMonitor

        flow = RikkaFlowMonitor()
        flow.start(
            "conv-raw-response",
            {
                "id": "conv-raw-response",
                "source": "debug",
                "type": "host.note",
                "text": "debug",
            },
        )
        raw_response_text = '{"spoken_text":"' + ("回响" * 400) + '"}'

        flow.record(
            "conv-raw-response",
            "validate",
            "ok",
            metadata={
                "raw_response_text": raw_response_text,
                "raw_response_hash": "abc",
                "other_text": "x" * 500,
            },
        )

        metadata = flow.snapshot()["active"]["stages"]["validate"]["metadata"]
        self.assertIn("回响" * 120, metadata["raw_response_text"])
        self.assertLessEqual(len(metadata["other_text"]), 242)
        self.assertTrue(metadata["other_text"].endswith("..."))

    def test_llm_provider_error_is_visible_in_flow_and_errors(self):
        tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(tmp_dir.cleanup)
        root = Path(tmp_dir.name)
        log_dir = root / "logs"
        log_dir.mkdir()
        context = SimpleNamespace(
            agent_engine=SimpleNamespace(_llm=ErrorTextAsyncLLM()),
            character_config=None,
            system_prompt="system",
        )
        app = FastAPI()
        app.include_router(
            init_rikka_routes(
                context,
                settings_store=RikkaSettingsStore(root / "settings.json"),
                config_path=root / "conf.yaml",
                log_dir=log_dir,
            )
        )
        client = TestClient(app)

        planned = client.post(
            "/rikka/debug/event",
            json={
                "type": "chat.message",
                "source": "debug",
                "text": "六花，LLM 报错测试。",
            },
        )

        self.assertEqual(planned.status_code, 200)
        payload = planned.json()
        self.assertFalse(payload["validation"]["ok"])
        self.assertEqual(payload["planner"]["last_error_kind"], "provider_error")
        self.assertIn("Rate limit exceeded", payload["planner"]["last_error"])

        flow = client.get("/rikka/debug/flow").json()
        self.assertEqual(flow["active"]["stages"]["planner"]["status"], "error")
        self.assertIn(
            "Rate limit exceeded",
            flow["active"]["stages"]["planner"]["detail"],
        )

        errors = client.get("/rikka/debug/errors").json()
        provider_errors = errors["provider_errors"]
        self.assertEqual(provider_errors[0]["source"], "planner")
        self.assertIn("Rate limit exceeded", provider_errors[0]["message"])

    def test_debug_logs_and_errors_return_tails(self):
        client, _ = self.make_client()

        logs = client.get("/rikka/debug/logs?max_files=1&max_lines=2")
        errors = client.get("/rikka/debug/errors")

        self.assertEqual(logs.status_code, 200)
        self.assertEqual(len(logs.json()["files"]), 1)
        self.assertEqual(logs.json()["files"][0]["lines"], ["ERROR planner failed cleanly", "Traceback demo"])
        self.assertEqual(errors.status_code, 200)
        messages = [item["message"] for item in errors.json()["errors"]]
        self.assertIn("ERROR planner failed cleanly", messages)
        self.assertIn("Traceback demo", messages)

    def test_log_and_error_snapshots_redact_secrets_and_provider_payloads(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            log_dir = Path(tmp_dir)
            (log_dir / "debug.log").write_text(
                "\n".join(
                    [
                        "INFO api_key='mimo-secret-demo' sessdata=secret-cookie",
                        "ERROR llm_api_key='sk-secret-demo-1234567890' failed",
                        "DEBUG voice_audio_base64='"
                        + ("a" * 240)
                        + "' data:audio/wav;base64,"
                        + ("b" * 240),
                        "DEBUG data:image/png;base64,"
                        + ("c" * 240),
                        "DEBUG raw_blob="
                        + ("d" * 180),
                        "DEBUG Messages: "
                        + ("prompt body with private persona " * 90),
                    ]
                ),
                encoding="utf-8",
            )

            logs = log_snapshot(log_dir, max_files=1, max_lines=10)
            errors = error_snapshot(log_dir, max_errors=10)
            rendered = str(logs) + str(errors)

            self.assertNotIn("mimo-secret-demo", rendered)
            self.assertNotIn("secret-cookie", rendered)
            self.assertNotIn("sk-secret-demo", rendered)
            self.assertNotIn("a" * 80, rendered)
            self.assertNotIn("b" * 80, rendered)
            self.assertNotIn("c" * 80, rendered)
            self.assertNotIn("d" * 80, rendered)
            self.assertNotIn("data:image", rendered)
            self.assertNotIn("private persona", rendered)
            self.assertIn("[redacted", rendered)

    def test_shared_log_redaction_handles_provider_payload_before_file_write(self):
        rendered = redact_debug_text(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": "data:image/png;base64," + ("x" * 240),
                    }
                ],
                "llm_api_key": "sk-secret-demo-1234567890",
                "headers": {"Authorization": "Bearer secret-token-value"},
                "voice_audio_base64": "a" * 240,
            }
        )

        self.assertNotIn("sk-secret-demo", rendered)
        self.assertNotIn("secret-token-value", rendered)
        self.assertNotIn("data:image", rendered)
        self.assertNotIn("x" * 80, rendered)
        self.assertNotIn("a" * 80, rendered)
        self.assertIn("[redacted", rendered)

    def test_error_snapshot_ignores_debug_errors_route_access_log(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            log_dir = Path(tmp_dir)
            (log_dir / "server.out").write_text(
                "\n".join(
                    [
                        'INFO: 127.0.0.1 - "GET /rikka/debug/errors HTTP/1.1" 200 OK',
                        "ERROR planner failed cleanly",
                    ]
                ),
                encoding="utf-8",
            )

            errors = error_snapshot(log_dir, max_errors=10)["errors"]
            messages = [item["message"] for item in errors]

            self.assertEqual(messages, ["ERROR planner failed cleanly"])


if __name__ == "__main__":
    unittest.main()

import unittest

import numpy as np

from open_llm_vtuber.asr.asr_factory import ASRFactory
from open_llm_vtuber.asr.null_asr import ASRDisabledError
from open_llm_vtuber.config_manager.asr import ASRConfig
from open_llm_vtuber.config_manager import read_yaml, validate_config


class ASRDisabledTests(unittest.TestCase):
    def test_asr_config_accepts_null_model(self):
        config = ASRConfig.model_validate({"asr_model": None})

        self.assertIsNone(config.asr_model)

    def test_asr_config_accepts_none_sentinel(self):
        config = ASRConfig.model_validate({"asr_model": "none"})

        self.assertEqual(config.asr_model, "none")

    def test_factory_returns_disabled_asr_for_null(self):
        engine = ASRFactory.get_asr_system(None)

        self.assertTrue(getattr(engine, "is_disabled", False))
        with self.assertRaises(ASRDisabledError):
            engine.transcribe_np(np.zeros(16000, dtype=np.float32))

    def test_default_templates_use_rikka_and_do_not_require_asr(self):
        for path in (
            "config_templates/conf.default.yaml",
            "config_templates/conf.ZH.default.yaml",
        ):
            with self.subTest(path=path):
                config = validate_config(read_yaml(path))

                self.assertEqual(config.character_config.conf_name, "rikka_live")
                self.assertEqual(
                    config.character_config.persona_prompt,
                    "$rikka_persona",
                )
                self.assertEqual(
                    config.character_config.agent_config.agent_settings.basic_memory_agent.llm_provider,
                    "openai_compatible_llm",
                )
                self.assertIsNone(config.character_config.asr_config.asr_model)


if __name__ == "__main__":
    unittest.main()

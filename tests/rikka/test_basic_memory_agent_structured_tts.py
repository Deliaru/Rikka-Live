import unittest
from types import SimpleNamespace

from open_llm_vtuber.agent.agents.basic_memory_agent import BasicMemoryAgent
from open_llm_vtuber.agent.input_types import BatchInput, TextData, TextSource
from open_llm_vtuber.agent.output_types import SentenceOutput
from open_llm_vtuber.config_manager import TTSPreprocessorConfig, TranslatorConfig


class FakeLLM:
    def __init__(self, chunks):
        self.chunks = chunks

    async def chat_completion(self, _messages, _system, tools=None):
        for chunk in self.chunks:
            yield chunk


class BasicMemoryAgentStructuredTtsTests(unittest.IsolatedAsyncioTestCase):
    async def test_rikka_json_response_sends_only_spoken_text_to_tts(self):
        agent = BasicMemoryAgent(
            llm=FakeLLM(
                [
                    '{"spoken_text":"听得到哦。",',
                    '"subtitle_text":"嗯，听得到哦。",',
                    '"emotion":"soft_smile","motion":"nod","gaze":"camera",',
                    '"priority":"normal","interruptible":true,',
                    '"reason_code":"reply_chat"}',
                ]
            ),
            system=(
                "Return JSON with spoken_text, subtitle_text, emotion, motion, "
                "gaze, priority, interruptible, reason_code."
            ),
            live2d_model=SimpleNamespace(
                extract_emotion=lambda _text: [],
                model_info={
                    "motionMap": {
                        "nod": {
                            "enabled": True,
                            "group": "TapBody",
                            "index": 0,
                        }
                    },
                    "gazeMap": {
                        "camera": {
                            "enabled": True,
                            "parameters": {"ParamAngleX": 0.0},
                        }
                    },
                },
            ),
            tts_preprocessor_config=TTSPreprocessorConfig(
                remove_special_char=True,
                translator_config=TranslatorConfig(
                    translate_audio=False,
                    translate_provider="deeplx",
                ),
            ),
        )

        outputs = [
            item
            async for item in agent.chat(
                BatchInput(
                    texts=[
                        TextData(
                            source=TextSource.INPUT,
                            content="六花，能听到吗",
                        )
                    ]
                )
            )
        ]

        self.assertEqual(len(outputs), 1)
        self.assertIsInstance(outputs[0], SentenceOutput)
        self.assertEqual(outputs[0].display_text.text, "听得到哦。")
        self.assertEqual(outputs[0].tts_text, "听得到哦。")
        self.assertEqual(outputs[0].actions.motions[0]["name"], "nod")
        self.assertEqual(outputs[0].actions.gaze["name"], "camera")
        self.assertNotIn("subtitle_text", outputs[0].tts_text)
        self.assertNotIn("spoken_text", outputs[0].tts_text)


if __name__ == "__main__":
    unittest.main()

import tempfile
import sys
from importlib.machinery import ModuleSpec
from types import ModuleType
import unittest
from pathlib import Path

for module_name in ("sherpa_onnx", "onnxruntime"):
    module = sys.modules.setdefault(module_name, ModuleType(module_name))
    if module.__spec__ is None:
        module.__spec__ = ModuleSpec(module_name, loader=None)

def sherpa_asr_class():
    from open_llm_vtuber.asr.sherpa_onnx_asr import VoiceRecognition

    return VoiceRecognition


def null_asr_class():
    from open_llm_vtuber.asr.null_asr import VoiceRecognition

    return VoiceRecognition


class StreamingASRStatusTests(unittest.TestCase):
    def test_null_asr_reports_disabled_streaming_status(self):
        NullASR = null_asr_class()
        self.assertEqual(NullASR().streaming_status(), "asr_disabled")

    def test_sherpa_reports_missing_streaming_config(self):
        SherpaOnnxASR = sherpa_asr_class()
        asr = SherpaOnnxASR.__new__(SherpaOnnxASR)
        asr.streaming = None

        self.assertEqual(asr.streaming_status(), "streaming_config_missing")

    def test_sherpa_reports_streaming_ready_when_required_files_exist(self):
        SherpaOnnxASR = sherpa_asr_class()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = {}
            for name in ("encoder", "decoder", "joiner", "tokens"):
                path = root / f"{name}.onnx"
                path.write_text("placeholder", encoding="utf-8")
                paths[name] = str(path)
            asr = SherpaOnnxASR.__new__(SherpaOnnxASR)
            asr.streaming = {"model_type": "transducer", **paths}

            self.assertEqual(asr.streaming_status(), "streaming_ready")


if __name__ == "__main__":
    unittest.main()

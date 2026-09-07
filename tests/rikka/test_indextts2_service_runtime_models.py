import importlib.util
import tempfile
import unittest
from pathlib import Path


def load_service_module():
    script_path = Path("scripts/run_indextts2_service.py").resolve()
    spec = importlib.util.spec_from_file_location(
        "run_indextts2_service_for_tests", script_path
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class IndexTTS2ServiceRuntimeModelTests(unittest.TestCase):
    def test_missing_runtime_models_reports_all_manual_files(self):
        service = load_service_module()

        with tempfile.TemporaryDirectory() as tmpdir:
            manual_root = Path(tmpdir)
            missing = service.missing_runtime_model_files(manual_root)
            message = service.runtime_model_download_message(manual_root, missing)

        expected = {
            "facebook/w2v-bert-2.0/config.json",
            "facebook/w2v-bert-2.0/preprocessor_config.json",
            "facebook/w2v-bert-2.0/model.safetensors",
            "amphion/MaskGCT/semantic_codec/model.safetensors",
            "funasr/campplus/campplus_cn_common.bin",
            "nvidia/bigvgan_v2_22khz_80band_256x/config.json",
            "nvidia/bigvgan_v2_22khz_80band_256x/bigvgan_generator.pt",
        }

        self.assertEqual(
            {f"{item['repo_id']}/{item['filename']}" for item in missing},
            expected,
        )
        self.assertIn("Runtime downloads are disabled by default", message)
        self.assertIn(
            "https://huggingface.co/facebook/w2v-bert-2.0/resolve/main/model.safetensors",
            message,
        )

    def test_manual_runtime_file_path_preserves_repo_and_subdirs(self):
        service = load_service_module()
        path = service.manual_runtime_file_path(
            Path("manual_hf"),
            "amphion/MaskGCT",
            "semantic_codec/model.safetensors",
        )

        self.assertEqual(
            path,
            Path("manual_hf/amphion/MaskGCT/semantic_codec/model.safetensors"),
        )


if __name__ == "__main__":
    unittest.main()

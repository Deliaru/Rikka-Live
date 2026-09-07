import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import get_args

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from open_llm_vtuber.rikka.schemas import RikkaEmotion
from prepare_live2d_model import prepare_model


class Live2DPreparationTests(unittest.TestCase):
    def test_model_dict_registers_local_rikka_model(self):
        model_dict = json.loads(Path("model_dict.json").read_text(encoding="utf-8"))
        entry = next(
            (model for model in model_dict if model["name"] == "rikka_mikazuki"),
            None,
        )

        self.assertIsNotNone(entry)
        self.assertEqual(
            entry["url"],
            "/live2d-models/rikka_mikazuki/rikka_mikazuki.model3.json",
        )
        self.assertEqual(entry["idleMotionGroupName"], "Idle")
        for emotion in get_args(RikkaEmotion):
            self.assertIn(emotion, entry["expressionPresets"])
        for preset in entry["expressionPresets"].values():
            self.assertIn("label", preset)
            self.assertIsInstance(preset["parameters"], dict)
            self.assertIn("fade_ms", preset)
        for motion in (
            "nod",
            "tilt_head",
            "look_close",
            "look_away",
            "small_wave",
            "thinking",
        ):
            self.assertIn(motion, entry["gestureMap"])
            self.assertIn("kind", entry["gestureMap"][motion])
            self.assertIn("cooldown_ms", entry["gestureMap"][motion])
        self.assertEqual(entry["identityParams"], {"Param84": 1.0})
        self.assertEqual(entry["speakingSmile"], {"gain": 0.02, "max": 0.25})
        self.assertTrue(entry["idleMicro"]["enabled"])
        self.assertNotIn("emotionMap", entry)
        self.assertNotIn("motionMap", entry)
        self.assertIn("camera", entry["gazeMap"])
        self.assertIn("chat", entry["gazeMap"])

    def test_prepare_model_patches_manifest_for_runtime(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            source.mkdir()
            (source / "runtime.2048").mkdir()
            (source / "animations").mkdir()
            (source / "runtime.2048" / "texture_00.png").write_bytes(b"png")
            (source / "avatar.moc3").write_bytes(b"moc")
            (source / "avatar.physics3.json").write_text("{}", encoding="utf-8")
            (source / "avatar.cdi3.json").write_text(
                json.dumps(
                    {
                        "Parameters": [
                            {"Id": "ParamEyeLOpen"},
                            {"Id": "ParamEyeROpen"},
                            {"Id": "ParamMouthOpenY"},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (source / "happy.exp3.json").write_text(
                json.dumps({"Type": "Live2D Expression", "Parameters": []}),
                encoding="utf-8",
            )
            (source / "animations" / "00_idle.motion3.json").write_text(
                json.dumps({"Version": 3}),
                encoding="utf-8",
            )
            (source / "wave.motion3.json").write_text(
                json.dumps({"Version": 3}),
                encoding="utf-8",
            )
            (source / "avatar.model3.json").write_text(
                json.dumps(
                    {
                        "Version": 3,
                        "FileReferences": {
                            "Moc": "avatar.moc3",
                            "Textures": ["runtime.2048/texture_00.png"],
                            "Physics": "avatar.physics3.json",
                            "DisplayInfo": "avatar.cdi3.json",
                        },
                    }
                ),
                encoding="utf-8",
            )

            manifest_path = prepare_model(
                source,
                root / "models",
                "rikka_test",
                overwrite=False,
            )
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

            self.assertEqual(manifest_path.name, "rikka_test.model3.json")
            self.assertEqual(
                manifest["FileReferences"]["Expressions"][0]["File"],
                "happy.exp3.json",
            )
            self.assertEqual(
                manifest["FileReferences"]["Motions"]["Idle"][0]["File"],
                "animations/00_idle.motion3.json",
            )
            self.assertEqual(
                manifest["Groups"][1]["Ids"],
                ["ParamMouthOpenY"],
            )
            self.assertEqual(manifest["HitAreas"][0]["Id"], "HitAreaHead")


if __name__ == "__main__":
    unittest.main()

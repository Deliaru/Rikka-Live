import os
import tempfile
import unittest
from pathlib import Path

from open_llm_vtuber.server import WebSocketServer


class ServerCacheCleanupTests(unittest.TestCase):
    def test_clean_cache_preserves_rikka_persistent_state(self):
        original_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmp_dir:
            try:
                os.chdir(tmp_dir)

                cache = Path("cache")
                cache.mkdir()
                (cache / "rikka_memory.json").write_text("memory", encoding="utf-8")
                (cache / "rikka_settings.json").write_text("settings", encoding="utf-8")
                (cache / "tts.wav").write_text("audio", encoding="utf-8")
                (cache / "frames").mkdir()
                (cache / "frames" / "frame.jpg").write_text("image", encoding="utf-8")

                WebSocketServer.clean_cache()

                self.assertTrue((cache / "rikka_memory.json").is_file())
                self.assertTrue((cache / "rikka_settings.json").is_file())
                self.assertFalse((cache / "tts.wav").exists())
                self.assertFalse((cache / "frames").exists())
            finally:
                os.chdir(original_cwd)


if __name__ == "__main__":
    unittest.main()

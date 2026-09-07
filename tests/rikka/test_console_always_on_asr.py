import unittest
from pathlib import Path


class ConsoleAlwaysOnASRTests(unittest.TestCase):
    def test_console_has_always_on_owner_control(self):
        html = Path("web_tool/rikka.html").read_text(encoding="utf-8")
        main = Path("web_tool/rikka/main.js").read_text(encoding="utf-8")
        always_on = Path("web_tool/rikka/always_on.js").read_text(encoding="utf-8")

        self.assertIn('id="always-on-listening"', html)
        self.assertIn('id="mic-owner-state"', html)
        self.assertIn("setupAlwaysOnListening", main)
        self.assertIn('"rikkaAlwaysOnListening"', always_on)
        self.assertIn('"client-capabilities"', always_on)
        self.assertIn('"mic-audio-data"', always_on)
        self.assertIn('"mic-audio-end"', always_on)
        self.assertIn('"asr-owner-state"', always_on)
        self.assertIn('"asr-streaming-partial"', always_on)
        self.assertIn("function requestMicOwner", always_on)
        self.assertIn('"mic-owner-request"', always_on)
        self.assertIn('"console_reconnected"', always_on)
        self.assertIn('"mic_already_active"', always_on)
        self.assertIn("chunksDroppedNotOwner", always_on)
        self.assertIn("chunksSent", always_on)


if __name__ == "__main__":
    unittest.main()

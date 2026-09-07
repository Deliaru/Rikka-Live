import base64
import unittest
from io import BytesIO

from PIL import Image

from open_llm_vtuber.rikka.capture import CapturedFrame, WindowInfo
from open_llm_vtuber.rikka.screen_change import ScreenChangeDetector
from open_llm_vtuber.rikka.settings import ProactiveSettings


def frame(color, width=32, height=18):
    image = Image.new("RGB", (width, height), color)
    out = BytesIO()
    image.save(out, format="JPEG")
    return CapturedFrame(
        data_base64=base64.b64encode(out.getvalue()).decode("ascii"),
        mime_type="image/jpeg",
        captured_at_ms=1,
        window=WindowInfo(handle=1, title="test", process_name="test", bounds=(0, 0, width, height)),
        width=width,
        height=height,
    )


class ScreenChangeDetectorTests(unittest.TestCase):
    def test_first_frame_commits_then_same_frame_is_unchanged(self):
        detector = ScreenChangeDetector(clock_ms=lambda: 100)
        settings = ProactiveSettings(screen_change_threshold=0.12)
        first = frame((0, 0, 0))

        result = detector.evaluate(first, settings)
        detector.commit_baseline()
        same = detector.evaluate(first, settings)

        self.assertTrue(result["changed"])
        self.assertFalse(same["changed"])
        self.assertAlmostEqual(same["score"], 0.0, delta=0.01)

    def test_bad_first_frame_still_counts_as_changed_without_baseline(self):
        detector = ScreenChangeDetector(clock_ms=lambda: 100)
        bad = CapturedFrame(
            data_base64="ZmFrZS1mcmFtZQ==",
            mime_type="image/jpeg",
            captured_at_ms=1,
            window=WindowInfo(handle=1, title="test", process_name="test", bounds=(0, 0, 1, 1)),
            width=1,
            height=1,
        )

        first = detector.evaluate(bad, ProactiveSettings())
        detector.commit_baseline()
        second = detector.evaluate(frame((255, 255, 255)), ProactiveSettings())

        self.assertTrue(first["changed"])
        self.assertTrue(second["changed"])

    def test_changed_and_decode_error_after_baseline(self):
        detector = ScreenChangeDetector(clock_ms=lambda: 100)
        settings = ProactiveSettings(screen_change_threshold=0.12)
        detector.evaluate(frame((0, 0, 0)), settings)
        detector.commit_baseline()

        changed = detector.evaluate(frame((255, 255, 255)), settings)
        bad = CapturedFrame(
            data_base64="not-base64",
            mime_type="image/jpeg",
            captured_at_ms=1,
            window=WindowInfo(handle=1, title="test", process_name="test", bounds=(0, 0, 1, 1)),
            width=1,
            height=1,
        )
        failed = detector.evaluate(bad, settings)

        self.assertTrue(changed["changed"])
        self.assertGreater(changed["score"], 0.9)
        self.assertFalse(failed["changed"])
        self.assertEqual(failed["reason"], "decode error")
        self.assertTrue(detector.status()["last_error"])

        recovered = detector.evaluate(frame((255, 255, 255)), settings)

        self.assertTrue(recovered["changed"])
        self.assertEqual(detector.status()["last_error"], "")
        self.assertNotIn("data_base64", detector.status())


if __name__ == "__main__":
    unittest.main()

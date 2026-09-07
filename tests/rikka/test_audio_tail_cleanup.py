"""Unit tests for generated-audio tail cleanup.

Covers the disabled no-op, conservative bounds, the tail-energy trim,
protection band, failure tolerance, and the linear fade envelope.
"""

import os
import tempfile
import unittest

import numpy as np

from open_llm_vtuber.rikka.settings import TtsPostProcessingSettings
from open_llm_vtuber.utils.audio_tail_cleanup import apply_tail_cleanup
from open_llm_vtuber.utils.stream_audio import AudioSegment


SR = 22050


def _sine_segment(
    duration_ms: int, freq: float = 440.0, amp: float = 0.3, sr: int = SR
) -> AudioSegment:
    """Generate a mono 16-bit sine-wave AudioSegment."""
    n = int(sr * duration_ms / 1000)
    t = np.linspace(0, duration_ms / 1000, n, endpoint=False)
    wave = (amp * np.sin(2 * np.pi * freq * t) * 32767).astype(np.int16)
    return AudioSegment(wave.tobytes(), frame_rate=sr, sample_width=2, channels=1)


def _low_noise_segment(
    duration_ms: int, amp: float = 0.005, sr: int = SR
) -> AudioSegment:
    """Low-amplitude high-frequency noise, simulating electrical tail hiss."""
    n = int(sr * duration_ms / 1000)
    rng = np.random.default_rng(42)
    wave = (amp * rng.standard_normal(n) * 32767 * 0.3).astype(np.int16)
    return AudioSegment(wave.tobytes(), frame_rate=sr, sample_width=2, channels=1)


def _write_wav(tmpdir: str, name: str, seg: AudioSegment) -> str:
    path = os.path.join(tmpdir, name)
    seg.export(path, format="wav")
    return path


class ApplyTailCleanupTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmpdir = self._tmp.name

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _base_settings(self, **overrides) -> TtsPostProcessingSettings:
        defaults = {
            "enabled": True,
            "trim_max_ms": 200,
            "trim_rms_threshold_db": -40.0,
            "trim_min_tail_ms": 80,
            "fade_out_ms": 15,
        }
        defaults.update(overrides)
        return TtsPostProcessingSettings(**defaults)

    # ---- disabled path -------------------------------------------------

    def test_disabled_returns_disabled_result_and_leaves_file(self) -> None:
        seg = _sine_segment(500)
        path = _write_wav(self.tmpdir, "disabled.wav", seg)
        original_size = os.path.getsize(path)

        result = apply_tail_cleanup(path, TtsPostProcessingSettings(enabled=False))

        self.assertFalse(result.applied)
        self.assertFalse(result.skipped)
        self.assertFalse(result.failed)
        self.assertEqual(result.reason, "disabled")
        self.assertEqual(os.path.getsize(path), original_size)

    # ---- short audio ---------------------------------------------------

    def test_short_audio_is_skipped(self) -> None:
        # shorter than min_tail_ms + trim_max_ms (80 + 200 = 280)
        seg = _sine_segment(150)
        path = _write_wav(self.tmpdir, "short.wav", seg)
        before = len(AudioSegment.from_file(path))

        result = apply_tail_cleanup(path, self._base_settings())

        self.assertTrue(result.skipped)
        self.assertEqual(result.reason, "audio too short")
        after = len(AudioSegment.from_file(path))
        self.assertEqual(after, before)

    # ---- clean tail (above threshold) ----------------------------------

    def test_clean_tail_above_threshold_is_not_trimmed(self) -> None:
        # Pure sine at amp=0.3 is ~-13 dBFS, well above -40 dBFS threshold.
        seg = _sine_segment(1000)
        path = _write_wav(self.tmpdir, "clean.wav", seg)
        before = len(AudioSegment.from_file(path))

        result = apply_tail_cleanup(path, self._base_settings())

        self.assertTrue(result.skipped)
        self.assertEqual(result.reason, "tail above threshold")
        self.assertEqual(result.trimmed_ms, 0)
        after = len(AudioSegment.from_file(path))
        self.assertEqual(after, before)

    # ---- noisy tail trimmed --------------------------------------------

    def test_noisy_tail_is_trimmed_within_bounds(self) -> None:
        # Sine body + 400 ms of low-amplitude noise tail.
        body = _sine_segment(800)
        tail = _low_noise_segment(400)
        seg = body + tail
        path = _write_wav(self.tmpdir, "noisy.wav", seg)
        before = len(AudioSegment.from_file(path))

        result = apply_tail_cleanup(path, self._base_settings())

        self.assertTrue(result.applied)
        self.assertEqual(result.reason, "trimmed")
        self.assertGreater(result.trimmed_ms, 0)
        # Cannot trim more than trim_max_ms (200).
        self.assertLessEqual(result.trimmed_ms, 200)
        after = len(AudioSegment.from_file(path))
        self.assertEqual(result.before_ms, before)
        self.assertEqual(result.after_ms, after)
        self.assertLess(after, before)
        # Protection band respected: never trim below before - trim_max_ms.
        self.assertGreaterEqual(after, before - 200)

    def test_protection_band_never_trimmed(self) -> None:
        # Even an all-noise tail cannot be trimmed past trim_max_ms.
        tail = _low_noise_segment(1000)
        path = _write_wav(self.tmpdir, "allnoise.wav", tail)
        before = len(AudioSegment.from_file(path))

        result = apply_tail_cleanup(path, self._base_settings())

        self.assertTrue(result.applied or result.skipped)
        # If applied, at most trim_max_ms removed.
        after = len(AudioSegment.from_file(path))
        self.assertGreaterEqual(after, before - 200)

    # ---- failure tolerance --------------------------------------------

    def test_corrupt_file_is_failed_without_raising(self) -> None:
        path = os.path.join(self.tmpdir, "bogus.wav")
        with open(path, "wb") as fh:
            fh.write(b"not a wav file")

        result = apply_tail_cleanup(path, self._base_settings())

        self.assertTrue(result.failed)
        self.assertFalse(result.applied)
        # Should never raise into the caller.

    # ---- fade envelope -------------------------------------------------

    def test_fade_applied_ramps_to_near_zero(self) -> None:
        body = _sine_segment(800)
        tail = _low_noise_segment(300)
        seg = body + tail
        path = _write_wav(self.tmpdir, "fade.wav", seg)

        result = apply_tail_cleanup(
            path,
            self._base_settings(fade_out_ms=30),
        )

        self.assertTrue(result.applied)
        cleaned = AudioSegment.from_file(path)
        arr = np.asarray(cleaned.get_array_of_samples(), dtype=np.float64)
        # Endpoint region (last ~1ms) should be attenuated strongly.
        tail_region = arr[-int(SR * 0.001) :]
        self.assertTrue(np.max(np.abs(tail_region)) < 0.3 * 32767)

    # ---- fade disabled (fade_ms = 0) -----------------------------------

    def test_fade_zero_does_not_crash(self) -> None:
        body = _sine_segment(800)
        tail = _low_noise_segment(300)
        seg = body + tail
        path = _write_wav(self.tmpdir, "nofade.wav", seg)

        result = apply_tail_cleanup(
            path,
            self._base_settings(fade_out_ms=0),
        )

        # Either trimmed (no fade) or skipped; must not fail.
        self.assertFalse(result.failed)
        self.assertGreaterEqual(result.fade_ms, 0)

    # ---- determinism ----------------------------------------------------

    def test_repeated_call_is_deterministic(self) -> None:
        body = _sine_segment(800)
        tail = _low_noise_segment(300)
        seg = body + tail
        path1 = _write_wav(self.tmpdir, "det1.wav", seg)
        path2 = _write_wav(self.tmpdir, "det2.wav", seg)

        r1 = apply_tail_cleanup(path1, self._base_settings())
        r2 = apply_tail_cleanup(path2, self._base_settings())

        self.assertEqual(r1.trimmed_ms, r2.trimmed_ms)
        self.assertEqual(os.path.getsize(path1), os.path.getsize(path2))


if __name__ == "__main__":
    unittest.main()

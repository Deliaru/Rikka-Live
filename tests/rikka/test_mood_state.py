import unittest

from open_llm_vtuber.rikka.mood import MoodState
from open_llm_vtuber.rikka.settings import MoodSettings


class MoodStateTests(unittest.TestCase):
    def test_happy_builds_positive_tts_override(self):
        now = 1000
        state = MoodState(clock_ms=lambda: now)
        settings = MoodSettings()

        state.register_emotion("happy", settings)
        state.register_emotion("happy", settings)
        overrides = state.tts_overrides(settings)

        self.assertIsNotNone(overrides)
        self.assertGreaterEqual(overrides["happy"], 0.10)
        self.assertLessEqual(overrides["happy"], 0.15)
        self.assertNotIn("angry", overrides)

    def test_worried_builds_sad_override(self):
        state = MoodState(clock_ms=lambda: 0)
        settings = MoodSettings()

        state.register_emotion("worried", settings)
        state.register_emotion("worried", settings)
        overrides = state.tts_overrides(settings)

        self.assertIsNotNone(overrides)
        self.assertLessEqual(overrides["sad"], 0.19)

    def test_surprise_decays_quickly(self):
        now = 1000
        state = MoodState(clock_ms=lambda: now)
        settings = MoodSettings()

        state.register_emotion("surprised", settings)
        self.assertIn("surprise", state.tts_overrides(settings))
        now = 5 * 60000 + 1000

        self.assertNotIn("surprise", state.tts_overrides(settings) or {})

    def test_half_life_decay(self):
        now = 0
        state = MoodState(clock_ms=lambda: now, valence=0.8, last_update_ms=1)
        settings = MoodSettings(half_life_minutes=10)
        now = 10 * 60000 + 1

        snapshot = state.snapshot(settings)

        self.assertAlmostEqual(snapshot["valence"], 0.4, delta=0.02)

    def test_unknown_and_neutral_do_not_emit_overrides(self):
        state = MoodState(clock_ms=lambda: 0)
        settings = MoodSettings()

        state.register_emotion("sparkle", settings)

        self.assertIsNone(state.tts_overrides(settings))

    def test_idle_expression_emotion_uses_existing_soft_smile_for_good_mood(self):
        state = MoodState(clock_ms=lambda: 1000)
        settings = MoodSettings()

        state.register_emotion("happy", settings)
        state.register_emotion("happy", settings)

        self.assertEqual(state.idle_expression_emotion(settings), "soft_smile")


if __name__ == "__main__":
    unittest.main()

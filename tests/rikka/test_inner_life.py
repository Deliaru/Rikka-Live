import random
import unittest

from open_llm_vtuber.rikka.inner_life import DEFAULT_ACTIVITY_POOL, InnerLifeState
from open_llm_vtuber.rikka.settings import InnerLifeSettings


class InnerLifeStateTests(unittest.TestCase):
    def test_current_is_stable_within_rotation_window(self):
        random.seed(1)
        now = 0
        state = InnerLifeState(clock_ms=lambda: now)
        settings = InnerLifeSettings(activities=["看屏幕", "哼歌"])

        first = state.current(settings)
        now = 60 * 1000

        self.assertEqual(state.current(settings), first)

    def test_rotates_after_window_and_avoids_same_activity(self):
        random.seed(2)
        now = 0
        state = InnerLifeState(clock_ms=lambda: now)
        settings = InnerLifeSettings(rotation_minutes=5, activities=["看屏幕", "哼歌"])

        first = state.current(settings)
        now = state._next_rotation_ms + 1
        second = state.current(settings)

        self.assertNotEqual(second, first)

    def test_custom_and_default_pool(self):
        state = InnerLifeState(clock_ms=lambda: 0)

        self.assertEqual(state.current(InnerLifeSettings(activities=["看屏幕"])), "看屏幕")
        state.reset()
        self.assertIn(state.current(InnerLifeSettings()), DEFAULT_ACTIVITY_POOL)

    def test_default_pool_avoids_private_address_terms(self):
        joined = "\n".join(DEFAULT_ACTIVITY_POOL)

        self.assertNotIn("主人", joined)
        self.assertNotIn("爸爸", joined)
        self.assertNotIn("父亲", joined)


if __name__ == "__main__":
    unittest.main()

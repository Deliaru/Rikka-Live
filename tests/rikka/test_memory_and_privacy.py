import tempfile
import time
import unittest
from types import SimpleNamespace
from pathlib import Path

from open_llm_vtuber.rikka.memory import MemoryStore
from open_llm_vtuber.rikka.schemas import LiveEvent, MemoryWrite


class FakeSettingsStore:
    def __init__(self, summary_per_kind=5, per_kind_cap=50):
        self.memory = SimpleNamespace(
            summary_per_kind=summary_per_kind,
            per_kind_cap=per_kind_cap,
        )

    def snapshot(self):
        return SimpleNamespace(memory=self.memory)


class RikkaMemoryAndPrivacyTest(unittest.TestCase):
    def test_memory_save_edit_delete(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            store = MemoryStore(Path(tmp_dir) / "memory.json")
            store.upsert(
                MemoryWrite(
                    kind="viewer_note",
                    key="alice",
                    value="喜欢安静的 Minecraft 陪播",
                )
            )
            store.upsert(
                MemoryWrite(
                    kind="viewer_note",
                    key="alice",
                    value="喜欢被轻声问候",
                )
            )

            self.assertIn("alice", store.dump()["viewer_note"])
            self.assertIn("轻声问候", store.summary())
            self.assertTrue(store.delete("viewer_note", "alice"))
            self.assertNotIn("alice", store.dump()["viewer_note"])

    def test_memory_summary_uses_recent_entries_and_capacity(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            store = MemoryStore(
                Path(tmp_dir) / "memory.json",
                settings_store=FakeSettingsStore(summary_per_kind=2, per_kind_cap=3),
            )
            for index in range(4):
                store.upsert(
                    MemoryWrite(
                        kind="preference",
                        key=f"k{index}",
                        value=f"value-{index}",
                    )
                )
                time.sleep(0.002)

            data = store.dump()["preference"]
            self.assertEqual(len(data), 3)
            self.assertNotIn("k0", data)
            summary = store.summary()
            self.assertIn("preference:k3=value-3", summary)
            self.assertIn("preference:k2=value-2", summary)
            self.assertNotIn("preference:k1=value-1", summary)

    def test_memory_deduplicates_normalized_keys(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            store = MemoryStore(Path(tmp_dir) / "memory.json")
            store.upsert(
                MemoryWrite(kind="viewer_note", key="Alice ", value="first")
            )
            store.upsert(
                MemoryWrite(kind="viewer_note", key=" alice", value="second")
            )

            data = store.dump()["viewer_note"]
            self.assertEqual(list(data.keys()), ["alice"])
            self.assertIn("second", store.summary())
            self.assertTrue(store.delete("viewer_note", "ALICE"))

    def test_raw_media_payload_is_redacted(self):
        event = LiveEvent.model_validate(
            {
                "type": "game.roi_changed",
                "source": "screen",
                "payload": {"frame": "raw-data"},
                "privacy": {
                    "contains_raw_media": True,
                    "cloud_upload_allowed": False,
                },
            }
        )

        self.assertTrue(event.payload["redacted"])
        self.assertNotIn("frame", event.payload)


if __name__ == "__main__":
    unittest.main()

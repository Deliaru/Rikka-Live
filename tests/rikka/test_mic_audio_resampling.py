import asyncio
import unittest
from types import SimpleNamespace

import numpy as np

from open_llm_vtuber.websocket_handler import WebSocketHandler, resample_audio_chunk


class MicAudioResamplingTests(unittest.TestCase):
    def make_handler(self, sample_rate=16000):
        handler = WebSocketHandler.__new__(WebSocketHandler)
        asr = SimpleNamespace(SAMPLE_RATE=sample_rate)
        handler.default_context_cache = SimpleNamespace(asr_engine=asr)
        handler.client_contexts = {"client": SimpleNamespace(asr_engine=asr)}
        handler.received_data_buffers = {"client": np.array([], dtype=np.float32)}
        return handler

    def test_resample_audio_chunk_downsamples_browser_rate(self):
        audio = np.linspace(-1.0, 1.0, num=480, dtype=np.float32)

        resampled = resample_audio_chunk(audio, 48000, 16000)

        self.assertEqual(resampled.dtype, np.float32)
        self.assertEqual(len(resampled), 160)

    def test_mic_audio_data_resamples_to_asr_engine_rate(self):
        async def run():
            handler = self.make_handler(sample_rate=16000)

            await handler._handle_audio_data(
                websocket=None,
                client_uid="client",
                data={
                    "type": "mic-audio-data",
                    "audio": [0.0] * 480,
                    "sample_rate": 48000,
                },
            )

            self.assertEqual(len(handler.received_data_buffers["client"]), 160)

        asyncio.run(run())

    def test_mic_audio_data_preserves_legacy_payload_without_sample_rate(self):
        async def run():
            handler = self.make_handler(sample_rate=16000)

            await handler._handle_audio_data(
                websocket=None,
                client_uid="client",
                data={
                    "type": "mic-audio-data",
                    "audio": [0.0] * 480,
                },
            )

            self.assertEqual(len(handler.received_data_buffers["client"]), 480)

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()

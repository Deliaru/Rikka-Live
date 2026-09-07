import asyncio
import unittest
from types import SimpleNamespace

import httpx
from loguru import logger

from open_llm_vtuber.agent.stateless_llm.openai_compatible_llm import AsyncLLM


class FakeChatStream:
    def __init__(self, chunks, *, delay_seconds=0):
        self._chunks = list(chunks)
        self._index = 0
        self.closed = False
        self.delay_seconds = delay_seconds

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.delay_seconds:
            await asyncio.sleep(self.delay_seconds)
        if self._index >= len(self._chunks):
            raise StopAsyncIteration
        chunk = self._chunks[self._index]
        self._index += 1
        if isinstance(chunk, Exception):
            raise chunk
        return chunk

    async def close(self):
        self.closed = True


class FakeChatCompletions:
    def __init__(self, stream):
        self.stream = stream

    async def create(self, **_kwargs):
        return self.stream


def chunk(content=None, *, choices=None, tool_calls=None):
    if choices is not None:
        return SimpleNamespace(choices=choices)
    return SimpleNamespace(
        choices=[SimpleNamespace(delta=SimpleNamespace(content=content, tool_calls=tool_calls))]
    )


class OpenAICompatibleLLMTests(unittest.TestCase):
    def test_chat_stream_skips_empty_choices_chunks(self):
        async def run():
            stream = FakeChatStream([chunk(choices=[]), chunk("ok")])
            llm = AsyncLLM(
                model="mimo-v2.5",
                base_url="https://example.invalid/v1",
                llm_api_key="test-key",
                api_mode="chat",
            )
            llm.client = SimpleNamespace(
                chat=SimpleNamespace(completions=FakeChatCompletions(stream))
            )
            chunks = []
            async for item in llm.chat_completion(
                [{"role": "user", "content": "hello"}],
                system="system",
            ):
                chunks.append(item)
            return chunks, stream.closed

        chunks, closed = asyncio.run(run())
        self.assertEqual(chunks, ["ok"])
        self.assertTrue(closed)

    def test_chat_stream_skips_empty_choices_before_tool_delta_access(self):
        async def run():
            stream = FakeChatStream([chunk(choices=[]), chunk("fine")])
            llm = AsyncLLM(
                model="mimo-v2.5",
                base_url="https://example.invalid/v1",
                llm_api_key="test-key",
                api_mode="chat",
            )
            llm.client = SimpleNamespace(
                chat=SimpleNamespace(completions=FakeChatCompletions(stream))
            )
            return [
                item
                async for item in llm.chat_completion(
                    [{"role": "user", "content": "hello"}],
                    system="system",
                )
            ]

        self.assertEqual(asyncio.run(run()), ["fine"])

    def test_chat_stream_skips_empty_choices_without_tool_support(self):
        async def run():
            stream = FakeChatStream([chunk(choices=[]), chunk("ok")])
            llm = AsyncLLM(
                model="mimo-v2.5",
                base_url="https://example.invalid/v1",
                llm_api_key="test-key",
                api_mode="chat",
            )
            llm.support_tools = False
            llm.client = SimpleNamespace(
                chat=SimpleNamespace(completions=FakeChatCompletions(stream))
            )
            chunks = []
            async for item in llm.chat_completion(
                [{"role": "user", "content": "hello"}],
                system="system",
            ):
                chunks.append(item)
            return chunks

        self.assertEqual(asyncio.run(run()), ["ok"])

    def test_chat_debug_log_redacts_messages_before_file_write(self):
        async def run():
            stream = FakeChatStream([chunk("ok")])
            llm = AsyncLLM(
                model="mimo-v2.5",
                base_url="https://example.invalid/v1",
                llm_api_key="sk-secret-demo-1234567890",
                api_mode="chat",
            )
            llm.client = SimpleNamespace(
                chat=SimpleNamespace(completions=FakeChatCompletions(stream))
            )
            async for _item in llm.chat_completion(
                [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": "data:image/png;base64," + ("a" * 240)
                                },
                            },
                            {
                                "type": "text",
                                "text": "llm_api_key='sk-secret-demo-1234567890'",
                            },
                        ],
                    }
                ],
                system="system prompt",
            ):
                pass

        records = []
        sink_id = logger.add(records.append, level="DEBUG", format="{message}")
        try:
            asyncio.run(run())
        finally:
            logger.remove(sink_id)

        rendered = "\n".join(str(record) for record in records)
        self.assertNotIn("data:image", rendered)
        self.assertNotIn("a" * 80, rendered)
        self.assertNotIn("sk-secret-demo", rendered)
        self.assertIn("[redacted", rendered)

    def test_chat_stream_chunk_timeout_yields_provider_error_and_closes_stream(self):
        async def run():
            stream = FakeChatStream([chunk("late")], delay_seconds=0.05)
            llm = AsyncLLM(
                model="mimo-v2.5",
                base_url="https://example.invalid/v1",
                llm_api_key="test-key",
                api_mode="chat",
                timeout_seconds=0.01,
            )
            llm.client = SimpleNamespace(
                chat=SimpleNamespace(completions=FakeChatCompletions(stream))
            )
            chunks = []
            async for item in llm.chat_completion(
                [{"role": "user", "content": "hello"}],
                system="system",
            ):
                chunks.append(item)
            return chunks, stream.closed

        chunks, closed = asyncio.run(run())
        self.assertEqual(len(chunks), 1)
        self.assertIn("Error calling the chat endpoint", chunks[0])
        self.assertIn("timed out", chunks[0])
        self.assertTrue(closed)

    def test_chat_stream_connection_error_yields_provider_error_and_closes_stream(self):
        async def run():
            stream = FakeChatStream([httpx.RemoteProtocolError("incomplete chunked read")])
            llm = AsyncLLM(
                model="mimo-v2.5",
                base_url="https://example.invalid/v1",
                llm_api_key="test-key",
                api_mode="chat",
                timeout_seconds=0.01,
            )
            llm.client = SimpleNamespace(
                chat=SimpleNamespace(completions=FakeChatCompletions(stream))
            )
            chunks = []
            async for item in llm.chat_completion(
                [{"role": "user", "content": "hello"}],
                system="system",
            ):
                chunks.append(item)
            return chunks, stream.closed

        chunks, closed = asyncio.run(run())
        self.assertEqual(len(chunks), 1)
        self.assertIn("Error calling the chat endpoint", chunks[0])
        self.assertIn("incomplete chunked read", chunks[0])
        self.assertTrue(closed)


if __name__ == "__main__":
    unittest.main()

"""Description: This file contains the implementation of the `AsyncLLM` class.
This class is responsible for handling asynchronous interaction with OpenAI API compatible
endpoints for language generation.
"""

import json
import asyncio
from typing import AsyncIterator, List, Dict, Any, Literal

import httpx
from openai import (
    AsyncStream,
    AsyncOpenAI,
    APIError,
    APIConnectionError,
    APITimeoutError,
    RateLimitError,
    NotGiven,
    NOT_GIVEN,
)
from openai.types.chat import ChatCompletionChunk
from openai.types.chat.chat_completion_chunk import ChoiceDeltaToolCall
from loguru import logger

from .stateless_llm_interface import StatelessLLMInterface
from ...mcpp.types import ToolCallObject
from ...utils.log_redaction import redact_debug_text


MAX_PROVIDER_ERROR_LENGTH = 900
DEFAULT_LLM_TIMEOUT_SECONDS = 60.0


class AsyncLLM(StatelessLLMInterface):
    def __init__(
        self,
        model: str,
        base_url: str,
        llm_api_key: str = "z",
        organization_id: str = "z",
        project_id: str = "z",
        temperature: float = 1.0,
        api_mode: Literal["chat", "responses"] | None = "chat",
        timeout_seconds: float | None = DEFAULT_LLM_TIMEOUT_SECONDS,
    ):
        """
        Initializes an instance of the `AsyncLLM` class.

        Parameters:
        - model (str): The model to be used for language generation.
        - base_url (str): The base URL for the OpenAI API.
        - organization_id (str, optional): The organization ID for the OpenAI API. Defaults to "z".
        - project_id (str, optional): The project ID for the OpenAI API. Defaults to "z".
        - llm_api_key (str, optional): The API key for the OpenAI API. Defaults to "z".
        - temperature (float, optional): What sampling temperature to use, between 0 and 2. Defaults to 1.0.
        """
        self.base_url = base_url
        self.model = model
        self.temperature = temperature
        self.api_mode = api_mode if api_mode in {"chat", "responses"} else "chat"
        self.timeout_seconds = (
            float(timeout_seconds)
            if timeout_seconds and float(timeout_seconds) > 0
            else DEFAULT_LLM_TIMEOUT_SECONDS
        )
        self.llm_api_key = llm_api_key or "z"
        self.organization_id = organization_id
        self.project_id = project_id
        self.client = AsyncOpenAI(
            base_url=base_url,
            organization=organization_id,
            project=project_id,
            api_key=self.llm_api_key,
            timeout=self.timeout_seconds,
        )
        self.support_tools = self.api_mode == "chat"

        logger.info(
            f"Initialized AsyncLLM with the parameters: {self.base_url}, "
            f"{self.model}, api_mode={self.api_mode}, timeout={self.timeout_seconds}s"
        )

    async def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        system: str = None,
        tools: List[Dict[str, Any]] | NotGiven = NOT_GIVEN,
    ) -> AsyncIterator[str | List[ChoiceDeltaToolCall]]:
        """
        Generates a chat completion using the OpenAI API asynchronously.

        Parameters:
        - messages (List[Dict[str, Any]]): The list of messages to send to the API.
        - system (str, optional): System prompt to use for this completion.
        - tools (List[Dict[str, str]], optional): List of tools to use for this completion.

        Yields:
        - str: The content of each chunk from the API response.
        - List[ChoiceDeltaToolCall]: The tool calls detected in the response.

        Raises:
        - APIConnectionError: When the server cannot be reached
        - RateLimitError: When a 429 status code is received
        - APIError: For other API-related errors
        """
        if self.api_mode == "responses":
            async for event in self._responses_completion(messages, system):
                yield event
            return

        stream = None
        # Tool call related state variables
        accumulated_tool_calls = {}
        in_tool_call = False

        try:
            # If system prompt is provided, add it to the messages
            messages_with_system = messages
            if system:
                messages_with_system = [
                    {"role": "system", "content": system},
                    *messages,
                ]
            logger.debug(
                "Messages: "
                f"{redact_debug_text(messages_with_system)}"
            )

            available_tools = tools if self.support_tools else NOT_GIVEN

            stream: AsyncStream[ChatCompletionChunk] = await asyncio.wait_for(
                self.client.chat.completions.create(
                    messages=messages_with_system,
                    model=self.model,
                    stream=True,
                    temperature=self.temperature,
                    tools=available_tools,
                ),
                timeout=self.timeout_seconds,
            )
            logger.debug(
                f"Tool Support: {self.support_tools}, Available tools: {available_tools}"
            )

            stream_iter = stream.__aiter__()
            while True:
                try:
                    chunk = await asyncio.wait_for(
                        stream_iter.__anext__(),
                        timeout=self.timeout_seconds,
                    )
                except StopAsyncIteration:
                    break
                if not chunk.choices:
                    logger.debug("Empty chunk received")
                    continue
                choice = chunk.choices[0]
                if self.support_tools:
                    has_tool_calls = (
                        hasattr(choice.delta, "tool_calls")
                        and choice.delta.tool_calls
                    )

                    if has_tool_calls:
                        logger.debug(
                            f"Tool calls detected in chunk: {choice.delta.tool_calls}"
                        )
                        in_tool_call = True
                        # Process tool calls in the current chunk
                        for tool_call in choice.delta.tool_calls:
                            index = (
                                tool_call.index if hasattr(tool_call, "index") else 0
                            )

                            # Initialize tool call for this index if needed
                            if index not in accumulated_tool_calls:
                                accumulated_tool_calls[index] = {
                                    "index": index,
                                    "id": getattr(tool_call, "id", None),
                                    "type": getattr(tool_call, "type", None),
                                    "function": {"name": "", "arguments": ""},
                                }

                            # Update tool call information
                            if hasattr(tool_call, "id") and tool_call.id:
                                accumulated_tool_calls[index]["id"] = tool_call.id
                            if hasattr(tool_call, "type") and tool_call.type:
                                accumulated_tool_calls[index]["type"] = tool_call.type

                            # Update function information
                            if hasattr(tool_call, "function"):
                                if (
                                    hasattr(tool_call.function, "name")
                                    and tool_call.function.name
                                ):
                                    accumulated_tool_calls[index]["function"][
                                        "name"
                                    ] = tool_call.function.name
                                if (
                                    hasattr(tool_call.function, "arguments")
                                    and tool_call.function.arguments
                                ):
                                    accumulated_tool_calls[index]["function"][
                                        "arguments"
                                    ] += tool_call.function.arguments

                        continue

                    # If we were in a tool call but now we're not, yield the tool call result
                    elif in_tool_call and not has_tool_calls:
                        in_tool_call = False
                        # Convert accumulated tool calls to the required format and output
                        logger.info(f"Complete tool calls: {accumulated_tool_calls}")

                        # Use the from_dict method to create a ToolCallObject instance from a dictionary
                        complete_tool_calls = [
                            ToolCallObject.from_dict(tool_data)
                            for tool_data in accumulated_tool_calls.values()
                        ]

                        yield complete_tool_calls
                        accumulated_tool_calls = {}  # Reset for potential future tool calls

                # Process regular content chunks
                content = choice.delta.content or ""
                if content:
                    yield content
                    continue
                raw_delta = self._diagnostic_delta_payload(choice)
                if raw_delta:
                    yield {
                        "type": "raw_delta",
                        "source": "chat",
                        "data": raw_delta,
                    }
                    continue
                yield ""

            # If stream ends while still in a tool call, make sure to yield the tool call
            if in_tool_call and accumulated_tool_calls:
                logger.info(f"Final tool call at stream end: {accumulated_tool_calls}")

                # Create a ToolCallObject instance from a dictionary using the from_dict method.
                complete_tool_calls = [
                    ToolCallObject.from_dict(tool_data)
                    for tool_data in accumulated_tool_calls.values()
                ]

                yield complete_tool_calls

        except APIConnectionError as e:
            message = self._format_api_error(
                "chat",
                e,
                fallback="connection error",
            )
            logger.error(message)
            yield message

        except RateLimitError as e:
            message = self._format_api_error(
                "chat",
                e,
                fallback="rate limit exceeded",
                fallback_status=429,
            )
            logger.error(message)
            yield message

        except (APITimeoutError, asyncio.TimeoutError) as e:
            message = self._format_api_error(
                "chat",
                e,
                fallback=f"request timed out after {self.timeout_seconds:.1f}s",
            )
            logger.error(message)
            yield message

        except httpx.RequestError as e:
            message = self._format_provider_response_error(
                "chat",
                None,
                f"connection error: {e}",
            )
            logger.error(message)
            yield message

        except APIError as e:
            if "does not support tools" in str(e):
                self.support_tools = False
                logger.warning(
                    f"{self.model} does not support tools. Disabling tool support."
                )
                yield "__API_NOT_SUPPORT_TOOLS__"
                return
            message = self._format_api_error("chat", e, fallback="provider error")
            logger.error(message)
            yield message

        finally:
            # make sure the stream is properly closed
            # so when interrupted, no more tokens will being generated.
            if stream:
                logger.debug("Chat completion finished.")
                await stream.close()
                logger.debug("Stream closed.")

    async def _responses_completion(
        self,
        messages: List[Dict[str, Any]],
        system: str = None,
    ) -> AsyncIterator[str]:
        """Generate text through an OpenAI-compatible Responses endpoint."""
        response_input = self._responses_input(messages, system)
        payload: dict[str, Any] = {
            "model": self.model,
            "input": response_input,
            "stream": True,
            "temperature": self.temperature,
        }
        headers = self._responses_headers()
        yielded_text = False

        try:
            async with httpx.AsyncClient(timeout=self._httpx_timeout()) as client:
                async with client.stream(
                    "POST",
                    self._responses_url(),
                    headers=headers,
                    json=payload,
                ) as response:
                    if response.status_code >= 400:
                        body = await response.aread()
                        message = self._format_provider_response_error(
                            "responses",
                            response.status_code,
                            body.decode(errors="replace"),
                        )
                        logger.error(message)
                        yield message
                        return

                    async for line in response.aiter_lines():
                        text = self._parse_responses_stream_line(
                            line,
                            include_completed=not yielded_text,
                        )
                        if text:
                            yielded_text = True
                            yield text
        except httpx.TimeoutException as exc:
            message = self._format_provider_response_error(
                "responses",
                None,
                f"request timed out after {self.timeout_seconds:.1f}s: {exc}",
            )
            logger.error(message)
            yield message
        except httpx.RequestError as exc:
            message = self._format_provider_response_error(
                "responses",
                None,
                f"connection error: {exc}",
            )
            logger.error(message)
            yield message

    def _responses_url(self) -> str:
        return f"{str(self.base_url).rstrip('/')}/responses"

    def _diagnostic_delta_payload(self, choice: Any) -> dict[str, Any]:
        """Return non-content provider delta fields for debug diagnostics."""
        try:
            delta_payload = choice.delta.model_dump(mode="json", exclude_none=True)
        except Exception:
            delta_payload = {}
        delta_payload.pop("content", None)
        delta_payload.pop("tool_calls", None)
        payload: dict[str, Any] = {}
        if delta_payload:
            payload["delta"] = delta_payload
        finish_reason = getattr(choice, "finish_reason", None)
        if finish_reason:
            payload["finish_reason"] = finish_reason
        return payload

    def _httpx_timeout(self) -> httpx.Timeout:
        connect_timeout = min(10.0, self.timeout_seconds)
        return httpx.Timeout(
            self.timeout_seconds,
            connect=connect_timeout,
        )

    def _format_api_error(
        self,
        endpoint: str,
        exc: Exception,
        *,
        fallback: str,
        fallback_status: int | None = None,
    ) -> str:
        status = (
            getattr(exc, "status_code", None)
            or getattr(getattr(exc, "response", None), "status_code", None)
            or fallback_status
        )
        detail = self._extract_api_error_detail(exc) or fallback
        return self._format_provider_response_error(endpoint, status, detail)

    def _extract_api_error_detail(self, exc: Exception) -> str:
        body = getattr(exc, "body", None)
        if body:
            if isinstance(body, (dict, list)):
                try:
                    return json.dumps(body, ensure_ascii=False)
                except (TypeError, ValueError):
                    return str(body)
            return str(body)

        response = getattr(exc, "response", None)
        if response is not None:
            try:
                text = response.text
                if text:
                    return text
            except Exception:
                pass

        cause = getattr(exc, "__cause__", None)
        if cause:
            return str(cause)
        return str(exc)

    def _format_provider_response_error(
        self,
        endpoint: str,
        status_code: int | None,
        detail: str,
    ) -> str:
        status_text = (
            f"provider returned HTTP {status_code}"
            if status_code is not None
            else "provider request failed"
        )
        detail = self._redact_provider_error(str(detail or ""))
        context = (
            f"base_url={self.base_url}, model={self.model}, "
            f"api_mode={self.api_mode}, temperature={self.temperature}"
        )
        return (
            f"Error calling the {endpoint} endpoint: {status_text}. "
            f"Detail: {detail}. Context: {context}"
        )

    def _redact_provider_error(self, text: str) -> str:
        redacted = (
            text.replace(self.llm_api_key, "[redacted]") if self.llm_api_key else text
        )
        redacted = redact_debug_text(redacted)
        redacted = redacted.replace("\r", " ").replace("\n", " ")
        redacted = " ".join(redacted.split())
        if len(redacted) > MAX_PROVIDER_ERROR_LENGTH:
            return f"{redacted[: MAX_PROVIDER_ERROR_LENGTH - 1]}..."
        return redacted

    def _responses_headers(self) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.llm_api_key}",
            "Content-Type": "application/json",
        }
        if self.organization_id and self.organization_id != "z":
            headers["OpenAI-Organization"] = self.organization_id
        if self.project_id and self.project_id != "z":
            headers["OpenAI-Project"] = self.project_id
        return headers

    def _responses_input(
        self,
        messages: List[Dict[str, Any]],
        system: str | None,
    ) -> list[dict[str, Any]]:
        response_messages: list[dict[str, Any]] = []
        if system:
            response_messages.append(
                {
                    "role": "system",
                    "content": [{"type": "input_text", "text": system}],
                }
            )
        for message in messages:
            role = str(message.get("role") or "user")
            if role not in {"system", "developer", "user", "assistant"}:
                role = "user"
            response_messages.append(
                {
                    "role": role,
                    "content": self._responses_content(
                        message.get("content", ""),
                        role=role,
                    ),
                }
            )
        return response_messages

    def _responses_content(self, content: Any, *, role: str) -> list[dict[str, Any]]:
        text_type = "output_text" if role == "assistant" else "input_text"
        if isinstance(content, str):
            return [{"type": text_type, "text": content}]
        if not isinstance(content, list):
            return [{"type": text_type, "text": str(content)}]

        response_content: list[dict[str, Any]] = []
        for item in content:
            if not isinstance(item, dict):
                response_content.append({"type": text_type, "text": str(item)})
                continue
            if item.get("type") == "text":
                response_content.append(
                    {"type": text_type, "text": str(item.get("text", ""))}
                )
                continue
            if role != "assistant" and item.get("type") == "image_url":
                image_url = item.get("image_url") or {}
                if isinstance(image_url, dict) and image_url.get("url"):
                    response_content.append(
                        {
                            "type": "input_image",
                            "image_url": image_url.get("url"),
                        }
                    )
                    continue
            response_content.append({"type": text_type, "text": str(item)})
        return response_content or [{"type": text_type, "text": ""}]

    def _parse_responses_stream_line(
        self,
        line: str,
        *,
        include_completed: bool,
    ) -> str:
        line = line.strip()
        if not line.startswith("data:"):
            return ""
        data = line.removeprefix("data:").strip()
        if not data or data == "[DONE]":
            return ""
        try:
            event = json.loads(data)
        except json.JSONDecodeError:
            logger.debug(f"Skipping non-JSON responses stream line: {line[:200]}")
            return ""

        event_type = event.get("type")
        if event_type in {"response.output_text.delta", "response.text.delta"}:
            return str(event.get("delta") or event.get("text") or "")
        if include_completed and event_type in {
            "response.completed",
            "response.done",
        }:
            return self._extract_completed_response_text(event.get("response") or event)
        if event_type in {"error", "response.failed"}:
            error = event.get("error") or event.get("response", {}).get("error") or {}
            message = error.get("message") if isinstance(error, dict) else str(error)
            logger.error(f"Responses endpoint returned error: {message}")
        return ""

    def _extract_completed_response_text(self, response: Any) -> str:
        if not isinstance(response, dict):
            return ""
        texts: list[str] = []
        for output in response.get("output") or []:
            if not isinstance(output, dict):
                continue
            for content in output.get("content") or []:
                if not isinstance(content, dict):
                    continue
                if content.get("type") in {"output_text", "text"}:
                    texts.append(str(content.get("text") or ""))
        if not texts and response.get("output_text"):
            texts.append(str(response.get("output_text") or ""))
        return "".join(texts)

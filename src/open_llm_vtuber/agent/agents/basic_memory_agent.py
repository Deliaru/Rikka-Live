from typing import (
    AsyncIterator,
    List,
    Dict,
    Any,
    Callable,
    Literal,
    Union,
    Optional,
)
import hashlib
import re
from loguru import logger
from .agent_interface import AgentInterface
from ..output_types import Actions, SentenceOutput, DisplayText
from ..stateless_llm.stateless_llm_interface import StatelessLLMInterface
from ..stateless_llm.claude_llm import AsyncLLM as ClaudeAsyncLLM
from ..stateless_llm.openai_compatible_llm import AsyncLLM as OpenAICompatibleAsyncLLM
from ...chat_history_manager import get_history
from ..transformers import (
    sentence_divider,
    actions_extractor,
    tts_filter,
    display_processor,
)
from ...config_manager import TTSPreprocessorConfig
from ..input_types import BatchInput, TextSource
from prompts import prompt_loader
from ...mcpp.tool_manager import ToolManager
from ...mcpp.json_detector import StreamJSONDetector
from ...mcpp.types import ToolCallObject
from ...mcpp.tool_executor import ToolExecutor
from ...rikka.core import validate_rikka_response
from ...rikka.debug_console import redact_debug_text
from ...rikka.presentation import rikka_response_to_actions
from ...rikka.schemas import RikkaResponse
from ...rikka.memory import get_default_memory_store
from ...rikka.mood import apply_rikka_mood_effects, get_default_mood_state
from ...rikka.inner_life import get_default_inner_life
from ...rikka.identity import identity_prompt_block
from ...rikka.agent_tools import (
    build_tool_result_content,
    get_default_tool_runner,
    parse_tool_request,
)
from ...rikka.settings import get_default_settings_store, live2d_expressions_enabled


def _extract_provider_error(raw_response: str) -> dict[str, Any]:
    text = str(raw_response or "").strip()
    if not text.startswith("Error calling the "):
        return {}
    endpoint_match = re.search(r"Error calling the ([^ ]+) endpoint:", text)
    status_match = re.search(r"provider returned HTTP (\d+)", text)
    detail_match = re.search(r"Detail: (.*?)(?:\. Context:|$)", text)
    return {
        "provider_error": True,
        "provider_endpoint": endpoint_match.group(1) if endpoint_match else "",
        "provider_status_code": int(status_match.group(1)) if status_match else None,
        "provider_error_detail": (
            redact_debug_text(detail_match.group(1) if detail_match else text)[:240]
        ),
        "provider_error_message": redact_debug_text(text)[:360],
    }


def _collapsed_redacted_text(value: Any) -> str:
    return " ".join(redact_debug_text(value).split())


def _safe_text_preview(value: Any, limit: int = 240) -> tuple[str, bool]:
    text = _collapsed_redacted_text(value)
    truncated = len(text) > limit
    return (f"{text[: limit - 1]}..." if truncated else text, truncated)


def _safe_raw_response_text(value: Any, limit: int = 4000) -> tuple[str, bool]:
    text = redact_debug_text(value)
    truncated = len(text) > limit
    return (f"{text[: limit - 1]}..." if truncated else text, truncated)


def _safe_text_hash(value: Any) -> str:
    text = _collapsed_redacted_text(value)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _llm_event_diagnostic_text(event: Any) -> str:
    if isinstance(event, str):
        return event
    try:
        return json.dumps(event, ensure_ascii=False, default=str)
    except Exception:
        return str(event)


def _is_empty_spoken_text_error(errors: list[str]) -> bool:
    return any(
        "spoken_text cannot be empty after cleaning" in error for error in errors
    )


def _classify_rikka_validation_failure(
    *,
    errors: list[str],
    provider_error: dict[str, Any],
    silent_on_empty: bool,
) -> str:
    if provider_error:
        return "provider_error"
    if silent_on_empty and _is_empty_spoken_text_error(errors):
        return "empty_proactive_response"
    joined = "\n".join(errors)
    if "No JSON object found in response" in joined:
        return "missing_json"
    if errors:
        return "schema_error"
    return "unknown_validation_error"


def _validation_diagnostics(
    *,
    raw_response: str,
    errors: list[str],
    provider_error: dict[str, Any],
    fallback: RikkaResponse,
    fallback_used: bool,
    silent_on_empty: bool,
    attached_image_count: int,
) -> dict[str, Any]:
    excerpt, truncated = _safe_text_preview(raw_response)
    raw_text, raw_text_truncated = _safe_raw_response_text(raw_response)
    spoken_preview, spoken_truncated = _safe_text_preview(fallback.spoken_text, 160)
    subtitle_preview, subtitle_truncated = _safe_text_preview(
        fallback.subtitle_text,
        160,
    )
    diagnostics: dict[str, Any] = {
        "failure_kind": _classify_rikka_validation_failure(
            errors=errors,
            provider_error=provider_error,
            silent_on_empty=silent_on_empty,
        ),
        "raw_response_length": len(str(raw_response or "")),
        "raw_response_hash": _safe_text_hash(raw_response),
        "raw_response_excerpt": excerpt,
        "raw_response_text": raw_text,
        "raw_response_text_truncated": raw_text_truncated,
        "raw_response_truncated": truncated,
        "error_count": len(errors),
        "errors": errors[:2],
        "attached_image_count": attached_image_count,
    }
    if fallback_used and not silent_on_empty:
        diagnostics.update(
            {
                "fallback_reason_code": fallback.reason_code,
                "fallback_spoken_preview": spoken_preview,
                "fallback_spoken_truncated": spoken_truncated,
                "fallback_subtitle_preview": subtitle_preview,
                "fallback_subtitle_truncated": subtitle_truncated,
            }
        )
    return diagnostics


def _repair_diagnostics(
    *,
    raw_response: str,
    repair_notes: list[str],
    response: RikkaResponse,
    attached_image_count: int,
) -> dict[str, Any]:
    excerpt, truncated = _safe_text_preview(raw_response)
    raw_text, raw_text_truncated = _safe_raw_response_text(raw_response)
    spoken_preview, spoken_truncated = _safe_text_preview(response.spoken_text, 160)
    subtitle_preview, subtitle_truncated = _safe_text_preview(
        response.subtitle_text,
        160,
    )
    return {
        "failure_kind": "schema_repaired",
        "raw_response_length": len(str(raw_response or "")),
        "raw_response_hash": _safe_text_hash(raw_response),
        "raw_response_excerpt": excerpt,
        "raw_response_text": raw_text,
        "raw_response_text_truncated": raw_text_truncated,
        "raw_response_truncated": truncated,
        "error_count": 0,
        "errors": [],
        "repair_notes": repair_notes[:8],
        "repaired": True,
        "fallback": False,
        "fallback_reason_code": "",
        "fallback_spoken_preview": spoken_preview,
        "fallback_spoken_truncated": spoken_truncated,
        "fallback_subtitle_preview": subtitle_preview,
        "fallback_subtitle_truncated": subtitle_truncated,
        "attached_image_count": attached_image_count,
    }


def _message_image_count(messages: list[dict[str, Any]]) -> int:
    count = 0
    for message in messages:
        content = message.get("content")
        if isinstance(content, list):
            count += sum(
                1
                for item in content
                if isinstance(item, dict) and item.get("type") == "image_url"
            )
    return count


class BasicMemoryAgent(AgentInterface):
    """Agent with basic chat memory and tool calling support."""

    _system: str = "You are a helpful assistant."

    def __init__(
        self,
        llm: StatelessLLMInterface,
        system: str,
        live2d_model,
        tts_preprocessor_config: TTSPreprocessorConfig = None,
        faster_first_response: bool = True,
        segment_method: str = "pysbd",
        use_mcpp: bool = False,
        interrupt_method: Literal["system", "user"] = "user",
        tool_prompts: Dict[str, str] = None,
        tool_manager: Optional[ToolManager] = None,
        tool_executor: Optional[ToolExecutor] = None,
        mcp_prompt_string: str = "",
    ):
        """Initialize agent with LLM and configuration."""
        super().__init__()
        self._memory = []
        self._live2d_model = live2d_model
        self._tts_preprocessor_config = tts_preprocessor_config
        self._faster_first_response = faster_first_response
        self._segment_method = segment_method
        self._use_mcpp = use_mcpp
        self.interrupt_method = interrupt_method
        self._tool_prompts = tool_prompts or {}
        self._interrupt_handled = False
        self.prompt_mode_flag = False

        self._tool_manager = tool_manager
        self._tool_executor = tool_executor
        self._mcp_prompt_string = mcp_prompt_string
        self._json_detector = StreamJSONDetector()

        self._formatted_tools_openai = []
        self._formatted_tools_claude = []
        if self._tool_manager:
            self._formatted_tools_openai = self._tool_manager.get_formatted_tools(
                "OpenAI"
            )
            self._formatted_tools_claude = self._tool_manager.get_formatted_tools(
                "Claude"
            )
            logger.debug(
                f"Agent received pre-formatted tools - OpenAI: {len(self._formatted_tools_openai)}, Claude: {len(self._formatted_tools_claude)}"
            )
        else:
            logger.debug(
                "ToolManager not provided, agent will not have pre-formatted tools."
            )

        self._set_llm(llm)
        self.set_system(system if system else self._system)

        if self._use_mcpp and not all(
            [
                self._tool_manager,
                self._tool_executor,
                self._json_detector,
            ]
        ):
            logger.warning(
                "use_mcpp is True, but some MCP components are missing in the agent. Tool calling might not work as expected."
            )
        elif not self._use_mcpp and any(
            [
                self._tool_manager,
                self._tool_executor,
                self._json_detector,
            ]
        ):
            logger.warning(
                "use_mcpp is False, but some MCP components were passed to the agent."
            )

        logger.info("BasicMemoryAgent initialized.")

    def _set_llm(self, llm: StatelessLLMInterface):
        """Set the LLM for chat completion."""
        self._llm = llm
        self.chat = self._chat_function_factory()

    def set_system(self, system: str):
        """Set the system prompt."""
        logger.debug(f"Memory Agent: Setting system prompt: '''{system}'''")

        if self.interrupt_method == "user":
            system = f"{system}\n\nIf you received `[interrupted by user]` signal, you were interrupted."

        self._system = system

    def _uses_rikka_response_contract(self) -> bool:
        system = self._system.lower()
        return all(
            field in system
            for field in ("spoken_text", "subtitle_text", "reason_code")
        )

    def _sentence_output_from_rikka_response(
        self,
        raw_response: str,
        fallback_text: str | None = None,
        *,
        silent_on_empty: bool = False,
        validation_events: list[dict[str, Any]] | None = None,
        attached_image_count: int = 0,
    ) -> SentenceOutput | None:
        result = validate_rikka_response(raw_response)
        plain_text_repaired = (
            result.ok
            and result.repaired
            and "plain text used as spoken_text" in result.repair_notes
        )
        if fallback_text and plain_text_repaired:
            result.ok = False
            result.errors = ["No JSON object found in response"]
            result.repaired = False
            result.repair_notes = []
        if not result.ok:
            provider_error = _extract_provider_error(raw_response)
            silent_empty = silent_on_empty and self._is_empty_spoken_text_error(
                result.errors
            )
            if fallback_text:
                result.response = RikkaResponse(
                    spoken_text=fallback_text,
                    subtitle_text=fallback_text,
                    emotion="soft_smile",
                    motion="thinking",
                    gaze="camera",
                    priority="normal",
                    interruptible=True,
                    reason_code="safety_fallback",
                    memory_writes=[],
                )
            if validation_events is not None:
                diagnostics = _validation_diagnostics(
                    raw_response=raw_response,
                    errors=result.errors,
                    provider_error=provider_error,
                    fallback=result.response,
                    fallback_used=True,
                    silent_on_empty=silent_empty,
                    attached_image_count=attached_image_count,
                )
                event = {
                    "type": "rikka_validation_status",
                    "ok": False,
                    "fallback": True,
                    "silent": silent_empty,
                    **diagnostics,
                }
                if provider_error:
                    event.update(provider_error)
                validation_events.append(event)
            logger.warning(
                "Rikka structured response validation failed; "
                f"using fallback: {result.errors[:2]}"
            )
            if silent_on_empty and self._is_empty_spoken_text_error(result.errors):
                logger.info(
                    "Rikka proactive response was empty; skipping speech instead of "
                    "using audible fallback."
                )
                return None
        else:
            if result.repaired and validation_events is not None:
                validation_events.append(
                    {
                        "type": "rikka_validation_status",
                        "ok": True,
                        "fallback": False,
                        "silent": False,
                        **_repair_diagnostics(
                            raw_response=raw_response,
                            repair_notes=result.repair_notes,
                            response=result.response,
                            attached_image_count=attached_image_count,
                        ),
                    }
                )
                logger.info(
                    "Rikka structured response repaired locally: "
                    f"{result.repair_notes[:4]}"
                )
            if result.response.memory_writes:
                try:
                    applied = get_default_memory_store().apply_writes(
                        result.response.memory_writes
                    )
                    logger.info(
                        f"Rikka conversation applied {len(applied)} memory writes"
                    )
                except Exception as exc:
                    logger.warning(f"Failed to apply Rikka memory writes: {exc}")
        actions = (
            rikka_response_to_actions(
                result.response,
                self._live2d_model,
                enable_expression_actions=live2d_expressions_enabled(),
            )
            if self._live2d_model is not None
            else Actions()
        )
        output = SentenceOutput(
            display_text=DisplayText(text=result.response.spoken_text),
            tts_text=result.response.spoken_text,
            actions=actions,
        )
        if result.ok:
            try:
                settings = get_default_settings_store().snapshot()
                if settings.mood.enabled:
                    tts_meta = apply_rikka_mood_effects(
                        emotion=result.response.emotion,
                        settings=settings.mood,
                        live2d_model=self._live2d_model,
                        actions=output.actions,
                        register=True,
                        enable_idle_expression=live2d_expressions_enabled(),
                    )
                    if tts_meta:
                        meta = dict(output.tts_meta or {})
                        meta.update(tts_meta)
                        output.tts_meta = meta
            except Exception as exc:
                logger.warning(f"Failed to update Rikka mood state: {exc}")
        return output

    def _is_empty_spoken_text_error(self, errors: list[str]) -> bool:
        return _is_empty_spoken_text_error(errors)

    def _filler_sentence_output(self, text: str) -> SentenceOutput:
        response = RikkaResponse(
            spoken_text=text,
            subtitle_text=text,
            emotion="curious",
            motion="thinking",
            gaze="down",
            priority="low",
            interruptible=True,
            reason_code="idle_fill",
        )
        actions = (
            rikka_response_to_actions(
                response,
                self._live2d_model,
                enable_expression_actions=live2d_expressions_enabled(),
            )
            if self._live2d_model is not None
            else Actions()
        )
        return SentenceOutput(
            display_text=DisplayText(text=response.spoken_text),
            tts_text=response.spoken_text,
            actions=actions,
        )

    def _rikka_memory_block(self) -> str:
        try:
            summary = get_default_memory_store().summary()
        except Exception as exc:
            logger.warning(f"Failed to read Rikka memory summary: {exc}")
            return ""
        return f"【你记得的事】\n{summary}" if summary else ""

    def _rikka_turn_system(self, include_tools: bool, runner=None, note: str = "") -> str:
        parts = [self._system]
        memory_block = self._rikka_memory_block()
        if memory_block:
            parts.append(memory_block)
        try:
            settings = get_default_settings_store().snapshot()
            identity_block = identity_prompt_block(settings.identity)
            if identity_block:
                parts.append(identity_block)
            if settings.mood.enabled:
                mood_block = get_default_mood_state().prompt_block(settings.mood)
                if mood_block:
                    parts.append(mood_block)
            if settings.inner_life.enabled:
                inner_life_block = get_default_inner_life().prompt_block(
                    settings.inner_life
                )
                if inner_life_block:
                    parts.append(inner_life_block)
        except Exception as exc:
            logger.warning(f"Failed to build Rikka liveliness prompt blocks: {exc}")
        if include_tools and runner is not None:
            tool_block = runner.tool_protocol_block()
            if tool_block:
                parts.append(tool_block)
        if note:
            parts.append(note)
        return "\n\n".join(parts)

    async def _collect_full_text(
        self, messages: List[Dict[str, Any]], system: str
    ) -> str:
        token_stream = self._llm.chat_completion(messages, system)
        complete_response = ""
        diagnostic_events: list[str] = []
        async for event in token_stream:
            text_chunk = ""
            if isinstance(event, dict) and event.get("type") == "text_delta":
                text_chunk = event.get("text", "")
            elif isinstance(event, dict) and event.get("type") == "raw_delta":
                diagnostic_events.append(_llm_event_diagnostic_text(event))
            elif isinstance(event, str):
                text_chunk = event
            elif isinstance(event, list):
                diagnostic_events.append(_llm_event_diagnostic_text(event))
            else:
                diagnostic_events.append(_llm_event_diagnostic_text(event))
                continue
            complete_response += text_chunk
        if complete_response.strip():
            return complete_response
        return "\n".join(event for event in diagnostic_events if event)

    async def _rikka_tool_interaction_loop(
        self,
        messages: List[Dict[str, Any]],
        runner,
        *,
        silent_on_empty: bool = False,
    ) -> AsyncIterator[Union[SentenceOutput, Dict[str, Any]]]:
        working = messages.copy()
        filler_emitted = False
        last_tool_failure_text = ""
        settings = get_default_settings_store().snapshot().agent
        for round_index in range(settings.max_tool_rounds + 1):
            last_round = round_index == settings.max_tool_rounds
            system = self._rikka_turn_system(
                include_tools=not last_round,
                runner=runner,
                note="（工具轮已用尽，直接输出最终 RikkaResponse JSON）" if last_round else "",
            )
            raw_response = await self._collect_full_text(working, system)
            request = parse_tool_request(raw_response)
            if request is None or last_round:
                validation_events: list[dict[str, Any]] = []
                output = self._sentence_output_from_rikka_response(
                    raw_response,
                    fallback_text=last_tool_failure_text or None,
                    silent_on_empty=silent_on_empty,
                    validation_events=validation_events,
                    attached_image_count=_message_image_count(messages),
                )
                for event in validation_events:
                    yield event
                if output is None:
                    return
                if filler_emitted and settings.result_pre_silence_ms > 0:
                    meta = dict(output.tts_meta or {})
                    meta["pre_silence_ms"] = settings.result_pre_silence_ms
                    output.tts_meta = meta
                yield output
                self._add_message(output.display_text.text, "assistant")
                return

            if settings.filler_enabled and not filler_emitted:
                filler = runner.filler_text(
                    [str(call.get("tool") or "") for call in request.calls]
                )
                if filler:
                    yield self._filler_sentence_output(filler)
                    filler_emitted = True

            results = []
            async for event in runner.run_iter(request.calls):
                if isinstance(event, tuple) and event[0] == "results":
                    results = event[1]
                    continue
                yield event
            failed_result = next((result for result in results if not result.ok), None)
            if failed_result and failed_result.spoken_error:
                last_tool_failure_text = failed_result.spoken_error
            working.append({"role": "assistant", "content": raw_response})
            working.append(
                {"role": "user", "content": build_tool_result_content(results)}
            )

    def _add_message(
        self,
        message: Union[str, List[Dict[str, Any]]],
        role: str,
        display_text: DisplayText | None = None,
        skip_memory: bool = False,
    ):
        """Add message to memory."""
        if skip_memory:
            return

        text_content = ""
        if isinstance(message, list):
            for item in message:
                if item.get("type") == "text":
                    text_content += item["text"] + " "
            text_content = text_content.strip()
        elif isinstance(message, str):
            text_content = message
        else:
            logger.warning(
                f"_add_message received unexpected message type: {type(message)}"
            )
            text_content = str(message)

        if not text_content and role == "assistant":
            return

        message_data = {
            "role": role,
            "content": text_content,
        }

        if display_text:
            if display_text.name:
                message_data["name"] = display_text.name
            if display_text.avatar:
                message_data["avatar"] = display_text.avatar

        if (
            self._memory
            and self._memory[-1]["role"] == role
            and self._memory[-1]["content"] == text_content
        ):
            return

        self._memory.append(message_data)

    def set_memory_from_history(self, conf_uid: str, history_uid: str) -> None:
        """Load memory from chat history."""
        messages = get_history(conf_uid, history_uid)

        self._memory = []
        for msg in messages:
            role = "user" if msg["role"] == "human" else "assistant"
            content = msg["content"]
            if isinstance(content, str) and content:
                self._memory.append(
                    {
                        "role": role,
                        "content": content,
                    }
                )
            else:
                logger.warning(f"Skipping invalid message from history: {msg}")
        logger.info(f"Loaded {len(self._memory)} messages from history.")

    def handle_interrupt(self, heard_response: str) -> None:
        """Handle user interruption."""
        if self._interrupt_handled:
            return

        self._interrupt_handled = True

        if self._memory and self._memory[-1]["role"] == "assistant":
            if not self._memory[-1]["content"].endswith("..."):
                self._memory[-1]["content"] = heard_response + "..."
            else:
                self._memory[-1]["content"] = heard_response + "..."
        else:
            if heard_response:
                self._memory.append(
                    {
                        "role": "assistant",
                        "content": heard_response + "...",
                    }
                )

        interrupt_role = "system" if self.interrupt_method == "system" else "user"
        self._memory.append(
            {
                "role": interrupt_role,
                "content": "[Interrupted by user]",
            }
        )
        logger.info(f"Handled interrupt with role '{interrupt_role}'.")

    def _to_text_prompt(self, input_data: BatchInput) -> str:
        """Format input data to text prompt."""
        message_parts = []

        for text_data in input_data.texts:
            if text_data.source == TextSource.INPUT:
                message_parts.append(text_data.content)
            elif text_data.source == TextSource.CLIPBOARD:
                message_parts.append(
                    f"[User shared content from clipboard: {text_data.content}]"
                )

        if input_data.images:
            message_parts.append("\n[User has also provided images]")

        return "\n".join(message_parts).strip()

    def _to_messages(self, input_data: BatchInput) -> List[Dict[str, Any]]:
        """Prepare messages for LLM API call."""
        messages = self._memory.copy()
        user_content = []
        text_prompt = self._to_text_prompt(input_data)
        if text_prompt:
            user_content.append({"type": "text", "text": text_prompt})

        if input_data.images:
            image_added = False
            for img_data in input_data.images:
                if isinstance(img_data.data, str) and img_data.data.startswith(
                    "data:image"
                ):
                    user_content.append(
                        {
                            "type": "image_url",
                            "image_url": {"url": img_data.data, "detail": "auto"},
                        }
                    )
                    image_added = True
                else:
                    logger.error(
                        f"Invalid image data format: {type(img_data.data)}. Skipping image."
                    )

            if not image_added and not text_prompt:
                logger.warning(
                    "User input contains images but none could be processed."
                )

        if user_content:
            user_message = {"role": "user", "content": user_content}
            messages.append(user_message)

            skip_memory = False
            if input_data.metadata and input_data.metadata.get("skip_memory", False):
                skip_memory = True

            if not skip_memory:
                self._add_message(
                    text_prompt if text_prompt else "[User provided image(s)]", "user"
                )
        else:
            logger.warning("No content generated for user message.")

        return messages

    async def _claude_tool_interaction_loop(
        self,
        initial_messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
    ) -> AsyncIterator[Union[str, Dict[str, Any]]]:
        """Handle Claude interaction loop with tool support."""
        messages = initial_messages.copy()
        current_turn_text = ""
        pending_tool_calls = []
        current_assistant_message_content = []

        while True:
            stream = self._llm.chat_completion(messages, self._system, tools=tools)
            pending_tool_calls.clear()
            current_assistant_message_content.clear()

            async for event in stream:
                if event["type"] == "text_delta":
                    text = event["text"]
                    current_turn_text += text
                    yield text
                    if (
                        not current_assistant_message_content
                        or current_assistant_message_content[-1]["type"] != "text"
                    ):
                        current_assistant_message_content.append(
                            {"type": "text", "text": text}
                        )
                    else:
                        current_assistant_message_content[-1]["text"] += text
                elif event["type"] == "tool_use_complete":
                    tool_call_data = event["data"]
                    logger.info(
                        f"Tool request: {tool_call_data['name']} (ID: {tool_call_data['id']})"
                    )
                    pending_tool_calls.append(tool_call_data)
                    current_assistant_message_content.append(
                        {
                            "type": "tool_use",
                            "id": tool_call_data["id"],
                            "name": tool_call_data["name"],
                            "input": tool_call_data["input"],
                        }
                    )
                # elif event["type"] == "message_delta":
                #     if event["data"]["delta"].get("stop_reason"):
                #         stop_reason = event["data"]["delta"].get("stop_reason")
                elif event["type"] == "message_stop":
                    break
                elif event["type"] == "error":
                    logger.error(f"LLM API Error: {event['message']}")
                    yield f"[Error from LLM: {event['message']}]"
                    return

            if pending_tool_calls:
                filtered_assistant_content = [
                    block
                    for block in current_assistant_message_content
                    if not (
                        block.get("type") == "text"
                        and not block.get("text", "").strip()
                    )
                ]

                if filtered_assistant_content:
                    messages.append(
                        {"role": "assistant", "content": filtered_assistant_content}
                    )
                    assistant_text_for_memory = "".join(
                        [
                            c["text"]
                            for c in filtered_assistant_content
                            if c["type"] == "text"
                        ]
                    ).strip()
                    if assistant_text_for_memory:
                        self._add_message(assistant_text_for_memory, "assistant")

                tool_results_for_llm = []
                if not self._tool_executor:
                    logger.error(
                        "Claude Tool interaction requested but ToolExecutor is not available."
                    )
                    yield "[Error: ToolExecutor not configured]"
                    return

                tool_executor_iterator = self._tool_executor.execute_tools(
                    tool_calls=pending_tool_calls,
                    caller_mode="Claude",
                )
                try:
                    while True:
                        update = await anext(tool_executor_iterator)
                        if update.get("type") == "final_tool_results":
                            tool_results_for_llm = update.get("results", [])
                            break
                        else:
                            yield update
                except StopAsyncIteration:
                    logger.warning(
                        "Tool executor finished without final results marker."
                    )

                if tool_results_for_llm:
                    messages.append({"role": "user", "content": tool_results_for_llm})

                # stop_reason = None
                continue
            else:
                if current_turn_text:
                    self._add_message(current_turn_text, "assistant")
                return

    async def _openai_tool_interaction_loop(
        self,
        initial_messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
    ) -> AsyncIterator[Union[str, Dict[str, Any]]]:
        """Handle OpenAI interaction with tool support."""
        messages = initial_messages.copy()
        current_turn_text = ""
        pending_tool_calls: Union[List[ToolCallObject], List[Dict[str, Any]]] = []
        current_system_prompt = self._system

        while True:
            if self.prompt_mode_flag:
                if self._mcp_prompt_string:
                    current_system_prompt = (
                        f"{self._system}\n\n{self._mcp_prompt_string}"
                    )
                else:
                    logger.warning("Prompt mode active but mcp_prompt_string is empty!")
                    current_system_prompt = self._system
                tools_for_api = None
            else:
                current_system_prompt = self._system
                tools_for_api = tools

            stream = self._llm.chat_completion(
                messages, current_system_prompt, tools=tools_for_api
            )
            pending_tool_calls.clear()
            current_turn_text = ""
            assistant_message_for_api = None
            detected_prompt_json = None
            goto_next_while_iteration = False

            async for event in stream:
                if self.prompt_mode_flag:
                    if isinstance(event, str):
                        current_turn_text += event
                        if self._json_detector:
                            potential_json = self._json_detector.process_chunk(event)
                            if potential_json:
                                try:
                                    if isinstance(potential_json, list):
                                        detected_prompt_json = potential_json
                                    elif isinstance(potential_json, dict):
                                        detected_prompt_json = [potential_json]

                                    if detected_prompt_json:
                                        break
                                except Exception as e:
                                    logger.error(f"Error parsing detected JSON: {e}")
                                    if self._json_detector:
                                        self._json_detector.reset()
                                    yield f"[Error parsing tool JSON: {e}]"
                                    goto_next_while_iteration = True
                                    break
                        yield event
                else:
                    if isinstance(event, str):
                        current_turn_text += event
                        yield event
                    elif isinstance(event, list) and all(
                        isinstance(tc, ToolCallObject) for tc in event
                    ):
                        pending_tool_calls = event
                        assistant_message_for_api = {
                            "role": "assistant",
                            "content": current_turn_text if current_turn_text else None,
                            "tool_calls": [
                                {
                                    "id": tc.id,
                                    "type": tc.type,
                                    "function": {
                                        "name": tc.function.name,
                                        "arguments": tc.function.arguments,
                                    },
                                }
                                for tc in pending_tool_calls
                            ],
                        }
                        break
                    elif event == "__API_NOT_SUPPORT_TOOLS__":
                        logger.warning(
                            f"LLM {getattr(self._llm, 'model', '')} has no native tool support. Switching to prompt mode."
                        )
                        self.prompt_mode_flag = True
                        if self._tool_manager:
                            self._tool_manager.disable()
                        if self._json_detector:
                            self._json_detector.reset()
                        goto_next_while_iteration = True
                        break
            if goto_next_while_iteration:
                continue

            if detected_prompt_json:
                logger.info("Processing tools detected via prompt mode JSON.")
                self._add_message(current_turn_text, "assistant")

                parsed_tools = self._tool_executor.process_tool_from_prompt_json(
                    detected_prompt_json
                )
                if parsed_tools:
                    tool_results_for_llm = []
                    if not self._tool_executor:
                        logger.error(
                            "Prompt Tool interaction requested but ToolExecutor/MCPClient is not available."
                        )
                        yield "[Error: ToolExecutor/MCPClient not configured for prompt mode]"
                        continue

                    tool_executor_iterator = self._tool_executor.execute_tools(
                        tool_calls=parsed_tools,
                        caller_mode="Prompt",
                    )
                    try:
                        while True:
                            update = await anext(tool_executor_iterator)
                            if update.get("type") == "final_tool_results":
                                tool_results_for_llm = update.get("results", [])
                                break
                            else:
                                yield update
                    except StopAsyncIteration:
                        logger.warning(
                            "Prompt mode tool executor finished without final results marker."
                        )

                    if tool_results_for_llm:
                        result_strings = [
                            res.get("content", "Error: Malformed result")
                            for res in tool_results_for_llm
                        ]
                        combined_results_str = "\n".join(result_strings)
                        messages.append(
                            {"role": "user", "content": combined_results_str}
                        )
                continue

            elif pending_tool_calls and assistant_message_for_api:
                messages.append(assistant_message_for_api)
                if current_turn_text:
                    self._add_message(current_turn_text, "assistant")

                tool_results_for_llm = []
                if not self._tool_executor:
                    logger.error(
                        "OpenAI Tool interaction requested but ToolExecutor/MCPClient is not available."
                    )
                    yield "[Error: ToolExecutor/MCPClient not configured for OpenAI mode]"
                    continue

                tool_executor_iterator = self._tool_executor.execute_tools(
                    tool_calls=pending_tool_calls,
                    caller_mode="OpenAI",
                )
                try:
                    while True:
                        update = await anext(tool_executor_iterator)
                        if update.get("type") == "final_tool_results":
                            tool_results_for_llm = update.get("results", [])
                            break
                        else:
                            yield update
                except StopAsyncIteration:
                    logger.warning(
                        "OpenAI tool executor finished without final results marker."
                    )

                if tool_results_for_llm:
                    messages.extend(tool_results_for_llm)
                continue

            else:
                if current_turn_text:
                    self._add_message(current_turn_text, "assistant")
                return

    def _chat_function_factory(
        self,
    ) -> Callable[[BatchInput], AsyncIterator[Union[SentenceOutput, Dict[str, Any]]]]:
        """Create the chat pipeline function."""

        @tts_filter(self._tts_preprocessor_config)
        @display_processor()
        @actions_extractor(self._live2d_model)
        @sentence_divider(
            faster_first_response=self._faster_first_response,
            segment_method=self._segment_method,
            valid_tags=["think"],
        )
        async def chat_with_memory(
            input_data: BatchInput,
        ) -> AsyncIterator[Union[str, Dict[str, Any]]]:
            """Process chat with memory and tools."""
            self.reset_interrupt()
            self.prompt_mode_flag = False

            messages = self._to_messages(input_data)
            silent_on_empty = bool(
                input_data.metadata and input_data.metadata.get("proactive_speak")
            )
            tools = None
            tool_mode = None
            llm_supports_native_tools = False

            if self._use_mcpp and self._tool_manager:
                tools = None
                if isinstance(self._llm, ClaudeAsyncLLM):
                    tool_mode = "Claude"
                    tools = self._formatted_tools_claude
                    llm_supports_native_tools = True
                elif isinstance(self._llm, OpenAICompatibleAsyncLLM):
                    tool_mode = "OpenAI"
                    tools = self._formatted_tools_openai
                    llm_supports_native_tools = True
                else:
                    logger.warning(
                        f"LLM type {type(self._llm)} not explicitly handled for tool mode determination."
                    )

                if llm_supports_native_tools and not tools:
                    logger.warning(
                        f"No tools available/formatted for '{tool_mode}' mode, despite MCP being enabled."
                    )

            if self._uses_rikka_response_contract():
                runner = get_default_tool_runner()
                if runner.available_tools():
                    async for output in self._rikka_tool_interaction_loop(
                        messages,
                        runner,
                        silent_on_empty=silent_on_empty,
                    ):
                        yield output
                    return

            if self._use_mcpp and tool_mode == "Claude":
                logger.debug(
                    f"Starting Claude tool interaction loop with {len(tools)} tools."
                )
                async for output in self._claude_tool_interaction_loop(
                    messages, tools if tools else []
                ):
                    yield output
                return
            elif self._use_mcpp and tool_mode == "OpenAI":
                logger.debug(
                    f"Starting OpenAI tool interaction loop with {len(tools)} tools."
                )
                async for output in self._openai_tool_interaction_loop(
                    messages, tools if tools else []
                ):
                    yield output
                return
            else:
                logger.info("Starting simple chat completion.")
                system_prompt = (
                    self._rikka_turn_system(include_tools=False, runner=None)
                    if self._uses_rikka_response_contract()
                    else self._system
                )
                token_stream = self._llm.chat_completion(messages, system_prompt)
                complete_response = ""
                diagnostic_events: list[str] = []
                async for event in token_stream:
                    text_chunk = ""
                    if isinstance(event, dict) and event.get("type") == "text_delta":
                        text_chunk = event.get("text", "")
                    elif isinstance(event, dict) and event.get("type") == "raw_delta":
                        diagnostic_events.append(_llm_event_diagnostic_text(event))
                    elif isinstance(event, str):
                        text_chunk = event
                    elif isinstance(event, list):
                        diagnostic_events.append(_llm_event_diagnostic_text(event))
                    else:
                        diagnostic_events.append(_llm_event_diagnostic_text(event))
                        continue
                    if text_chunk and not self._uses_rikka_response_contract():
                        yield text_chunk
                    complete_response += text_chunk
                if not complete_response.strip() and diagnostic_events:
                    complete_response = "\n".join(
                        event for event in diagnostic_events if event
                    )
                if complete_response:
                    assistant_text = complete_response
                    if self._uses_rikka_response_contract():
                        validation_events: list[dict[str, Any]] = []
                        output = self._sentence_output_from_rikka_response(
                            complete_response,
                            silent_on_empty=silent_on_empty,
                            validation_events=validation_events,
                            attached_image_count=len(input_data.images or []),
                        )
                        for event in validation_events:
                            yield event
                        if output is None:
                            return
                        assistant_text = output.display_text.text
                        yield output
                    else:
                        yield assistant_text
                    self._add_message(assistant_text, "assistant")

        return chat_with_memory

    async def chat(
        self,
        input_data: BatchInput,
    ) -> AsyncIterator[Union[SentenceOutput, Dict[str, Any]]]:
        """Run chat pipeline."""
        chat_func_decorated = self._chat_function_factory()
        async for output in chat_func_decorated(input_data):
            yield output

    def reset_interrupt(self) -> None:
        """Reset interrupt flag."""
        self._interrupt_handled = False

    def start_group_conversation(
        self, human_name: str, ai_participants: List[str]
    ) -> None:
        """Start a group conversation."""
        if not self._tool_prompts:
            logger.warning("Tool prompts dictionary is not set.")
            return

        other_ais = ", ".join(name for name in ai_participants)
        prompt_name = self._tool_prompts.get("group_conversation_prompt", "")

        if not prompt_name:
            logger.warning("No group conversation prompt name found.")
            return

        try:
            group_context = prompt_loader.load_util(prompt_name).format(
                human_name=human_name, other_ais=other_ais
            )
            self._memory.append({"role": "user", "content": group_context})
        except FileNotFoundError:
            logger.error(f"Group conversation prompt file not found: {prompt_name}")
        except KeyError as e:
            logger.error(f"Missing formatting key in group conversation prompt: {e}")
        except Exception as e:
            logger.error(f"Failed to load group conversation prompt: {e}")

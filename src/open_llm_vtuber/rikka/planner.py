"""Async structured response planner for Rikka Live."""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any

from loguru import logger

from ..agent.stateless_llm_factory import LLMFactory
from .core import RikkaValidationResult, plan_rikka_response
from .identity import identity_prompt_block
from .memory import MemoryStore
from .persona import build_rikka_system_prompt
from .settings import get_default_settings_store
from .schemas import LiveEvent


DEFAULT_PLANNER_TIMEOUT_SECONDS = 120.0
DEFAULT_PLANNER_FAILURE_COOLDOWN_SECONDS = 30.0
LLM_PROVIDER_ERROR_PREFIXES = (
    "Error calling the chat endpoint:",
    "Error calling the responses endpoint:",
)
LLM_PROVIDER_ERROR_TOKENS = {"__API_NOT_SUPPORT_TOOLS__"}


class RikkaPlannerProviderError(RuntimeError):
    """Raised when the LLM adapter reports a provider/API failure as text."""


class RikkaStructuredPlanner:
    """Plan validated Rikka responses with an LLM and deterministic fallback."""

    def __init__(
        self,
        context: Any | None = None,
        memory_store: MemoryStore | None = None,
        llm: Any | None = None,
        system_prompt: str | None = None,
        provider_name: str | None = None,
        model_name: str | None = None,
        timeout_seconds: float = DEFAULT_PLANNER_TIMEOUT_SECONDS,
        failure_cooldown_seconds: float = DEFAULT_PLANNER_FAILURE_COOLDOWN_SECONDS,
    ):
        self._context = context
        self._memory_store = memory_store
        self._direct_llm = llm
        self._system_prompt = system_prompt
        self._provider_name = provider_name
        self._model_name = model_name
        self._timeout_seconds = timeout_seconds
        self._failure_cooldown_seconds = failure_cooldown_seconds
        self._cached_llm: Any | None = None
        self._cached_signature: tuple[Any, ...] | None = None
        self._disabled_until = 0.0

        self._last_mode = "fallback"
        self._last_available = False
        self._last_error = ""
        self._last_error_kind = ""
        self._last_failure_error = ""
        self._last_failure_kind = ""
        self._last_latency_ms: int | None = None
        self._last_validation_ok: bool | None = None

    def status(self) -> dict[str, Any]:
        """Return privacy-safe planner status for health and console UI."""
        provider, model, _ = self._resolve_config_snapshot()
        return {
            "mode": self._last_mode,
            "available": self._last_available or self._has_configured_llm(),
            "provider": self._provider_name or provider,
            "model": self._model_name or model,
            "timeout_seconds": self._timeout_seconds,
            "failure_cooldown_seconds": self._failure_cooldown_seconds,
            "retry_after_ms": self._retry_after_ms(),
            "last_error": self._last_error,
            "last_error_kind": self._last_error_kind,
            "last_latency_ms": self._last_latency_ms,
            "last_validation_ok": self._last_validation_ok,
        }

    def set_context(self, context: Any | None) -> None:
        """Point the planner at the latest service context without losing status."""
        if context is self._context:
            return
        self._context = context
        self.clear_llm_cache()

    def clear_llm_cache(self) -> None:
        """Drop cached planner LLM so updated runtime config is used next turn."""
        self._cached_llm = None
        self._cached_signature = None

    async def plan(
        self,
        event: LiveEvent,
        candidate_response: Any | None = None,
    ) -> RikkaValidationResult:
        """Plan a response for a normalized event and always return validation output."""
        started_at = time.perf_counter()
        self._last_error = ""
        self._last_error_kind = ""

        if candidate_response is not None:
            result = plan_rikka_response(event, candidate_response=candidate_response)
            self._record_result(
                "candidate_response" if result.ok else "fallback",
                result,
                started_at,
            )
            return result

        cooldown_remaining = self._cooldown_remaining_seconds()
        if cooldown_remaining > 0:
            previous = ""
            if self._last_failure_error:
                previous = (
                    f" after {self._last_failure_kind or 'failure'}: "
                    f"{self._last_failure_error}"
                )
            self._last_error = f"planner in fallback cooldown for {cooldown_remaining:.1f}s{previous}"
            self._last_error_kind = "cooldown"
            result = self._fallback_error_result(event, self._last_error)
            self._record_result("fallback", result, started_at)
            return result

        llm = self._get_llm()
        if llm is None:
            if self._last_error:
                result = self._fallback_error_result(event, self._last_error)
            else:
                result = plan_rikka_response(event)
            self._record_result("fallback", result, started_at)
            return result

        try:
            raw_response = await asyncio.wait_for(
                self._collect_llm_response(llm, event),
                timeout=self._timeout_seconds,
            )
            result = plan_rikka_response(event, candidate_response=raw_response)
            if result.ok:
                self._record_result("llm_structured", result, started_at)
                return result

            self._last_error = "; ".join(result.errors)
            self._last_error_kind = "validation"
            logger.warning(
                f"Rikka structured planner output validation failed: {self._last_error}"
            )
            self._record_result("fallback", result, started_at)
            return result
        except RikkaPlannerProviderError as exc:
            self._last_error = str(exc) or exc.__class__.__name__
            self._last_error_kind = "provider_error"
            self._remember_failure()
            self._open_failure_cooldown()
            logger.error(f"Rikka structured planner provider error: {self._last_error}")
        except asyncio.TimeoutError:
            self._last_error = self._format_timeout_error(llm)
            self._last_error_kind = "timeout"
            self._remember_failure()
            self._open_failure_cooldown()
            logger.error(self._last_error)
        except Exception as exc:
            self._last_error = str(exc) or exc.__class__.__name__
            self._last_error_kind = "exception"
            self._remember_failure()
            self._open_failure_cooldown()
            logger.exception(f"Rikka structured planner failed: {exc}")

        result = self._fallback_error_result(event, self._last_error)
        self._record_result("fallback", result, started_at)
        return result

    def _record_result(
        self,
        mode: str,
        result: RikkaValidationResult,
        started_at: float,
    ) -> None:
        self._last_mode = mode
        self._last_latency_ms = int((time.perf_counter() - started_at) * 1000)
        self._last_validation_ok = result.ok
        self._last_available = self._has_configured_llm()
        if result.errors and not self._last_error:
            self._last_error = "; ".join(result.errors)
            self._last_error_kind = "validation"

    async def _collect_llm_response(self, llm: Any, event: LiveEvent) -> str:
        messages = [
            {
                "role": "user",
                "content": self._build_user_prompt(event),
            }
        ]
        output: list[str] = []
        async for chunk in llm.chat_completion(
            messages,
            system=self._resolve_system_prompt(),
        ):
            if isinstance(chunk, str):
                if self._is_provider_error_text(chunk):
                    raise RikkaPlannerProviderError(chunk.strip())
                output.append(chunk)
            elif isinstance(chunk, dict) and chunk.get("type") == "text_delta":
                output.append(str(chunk.get("text", "")))
        response = "".join(output).strip()
        if not response:
            raise RikkaPlannerProviderError("LLM returned an empty response")
        return response

    @staticmethod
    def _is_provider_error_text(text: str) -> bool:
        value = text.strip()
        return value in LLM_PROVIDER_ERROR_TOKENS or any(
            value.startswith(prefix) for prefix in LLM_PROVIDER_ERROR_PREFIXES
        )

    @staticmethod
    def _fallback_error_result(event: LiveEvent, message: str) -> RikkaValidationResult:
        fallback = plan_rikka_response(event)
        return RikkaValidationResult(
            ok=False,
            response=fallback.response,
            errors=[message or "planner failed"],
        )

    def _build_user_prompt(self, event: LiveEvent) -> str:
        memory_summary = self._memory_summary()
        event_json = json.dumps(
            event.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
        )
        return (
            "请根据这个规范化 LiveEvent 生成一个 RikkaResponse JSON 对象。\n"
            "只输出 JSON，不要 Markdown，不要解释，不要内部思考。\n\n"
            f"轻量记忆摘要：\n{memory_summary or '无'}\n\n"
            f"LiveEvent：\n{event_json}\n\n"
            "输出字段必须包含 spoken_text, subtitle_text, emotion, motion, gaze, "
            "priority, interruptible, reason_code；memory_writes 可为空数组。"
        )

    def _memory_summary(self) -> str:
        if not self._memory_store:
            return ""
        try:
            return self._memory_store.summary()
        except Exception as exc:
            logger.warning(f"Failed to summarize Rikka memory for planner: {exc}")
            return ""

    def _open_failure_cooldown(self) -> None:
        if self._failure_cooldown_seconds <= 0:
            return
        self._disabled_until = time.monotonic() + self._failure_cooldown_seconds

    def _remember_failure(self) -> None:
        self._last_failure_error = self._last_error
        self._last_failure_kind = self._last_error_kind

    def _format_timeout_error(self, llm: Any) -> str:
        context = self._llm_context_for_error(llm)
        return (
            f"planner timed out after {self._timeout_seconds:.1f}s waiting for "
            f"LLM response. Context: {context}"
        )

    def _llm_context_for_error(self, llm: Any) -> str:
        provider, model, config = self._resolve_config_snapshot()
        base_url = getattr(llm, "base_url", None) or config.get("base_url")
        model_name = getattr(llm, "model", None) or self._model_name or model
        api_mode = getattr(llm, "api_mode", None) or config.get("api_mode")
        provider_name = self._provider_name or provider or llm.__class__.__name__
        pieces = [
            f"provider={provider_name}",
            f"model={model_name or 'unknown'}",
        ]
        if base_url:
            pieces.append(f"base_url={base_url}")
        if api_mode:
            pieces.append(f"api_mode={api_mode}")
        return ", ".join(pieces)

    def _cooldown_remaining_seconds(self) -> float:
        return max(0.0, self._disabled_until - time.monotonic())

    def _retry_after_ms(self) -> int:
        return int(self._cooldown_remaining_seconds() * 1000)

    def _resolve_system_prompt(self) -> str:
        identity_block = self._identity_prompt_block()
        if self._system_prompt:
            return self._append_identity_block(self._system_prompt, identity_block)

        context_prompt = getattr(self._context, "system_prompt", None)
        if context_prompt:
            return self._append_identity_block(context_prompt, identity_block)

        try:
            live2d_model = getattr(self._context, "live2d_model", None)
            return self._append_identity_block(
                build_rikka_system_prompt(
                    getattr(live2d_model, "model_info", None)
                ),
                identity_block,
            )
        except FileNotFoundError:
            return self._append_identity_block(
                "你是弥生月六花的陪播响应规划器。最终只输出一个满足 "
                "RikkaResponse 协议的 JSON 对象。",
                identity_block,
            )

    @staticmethod
    def _append_identity_block(system_prompt: str, identity_block: str) -> str:
        if not identity_block:
            return system_prompt
        return f"{system_prompt}\n\n{identity_block}"

    def _identity_prompt_block(self) -> str:
        try:
            return identity_prompt_block(get_default_settings_store().snapshot().identity)
        except Exception as exc:
            logger.warning(f"Failed to build Rikka identity prompt block: {exc}")
            return identity_prompt_block()

    def _get_llm(self) -> Any | None:
        if self._direct_llm is not None:
            return self._direct_llm

        agent_llm = getattr(getattr(self._context, "agent_engine", None), "_llm", None)
        if self._is_usable_llm(agent_llm):
            return agent_llm

        provider, model, config = self._resolve_config_snapshot()
        if not provider or not config:
            return None

        signature = (
            provider,
            model,
            config.get("base_url"),
            config.get("model_path"),
            config.get("api_mode"),
            config.get("temperature"),
        )
        if self._cached_llm is not None and self._cached_signature == signature:
            return self._cached_llm

        try:
            llm_config = dict(config)
            llm_config.pop("interrupt_method", None)
            self._cached_llm = LLMFactory.create_llm(provider, **llm_config)
            self._cached_signature = signature
            return self._cached_llm
        except Exception as exc:
            self._last_error = str(exc)
            self._last_error_kind = "provider_init"
            self._remember_failure()
            logger.exception(f"Failed to initialize Rikka planner LLM: {exc}")
            return None

    def _has_configured_llm(self) -> bool:
        if self._direct_llm is not None:
            return True
        agent_llm = getattr(getattr(self._context, "agent_engine", None), "_llm", None)
        if self._is_usable_llm(agent_llm):
            return True
        _, _, config = self._resolve_config_snapshot()
        return bool(config)

    @staticmethod
    def _is_usable_llm(llm: Any) -> bool:
        return llm is not None and callable(getattr(llm, "chat_completion", None))

    def _resolve_config_snapshot(self) -> tuple[str | None, str | None, dict[str, Any]]:
        character_config = getattr(self._context, "character_config", None)
        agent_config = getattr(character_config, "agent_config", None)
        if not agent_config:
            return None, None, {}

        basic_agent = getattr(agent_config.agent_settings, "basic_memory_agent", None)
        provider = getattr(basic_agent, "llm_provider", None)
        if not provider:
            return None, None, {}

        llm_config_obj = getattr(agent_config.llm_configs, provider, None)
        if llm_config_obj is None:
            return provider, None, {}

        if hasattr(llm_config_obj, "model_dump"):
            config = llm_config_obj.model_dump()
        elif isinstance(llm_config_obj, dict):
            config = dict(llm_config_obj)
        else:
            config = {}
        model = config.get("model") or config.get("model_path")
        return provider, model, config

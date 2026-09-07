"""Microphone wake-word text gate for Rikka voice turns."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Literal

from .settings import AudioInteractionSettings


def _now_ms() -> int:
    return int(time.time() * 1000)


IGNORED_WAKE_CHARS_RE = re.compile(
    r"[\s，。！？、,.!?：:；;「」『』\"'`~\-_/\\…—]+|[嗯呃额啊哦喔诶欸唔]+"
)
MAX_WAKE_PREFIX_CHARS = 2
CJK_SPACED_CHAR_RE = re.compile(
    r"(?<=[\u3400-\u9fff\u3040-\u30ff])\s+(?=[\u3400-\u9fff\u3040-\u30ff])"
)


def _compact_text(text: str) -> str:
    return IGNORED_WAKE_CHARS_RE.sub("", text).lower()


def normalize_asr_text(text: str) -> str:
    """Repair common streaming ASR spacing without changing non-CJK word gaps."""
    normalized = CJK_SPACED_CHAR_RE.sub("", text or "")
    return re.sub(r"\s+", " ", normalized).strip()


def _compact_with_index_map(text: str) -> tuple[str, list[int]]:
    chars: list[str] = []
    indexes: list[int] = []
    for index, char in enumerate(text):
        if IGNORED_WAKE_CHARS_RE.fullmatch(char):
            continue
        chars.append(char.lower())
        indexes.append(index)
    return "".join(chars), indexes


@dataclass(frozen=True)
class WakePhraseMatch:
    """Matched wake phrase plus the transcript remainder."""

    remainder: str
    matched_phrase: str
    match_kind: Literal["canonical", "asr_confusion"]


@dataclass(frozen=True)
class WakeGateDecision:
    """Decision returned after evaluating a transcribed microphone turn."""

    should_process: bool
    text: str
    woke: bool
    active: bool
    reason: str
    active_until_ms: int | None = None
    match_kind: Literal["canonical", "asr_confusion"] | None = None
    matched_phrase: str | None = None

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "should_process": self.should_process,
            "text": self.text,
            "woke": self.woke,
            "active": self.active,
            "reason": self.reason,
            "active_until_ms": self.active_until_ms,
        }
        if self.match_kind is not None:
            payload["match_kind"] = self.match_kind
        if self.matched_phrase is not None:
            payload["matched_phrase"] = self.matched_phrase
        return payload

    def to_flow_metadata(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "active": self.active,
            "woke": self.woke,
            "should_process": self.should_process,
            "reason": self.reason,
        }
        if self.match_kind is not None:
            payload["match_kind"] = self.match_kind
        if self.matched_phrase is not None:
            payload["matched_phrase"] = self.matched_phrase
        return payload


class WakeGate:
    """Stateful ASR text gate keyed by WebSocket client id."""

    def __init__(self, clock_ms=_now_ms):
        self._clock_ms = clock_ms
        self._active_until_by_client: dict[str, int] = {}

    def reset(self, client_uid: str | None = None) -> None:
        if client_uid is None:
            self._active_until_by_client.clear()
            return
        self._active_until_by_client.pop(client_uid, None)

    def activate(self, client_uid: str, duration_ms: int) -> int:
        """Start or extend the follow-up window after a response finishes."""
        active_until = self._clock_ms() + duration_ms
        self._active_until_by_client[client_uid] = active_until
        return active_until

    def status(self, client_uid: str | None = None) -> dict[str, object]:
        now = self._clock_ms()
        if client_uid is None:
            active_clients = [
                uid
                for uid, active_until in self._active_until_by_client.items()
                if active_until > now
            ]
            return {"active_clients": active_clients, "now_ms": now}
        active_until = self._active_until_by_client.get(client_uid, 0)
        return {
            "active": active_until > now,
            "active_until_ms": active_until if active_until > now else None,
            "now_ms": now,
        }

    def evaluate(
        self,
        client_uid: str,
        transcript: str,
        settings: AudioInteractionSettings,
    ) -> WakeGateDecision:
        text = normalize_asr_text(transcript)
        if not settings.wake_gate_enabled:
            return WakeGateDecision(
                should_process=bool(text),
                text=text,
                woke=False,
                active=False,
                reason="wake_gate_disabled",
            )
        if not settings.mic_conversation_enabled:
            return WakeGateDecision(
                should_process=False,
                text="",
                woke=False,
                active=False,
                reason="mic_conversation_disabled",
            )

        now = self._clock_ms()
        active_until = self._active_until_by_client.get(client_uid, 0)
        if active_until > now:
            next_until = now + settings.wake_active_window_ms
            self._active_until_by_client[client_uid] = next_until
            return WakeGateDecision(
                should_process=bool(text),
                text=text,
                woke=False,
                active=True,
                reason="wake_window_active",
                active_until_ms=next_until,
            )

        wake_match = self._match_configured_wake(text, settings)
        if wake_match is None:
            return WakeGateDecision(
                should_process=False,
                text="",
                woke=False,
                active=False,
                reason="wake_phrase_missing",
            )

        remainder = wake_match.remainder.strip()
        if not remainder:
            next_until = self.activate(client_uid, settings.wake_active_window_ms)
            return WakeGateDecision(
                should_process=False,
                text="",
                woke=True,
                active=True,
                reason="wake_only",
                active_until_ms=next_until,
                match_kind=wake_match.match_kind,
                matched_phrase=wake_match.matched_phrase,
            )
        return WakeGateDecision(
            should_process=True,
            text=remainder,
            woke=True,
            active=False,
            reason="wake_phrase_matched",
            active_until_ms=None,
            match_kind=wake_match.match_kind,
            matched_phrase=wake_match.matched_phrase,
        )

    def preview(
        self,
        transcript: str,
        settings: AudioInteractionSettings,
    ) -> WakeGateDecision:
        """Evaluate partial ASR text without mutating wake-window state."""
        text = normalize_asr_text(transcript)
        if not settings.wake_gate_enabled:
            return WakeGateDecision(
                should_process=False,
                text=text,
                woke=False,
                active=False,
                reason="wake_gate_disabled",
            )
        if not settings.mic_conversation_enabled:
            return WakeGateDecision(
                should_process=False,
                text="",
                woke=False,
                active=False,
                reason="mic_conversation_disabled",
            )
        wake_match = self._match_configured_wake(text, settings)
        if wake_match is None:
            return WakeGateDecision(
                should_process=False,
                text="",
                woke=False,
                active=False,
                reason="wake_phrase_missing",
            )
        remainder = wake_match.remainder.strip()
        if not remainder:
            return WakeGateDecision(
                should_process=False,
                text="",
                woke=True,
                active=True,
                reason="wake_only",
                match_kind=wake_match.match_kind,
                matched_phrase=wake_match.matched_phrase,
            )
        return WakeGateDecision(
            should_process=False,
            text=remainder,
            woke=True,
            active=False,
            reason="wake_phrase_matched",
            match_kind=wake_match.match_kind,
            matched_phrase=wake_match.matched_phrase,
        )

    def _match_configured_wake(
        self,
        text: str,
        settings: AudioInteractionSettings,
    ) -> WakePhraseMatch | None:
        return self._match_wake_phrase(
            text,
            settings.wake_phrases,
            "canonical",
        ) or self._match_wake_phrase(
            text,
            settings.wake_asr_confusions,
            "asr_confusion",
        )

    def _match_wake_phrase(
        self,
        text: str,
        wake_phrases: list[str],
        match_kind: Literal["canonical", "asr_confusion"],
    ) -> WakePhraseMatch | None:
        compact, index_map = _compact_with_index_map(text)
        for phrase in wake_phrases:
            wake = _compact_text(phrase)
            if not wake:
                continue
            index = compact.find(wake)
            if index < 0 or index > MAX_WAKE_PREFIX_CHARS:
                continue
            end_index = index + len(wake) - 1
            if index >= len(index_map) or end_index >= len(index_map):
                return WakePhraseMatch(
                    remainder=text,
                    matched_phrase=phrase,
                    match_kind=match_kind,
                )
            start_original = index_map[index]
            end_original = index_map[end_index] + 1
            return WakePhraseMatch(
                remainder=normalize_asr_text(
                    (text[:start_original] + text[end_original:]).strip(
                        " ，。！？,.!?:："
                    )
                ),
                matched_phrase=phrase,
                match_kind=match_kind,
            )
        return None


_DEFAULT_WAKE_GATE: WakeGate | None = None


def get_default_wake_gate() -> WakeGate:
    global _DEFAULT_WAKE_GATE
    if _DEFAULT_WAKE_GATE is None:
        _DEFAULT_WAKE_GATE = WakeGate()
    return _DEFAULT_WAKE_GATE

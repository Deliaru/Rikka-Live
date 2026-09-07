"""Privacy-safe flow telemetry for the Rikka debug console."""

from __future__ import annotations

import time
from collections import OrderedDict
from collections.abc import Callable
from typing import Any


FLOW_STAGES: tuple[str, ...] = (
    "event",
    "normalize",
    "planner",
    "validate",
    "memory",
    "delivery",
    "tts",
    "live2d",
    "actions",
    "complete",
)


def _now_ms() -> int:
    return int(time.time() * 1000)


def _short_text(value: Any, limit: int = 180) -> str:
    text = str(value or "")
    return text if len(text) <= limit else f"{text[: limit - 1]}..."


class RikkaFlowMonitor:
    """Tracks the current co-streaming pipeline without storing raw media."""

    def __init__(self, limit: int = 80):
        self.limit = limit
        self._flows: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self._frontend_actions: list[dict[str, Any]] = []
        self._event_sink: Callable[[dict[str, Any]], None] | None = None

    def set_event_sink(self, sink: Callable[[dict[str, Any]], None] | None) -> None:
        """Attach a privacy-safe event history sink for every flow start."""
        self._event_sink = sink

    def start(self, flow_id: str, event: dict[str, Any]) -> dict[str, Any]:
        started_at_ms = _now_ms()
        event_source = event.get("source") or "unknown"
        event_type = event.get("type") or "unknown"
        event_text = _short_text(event.get("text"))
        actor_name = _short_text((event.get("actor") or {}).get("display_name"))
        flow = {
            "id": flow_id,
            "source": event_source,
            "event_type": event_type,
            "event_text": event_text,
            "actor": actor_name,
            "started_at_ms": started_at_ms,
            "updated_at_ms": started_at_ms,
            "current_stage": "event",
            "status": "running",
            "stages": {
                stage: {
                    "status": "pending",
                    "at_ms": None,
                    "duration_ms": None,
                    "elapsed_ms": None,
                    "detail": "",
                }
                for stage in FLOW_STAGES
            },
            "timeline": [],
        }
        self._flows[flow_id] = flow
        self._flows.move_to_end(flow_id)
        self._trim()
        self._emit_event_start(flow_id, event, started_at_ms)
        self.record(flow_id, "event", "ok", detail="event received")
        return self.summary(flow_id)

    def _emit_event_start(
        self,
        flow_id: str,
        event: dict[str, Any],
        started_at_ms: int,
    ) -> None:
        if self._event_sink is None:
            return
        try:
            self._event_sink(
                {
                    "id": flow_id,
                    "type": event.get("type") or "unknown",
                    "source": event.get("source") or "unknown",
                    "text": _short_text(event.get("text")),
                    "created_at_ms": started_at_ms,
                    "actor": _safe_metadata(event.get("actor") or {}),
                    "payload": {
                        "flow_id": flow_id,
                        "flow_source": event.get("source") or "unknown",
                    },
                    "privacy": {"contains_raw_media": False},
                }
            )
        except Exception:
            return

    def record(
        self,
        flow_id: str | None,
        stage: str,
        status: str = "ok",
        *,
        detail: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if not flow_id:
            return
        flow = self._flows.get(flow_id)
        if not flow:
            flow = self.start(
                flow_id,
                {
                    "id": flow_id,
                    "source": "unknown",
                    "type": "unknown",
                    "text": "",
                },
            )
            flow = self._flows.get(flow_id)
        if not flow:
            return

        now = _now_ms()
        started_at_ms = int(flow.get("started_at_ms") or now)
        previous_timeline = flow.get("timeline") or []
        previous_at_ms = (
            int(previous_timeline[-1].get("at_ms") or started_at_ms)
            if previous_timeline
            else started_at_ms
        )
        stage_data = flow["stages"].setdefault(
            stage,
            {
                "status": "pending",
                "at_ms": None,
                "duration_ms": None,
                "elapsed_ms": None,
                "detail": "",
            },
        )
        stage_started_at_ms = int(stage_data.get("at_ms") or previous_at_ms)
        duration_ms = max(0, now - stage_started_at_ms)
        elapsed_ms = max(0, now - started_at_ms)
        stage_data.update(
            {
                "status": status,
                "at_ms": stage_started_at_ms,
                "updated_at_ms": now,
                "duration_ms": duration_ms,
                "elapsed_ms": elapsed_ms,
                "detail": _short_text(detail),
            }
        )
        if metadata:
            stage_data["metadata"] = _safe_metadata(metadata)

        already_complete = flow.get("status") == "complete"
        already_error = flow.get("status") == "error"
        if status == "error" or (not already_complete and not already_error):
            flow["current_stage"] = stage
        flow["updated_at_ms"] = now
        if status == "error" or already_error:
            flow["status"] = "error"
        elif stage == "complete" or already_complete:
            flow["status"] = "complete"
        else:
            flow["status"] = "running"
        flow["timeline"].append(
            {
                "stage": stage,
                "status": status,
                "at_ms": now,
                "duration_ms": duration_ms,
                "elapsed_ms": elapsed_ms,
                "detail": _short_text(detail),
                "metadata": _safe_metadata(metadata or {}),
            }
        )
        flow["timeline"] = flow["timeline"][-40:]
        self._flows.move_to_end(flow_id)

    def record_frontend_action(self, payload: dict[str, Any]) -> dict[str, Any]:
        flow_id = str(payload.get("flow_id") or payload.get("event_id") or "")
        inferred_flow_id = False
        if not flow_id:
            flow_id = self._latest_flow_id()
            inferred_flow_id = bool(flow_id)
        metadata = _safe_metadata(payload.get("metadata") or {})
        if inferred_flow_id:
            metadata["inferred_flow_id"] = True
        action = {
            "flow_id": flow_id,
            "kind": _short_text(payload.get("kind") or "action"),
            "status": _short_text(payload.get("status") or "ok"),
            "detail": _short_text(payload.get("detail")),
            "metadata": metadata,
            "at_ms": _now_ms(),
        }
        self._frontend_actions.append(action)
        self._frontend_actions = self._frontend_actions[-80:]

        if flow_id:
            status = "error" if action["status"] == "error" else "ok"
            self.record(
                flow_id,
                "actions",
                status,
                detail=f"{action['kind']}: {action['detail'] or action['status']}",
                metadata=action["metadata"],
            )
            if action["kind"] in {"motion", "gaze"} and action["status"] == "ok":
                self.record(flow_id, "live2d", "ok", detail="frontend action applied")
        return action

    def summary(self, flow_id: str | None) -> dict[str, Any]:
        if not flow_id or flow_id not in self._flows:
            return {}
        flow = self._flows[flow_id]
        return {
            "id": flow["id"],
            "source": flow["source"],
            "event_type": flow["event_type"],
            "current_stage": flow["current_stage"],
            "status": flow["status"],
            "updated_at_ms": flow["updated_at_ms"],
        }

    def snapshot(self) -> dict[str, Any]:
        flows = list(reversed(list(self._flows.values())))
        active = flows[0] if flows else None
        return {
            "stages": list(FLOW_STAGES),
            "active": active,
            "flows": flows[:20],
            "frontend_actions": list(reversed(self._frontend_actions[-20:])),
        }

    def _trim(self) -> None:
        while len(self._flows) > self.limit:
            self._flows.popitem(last=False)

    def _latest_flow_id(self) -> str:
        if not self._flows:
            return ""
        return next(reversed(self._flows))


def _safe_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    safe: dict[str, Any] = {}
    for key, value in metadata.items():
        key_text = str(key)
        if any(secret in key_text.lower() for secret in ("key", "token", "sessdata")):
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            string_limit = 4000 if key_text == "raw_response_text" else 240
            safe[key_text] = (
                _short_text(value, string_limit) if isinstance(value, str) else value
            )
        elif isinstance(value, list):
            safe[key_text] = [
                _safe_metadata(item)
                if isinstance(item, dict)
                else _short_text(item, 80)
                for item in value[:12]
            ]
        elif isinstance(value, dict):
            safe[key_text] = _safe_metadata(value)
        else:
            safe[key_text] = _short_text(value)
    return safe

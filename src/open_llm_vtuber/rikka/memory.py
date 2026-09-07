"""Lightweight editable memory for the first Rikka Live milestone."""

from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path
from typing import Any

from .schemas import MemoryKind, MemoryWrite
from .text_safety import clean_public_text

DEFAULT_MEMORY_PATH = Path("cache") / "rikka_memory.json"
logger = logging.getLogger(__name__)


def _now_ms() -> int:
    return int(time.time() * 1000)


def _normalize_key(key: str) -> str:
    return re.sub(r"\s+", " ", clean_public_text(key).casefold()).strip()


class MemoryStore:
    """JSON-backed memory store for small, user-editable facts."""

    def __init__(self, path: str | Path = DEFAULT_MEMORY_PATH, settings_store=None):
        self.path = Path(path)
        self.settings_store = settings_store
        self._data = self._load()

    def _empty(self) -> dict[str, dict[str, dict[str, Any]]]:
        return {
            "viewer_note": {},
            "stream_summary": {},
            "joke": {},
            "preference": {},
            "blocked_topic": {},
        }

    def _load(self) -> dict[str, dict[str, dict[str, Any]]]:
        if not self.path.exists():
            return self._empty()

        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning(f"Failed to read Rikka memory store: {exc}")
            return self._empty()

        data = self._empty()
        migrated = False
        for kind in data:
            entries = raw.get(kind, {})
            if isinstance(entries, dict):
                for key, value in entries.items():
                    clean_key = _normalize_key(key)
                    if not clean_key or not isinstance(value, dict):
                        continue
                    item = dict(value)
                    item["kind"] = item.get("kind") or kind
                    item["key"] = clean_public_text(str(item.get("key") or key))
                    item["value"] = clean_public_text(str(item.get("value") or ""))
                    try:
                        item["updated_at_ms"] = int(item.get("updated_at_ms") or 0)
                    except (TypeError, ValueError):
                        item["updated_at_ms"] = 0
                    existing = data[kind].get(clean_key)
                    if (
                        existing is None
                        or item["updated_at_ms"] >= existing.get("updated_at_ms", 0)
                    ):
                        data[kind][clean_key] = item
                    migrated = migrated or clean_key != key or item != value
        if migrated:
            self._data = data
            self._save()
        return data

    def _memory_settings(self):
        if self.settings_store is not None:
            return self.settings_store.snapshot().memory
        from .settings import get_default_settings_store

        return get_default_settings_store().snapshot().memory

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def dump(self) -> dict[str, dict[str, dict[str, Any]]]:
        return self._data

    def summary(self, limit_per_kind: int | None = None) -> str:
        if limit_per_kind is None:
            limit_per_kind = self._memory_settings().summary_per_kind
        lines: list[str] = []
        for kind, entries in self._data.items():
            recent_items = sorted(
                entries.items(),
                key=lambda entry: int(entry[1].get("updated_at_ms") or 0),
                reverse=True,
            )
            for key, item in recent_items[:limit_per_kind]:
                value = clean_public_text(item.get("value", ""))
                if value:
                    lines.append(f"{kind}:{key}={value}")
        return "\n".join(lines)

    def _trim_kind(self, kind: str) -> None:
        cap = self._memory_settings().per_kind_cap
        entries = self._data[kind]
        while len(entries) > cap:
            oldest_key = min(
                entries,
                key=lambda key: int(entries[key].get("updated_at_ms") or 0),
            )
            entries.pop(oldest_key, None)

    def upsert(self, write: MemoryWrite | dict[str, Any]) -> dict[str, Any]:
        memory_write = (
            write if isinstance(write, MemoryWrite) else MemoryWrite.model_validate(write)
        )
        clean_key = clean_public_text(memory_write.key)
        normalized_key = _normalize_key(memory_write.key)
        item = {
            "kind": memory_write.kind,
            "key": clean_key,
            "value": memory_write.value,
            "updated_at_ms": _now_ms(),
        }
        self._data[memory_write.kind][normalized_key] = item
        self._trim_kind(memory_write.kind)
        self._save()
        return item

    def apply_writes(self, writes: list[MemoryWrite]) -> list[dict[str, Any]]:
        return [self.upsert(write) for write in writes]

    def delete(self, kind: MemoryKind, key: str) -> bool:
        clean_key = _normalize_key(key)
        existed = clean_key in self._data[kind]
        self._data[kind].pop(clean_key, None)
        self._save()
        return existed

    def reset(self) -> None:
        self._data = self._empty()
        self._save()


_DEFAULT_STORE: MemoryStore | None = None


def get_default_memory_store() -> MemoryStore:
    global _DEFAULT_STORE
    if _DEFAULT_STORE is None:
        _DEFAULT_STORE = MemoryStore()
    return _DEFAULT_STORE

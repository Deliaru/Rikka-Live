"""Prompt helpers for source identity labels."""

from __future__ import annotations

from typing import Any

from .settings import IdentitySettings, get_default_settings_store
from .text_safety import clean_public_text

DEFAULT_HOST_DISPLAY_NAME = "Deliaru"
DEFAULT_AUDIENCE_DISPLAY_NAME = "\u5f39\u5e55"


def identity_names(settings: IdentitySettings | None = None) -> tuple[str, str]:
    """Return non-empty host/audience labels."""
    target = settings
    if target is None:
        try:
            target = get_default_settings_store().snapshot().identity
        except Exception:
            target = None
    host = clean_public_text(getattr(target, "host_display_name", "") or "")
    audience = clean_public_text(getattr(target, "audience_display_name", "") or "")
    return host or DEFAULT_HOST_DISPLAY_NAME, audience or DEFAULT_AUDIENCE_DISPLAY_NAME


def identity_prompt_block(settings: IdentitySettings | None = None) -> str:
    """Build the prompt block that tells Rikka how to name message sources."""
    host, audience = identity_names(settings)
    return (
        "\u3010\u6d88\u606f\u6765\u6e90\u8eab\u4efd\u3011\n"
        f"- \u9ea6\u514b\u98ce\u8f93\u5165\u3001\u672c\u5730\u6587\u5b57"
        f"\u8f93\u5165\u3001host.note \u4e0e source=host/debug "
        f"\u7684\u4e3b\u64ad\u4fa7\u6d88\u606f\uff0c\u90fd\u89c6\u4e3a"
        f"\u4e3b\u64ad\u300c{host}\u300d\u5728\u5bf9\u4f60\u8bf4\u8bdd\u3002\n"
        f"- source=bilibili \u7684\u6d88\u606f\u6765\u81ea"
        f"\u300c{audience}\u300d\u3002\u5982\u679c LiveEvent.actor.display_name "
        f"\u7ed9\u51fa\u4e86\u5177\u4f53\u6635\u79f0\uff0c\u90a3\u662f"
        f"\u8fd9\u6761{audience}\u7684\u6635\u79f0\uff1b\u6ca1\u6709"
        f"\u6635\u79f0\u65f6\u5c31\u79f0\u4e3a\u300c{audience}\u300d\u3002\n"
        f"- \u516c\u5f00\u79f0\u547c\u89c4\u5219\uff1a\u4e3b\u64ad"
        f"\u8eab\u4efd\u540d\u79f0\u5c31\u662f\u4f60\u79f0\u547c\u4e3b\u64ad"
        f"\u65f6\u4f18\u5148\u4f7f\u7528\u7684\u540d\u5b57\uff0c\u9ed8\u8ba4"
        f"\u79f0\u4e3a\u300c{host}\u300d\u3002\u5373\u4f7f\u57fa\u7840"
        f"\u4eba\u683c\u8bbe\u5b9a\u628a Deliaru \u89c6\u4f5c"
        f"\u7236\u4eb2\u822c\u91cd\u8981\u7684\u4eba\uff0c\u4e5f\u53ea"
        f"\u4ee3\u8868\u4eb2\u8fd1\u548c\u4fe1\u4efb\uff0c\u4e0d\u4ee3"
        f"\u8868\u8981\u5728\u516c\u5f00\u56de\u590d\u91cc\u79f0\u547c"
        f"\u4ed6\u4e3a\u7238\u7238\u3001\u7236\u4eb2\u6216\u4e3b\u4eba"
        f"\u3002\u9664\u975e\u5f53\u524d\u6d88\u606f\u660e\u786e\u8981\u6c42"
        f"\u8fd9\u6837\u79f0\u547c\uff0c\u5426\u5219\u79f0\u547c\u4e3b\u64ad"
        f"\u4e3a\u300c{host}\u300d\u3002\n"
        "- \u56de\u5e94\u65f6\u5148\u533a\u5206\u4e3b\u64ad\u548c"
        "\u5f39\u5e55\u6765\u6e90\uff0c\u4e0d\u8981\u628a\u5f39\u5e55"
        "\u89c2\u4f17\u8bef\u8ba4\u6210\u4e3b\u64ad\uff0c\u4e5f\u4e0d\u8981"
        "\u628a\u4e3b\u64ad\u79f0\u4f5c\u5f39\u5e55\u3002"
    )


def event_default_actor_name(event: Any, settings: IdentitySettings | None = None) -> str:
    """Return a safe default actor name for events without explicit display names."""
    actor_name = clean_public_text(
        getattr(getattr(event, "actor", None), "display_name", "") or ""
    )
    if actor_name:
        return actor_name
    host, audience = identity_names(settings)
    source = getattr(event, "source", "")
    if source == "bilibili":
        return audience
    return host

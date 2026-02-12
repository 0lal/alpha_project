"""
Goal
----
وحدة استرجاع الحالة السابقة (state) لاستخدامات التحقق السياقي والتحليل الفوري.

Dependencies
------------
- hot cache (RAM/Redis)
- cold storage fallback
- validators/contextual
"""
from __future__ import annotations

from typing import Any


def fetch_previous_state(symbol: str, cache: dict[str, dict[str, Any]], default: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """إرجاع آخر حالة معروفة للرمز. يستخدم default إذا لم تتوفر حالة."""
    state = cache.get(symbol)
    if state is not None:
        return dict(state)
    return dict(default) if default is not None else None


def upsert_state(symbol: str, state: dict[str, Any], cache: dict[str, dict[str, Any]]) -> None:
    """تحديث الحالة اللحظية في الذاكرة بطريقة آمنة."""
    cache[symbol] = dict(state)

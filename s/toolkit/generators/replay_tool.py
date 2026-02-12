"""
Goal
----
أداة إعادة بث تاريخي deterministic لتشغيل اختبارات regression.

Dependencies
------------
- audit logs
- storage schemas
- validators pipeline
"""
from __future__ import annotations

from typing import Iterable, Any


def replay(records: Iterable[dict[str, Any]], *, max_items: int | None = None) -> list[dict[str, Any]]:
    """إرجاع نسخة قابلة للإعادة من السجلات مع حد اختياري."""
    out: list[dict[str, Any]] = []
    for i, rec in enumerate(records):
        if max_items is not None and i >= max_items:
            break
        out.append(dict(rec))
    return out

"""
Goal
----
إثراء البيانات الموحّدة بمشتقات مفيدة لقرارات الذكاء والمخاطر.

Dependencies
------------
- mutators/sanitizer
- memory/state_fetcher
- feature store
"""
from __future__ import annotations

from typing import Any


def enrich_tick(payload: dict[str, Any]) -> dict[str, Any]:
    """إضافة mid/spread وإشارات اتجاهية بسيطة دون تعديل القيم الأصلية."""
    enriched = dict(payload)

    bid = payload.get("bid")
    ask = payload.get("ask")
    price = payload.get("price")

    if isinstance(bid, (int, float)) and isinstance(ask, (int, float)) and ask >= bid:
        enriched["mid"] = (bid + ask) / 2
        if isinstance(price, (int, float)) and price > 0:
            enriched["spread_bps"] = ((ask - bid) / price) * 10000

    if isinstance(price, (int, float)) and isinstance(enriched.get("mid"), (int, float)):
        enriched["micro_trend"] = "UP" if price >= enriched["mid"] else "DOWN"

    return enriched

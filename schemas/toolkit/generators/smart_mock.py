"""
Goal
----
توليد بيانات سوق وهمية ذكية لاختبارات validators والمخاطر.

Dependencies
------------
- storage/hot schemas
- intelligence validators
"""
from __future__ import annotations

import random


def mock_tick(symbol: str = "BTCUSDT", *, base: float = 100.0, jitter: float = 0.2) -> dict[str, float | str | int]:
    """توليد tick مع bid/ask/price وتوقيت بالمللي ثانية."""
    mid = base + random.uniform(-jitter, jitter)
    spread = max(0.01, random.uniform(0.01, 0.05))
    bid = mid - spread / 2
    ask = mid + spread / 2
    return {
        "symbol": symbol,
        "bid": round(bid, 6),
        "ask": round(ask, 6),
        "price": round(mid, 6),
        "quantity": round(random.uniform(0.1, 5.0), 6),
        "event_time_ms": 1700000000000,
    }

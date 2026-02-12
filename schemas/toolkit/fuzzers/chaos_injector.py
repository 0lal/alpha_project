"""
Goal
----
حقن اضطرابات متحكم بها في payload لاختبار مناعة المنظومة.

Dependencies
------------
- validators
- mutators
- test harness
"""
from __future__ import annotations

import random
from typing import Any


def inject_noise(payload: dict[str, Any], *, price_spike_pct: float = 0.0, invert_book: bool = False) -> dict[str, Any]:
    """إرجاع payload معدل يمثل سيناريو فوضى محدد."""
    out = dict(payload)
    if price_spike_pct and isinstance(out.get("price"), (int, float)):
        out["price"] = out["price"] * (1 + price_spike_pct / 100.0)
    if invert_book and isinstance(out.get("bid"), (int, float)) and isinstance(out.get("ask"), (int, float)):
        out["bid"], out["ask"] = out["ask"], out["bid"]
    out["_chaos"] = {
        "seed": random.randint(1, 1_000_000),
        "price_spike_pct": price_spike_pct,
        "invert_book": invert_book,
    }
    return out

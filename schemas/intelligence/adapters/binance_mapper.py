"""
Goal
----
تحويل رسائل Binance الخام إلى نموذج قياسي موحّد داخل Bio-Schema.

Dependencies
------------
- market ingestion connectors
- validators pipeline
- transport/storage schemas
"""
from __future__ import annotations

from typing import Any


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def map_binance_tick(payload: dict[str, Any]) -> dict[str, Any]:
    """تحويل tick إلى بنية موحدة مع حقول زمن/سبريد جاهزة للتحقق."""
    bid = _to_float(payload.get("b"))
    ask = _to_float(payload.get("a"))
    last = _to_float(payload.get("c"))
    spread_bps = ((ask - bid) / max(last, 1e-9)) * 10000 if ask >= bid and last > 0 else 0.0

    return {
        "source": "binance",
        "symbol": payload.get("s"),
        "bid": bid,
        "ask": ask,
        "price": last,
        "quantity": _to_float(payload.get("q")),
        "event_time_ms": int(payload.get("E", 0) or 0),
        "trade_time_ms": int(payload.get("T", 0) or 0),
        "spread_bps": spread_bps,
        "raw_event_type": payload.get("e", "unknown"),
    }

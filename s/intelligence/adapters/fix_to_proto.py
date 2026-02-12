"""
Goal
----
محول FIX -> نموذج proto داخلي موحّد لدعم وسطاء/بورصات متعددة.

Dependencies
------------
- FIX connectors
- transport/rpc schemas
- risk + execution pipeline
"""
from __future__ import annotations

from typing import Any

FIX_SIDE_MAP = {"1": "BUY", "2": "SELL"}
FIX_TYPE_MAP = {"1": "MARKET", "2": "LIMIT", "3": "STOP", "4": "STOP_LIMIT"}


def _safe_float(v: Any) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def map_fix_message(fix_fields: dict[str, Any]) -> dict[str, Any]:
    """تحويل حقول FIX الشائعة إلى envelope قياسي قابل للإرسال داخل النظام."""
    return {
        "symbol": fix_fields.get("55"),
        "side": FIX_SIDE_MAP.get(str(fix_fields.get("54", "")), "UNKNOWN"),
        "order_type": FIX_TYPE_MAP.get(str(fix_fields.get("40", "")), "UNKNOWN"),
        "quantity": _safe_float(fix_fields.get("38")),
        "price": _safe_float(fix_fields.get("44")),
        "stop_price": _safe_float(fix_fields.get("99")),
        "client_order_id": fix_fields.get("11"),
        "time_in_force": fix_fields.get("59"),
        "transact_time": fix_fields.get("60"),
        "raw_tags": fix_fields,
    }

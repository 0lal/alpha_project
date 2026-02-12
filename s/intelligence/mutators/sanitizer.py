"""
Goal
----
تنظيف البيانات بطريقة غير مدمرة (Non-Destructive Mutation).

Dependencies
------------
- audit trail
- governance policies
- mutator pipeline

الفكرة الأساسية
---------------
بدل تعديل payload مباشرة، نحافظ على نسختين:
1) raw      : النسخة الأصلية كما دخلت من المصدر.
2) corrected: النسخة بعد التصحيح الآلي.

ثم نضيف metadata جنائي:
- auto_fixed: هل تم إصلاح شيء أم لا.
- fix_reasons: ما الذي تم إصلاحه.
- raw_hash / corrected_hash: بصمات للتتبع والتحقق.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from typing import Any


def _payload_hash(payload: dict[str, Any]) -> str:
    """بصمة ثابتة للـ payload بهدف الربط بين النسخ في السجل الجنائي."""
    return sha256(repr(sorted(payload.items())).encode("utf-8")).hexdigest()


def sanitize_tick(payload: dict[str, Any]) -> dict[str, Any]:
    """
    ينفذ إصلاحات آلية آمنة مع الاحتفاظ بالأصل.

    الإصلاحات الحالية:
    - عكس bid/ask إن كانا مقلوبين.
    - تطبيع السعر السالب إلى قيمة موجبة (حالة edge قابلة للنقاش حسب نوع الأصل).
    """
    raw = deepcopy(payload)
    corrected = deepcopy(payload)

    fixes: list[str] = []

    bid = corrected.get("bid")
    ask = corrected.get("ask")
    if bid is not None and ask is not None and bid > ask:
        corrected["bid"], corrected["ask"] = ask, bid
        fixes.append("swap_inverted_bid_ask")

    if corrected.get("price") is not None and corrected["price"] < 0:
        corrected["price"] = abs(corrected["price"])
        fixes.append("normalize_negative_price")

    return {
        "raw": raw,
        "corrected": corrected,
        "auto_fixed": bool(fixes),
        "fix_reasons": fixes,
        "raw_hash": _payload_hash(raw),
        "corrected_hash": _payload_hash(corrected),
    }

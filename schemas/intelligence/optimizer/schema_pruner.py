"""
Goal
----
تحليل استخدام الحقول واقتراح تقليم schema بدون كسر التوافق.

Dependencies
------------
- telemetry field usage
- compatibility linter
- registry history
"""
from __future__ import annotations


def find_unused_fields(field_usage: dict[str, int], threshold: int = 0) -> list[str]:
    """الحقول التي لا تتجاوز threshold تعتبر مرشحة للتقليم."""
    return [name for name, cnt in field_usage.items() if cnt <= threshold]


def pruner_report(field_usage: dict[str, int], threshold: int = 0) -> dict[str, object]:
    """تقرير جاهز للأرشفة والمراجعة قبل حذف أي حقل فعليًا."""
    candidates = find_unused_fields(field_usage, threshold)
    return {
        "total_fields": len(field_usage),
        "threshold": threshold,
        "candidates": candidates,
        "candidate_ratio": (len(candidates) / max(len(field_usage), 1)),
    }

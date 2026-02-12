"""
Goal
----
قياس انحراف النمط الحالي عن خط الأساس التاريخي لاكتشاف data drift مبكرًا.

Dependencies
------------
- state_fetcher
- historical snapshots
- contextual validator
"""
from __future__ import annotations


def pattern_distance(current: list[float], baseline: list[float]) -> float:
    """متوسط الفرق المطلق بين متجهين متساويين الطول."""
    if not current or not baseline or len(current) != len(baseline):
        return 1.0
    return sum(abs(a - b) for a, b in zip(current, baseline)) / len(current)


def drift_score(current: list[float], baseline: list[float], scale: float = 1.0) -> float:
    """درجة drift مطبّعة (0 جيد، 1 سيء)."""
    d = pattern_distance(current, baseline)
    return min(1.0, max(0.0, d / max(scale, 1e-9)))

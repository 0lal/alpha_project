"""
Goal
----
خط تحقق ذكي موحّد يجمع مستويات المناعة الثلاثة:
1) Atomic   : التحقق البنيوي.
2) Semantic : التحقق الدلالي.
3) Contextual: التحقق السياقي مقابل سياسات الحوكمة الحية.

Dependencies
------------
- validators.atomic
- validators.semantic
- validators.contextual

مخرجات هذا المحرك تستخدم مباشرة في:
- قرار القبول/الرفض قبل الإدراج.
- السجل الجنائي audit trail.
- telemetry لتتبع الأداء وجودة البيانات.
"""
from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any

from s.intelligence.validators.atomic import ValidationIssue, validate_atomic
from s.intelligence.validators.contextual import ContextualValidator
from s.intelligence.validators.semantic import validate_semantic


@dataclass
class ValidationResult:
    """نتيجة الفحص النهائية."""

    accepted: bool
    decision: str
    confidence_score: float
    issues: list[ValidationIssue]
    governance_hash: str
    stage_timings_ms: dict[str, float]


class SmartValidationPipeline:
    """Orchestrator لطبقة المناعة الرقمية للبيانات."""

    def __init__(self, contextual: ContextualValidator | None = None):
        self.contextual = contextual or ContextualValidator()

    @staticmethod
    def _score(issues: list[ValidationIssue]) -> float:
        """حساب درجة ثقة تقريبية (1.0 ممتازة -> 0.0 مرفوضة)."""
        penalty = 0.0
        for i in issues:
            if i.severity == "CRITICAL":
                penalty += 0.50
            elif i.severity == "ERROR":
                penalty += 0.25
            elif i.severity == "WARNING":
                penalty += 0.10
            else:
                penalty += 0.02
        return max(0.0, round(1.0 - penalty, 4))

    def validate_tick(self, payload: dict[str, Any], prev_price: float | None = None) -> ValidationResult:
        timings: dict[str, float] = {}
        issues: list[ValidationIssue] = []

        t0 = time.perf_counter()
        issues.extend(validate_atomic(payload, required_fields=("symbol", "price", "event_time_ms")))
        timings["atomic"] = (time.perf_counter() - t0) * 1000

        t1 = time.perf_counter()
        issues.extend(validate_semantic(payload))
        timings["semantic"] = (time.perf_counter() - t1) * 1000

        t2 = time.perf_counter()
        if prev_price is not None and payload.get("price") is not None:
            spread_bps = float(payload.get("spread_bps", 0.0))
            issues.extend(self.contextual.validate_market(prev_price, float(payload["price"]), spread_bps))
        timings["contextual"] = (time.perf_counter() - t2) * 1000

        accepted = not any(i.severity in {"ERROR", "CRITICAL"} for i in issues)
        confidence = self._score(issues)
        decision = "ACCEPT" if accepted else "REJECT"

        return ValidationResult(
            accepted=accepted,
            decision=decision,
            confidence_score=confidence,
            issues=issues,
            governance_hash=self.contextual.get_snapshot().version_hash,
            stage_timings_ms=timings,
        )

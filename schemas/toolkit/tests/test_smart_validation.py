"""
Goal
----
اختبارات تكاملية سريعة لمكونات Bio-Schema الذكية.

Dependencies
------------
- s.intelligence.validators.contextual
- s.intelligence.validators.pipeline
- s.toolkit.linters.compatibility
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from s.intelligence.validators.contextual import ContextualValidator
from s.intelligence.validators.pipeline import SmartValidationPipeline
from s.toolkit.linters.compatibility import proto_breaking_change


def test_contextual_hot_reload() -> None:
    """يجب أن يتغير القرار بعد تحديث ملف الحوكمة بدون إعادة تشغيل."""
    with tempfile.TemporaryDirectory() as td:
        v_path = Path(td) / "volatility.yaml"
        r_path = Path(td) / "risk_limits.yaml"

        v_path.write_text("volatility:\n  max_drop_pct_per_sec: 1\n  max_spread_bps: 10\n", encoding="utf-8")
        r_path.write_text("risk_limits:\n  max_exposure_usd: 100\n  max_leverage: 2\n  max_daily_loss_usd: 10\n", encoding="utf-8")

        validator = ContextualValidator(str(v_path), str(r_path), poll_seconds=0.1)
        issues = validator.validate_market(prev_price=100, current_price=95, spread_bps=1)
        assert any(i.code == "volatility.drop_exceeded" for i in issues)

        v_path.write_text("volatility:\n  max_drop_pct_per_sec: 20\n  max_spread_bps: 100\n", encoding="utf-8")
        validator.refresh()
        issues2 = validator.validate_market(prev_price=100, current_price=95, spread_bps=1)
        assert not any(i.code == "volatility.drop_exceeded" for i in issues2)


def test_pipeline_rejects_critical_and_reports_timings() -> None:
    """أي خطأ CRITICAL/ERROR يجب أن يرفض الحزمة ويعيد stage timings وconfidence."""
    p = SmartValidationPipeline()
    payload = {"symbol": "BTCUSDT", "price": 0, "event_time_ms": 1700000000000}
    result = p.validate_tick(payload, prev_price=100)
    assert not result.accepted
    assert result.decision == "REJECT"
    assert set(result.stage_timings_ms) == {"atomic", "semantic", "contextual"}
    assert 0.0 <= result.confidence_score <= 1.0


def test_proto_compatibility_breaking_detection() -> None:
    """التأكد من كشف التغييرات الكاسرة في proto."""
    old = """
    message A { string f1 = 1; int32 f2 = 2; }
    """
    new_removed = """
    message A { string f1 = 1; }
    """
    new_renumbered = """
    message A { string f1 = 9; int32 f2 = 2; }
    """
    assert proto_breaking_change(old, new_removed)
    assert proto_breaking_change(old, new_renumbered)

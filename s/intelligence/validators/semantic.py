"""Goal: فحص المعنى بين الحقول (bid/ask, price bounds, invariants).
Dependencies: market rules, atomic validator, governance thresholds.
"""
from __future__ import annotations

from typing import Any

from s.intelligence.validators.atomic import ValidationIssue


def validate_semantic(payload: dict[str, Any]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    bid = payload.get("bid")
    ask = payload.get("ask")
    last = payload.get("price") or payload.get("last")

    if bid is not None and ask is not None:
        if bid > ask:
            issues.append(
                ValidationIssue(
                    code="orderbook.inverted",
                    field="bid/ask",
                    message="bid must not exceed ask.",
                )
            )

    if bid is not None and ask is not None and last is not None and bid <= ask:
        if not (bid * 0.5 <= last <= ask * 1.5):
            issues.append(
                ValidationIssue(
                    code="price.outlier_band",
                    field="price",
                    message="last price far from bid/ask expected band.",
                    severity="WARNING",
                )
            )

    open_ = payload.get("open")
    high = payload.get("high")
    low = payload.get("low")
    close = payload.get("close")

    if all(v is not None for v in (open_, high, low, close)):
        if low > high:
            issues.append(
                ValidationIssue(
                    code="ohlc.invalid_range",
                    field="low/high",
                    message="low cannot exceed high.",
                )
            )
        if not (low <= open_ <= high):
            issues.append(ValidationIssue("ohlc.open_outside", "open", "open outside [low, high]."))
        if not (low <= close <= high):
            issues.append(ValidationIssue("ohlc.close_outside", "close", "close outside [low, high]."))

    return issues

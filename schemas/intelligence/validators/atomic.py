"""Goal: فحص القيم الذرية (النوع/المدى/الإلزامية) بشكل production-grade.
Dependencies: ingestion pipeline, schema registry, governance policies.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    field: str
    message: str
    severity: str = "ERROR"


def _is_number(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def validate_atomic(
    payload: dict[str, Any],
    *,
    required_fields: Iterable[str] = ("symbol", "price", "event_time_ms"),
    allow_negative_price: bool = False,
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    for field in required_fields:
        if field not in payload or payload[field] in (None, ""):
            issues.append(
                ValidationIssue(
                    code="required.missing",
                    field=field,
                    message=f"Field '{field}' is required.",
                )
            )

    symbol = payload.get("symbol")
    if symbol is not None and (not isinstance(symbol, str) or len(symbol) > 30):
        issues.append(
            ValidationIssue(
                code="symbol.invalid",
                field="symbol",
                message="symbol must be string with max length 30.",
            )
        )

    price = payload.get("price")
    if price is not None:
        if not _is_number(price):
            issues.append(
                ValidationIssue(
                    code="price.type",
                    field="price",
                    message="price must be numeric.",
                )
            )
        elif (not allow_negative_price) and price <= 0:
            issues.append(
                ValidationIssue(
                    code="price.non_positive",
                    field="price",
                    message="price must be > 0 unless explicitly allowed.",
                )
            )

    qty = payload.get("quantity")
    if qty is not None and (not _is_number(qty) or qty < 0):
        issues.append(
            ValidationIssue(
                code="quantity.invalid",
                field="quantity",
                message="quantity must be numeric and >= 0.",
            )
        )

    ts = payload.get("event_time_ms")
    if ts is not None and (not isinstance(ts, int) or ts <= 0):
        issues.append(
            ValidationIssue(
                code="timestamp.invalid",
                field="event_time_ms",
                message="event_time_ms must be a positive integer in milliseconds.",
            )
        )

    return issues

"""
Goal
----
محرك التحقق السياقي (Contextual Validator) الذي يقرأ سياسات الحوكمة من YAML
ويحوّلها إلى snapshot ثابت (immutable snapshot) قابل للتدقيق والمقارنة.

Dependencies
------------
- s/governance/thresholds/volatility.yaml
- s/governance/thresholds/risk_limits.yaml
- validator pipeline
- audit/forensics

لماذا هذا الملف مهم؟
--------------------
في الأنظمة المالية، القيم الحدّية (thresholds) ليست ثابتة. مدير المخاطر قد يغيّر
الحدود أثناء جلسة التداول. لذلك لا نستخدم ثوابت hardcoded داخل الكود، بل نربط
المحرك بملفات حوكمة قابلة للتحديث مع آلية Hot Reload.

مبدأ العمل
-----------
1) نقرأ ملفات الحوكمة ونحوّلها إلى dataclasses typed.
2) نبني GovernanceSnapshot يحتوي hash للإصدار الحالي.
3) نعمل polling thread لتحديث snapshot عندما تتغير الملفات.
4) نوفر واجهات validate_market و validate_risk لاستهلاك بقية النظام.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from hashlib import sha256
from pathlib import Path
from threading import Event, Lock, Thread
import time
from typing import Any, Callable

try:
    import yaml  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    yaml = None

from s.intelligence.validators.atomic import ValidationIssue


@dataclass(frozen=True)
class VolatilityThresholds:
    """حدود التقلب القصوى المسموح بها."""

    max_drop_pct_per_sec: float = 5.0
    max_spread_bps: float = 250.0
    max_jump_sigma: float = 6.0


@dataclass(frozen=True)
class RiskThresholds:
    """حدود المخاطر الرأسمالية والتشغيلية."""

    max_exposure_usd: float = 10_000.0
    max_leverage: float = 5.0
    max_daily_loss_usd: float = 2_000.0


@dataclass(frozen=True)
class GovernanceSnapshot:
    """نسخة ثابتة من الحوكمة مع metadata للتدقيق."""

    volatility: VolatilityThresholds
    risk: RiskThresholds
    version_hash: str
    loaded_at_ms: int


class ContextualValidator:
    """
    Engine للتحقق السياقي مع دعم hot reload.

    ملاحظات هندسية:
    - Thread-safe عبر Lock.
    - في حال غياب PyYAML نستخدم parser مبسط كمسار بديل.
    - يوفر callback hook عند تغير snapshot لربط telemetry/audit.
    """

    def __init__(
        self,
        volatility_file: str = "s/governance/thresholds/volatility.yaml",
        risk_file: str = "s/governance/thresholds/risk_limits.yaml",
        poll_seconds: float = 0.5,
        on_reload: Callable[[GovernanceSnapshot], None] | None = None,
    ):
        self.volatility_path = Path(volatility_file)
        self.risk_path = Path(risk_file)
        self.poll_seconds = poll_seconds
        self.on_reload = on_reload

        self._lock = Lock()
        self._stop = Event()
        self._thread: Thread | None = None
        self._last_file_signature = ""
        self._snapshot = self._load_snapshot(force=True)

    def _calc_signature(self) -> str:
        parts = []
        for p in (self.volatility_path, self.risk_path):
            if p.exists():
                stat = p.stat()
                parts.append(f"{p}:{stat.st_mtime_ns}:{stat.st_size}")
            else:
                parts.append(f"{p}:missing")
        return "|".join(parts)

    @staticmethod
    def _read_yaml(path: Path) -> dict[str, Any]:
        """قراءة YAML مع fallback parser بسيط للـ key/value."""
        if not path.exists():
            return {}
        raw = path.read_text(encoding="utf-8")
        if yaml is not None:
            content = yaml.safe_load(raw)
            return content if isinstance(content, dict) else {}

        root: dict[str, Any] = {}
        current: dict[str, Any] | None = None
        for line in raw.splitlines():
            if not line.strip() or line.strip().startswith("#"):
                continue
            if not line.startswith(" ") and line.endswith(":"):
                key = line[:-1].strip()
                root[key] = {}
                current = root[key]
                continue
            if current is not None and ":" in line:
                k, v = line.strip().split(":", 1)
                v = v.strip()
                try:
                    current[k] = float(v) if "." in v else int(v)
                except ValueError:
                    current[k] = v
        return root

    @staticmethod
    def _validate_positive(name: str, value: float, default: float) -> float:
        """يحمي النظام من threshold سلبي/صفري بسبب إعداد خاطئ."""
        return value if value > 0 else default

    def _load_snapshot(self, *, force: bool = False) -> GovernanceSnapshot:
        sig = self._calc_signature()
        if not force and sig == self._last_file_signature:
            return self._snapshot

        v = self._read_yaml(self.volatility_path).get("volatility", {})
        r = self._read_yaml(self.risk_path).get("risk_limits", {})

        vol = VolatilityThresholds(
            max_drop_pct_per_sec=self._validate_positive(
                "max_drop_pct_per_sec", float(v.get("max_drop_pct_per_sec", 5.0)), 5.0
            ),
            max_spread_bps=self._validate_positive("max_spread_bps", float(v.get("max_spread_bps", 250.0)), 250.0),
            max_jump_sigma=self._validate_positive("max_jump_sigma", float(v.get("max_jump_sigma", 6.0)), 6.0),
        )
        risk = RiskThresholds(
            max_exposure_usd=self._validate_positive(
                "max_exposure_usd", float(r.get("max_exposure_usd", 10_000.0)), 10_000.0
            ),
            max_leverage=self._validate_positive("max_leverage", float(r.get("max_leverage", 5.0)), 5.0),
            max_daily_loss_usd=self._validate_positive(
                "max_daily_loss_usd", float(r.get("max_daily_loss_usd", 2_000.0)), 2_000.0
            ),
        )

        snapshot_bytes = str({"volatility": asdict(vol), "risk": asdict(risk)}).encode("utf-8")
        snapshot = GovernanceSnapshot(
            volatility=vol,
            risk=risk,
            version_hash=sha256(snapshot_bytes).hexdigest(),
            loaded_at_ms=int(time.time() * 1000),
        )
        self._last_file_signature = sig
        return snapshot

    def refresh(self) -> GovernanceSnapshot:
        with self._lock:
            previous = self._snapshot
            self._snapshot = self._load_snapshot()
            if self.on_reload and self._snapshot.version_hash != previous.version_hash:
                self.on_reload(self._snapshot)
            return self._snapshot

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = Thread(target=self._watch_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=1)

    def _watch_loop(self) -> None:
        while not self._stop.is_set():
            self.refresh()
            self._stop.wait(self.poll_seconds)

    def get_snapshot(self) -> GovernanceSnapshot:
        with self._lock:
            return self._snapshot

    def validate_market(self, prev_price: float, current_price: float, spread_bps: float) -> list[ValidationIssue]:
        """يتحقق من سقوط السعر المفاجئ واتساع السبريد."""
        s = self.get_snapshot()
        issues: list[ValidationIssue] = []

        if prev_price > 0:
            drop_pct = ((prev_price - current_price) / prev_price) * 100
            if drop_pct > s.volatility.max_drop_pct_per_sec:
                issues.append(
                    ValidationIssue(
                        code="volatility.drop_exceeded",
                        field="price",
                        message=f"Drop {drop_pct:.2f}% > {s.volatility.max_drop_pct_per_sec:.2f}%",
                        severity="CRITICAL",
                    )
                )

        if spread_bps > s.volatility.max_spread_bps:
            issues.append(
                ValidationIssue(
                    code="volatility.spread_exceeded",
                    field="spread_bps",
                    message=f"Spread {spread_bps:.2f} bps > {s.volatility.max_spread_bps:.2f} bps",
                )
            )

        return issues

    def validate_risk(self, exposure_usd: float, leverage: float, daily_loss_usd: float) -> list[ValidationIssue]:
        """يتحقق من تجاوزات exposure/leverage/daily loss."""
        s = self.get_snapshot()
        issues: list[ValidationIssue] = []

        if exposure_usd > s.risk.max_exposure_usd:
            issues.append(
                ValidationIssue(
                    code="risk.exposure_exceeded",
                    field="exposure_usd",
                    message=f"Exposure {exposure_usd:.2f} > {s.risk.max_exposure_usd:.2f}",
                    severity="CRITICAL",
                )
            )
        if leverage > s.risk.max_leverage:
            issues.append(
                ValidationIssue(
                    code="risk.leverage_exceeded",
                    field="leverage",
                    message=f"Leverage {leverage:.2f} > {s.risk.max_leverage:.2f}",
                )
            )
        if daily_loss_usd > s.risk.max_daily_loss_usd:
            issues.append(
                ValidationIssue(
                    code="risk.daily_loss_exceeded",
                    field="daily_loss_usd",
                    message=f"Daily loss {daily_loss_usd:.2f} > {s.risk.max_daily_loss_usd:.2f}",
                )
            )

        return issues

"""
Goal
----
فاحص نمط التوثيق المباشر للملفات الحساسة (.proto/.json).

Dependencies
------------
- CI hooks
- schema repository
- registry manifest

قواعد الفحص الحالية
-------------------
- كل ملف .proto يجب أن يحتوي Goal + Dependencies في بداية الملف.
- كل ملف .json يجب أن يحتوي _header يضم Goal + Dependencies.
"""
from __future__ import annotations

from pathlib import Path
import json
import sys

MANDATORY_EXTS = {".proto", ".json"}
SKIP_FILES = {"manifest.json", "compiled_catalog.json"}


def _json_has_header(path: Path) -> bool:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    header = data.get("_header", {})
    return isinstance(header, dict) and "Goal" in header and "Dependencies" in header


def has_required_header(path: Path) -> bool:
    if path.suffix == ".proto":
        text = path.read_text(encoding="utf-8", errors="ignore")
        return ("Goal:" in text[:800]) and ("Dependencies:" in text[:800])
    if path.suffix == ".json":
        return _json_has_header(path)
    return True


def run(root: str = "s") -> int:
    base = Path(root)
    failures: list[str] = []

    for p in base.rglob("*"):
        if not p.is_file() or p.suffix not in MANDATORY_EXTS:
            continue
        if p.name in SKIP_FILES:
            continue
        if not has_required_header(p):
            failures.append(str(p))

    if failures:
        print("STYLE_CHECK_FAIL")
        for f in failures:
            print(f" - missing/invalid Goal+Dependencies header: {f}")
        return 1

    print("STYLE_CHECK_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(run(sys.argv[1] if len(sys.argv) > 1 else "s"))

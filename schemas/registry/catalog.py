"""
Goal
----
واجهة Registry SDK لاكتشاف ملفات الـ schema الرسمية وحساب بصماتها.

Dependencies
------------
- s/registry/manifest.json
- toolkit compilers

لماذا؟
------
في نظام مالي، لازم نعرف بالضبط أي نسخة schema تم استخدامها.
لذلك ننتج inventory شامل مع SHA-256 لكل ملف لتأمين القابلية للتدقيق (Auditability).
"""
from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

SCHEMA_EXTENSIONS = {".proto", ".fbs", ".sql", ".json", ".yaml", ".yml"}


def load_manifest(path: str = "s/registry/manifest.json") -> dict:
    """تحميل ملف manifest الرسمي."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def list_schema_files(root: str = "s") -> list[str]:
    """إرجاع جميع ملفات schema المعروفة ضمن الجذر المحدد."""
    base = Path(root)
    files: list[str] = []
    for p in base.rglob("*"):
        if p.is_file() and p.suffix in SCHEMA_EXTENSIONS and "__pycache__" not in p.parts:
            files.append(str(p).replace("\\", "/"))
    return sorted(files)


def file_sha256(path: str) -> str:
    """حساب SHA-256 لتثبيت هوية الملف."""
    raw = Path(path).read_bytes()
    return sha256(raw).hexdigest()

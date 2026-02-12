"""
Goal
----
فاحص توافق خفيف (Lightweight) لاكتشاف تغييرات .proto الكاسرة.

Dependencies
------------
- registry history
- CI policy

ما الذي نعدّه "كاسر" هنا؟
------------------------
- حذف field موجود سابقًا.
- إعادة استخدام رقم field لاسم مختلف (field-number reuse).
"""
from __future__ import annotations

from pathlib import Path
import re


FIELD_RE = re.compile(r"\b[a-zA-Z_][a-zA-Z0-9_.<>]*\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(\d+)\s*;")


def _extract_name_to_number(text: str) -> dict[str, int]:
    return {name: int(num) for name, num in FIELD_RE.findall(text)}


def _extract_number_to_name(text: str) -> dict[int, str]:
    return {int(num): name for name, num in FIELD_RE.findall(text)}


def proto_breaking_change(old_text: str, new_text: str) -> bool:
    old_map = _extract_name_to_number(old_text)
    new_map = _extract_name_to_number(new_text)

    # rule 1: field removal
    if not set(old_map).issubset(set(new_map)):
        return True

    # rule 2: existing field number changed
    for name, old_num in old_map.items():
        if new_map.get(name) != old_num:
            return True

    # rule 3: number reused for a different name
    old_num_name = _extract_number_to_name(old_text)
    new_num_name = _extract_number_to_name(new_text)
    for num, old_name in old_num_name.items():
        if num in new_num_name and new_num_name[num] != old_name:
            return True

    return False


def compare_files(old_path: str, new_path: str) -> bool:
    old = Path(old_path).read_text(encoding="utf-8")
    new = Path(new_path).read_text(encoding="utf-8")
    if old_path.endswith(".proto") and new_path.endswith(".proto"):
        return proto_breaking_change(old, new)
    return False

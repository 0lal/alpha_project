"""
Goal
----
Builder لتجميع كتالوج schema قابل للاستهلاك من الأدوات/CI.

Dependencies
------------
- s/registry/catalog.py
- s/registry/manifest.json

المخرجات
--------
ملف `s/registry/compiled_catalog.json` ويحتوي:
- version manifest
- الجذور النشطة
- عدد الملفات
- بصمة SHA-256 لكل ملف
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from s.registry.catalog import file_sha256, list_schema_files, load_manifest


def build_catalog(output_path: str = "s/registry/compiled_catalog.json") -> dict:
    manifest = load_manifest()
    roots: list[str] = manifest.get("active_roots", [])

    artifacts = []
    for root in roots:
        for f in list_schema_files(root):
            artifacts.append({"path": f, "sha256": file_sha256(f)})

    # deduplicate in case overlapping roots
    unique = {a["path"]: a for a in artifacts}
    artifacts = [unique[k] for k in sorted(unique)]

    result = {
        "_header": {
            "Goal": "كتالوج مبني آلياً لملفات schema والبصمات.",
            "Dependencies": ["s/registry/manifest.json", "s/registry/catalog.py"]
        },
        "manifest_version": manifest.get("version", "unknown"),
        "active_roots": roots,
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
    }

    out = Path(output_path)
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return result


if __name__ == "__main__":
    catalog = build_catalog()
    print(f"compiled {catalog['artifact_count']} artifacts")

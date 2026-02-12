"""
Goal
----
بناء خريطة اعتماديات schema بشكل قابل للعرض في الأدوات الرسومية.

Dependencies
------------
- registry catalog
- manifest
- visualization tools (اختياري)
"""
from __future__ import annotations

from pathlib import Path
import json


def build_graph(catalog_path: str = "s/registry/compiled_catalog.json") -> dict:
    """تحويل catalog إلى رسم بياني مبسط (nodes/edges)."""
    data = json.loads(Path(catalog_path).read_text(encoding="utf-8"))
    artifacts = data.get("artifacts", [])

    nodes = [{"id": a["path"], "label": Path(a["path"]).name} for a in artifacts]
    edges = []

    # edge heuristic: same directory implies weak relation
    by_dir: dict[str, list[str]] = {}
    for a in artifacts:
        d = str(Path(a["path"]).parent)
        by_dir.setdefault(d, []).append(a["path"])
    for _, paths in by_dir.items():
        for i in range(len(paths) - 1):
            edges.append({"source": paths[i], "target": paths[i + 1], "type": "co-located"})

    return {"nodes": nodes, "edges": edges, "node_count": len(nodes), "edge_count": len(edges)}

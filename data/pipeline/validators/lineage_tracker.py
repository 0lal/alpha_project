# -*- coding: utf-8 -*-
# ALPHA SOVEREIGN - DATA LINEAGE TRACKER (DATA GENOME)
# =================================================================
# Component Name: data/governance/lineage_tracker.py
# Core Responsibility: تسجيل وتتبع جينوم البيانات (من أين جاءت وكيف تحولت).
# Design Pattern: Directed Acyclic Graph (DAG) Manager
# Forensic Impact: يوفر "سلسلة نسب" (Pedigree) لكل معلومة، مما يسمح بتتبع التلوث من المنبع إلى المصب.
# =================================================================

import logging
import uuid
import json
from datetime import datetime
from typing import Dict, List, Any, Optional, Set

class LineageNode:
    """
    عقدة في شجرة النسب. تمثل حالة بيانات معينة في لحظة زمنية.
    """
    def __init__(self, data_id: str, component: str, meta: Dict[str, Any]):
        self.id = data_id
        self.timestamp = datetime.utcnow().isoformat()
        self.component = component  # من الذي أنتج هذه البيانات؟
        self.meta = meta            # وصف البيانات (مثلاً: Raw Tick, Normalized Candle)
        self.parents: List[str] = [] # معرفات البيانات الأصل (Upstream)

class LineageTracker:
    """
    متتبع السلالة.
    يبني رسماً بيانياً موجهاً (DAG) يربط المدخلات بالمخرجات عبر عمليات التحويل.
    """

    def __init__(self):
        self.logger = logging.getLogger("Alpha.Governance.Lineage")
        
        # تخزين العقد (Nodes) - قاموس للبحث السريع
        self._nodes: Dict[str, LineageNode] = {}
        
        # تخزين العلاقات (Edges) - من الآباء للأبناء (للتتبع الأمامي)
        self._forward_map: Dict[str, List[str]] = {}

    def register_source(self, data_id: str, source_name: str, description: str) -> str:
        """
        تسجيل ولادة بيانات جديدة (نقطة المنشأ).
        مثلاً: استقبال حزمة من Binance.
        """
        if not data_id:
            data_id = str(uuid.uuid4())

        node = LineageNode(
            data_id=data_id,
            component=source_name,
            meta={"type": "ORIGIN", "desc": description}
        )
        
        self._add_node(node)
        # self.logger.debug(f"LINEAGE_BIRTH: تم تسجيل أصل جديد {data_id} من {source_name}")
        return data_id

    def register_transformation(self, 
                                input_ids: List[str], 
                                output_id: str, 
                                component: str, 
                                operation: str) -> str:
        """
        تسجيل عملية تحويل (Transformation Event).
        مثلاً: تحويل Tick -> Candle.
        
        Args:
            input_ids: معرفات البيانات المدخلة (الآباء).
            output_id: معرف البيانات الناتجة (الابن).
            component: اسم الوحدة التي قامت بالتحويل (Normalizer, Strategy).
            operation: وصف العملية (Cleaning, Aggregation).
        """
        if not output_id:
            output_id = str(uuid.uuid4())

        # التحقق من وجود الآباء (سلامة النسب)
        missing_parents = [pid for pid in input_ids if pid not in self._nodes]
        if missing_parents:
            self.logger.warning(f"ORPHAN_DATA: محاولة اشتقاق بيانات من آباء مجهولين: {missing_parents}")
            # نقوم بتسجيلهم كأشباح (Ghosts) للحفاظ على التماسك الهيكلي

        node = LineageNode(
            data_id=output_id,
            component=component,
            meta={"type": "DERIVED", "op": operation}
        )
        node.parents = input_ids # تسجيل النسب الخلفي

        self._add_node(node)
        
        # تسجيل النسب الأمامي (من الآباء للابن)
        for parent_id in input_ids:
            if parent_id not in self._forward_map:
                self._forward_map[parent_id] = []
            self._forward_map[parent_id].append(output_id)

        return output_id

    def trace_back(self, data_id: str) -> Dict[str, Any]:
        """
        التحقيق الجنائي العكسي (Back-Tracing).
        يعيد شجرة النسب الكاملة للوراء لمعرفة أصل هذه البيانات.
        """
        if data_id not in self._nodes:
            return {"error": "DATA_NOT_FOUND"}

        node = self._nodes[data_id]
        lineage = {
            "id": node.id,
            "component": node.component,
            "timestamp": node.timestamp,
            "meta": node.meta,
            "parents": []
        }

        # استدعاء تداخلي (Recursive) للآباء
        for parent_id in node.parents:
            lineage["parents"].append(self.trace_back(parent_id))

        return lineage

    def get_impact_analysis(self, source_id: str) -> List[str]:
        """
        تحليل التأثير (Forward-Tracing).
        إذا اكتشفنا أن مصدراً معيناً كان فاسداً، ما هي البيانات التي تلوثت بسببه؟
        """
        impacted_nodes = set()
        stack = [source_id]

        while stack:
            current_id = stack.pop()
            if current_id in impacted_nodes:
                continue
            
            impacted_nodes.add(current_id)
            
            # إضافة جميع الأبناء للطابور
            children = self._forward_map.get(current_id, [])
            stack.extend(children)

        # إزالة المصدر نفسه من القائمة
        impacted_nodes.discard(source_id)
        return list(impacted_nodes)

    def _add_node(self, node: LineageNode):
        """إضافة عقدة للذاكرة."""
        self._nodes[node.id] = node

    def export_graph_json(self) -> str:
        """تصدير الرسم البياني بالكامل لغرض التصوير (Visualization)."""
        graph = {
            "nodes": [{"id": n.id, "label": f"{n.component} ({n.meta.get('type')})"} for n in self._nodes.values()],
            "edges": []
        }
        
        for parent, children in self._forward_map.items():
            for child in children:
                graph["edges"].append({"source": parent, "target": child})
                
        return json.dumps(graph, indent=2)
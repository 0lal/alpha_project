# -*- coding: utf-8 -*-
# ALPHA SOVEREIGN - FINANCIAL KNOWLEDGE GRAPH (CAUSALITY ENGINE)
# =================================================================
# Component Name: brain/memory/knowledge_graph.py
# Core Responsibility: بناء شبكة علاقات سببية بين الأحداث والأسواق (Intelligence Pillar).
# Design Pattern: Directed Acyclic Graph (DAG) / Network Analysis
# Forensic Impact: يكشف "العدوى المالية" (Contagion). يفسر لماذا انهارت عملة الكريبتو بسبب خبر في سوق السندات اليابانية.
# =================================================================

import logging
import networkx as nx
from typing import Dict, List, Any, Tuple, Optional

class KnowledgeGraph:
    """
    الرسم البياني للمعرفة المالية.
    يستخدم مكتبة NetworkX لتمثيل الأصول والأحداث كعقد (Nodes)،
    والعلاقات السببية كحواف موجهة (Directed Edges).
    """

    def __init__(self):
        self.logger = logging.getLogger("Alpha.Brain.Memory.Graph")
        # DiGraph = Directed Graph (العلاقة لها اتجاه: A يسبب B)
        self.graph = nx.DiGraph()
        
        # تهيئة العلاقات الأساسية الثابتة (Ontology Initialization)
        self._initialize_base_ontology()

    def _initialize_base_ontology(self):
        """بناء الهيكل العظمي للعالم المالي."""
        # علاقات الأصول (Assets)
        self.add_causal_link("GOLD", "USD", weight=-0.8, relation_type="INVERSE_CORRELATION")
        self.add_causal_link("BTC", "NASDAQ", weight=0.7, relation_type="CORRELATION")
        self.add_causal_link("OIL", "AIRLINE_STOCKS", weight=-0.6, relation_type="COST_INPUT")
        
        # علاقات جيوسياسية (Geopolitics)
        self.add_causal_link("WAR_MIDDLE_EAST", "OIL", weight=0.9, relation_type="SUPPLY_SHOCK")
        self.add_causal_link("FED_RATE_HIKE", "CRYPTO", weight=-0.7, relation_type="LIQUIDITY_DRAIN")
        self.add_causal_link("FED_RATE_HIKE", "DXY", weight=0.8, relation_type="CAPITAL_INFLOW")

    def add_causal_link(self, source: str, target: str, weight: float, relation_type: str):
        """
        إضافة علاقة سببية جديدة.
        Weight: من -1.0 (عكسي تام) إلى 1.0 (طردي تام).
        """
        self.graph.add_edge(source, target, weight=weight, type=relation_type)
        self.logger.debug(f"GRAPH_UPDATE: Added {source} --[{relation_type}]--> {target}")

    def propagate_shock(self, event_node: str, initial_impact: float = 1.0) -> Dict[str, float]:
        """
        محاكاة انتشار الصدمة (Ripple Effect Simulation).
        إذا حدث هذا الحدث، ماذا يتأثر؟
        
        Args:
            event_node: العقدة المسببة (مثلاً "WAR_MIDDLE_EAST").
            initial_impact: قوة الحدث (0.0 to 1.0).
            
        Returns:
            قائمة بالأصول المتأثرة ودرجة التأثر المتوقعة.
        """
        if event_node not in self.graph:
            return {}

        impacts = {event_node: initial_impact}
        visited = set()
        queue = [(event_node, initial_impact)] # Breadth-First Search queue

        while queue:
            current_node, current_force = queue.pop(0)
            
            if current_node in visited:
                continue
            visited.add(current_node)

            # إذا تلاشت القوة، نتوقف عن التتبع في هذا الفرع
            if abs(current_force) < 0.05:
                continue

            # البحث في الجيران (المتأثرين المباشرين)
            for neighbor in self.graph.successors(current_node):
                edge_data = self.graph.get_edge_data(current_node, neighbor)
                edge_weight = edge_data.get("weight", 0.0)
                
                # انتقال الصدمة: القوة الحالية * وزن العلاقة
                # (مع إضافة عامل تخميد decay بسيط 0.9 لتقليل التأثير مع البعد)
                transferred_force = current_force * edge_weight * 0.9
                
                # تجميع التأثيرات (قد يتأثر أصل واحد من عدة جهات)
                if neighbor in impacts:
                    impacts[neighbor] += transferred_force
                else:
                    impacts[neighbor] = transferred_force
                
                queue.append((neighbor, transferred_force))

        # تنظيف النتائج (إزالة الحدث نفسه والنتائج الضعيفة)
        del impacts[event_node]
        significant_impacts = {k: round(v, 2) for k, v in impacts.items() if abs(v) >= 0.1}
        
        return significant_impacts

    def find_explanation_path(self, cause: str, effect: str) -> List[str]:
        """
        البحث عن "سلسلة التفسير" (Explainability Chain).
        لماذا نعتقد أن X سيؤثر على Y؟
        """
        try:
            path = nx.shortest_path(self.graph, source=cause, target=effect)
            return path
        except nx.NetworkXNoPath:
            return []
        except Exception:
            return []

    def export_graph_stats(self) -> Dict[str, Any]:
        """تصدير إحصائيات الرسم البياني للتحليل."""
        return {
            "total_nodes": self.graph.number_of_nodes(),
            "total_edges": self.graph.number_of_edges(),
            "density": nx.density(self.graph)
        }
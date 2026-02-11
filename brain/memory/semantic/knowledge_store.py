# -*- coding: utf-8 -*-
# ALPHA SOVEREIGN - SEMANTIC (LONG-TERM) KNOWLEDGE STORE
# =================================================================
# Component Name: brain/memory/semantic/knowledge_store.py
# Core Responsibility: إدارة الذاكرة الطويلة المدى والأنماط التاريخية (Intelligence Pillar).
# Design Pattern: Vector Store Interface / Repository
# Forensic Impact: يسمح للنظام بـ "الاستشهاد بالسوابق" (Citing Precedents). يبرر القرار بناءً على دروس عام 2020 أو 2024.
# =================================================================

import logging
import json
from typing import Dict, List, Any, Optional
from datetime import datetime

# استيراد عميل قاعدة البيانات المتجهة (تمت الإشارة إليه في الملف 85)
# نفترض وجوده كواجهة للتعامل مع Qdrant أو Pinecone
from data.storage.vector.qdrant_client import AlphaQdrantClient

class SemanticMemory:
    """
    مخزن المعرفة الدلالية.
    يحتفظ بـ "حكمة" النظام المستخلصة من آلاف الصفقات السابقة.
    يعتمد على التضمين المتجه (Vector Embeddings) للبحث عن الأنماط المشابهة.
    """

    def __init__(self):
        self.logger = logging.getLogger("Alpha.Brain.Memory.Semantic")
        self.vector_db = AlphaQdrantClient()
        
        # مجموعات المعرفة (Knowledge Collections)
        self.collections = {
            "MARKET_PATTERNS": "patterns_v1",  # أنماط الشموع والسيولة
            "STRATEGY_RESULTS": "outcomes_v1", # نتائج الاستراتيجيات
            "MACRO_EVENTS": "macro_history_v1" # تأثير الأخبار الاقتصادية
        }

    async def consolidate_lesson(self, 
                                 context_vector: List[float], 
                                 outcome: Dict[str, Any], 
                                 lesson_tags: List[str]) -> bool:
        """
        ترسيخ درس جديد في الذاكرة الطويلة (Learning).
        يتم استدعاء هذه الدالة بعد إغلاق الصفقة وتحليل نتائجها.
        
        Args:
            context_vector: تمثيل رقمي لحالة السوق وقت الدخول.
            outcome: النتيجة {profit: 100, success: True, reason: "Good trend"}.
            lesson_tags: وسوم للبحث (e.g., ["BULL_FLAG", "HIGH_VOLATILITY"]).
        """
        try:
            # صياغة "الذاكرة"
            memory_point = {
                "vector": context_vector,
                "payload": {
                    "timestamp": datetime.utcnow().isoformat(),
                    "tags": lesson_tags,
                    "outcome_summary": outcome,
                    "effectiveness": outcome.get("roi_pct", 0.0)
                }
            }
            
            # تخزين في قاعدة البيانات المتجهة
            # النظام يتعلم: "في مثل هذه الظروف (Vector)، كانت النتيجة X"
            success = await self.vector_db.upsert(
                collection_name=self.collections["STRATEGY_RESULTS"],
                points=[memory_point]
            )
            
            if success:
                self.logger.info(f"LEARNING: Lesson consolidated. Tags: {lesson_tags}")
                
            return success

        except Exception as e:
            self.logger.error(f"CONSOLIDATION_FAIL: {e}")
            return False

    async def recall_similar_experience(self, current_market_vector: List[float], top_k: int = 3) -> List[Dict[str, Any]]:
        """
        استدعاء الخبرات المشابهة (Recall).
        "هل مررنا بهذا من قبل؟"
        
        Args:
            current_market_vector: حالة السوق الحالية.
            
        Returns:
            قائمة بأقرب السيناريوهات التاريخية ونتائجها.
        """
        try:
            results = await self.vector_db.search(
                collection_name=self.collections["STRATEGY_RESULTS"],
                query_vector=current_market_vector,
                limit=top_k
            )
            
            # تحليل النتائج المسترجعة
            # إذا كانت معظم النتائج المشابهة "خسارة"، فهذا تحذير قوي
            experiences = []
            for point in results:
                experiences.append({
                    "similarity_score": point.score, # مدى الشبه (0.0 to 1.0)
                    "date": point.payload.get("timestamp"),
                    "outcome": point.payload.get("outcome_summary"),
                    "lesson": f"Similar scenario yielded {point.payload.get('effectiveness')}% ROI"
                })
                
            return experiences

        except Exception as e:
            self.logger.error(f"RECALL_FAIL: {e}")
            return []

    def get_abstract_concept(self, concept_key: str) -> Optional[Dict[str, Any]]:
        """
        استرجاع قاعدة ثابتة أو تعريف (Rule-Based Memory).
        مثلاً: "ما هو تعريف الركود؟"
        """
        # (في التطبيق الفعلي، قد تكون هذه قاعدة بيانات Graph DB أو SQL)
        # هنا نستخدم قاموساً بسيطاً للمثال
        static_knowledge = {
            "RECESSION_DEF": {"rule": "Two consecutive quarters of negative GDP", "action": "SHIFT_TO_BONDS"},
            "WHALE_SPLASH": {"rule": "Volume > 500 BTC in 1 min", "action": "WAIT_FOR_RETRACEMENT"}
        }
        return static_knowledge.get(concept_key)
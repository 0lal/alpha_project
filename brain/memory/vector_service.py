# -*- coding: utf-8 -*-
# ALPHA SOVEREIGN - HIGH-PERFORMANCE VECTOR SEARCH SERVICE
# =================================================================
# Component Name: brain/memory/vector_service.py
# Core Responsibility: تشغيل محرك البحث في المتجهات لاسترجاع المواقف المشابهة (Intelligence Pillar).
# Design Pattern: Service Facade / Adapter
# Forensic Impact: يضمن دقة استرجاع المعلومات. إذا كان البحث خاطئاً، فالقرار سيكون خاطئاً.
# =================================================================

import logging
import numpy as np
from typing import Dict, List, Any, Optional, Union
from data.storage.vector.qdrant_client import AlphaQdrantClient

class VectorService:
    """
    خدمة المتجهات (Vector Service).
    طبقة تجريد (Abstraction Layer) تفصل منطق العمل عن قاعدة البيانات (Qdrant/Pinecone).
    تقوم بمعالجة المتجهات (Normalization) قبل البحث لضمان دقة النتائج.
    """

    def __init__(self):
        self.logger = logging.getLogger("Alpha.Brain.Memory.VectorSvc")
        
        # الاتصال بقاعدة البيانات الخلفية
        # (تم تعريف العميل في ملف سابق 85)
        self.db_client = AlphaQdrantClient()
        
        # عتبة التشابه المقبولة (Similarity Threshold)
        # أي نتيجة تشابهها أقل من 75% تعتبر "غير ذات صلة"
        self.similarity_threshold = 0.75

    async def search_memory(self, 
                            collection: str, 
                            query_vector: List[float], 
                            limit: int = 5,
                            filter_tags: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        البحث عن متجهات مشابهة.
        
        Args:
            collection: اسم المجموعة (e.g., 'market_patterns').
            query_vector: متجه الحالة الحالية للسوق.
            limit: عدد النتائج المطلوبة.
            filter_tags: تصفية النتائج (مثلاً: ابحث فقط في صفقات 'BITCOIN').
            
        Returns:
            قائمة بالنتائج المرتبة حسب التشابه.
        """
        try:
            # 1. تطبيع المتجه (Engineering Pre-processing)
            # البحث بالـ Cosine Similarity يتطلب متجهات بطول موحد (Unit Vectors)
            normalized_query = self._normalize_vector(query_vector)

            # 2. تنفيذ البحث في قاعدة البيانات
            search_results = await self.db_client.search(
                collection_name=collection,
                query_vector=normalized_query,
                limit=limit,
                tags=filter_tags
            )

            # 3. تصفية ومعالجة النتائج
            relevant_memories = []
            for hit in search_results:
                # تجاهل النتائج الضعيفة (Noise Filtering)
                if hit.score < self.similarity_threshold:
                    continue

                relevant_memories.append({
                    "id": hit.id,
                    "similarity": round(hit.score, 4),
                    "payload": hit.payload, # البيانات الوصفية (النتيجة، التاريخ، الزوج)
                    "vector": hit.vector if hasattr(hit, 'vector') else None
                })

            if relevant_memories:
                self.logger.debug(f"VECTOR_HIT: Found {len(relevant_memories)} similar events in {collection} (Top Score: {relevant_memories[0]['similarity']})")
            else:
                self.logger.debug(f"VECTOR_MISS: No similar events found above threshold {self.similarity_threshold}")

            return relevant_memories

        except Exception as e:
            self.logger.error(f"VECTOR_SEARCH_FAIL: {e}")
            return []

    async def archive_experience(self, 
                                 collection: str, 
                                 vector: List[float], 
                                 metadata: Dict[str, Any]) -> bool:
        """
        أرشفة تجربة جديدة (كتابة في الذاكرة).
        """
        try:
            # تطبيع المتجه قبل التخزين لضمان الاتساق
            norm_vector = self._normalize_vector(vector)
            
            success = await self.db_client.upsert(
                collection_name=collection,
                points=[{
                    "vector": norm_vector,
                    "payload": metadata
                }]
            )
            return success
        except Exception as e:
            self.logger.error(f"VECTOR_WRITE_FAIL: {e}")
            return False

    def _normalize_vector(self, vector: Union[List[float], np.ndarray]) -> List[float]:
        """
        تحويل المتجه إلى متجه وحدة (Unit Vector).
        Formula: v / ||v||
        هذا يجعل طول المتجه = 1، مما يجعل الضرب النقطي (Dot Product) يساوي Cosine Similarity.
        """
        np_vec = np.array(vector, dtype=np.float32)
        norm = np.linalg.norm(np_vec)
        
        if norm == 0:
            return vector # تجنب القسمة على صفر (متجه صفري)
            
        return (np_vec / norm).tolist()

    def health_check(self) -> bool:
        """فحص اتصال خدمة المتجهات."""
        try:
            # محاولة قراءة خفيفة للتأكد من الاتصال
            return self.db_client.is_connected()
        except Exception:
            return False
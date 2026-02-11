# -*- coding: utf-8 -*-
# ALPHA SOVEREIGN - VECTOR MEMORY BRIDGE (QDRANT)
# =================================================================
# Component Name: data/vector_db_wrapper.py
# Core Responsibility: توفير جسر للتواصل مع قاعدة بيانات المتجهات لخدمة العقل المعرفي (Pillar: Intelligence).
# Design Pattern: Facade / Adapter
# Forensic Impact: يسمح بتتبع "لماذا" اتخذ الذكاء الاصطناعي قراراً معيناً بناءً على تشابه مع أحداث ماضية.
# =================================================================

import logging
from typing import List, Dict, Any, Optional, Union
from datetime import datetime

# استيراد مكتبة Qdrant الرسمية
try:
    from qdrant_client import QdrantClient as QbClient
    from qdrant_client.http import models
except ImportError:
    # حماية النظام في حال لم يتم تثبيت المكتبة بعد
    QbClient = None
    models = None

class AlphaQdrantClient:
    """
    عميل الذاكرة المتجهية.
    يدير تخزين واسترجاع "الذكريات الدلالية" (Semantic Memories).
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 6333):
        """
        تهيئة الاتصال بقاعدة الذاكرة.
        
        Args:
            host: عنوان الخادم (Localhost للأمان).
            port: المنفذ الافتراضي لـ Qdrant.
        """
        self.logger = logging.getLogger("Alpha.Storage.Vector")
        self.host = host
        self.port = port
        self.client: Optional[QbClient] = None
        self.is_active = False

        if QbClient is None:
            self.logger.critical("DEPENDENCY_MISSING: مكتبة 'qdrant-client' غير مثبتة.")
            return

        self._connect()

    def _connect(self):
        """تأسيس الاتصال الداخلي."""
        try:
            self.client = QbClient(host=self.host, port=self.port)
            # فحص سريع للاتصال
            self.client.get_collections()
            self.is_active = True
            self.logger.info("VECTOR_DB_CONNECTED: الذاكرة الدلالية متصلة بنجاح.")
        except Exception as e:
            self.logger.error(f"VECTOR_DB_DOWN: فشل الاتصال بـ Qdrant: {e}")
            self.is_active = False

    def ensure_collection(self, collection_name: str, vector_size: int = 768):
        """
        التأكد من وجود "وعاء الذكريات" (Collection).
        إذا لم يكن موجوداً، يتم إنشاؤه بإعدادات المسافة (Cosine Similarity).
        
        Args:
            collection_name: اسم المجموعة (مثلاً 'market_patterns').
            vector_size: حجم المتجه (يعتمد على الموديل المستخدم، مثلاً BERT=768).
        """
        if not self.is_active: return

        try:
            collections = self.client.get_collections().collections
            exists = any(c.name == collection_name for c in collections)

            if not exists:
                self.logger.info(f"INIT_MEMORY: إنشاء مجموعة جديدة '{collection_name}'...")
                self.client.create_collection(
                    collection_name=collection_name,
                    vectors_config=models.VectorParams(
                        size=vector_size,
                        distance=models.Distance.COSINE # التشابه الجيبي هو الأفضل للمعاني
                    )
                )
        except Exception as e:
            self.logger.error(f"COLLECTION_ERROR: فشل إنشاء المجموعة: {e}")

    def store_memory(self, 
                     collection_name: str, 
                     vector: List[float], 
                     payload: Dict[str, Any], 
                     memory_id: Optional[Union[int, str]] = None):
        """
        تخزين "ذكرى" جديدة (Upsert).
        
        Args:
            vector: قائمة الأرقام التي تمثل المعنى (Embedding).
            payload: البيانات الوصفية (النص الأصلي، الوقت، المصدر).
            memory_id: معرف فريد (إذا ترك فارغاً سيتم توليده).
        """
        if not self.is_active: return

        try:
            # إضافة طابع زمني للحظة التذكر
            payload['stored_at'] = datetime.utcnow().isoformat()
            
            # استخدام رقم عشوائي كمعرف إذا لم يحدد
            if memory_id is None:
                import uuid
                memory_id = str(uuid.uuid4())

            point = models.PointStruct(
                id=memory_id,
                vector=vector,
                payload=payload
            )

            self.client.upsert(
                collection_name=collection_name,
                points=[point]
            )
            # self.logger.debug(f"MEMORY_STORED: تم حفظ الذكرى {memory_id} في {collection_name}")

        except Exception as e:
            self.logger.error(f"STORE_FAIL: فشل حفظ الذكرى: {e}")

    def recall_similar(self, 
                       collection_name: str, 
                       query_vector: List[float], 
                       limit: int = 5,
                       score_threshold: float = 0.7) -> List[Dict[str, Any]]:
        """
        استرجاع الذكريات المشابهة (Semantic Search).
        
        Args:
            query_vector: متجه الحالة الحالية (ما نبحث عنه).
            limit: عدد النتائج المطلوبة.
            score_threshold: أدنى نسبة تشابه مقبولة (0.0 - 1.0).
            
        Returns:
            List: قائمة بالذكريات المشابهة مع نسبة التشابه.
        """
        if not self.is_active: return []

        try:
            search_result = self.client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=limit,
                score_threshold=score_threshold
            )

            results = []
            for hit in search_result:
                results.append({
                    "id": hit.id,
                    "score": hit.score, # نسبة التطابق (جنائياً: مدى ثقة النظام)
                    "payload": hit.payload
                })
            
            return results

        except Exception as e:
            self.logger.error(f"RECALL_FAIL: فشل استرجاع الذكريات: {e}")
            return []

    def health_check(self) -> Dict[str, str]:
        """فحص حالة العقل."""
        return {
            "status": "ONLINE" if self.is_active else "OFFLINE",
            "provider": "Qdrant (Local)"
        }
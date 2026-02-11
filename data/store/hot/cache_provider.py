# -*- coding: utf-8 -*-
# ALPHA SOVEREIGN - HOT MEMORY PROVIDER (REDIS)
# =================================================================
# Component Name: data/storage/hot/cache_provider.py
# Core Responsibility: إدارة التفاعل السريع مع الذاكرة العشوائية (Redis).
# Design Pattern: Provider / Singleton Proxy
# Forensic Impact: تخزين البيانات المتطايرة (Volatile). أي دليل هنا يضيع عند انقطاع الطاقة.
# =================================================================

import json
import logging
import asyncio
from typing import Optional, Any, Dict, Union
import redis.asyncio as redis  # مكتبة Redis غير المتزامنة للأداء العالي

class CacheProvider:
    """
    مزود الذاكرة الحارة (Hot Storage).
    واجهة موحدة للتعامل مع Redis الموجود على Localhost.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 6379, db_index: int = 0):
        """
        تهيئة الاتصال.
        
        Args:
            host (str): عنوان الخادم (مثبت على 127.0.0.1 للأمان).
            port (int): المنفذ القياسي 6379.
            db_index (int): رقم قاعدة البيانات (0 للبيانات الحية، 1 للاختبار).
        """
        self.logger = logging.getLogger("Alpha.Storage.Cache")
        self.redis_url = f"redis://{host}:{port}/{db_index}"
        
        # العميل غير المتزامن (لا نحجزه هنا، يتم إنشاؤه عند الاتصال)
        self.client: Optional[redis.Redis] = None
        self._is_connected = False

    async def connect(self) -> bool:
        """
        تأسيس الاتصال بالذاكرة الحية.
        """
        try:
            self.logger.info(f"CACHE_INIT: محاولة الاتصال بـ Redis على {self.redis_url}...")
            
            # إنشاء العميل مع إعدادات فك التشفير التلقائي
            self.client = redis.from_url(
                self.redis_url, 
                decode_responses=True, # لإرجاع نصوص بدلاً من Bytes
                socket_timeout=5.0
            )
            
            # اختبار الاتصال (Ping)
            await self.client.ping()
            
            self._is_connected = True
            self.logger.info("CACHE_CONNECTED: الذاكرة الحارة جاهزة للعمل.")
            return True

        except redis.ConnectionError as e:
            self.logger.critical(f"CACHE_DOWN: فشل الاتصال بـ Redis! تأكد من تشغيل الخادم. الخطأ: {e}")
            self._is_connected = False
            return False
        except Exception as e:
            self.logger.error(f"CACHE_ERROR: خطأ غير متوقع: {e}")
            return False

    async def disconnect(self):
        """
        إغلاق الاتصال بأمان.
        """
        if self.client:
            await self.client.close()
            self._is_connected = False
            self.logger.info("CACHE_DISCONNECTED: تم فصل الذاكرة الحارة.")

    async def set(self, key: str, value: Any, ttl_seconds: int = None) -> bool:
        """
        تخزين قيمة في الذاكرة.
        
        Args:
            key: مفتاح البحث.
            value: البيانات (يتم تحويلها لـ JSON تلقائياً إذا كانت قاموساً).
            ttl_seconds: عمر البيانات بالثواني (اختياري).
        """
        if not self._is_connected:
            return False

        try:
            # التسلسل (Serialization): تحويل الكائنات المعقدة لنص
            if isinstance(value, (dict, list)):
                payload = json.dumps(value)
            else:
                payload = str(value)

            # تنفيذ الأمر
            if ttl_seconds:
                await self.client.setex(key, ttl_seconds, payload)
            else:
                await self.client.set(key, payload)
                
            return True

        except Exception as e:
            self.logger.error(f"WRITE_FAIL: فشل الكتابة للمفتاح {key}: {e}")
            return False

    async def get(self, key: str) -> Union[Dict, str, None]:
        """
        استرجاع قيمة بسرعة فائقة.
        """
        if not self._is_connected:
            return None

        try:
            data = await self.client.get(key)
            
            if data is None:
                return None

            # محاولة فك التسلسل (Deserialization) إذا كان JSON
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                return data # إرجاع النص كما هو إذا لم يكن JSON

        except Exception as e:
            self.logger.error(f"READ_FAIL: فشل القراءة للمفتاح {key}: {e}")
            return None

    async def delete(self, key: str) -> bool:
        """
        حذف مفتاح (تنظيف الأدلة أو البيانات القديمة).
        """
        if not self._is_connected:
            return False
        try:
            await self.client.delete(key)
            return True
        except Exception:
            return False

    async def exists(self, key: str) -> bool:
        """
        التحقق من وجود المفتاح.
        """
        if not self._is_connected:
            return False
        return await self.client.exists(key) > 0

    async def get_metrics(self) -> Dict[str, Any]:
        """
        إحصائيات صحة الذاكرة (Memory Health).
        مهم جنائياً لمعرفة هل الذاكرة ممتلئة (Eviction Policy Active).
        """
        if not self._is_connected:
            return {"status": "DISCONNECTED"}
        
        try:
            info = await self.client.info(section="memory")
            return {
                "used_memory_human": info.get("used_memory_human"),
                "peak_memory_human": info.get("used_memory_peak_human"),
                "status": "ONLINE"
            }
        except Exception:
            return {"status": "UNKNOWN"}
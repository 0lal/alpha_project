# -*- coding: utf-8 -*-
# ALPHA SOVEREIGN - REQUEST ID TAGGER
# =================================================================
# Component Name: shield/nexus/gateway/middleware/request_id_tagger.py
# Core Responsibility: وسم كل طلب بمعرف فريد (UUID) للتتبع الجنائي.
# Design Pattern: Interceptor / Correlation ID
# Forensic Impact: يسمح بربط السجلات المتناثرة عبر الأنظمة المختلفة (Distributed Tracing).
# =================================================================

import uuid
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

# إعداد السجلات
logger = logging.getLogger("Alpha.Shield.RequestTagger")

class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    برمجية وسيطة لضمان وجود معرف فريد لكل طلب.
    هذا المعرف سيستخدم لاحقاً في جميع سجلات النظام (Logs).
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        """
        اعتراض الطلب قبل دخوله للنظام، وختمه بالمعرف.
        """
        # 1. البحث عن معرف موجود مسبقاً (في حال وجود Load Balancer خارجي)
        # نحن نظام سيادي، غالباً لن نثق بالمعرفات الخارجية، لكننا نسجلها للمرجعية.
        incoming_id = request.headers.get("X-Request-ID")
        
        # 2. توليد معرف سيادي جديد (UUIDv4)
        # نستخدم uuid4 لأنه عشوائي تماماً وشبه مستحيل التكرار.
        request_id = str(uuid.uuid4())
        
        if incoming_id:
            # إذا كان هناك معرف خارجي، نربطه بالداخلي في السجلات (Chain of Custody)
            logger.debug(f"TRACE_LINK: External ID {incoming_id} -> Sovereign ID {request_id}")

        # 3. حقن المعرف في "حالة الطلب" (Request State)
        # هذا يسمح لباقي الكود (مثل الموجهات وقواعد البيانات) بالوصول للرقم عبر request.state.request_id
        request.state.request_id = request_id

        # 4. تنفيذ الطلب
        response = await call_next(request)

        # 5. ختم الاستجابة بالمعرف
        # نعيد الرقم للعميل (الواجهة) لكي يتمكن من استخدامه عند الإبلاغ عن مشكلة.
        response.headers["X-Request-ID"] = request_id

        return response
# -*- coding: utf-8 -*-
# ALPHA SOVEREIGN - NEXUS GATEWAY ENTRY POINT
# =================================================================
# Component Name: shield/nexus/gateway/app_entry.py
# Core Responsibility: نقطة الدخول الرئيسية (FastAPI Factory) وتشغيل الخادم.
# Design Pattern: Application Factory
# Security Level: Critical (Public Facing Interface)
# =================================================================

import logging
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# إعداد السجلات المركزية
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("Alpha.Nexus.Gateway")

# --- (Placeholder Imports) سيتم تفعيلها عند بناء الملفات التالية ---
# from shield.nexus.gateway.router import api_router
# from shield.nexus.gateway.middleware.request_id_tagger import RequestIDMiddleware
# from shield.nexus.gateway.middleware.rate_limiter import RateLimitMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    إدارة دورة حياة التطبيق (Lifecycle Manager).
    يضمن تشغيل الاتصالات (Redis/Brain) قبل استقبال أي طلب،
    وإغلاقها بأمان عند إيقاف النظام.
    """
    # 1. Startup Sequence
    logger.info("NEXUS_IGNITION: جاري تشغيل الجهاز العصبي...")
    
    # محاكاة الاتصال بالخدمات الخلفية
    # await redis_pool.connect()
    # await brain_uplink.establish()
    
    yield # هنا يعمل التطبيق ويستقبل الطلبات

    # 2. Shutdown Sequence
    logger.info("NEXUS_SHUTDOWN: جاري فصل الأنظمة وإيقاف الواجهة...")
    # await redis_pool.close()
    # await brain_uplink.disconnect()

def create_app() -> FastAPI:
    """
    مصنع التطبيق (Factory Function).
    يقوم بتجميع كل قطع الـ Nexus (الموجهات، الحماية، البروتوكولات) في تطبيق واحد.
    """
    app = FastAPI(
        title="Alpha Sovereign Nexus",
        description="The Neural Interface & Command Gateway",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs", # توثيق تلقائي للأوامر
        redoc_url=None,   # تعطيل الواجهة البديلة لتقليل الفوضى
        openapi_url="/openapi.json"
    )

    # ----------------------------------------------------------------
    # 1. جدار الحماية الأولي (CORS Guard)
    # ----------------------------------------------------------------
    # نسمح فقط للواجهة المحلية (Localhost) بالاتصال.
    # أي طلب من خارج الجهاز (IP غريب) سيتم رفضه فوراً.
    origins = [
        "http://localhost:3000",      # واجهة الويب المحلية
        "http://127.0.0.1:3000",
        "app://alpha.sovereign.tui"   # واجهة التيرمينال
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"], # أفعال محددة فقط
        allow_headers=["*"],
    )

    # ----------------------------------------------------------------
    # 2. تفعيل طبقات الحماية الوسيطة (Middleware)
    # ----------------------------------------------------------------
    # سنقوم بإلغاء التعليق عنها بمجرد إنشاء ملفاتها
    # app.add_middleware(RequestIDMiddleware) # وسم كل طلب بمعرف جنائي
    # app.add_middleware(RateLimitMiddleware) # الحماية من الطوفان (DDoS)

    # ----------------------------------------------------------------
    # 3. ربط الموجهات (Routers)
    # ----------------------------------------------------------------
    # app.include_router(api_router, prefix="/api/v1")

    # ----------------------------------------------------------------
    # 4. نقاط النهاية الأساسية (Base Endpoints)
    # ----------------------------------------------------------------
    @app.get("/health", tags=["System Status"])
    async def health_check():
        """فحص نبض النظام (Heartbeat)."""
        return {
            "status": "ONLINE",
            "system": "Alpha Nexus",
            "security_level": "SOVEREIGN_MODE"
        }

    return app

# ----------------------------------------------------------------
# نقطة التشغيل المباشر (Execution Entry Point)
# ----------------------------------------------------------------
if __name__ == "__main__":
    # تشغيل خادم Uvicorn بتكوين عالي الأداء
    # Host = 127.0.0.1 لضمان السيادة (لا يمكن الوصول إليه من الشبكة الخارجية)
    uvicorn.run(
        "app_entry:create_app",
        host="127.0.0.1",
        port=8000,
        reload=True,      # إعادة التشغيل التلقائي عند تعديل الكود (للتطوير)
        factory=True,     # إخبار uvicorn أننا نستخدم factory function
        log_level="info",
        workers=1         # عامل واحد يكفي لأننا نستخدم Async IO
    )
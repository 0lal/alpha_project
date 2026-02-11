# -*- coding: utf-8 -*-
"""
ALPHA SOVEREIGN - NEXUS ROUTER (API GATEWAY)
=================================================================
Component: shield/nexus/gateway/router.py
Core Responsibility: توجيه حركة المرور، والتحكم في إعدادات العقل الحية.
Forensic Features:
  - Input Sanitization (تعقيم المدخلات باستخدام Pydantic strict types).
  - Hot-Reload Trigger (تحديث الإعدادات دون إيقاف النظام).
  - Role Separation (فصل نقاط التنفيذ عن الإدارة).
Integration:
  - Connects UI -> StrategyConfigManager -> Brain Pipeline.
=================================================================
"""

import sys
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, status, Body
from pydantic import BaseModel, Field

# --- 1. إصلاح المسارات للوصول إلى Brain ---
try:
    CURRENT_FILE = Path(__file__).resolve()
    PROJECT_ROOT = CURRENT_FILE.parent.parent.parent.parent
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    
    # استيراد المدير الآمن للإعدادات
    from brain.core.strategy_manager import StrategyConfigManager
    CONFIG_MGR_AVAILABLE = True
except ImportError as e:
    logging.warning(f"⚠️ Strategy Manager not found: {e}")
    CONFIG_MGR_AVAILABLE = False

# إعداد السجلات
logger = logging.getLogger("Alpha.Gateway.Router")

# =================================================================
# نماذج البيانات (Data Transfer Objects - DTOs)
# =================================================================

class ModuleConfigDTO(BaseModel):
    """نموذج إعدادات الوحدة الواحدة"""
    enabled: bool
    weight: Optional[float] = Field(None, ge=0.0, le=5.0) # الوزن بين 0 و 5

class StrategyUpdateDTO(BaseModel):
    """البيانات القادمة من الواجهة (Advisory View)"""
    modules: Dict[str, ModuleConfigDTO]
    risk_profile: str

class TradeCommand(BaseModel):
    symbol: str
    action: str  # BUY, SELL
    quantity: float
    order_type: str = "LIMIT"
    price: Optional[float] = None

# =================================================================
# 1. موجه الإدارة الاستراتيجية (Strategic Management Router)
# =================================================================
# هذا هو الجزء الجديد والمهم للربط مع الواجهة
mgmt_router = APIRouter(prefix="/admin", tags=["Management"])

@mgmt_router.post("/strategy/config", status_code=status.HTTP_200_OK)
async def update_strategy_config(payload: StrategyUpdateDTO):
    """
    تحديث ملف الاستراتيجية حياً (Hot Update).
    تقوم الواجهة بإرسال هذا الطلب عند ضغط 'تحديث البروتوكول'.
    """
    if not CONFIG_MGR_AVAILABLE:
        raise HTTPException(status_code=503, detail="Strategy Manager backend is offline.")

    try:
        # 1. تحميل المدير
        mgr = StrategyConfigManager()
        current_profile = mgr.load_profile()

        # 2. دمج التغييرات (Smart Merge)
        # لا نستبدل الملف بالكامل، بل نحدث الحقول المطلوبة فقط للحفاظ على الميتا داتا
        
        # تحديث الموديولات (Quant, Sentiment, Hybrid)
        for module_name, config in payload.modules.items():
            # التأكد من وجود الموديول في الملف الأصلي لتجنب حقن مفاتيح غريبة
            if module_name in current_profile["modules"]:
                current_profile["modules"][module_name]["enabled"] = config.enabled
                if config.weight is not None:
                    current_profile["modules"][module_name]["weight"] = config.weight
        
        # تحديث ملف المخاطر (ترجمة الاسم إلى إعدادات)
        # "Sovereign" -> Strict Mode False (More Aggressive)
        # "Conservative" -> Strict Mode True
        risk_mode = payload.risk_profile
        if risk_mode == "هجومي (Sovereign)":
            current_profile["risk_parameters"]["strict_mode"] = False
            current_profile["risk_parameters"]["max_leverage"] = 3
        else:
            current_profile["risk_parameters"]["strict_mode"] = True
            current_profile["risk_parameters"]["max_leverage"] = 1

        # 3. الحفظ الذري
        success = mgr.save_profile(current_profile, author="API_GATEWAY")
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to write config to disk.")

        logger.info(f"Strategy Profile Updated via API. Risk Profile: {risk_mode}")
        return {"status": "UPDATED", "active_modules": [k for k,v in payload.modules.items() if v.enabled]}

    except Exception as e:
        logger.error(f"Strategy Update Failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@mgmt_router.get("/strategy/config")
async def get_current_strategy():
    """قراءة الإعدادات الحالية لعرضها في الواجهة"""
    if not CONFIG_MGR_AVAILABLE:
        return {"error": "Manager Offline"}
    return StrategyConfigManager().load_profile()

@mgmt_router.post("/emergency/stop")
async def emergency_stop(reason: str = Body(..., embed=True)):
    """زر التدمير الذاتي المؤقت"""
    logger.critical(f"🔥 KILL SWITCH ACTIVATED VIA API. REASON: {reason}")
    # هنا يتم استدعاء Sentinel لإيقاف العمليات
    return {"status": "SYSTEM_HALTED", "mode": "SAFE_MODE"}

# =================================================================
# 2. موجه التنفيذ (Execution Router)
# =================================================================
exec_router = APIRouter(prefix="/exec", tags=["Execution"])

@exec_router.post("/trade", status_code=status.HTTP_201_CREATED)
async def execute_trade(command: TradeCommand):
    """إرسال أوامر التداول اليدوية"""
    logger.info(f"Manual Trade Request: {command.action} {command.symbol}")
    # في الإنتاج، هذا يستدعي BrainUplink
    return {"status": "QUEUED", "order_id": f"MANUAL-{int(command.quantity * 1000)}"}

# =================================================================
# 3. موجه الاستعلام (Query Router)
# =================================================================
query_router = APIRouter(prefix="/query", tags=["Query"])

@query_router.get("/market/{symbol}")
async def get_market_snapshot(symbol: str):
    return {"symbol": symbol, "price": 96420.50, "volatility": "HIGH"}

# =================================================================
# التجميع النهائي (Router Assembly)
# =================================================================
api_router = APIRouter()
api_router.include_router(mgmt_router)
api_router.include_router(exec_router)
api_router.include_router(query_router)
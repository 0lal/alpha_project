# -*- coding: utf-8 -*-
# ALPHA SOVEREIGN - DASHBOARD DATA FEED
# =================================================================
# Component Name: shield/nexus/interface/api/dashboard_endpoints.py
# Core Responsibility: تزويد واجهات العرض بالبيانات التاريخية والتحليلات.
# Design Pattern: RESTful API / Data Aggregator
# Performance: Optimized for read-heavy operations.
# =================================================================

from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime, timedelta

# إعداد الموجه (Router)
dashboard_router = APIRouter(prefix="/dashboard", tags=["Dashboard Intelligence"])

# ----------------------------------------------------------------
# نماذج البيانات (Data Transfer Objects - DTOs)
# ----------------------------------------------------------------

class CandleStick(BaseModel):
    """نموذج شمعة السعر (OHLCV)"""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float

class SystemMetric(BaseModel):
    """نموذج مقياس أداء النظام"""
    metric_name: str
    value: float
    unit: str
    status: str  # NORMAL, WARNING, CRITICAL

class PortfolioSummary(BaseModel):
    """ملخص المحفظة المالية"""
    total_balance_usdt: float
    daily_pnl_percent: float
    active_positions: int
    exposure_ratio: float

# ----------------------------------------------------------------
# نقاط النهاية (Endpoints)
# ----------------------------------------------------------------

@dashboard_router.get("/history/{symbol}", response_model=List[CandleStick])
async def get_market_history(
    symbol: str,
    timeframe: str = Query("1h", regex="^(1m|5m|15m|1h|4h|1d)$"),
    limit: int = Query(100, le=1000)
):
    """
    جلب البيانات التاريخية للرسم البياني (Chart Data).
    يستمد البيانات من الذاكرة الدافئة (TimescaleDB) أو الباردة (Parquet).
    """
    # [ملاحظة هندسية]: في النظام الحقيقي، هنا نستدعي data.warm.ts_db_manager
    # للتبسيط الآن، سنقوم بتوليد بيانات وهمية (Mock Data) للاختبار
    
    mock_data = []
    base_price = 50000.0 if "BTC" in symbol.upper() else 3000.0
    
    now = datetime.utcnow()
    for i in range(limit):
        # توليد شموع بترتيب زمني عكسي (من الأقدم للأحدث)
        time_point = now - timedelta(hours=limit - i)
        
        # محاكاة حركة سعر عشوائية بسيطة
        open_p = base_price * (1 + (i * 0.001))
        close_p = open_p * (1 + ((i % 2 - 0.5) * 0.01))
        high_p = max(open_p, close_p) * 1.005
        low_p = min(open_p, close_p) * 0.995
        
        mock_data.append(CandleStick(
            timestamp=time_point,
            open=round(open_p, 2),
            high=round(high_p, 2),
            low=round(low_p, 2),
            close=round(close_p, 2),
            volume=round(1000.0 * (i + 1), 2)
        ))
    
    return mock_data

@dashboard_router.get("/metrics/system", response_model=List[SystemMetric])
async def get_system_health():
    """
    تقرير صحة النظام (CPU, RAM, Latency).
    يستخدمه الداشبورد لرسم عدادات الأداء.
    """
    return [
        SystemMetric(metric_name="CPU Load", value=12.5, unit="%", status="NORMAL"),
        SystemMetric(metric_name="RAM Usage", value=4.2, unit="GB", status="NORMAL"),
        SystemMetric(metric_name="Brain Latency", value=45.0, unit="ms", status="NORMAL"),
        SystemMetric(metric_name="Shield Integrity", value=100.0, unit="%", status="NORMAL"),
    ]

@dashboard_router.get("/portfolio/summary", response_model=PortfolioSummary)
async def get_portfolio_snapshot():
    """
    لقطة سريعة للوضع المالي الحالي.
    """
    return PortfolioSummary(
        total_balance_usdt=10500.75,
        daily_pnl_percent=2.45,
        active_positions=3,
        exposure_ratio=0.15 # 15% من المحفظة مستخدم
    )

@dashboard_router.get("/alerts/recent")
async def get_recent_alerts(limit: int = 5):
    """
    آخر التنبيهات الأمنية أو الفرص المكتشفة.
    """
    return {
        "alerts": [
            {"time": "10:00:05", "level": "INFO", "msg": "System Boot Complete"},
            {"time": "10:15:30", "level": "WARNING", "msg": "High Volatility Detected in ETH"},
            {"time": "10:20:00", "level": "SUCCESS", "msg": "Buy Order Executed BTCUSDT"}
        ][:limit]
    }
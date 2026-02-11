# -*- coding: utf-8 -*-
# ALPHA SOVEREIGN - HOT DATA FEED BRIDGE
# =================================================================
# Component Name: shield/nexus/bridge/data_feed.py
# Core Responsibility: سحب البيانات اللحظية من الذاكرة الحارة (Redis) وضخها للواجهة.
# Design Pattern: Adapter / Fallback Strategy
# Feature: Auto-Mocking (يعمل ببيانات وهمية إذا لم تتوفر قاعدة البيانات).
# =================================================================

import asyncio
import json
import logging
import random
from typing import Optional, Dict, Any

# محاولة استيراد مكتبة Redis غير المتزامنة
try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from shield.nexus.websocket.stream_manager import stream_manager

# إعداد السجلات
logger = logging.getLogger("Alpha.Nexus.DataFeed")

class DataFeedBridge:
    """
    جسر البيانات.
    يقوم بالاشتراك في قنوات Redis Pub/Sub للاستماع لتحديثات السوق
    وتمريرها فوراً لمدير البث (StreamManager).
    """

    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.redis_url = redis_url
        self.redis_client: Optional[redis.Redis] = None
        self.pubsub = None
        self.is_running = False
        self._task = None

    async def start(self):
        """
        تشغيل الجسر. يحاول الاتصال بـ Redis، وإذا فشل، يعمل بوضع المحاكاة.
        """
        self.is_running = True
        
        if REDIS_AVAILABLE:
            try:
                # محاولة الاتصال الحقيقي
                self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
                await self.redis_client.ping()
                logger.info("FEED_INIT: تم الاتصال بـ Redis بنجاح. بدء وضع البث المباشر.")
                
                # بدء الاستماع للقنوات الحقيقية
                self._task = asyncio.create_task(self._redis_listener())
                return
            except Exception as e:
                logger.warning(f"FEED_WARN: تعذر الاتصال بـ Redis ({e}). التحويل لوضع المحاكاة.")
        else:
            logger.warning("FEED_WARN: مكتبة Redis غير مثبتة. التحويل لوضع المحاكاة.")

        # السقوط للخلف: وضع المحاكاة (لغرض العرض والاختبار)
        self._task = asyncio.create_task(self._mock_data_generator())

    async def stop(self):
        """إيقاف الجسر."""
        self.is_running = False
        if self.pubsub:
            await self.pubsub.close()
        if self.redis_client:
            await self.redis_client.close()
        if self._task:
            self._task.cancel()
        logger.info("FEED_STOP: تم إيقاف تدفق البيانات.")

    async def _redis_listener(self):
        """
        الحلقة الرئيسية للاستماع لـ Redis Pub/Sub.
        """
        async with self.redis_client.pubsub() as pubsub:
            # الاشتراك في قنوات التحديثات المهمة
            await pubsub.subscribe("market_ticks", "system_alerts", "trade_executions")
            
            while self.is_running:
                try:
                    message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                    if message:
                        channel = message["channel"]
                        data = message["data"]
                        
                        # تمرير البيانات لمدير البث لتوزيعها على العملاء
                        # نتوقع أن البيانات في Redis هي نص JSON
                        try:
                            payload = json.loads(data)
                            await stream_manager.broadcast(channel, payload)
                        except json.JSONDecodeError:
                            pass # تجاهل البيانات التالفة
                            
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"FEED_ERROR: خطأ في استقبال Redis: {e}")
                    await asyncio.sleep(5) # انتظار قبل إعادة المحاولة

    async def _mock_data_generator(self):
        """
        مولد بيانات وهمي (Simulated Market Maker).
        يخلق سوقاً حياً "مزيفاً" لاختبار الواجهة والرسوم البيانية.
        """
        logger.info("MOCK_MODE: بدء توليد أسعار وهمية لـ BTC, ETH, SOL...")
        
        # الأسعار المبدئية
        prices = {"BTCUSDT": 65000.0, "ETHUSDT": 3500.0, "SOLUSDT": 145.0}
        
        while self.is_running:
            try:
                for symbol, price in prices.items():
                    # تغيير عشوائي للسعر (-0.2% إلى +0.2%)
                    change_pct = (random.random() - 0.5) * 0.004
                    new_price = price * (1 + change_pct)
                    prices[symbol] = new_price # تحديث السعر للدفعة القادمة
                    
                    # بناء رسالة التيك (Tick Payload)
                    tick = {
                        "type": "TICKER",
                        "symbol": symbol,
                        "price": round(new_price, 2),
                        "change": round(change_pct * 100, 3),
                        "volume": round(random.random() * 10, 4),
                        "timestamp": "LIVE"
                    }
                    
                    # بث البيانات عبر القناة الخاصة بالعملة
                    # الواجهة تشترك عادة في اسم العملة كقناة
                    await stream_manager.broadcast(symbol, tick)
                    
                    # وأيضاً عبر قناة عامة للسوق
                    await stream_manager.broadcast("market_feed", tick)

                # سرعة التحديث (10 مرات في الثانية لتبدو سلسة جداً)
                await asyncio.sleep(0.1) 
                
            except asyncio.CancelledError:
                break

# =================================================================
# Global Instance
# =================================================================
data_feed = DataFeedBridge()
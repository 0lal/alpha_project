# -*- coding: utf-8 -*-
# ALPHA SOVEREIGN - REAL-TIME STREAM MANAGER
# =================================================================
# Component Name: shield/nexus/websocket/stream_manager.py
# Core Responsibility: إدارة قنوات البث (Pub/Sub) وتوزيع البيانات الحية للمشتركين.
# Design Pattern: Publisher-Subscriber (Observer)
# Performance: Zero-Latency Broadcasting via AsyncIO
# =================================================================

import asyncio
import logging
import json
from typing import Dict, Set, Any, List
from fastapi import WebSocket, WebSocketDisconnect

# إعداد السجلات
logger = logging.getLogger("Alpha.Nexus.Stream")

class StreamManager:
    """
    مدير قنوات البث المركزي.
    يعمل كموزع بريد فائق السرعة: يستلم البيانات من (Redis/Brain)
    ويوزعها فوراً على مئات عملاء الويب المتصلين (WebSockets).
    """

    def __init__(self):
        # خريطة الاشتراكات: المفتاح هو القناة (Topic)، والقيمة هي مجموعة الاتصالات النشطة
        # مثال: "BTCUSDT" -> {ws_client_1, ws_client_2}
        self.active_subscriptions: Dict[str, Set[WebSocket]] = {}
        
        # قفل لضمان سلامة العمليات التزامنية
        self._lock = asyncio.Lock()
        
        # حالة النظام
        self.is_running = False

    async def connect(self, websocket: WebSocket, topics: List[str]):
        """
        تسجيل عميل جديد واشتراكه في قنوات محددة.
        """
        # ملاحظة: لا نقوم بـ websocket.accept() هنا لأن ClientHandler قام بها بالفعل
        # ولكن للتأكد، نفحص حالة الاتصال
        async with self._lock:
            for topic in topics:
                if topic not in self.active_subscriptions:
                    self.active_subscriptions[topic] = set()
                
                self.active_subscriptions[topic].add(websocket)
                
            # logger.info(f"STREAM_CONNECT: العميل اشترك في {topics}")

    async def disconnect(self, websocket: WebSocket, topics: List[str] = None):
        """
        إلغاء اشتراك العميل وتنظيف الموارد.
        """
        async with self._lock:
            # إذا لم يتم تحديد قنوات، نحذفه من كل مكان (قطع اتصال كامل)
            target_topics = topics if topics else list(self.active_subscriptions.keys())

            for topic in target_topics:
                if topic in self.active_subscriptions:
                    if websocket in self.active_subscriptions[topic]:
                        self.active_subscriptions[topic].remove(websocket)
                    
                    # تنظيف القنوات الفارغة لتوفير الذاكرة
                    if not self.active_subscriptions[topic]:
                        del self.active_subscriptions[topic]

    async def disconnect_zombies(self, dead_sockets: List[WebSocket]):
        """
        [ADDED] دالة خاصة لتنظيف الاتصالات الميتة دفعة واحدة.
        تستخدمها HeartbeatMonitor لإزالة الجثث بكفاءة عالية.
        """
        if not dead_sockets:
            return

        async with self._lock:
            # المرور على كل القنوات وحذف هذه المقابس منها
            for topic in list(self.active_subscriptions.keys()):
                # نستخدم discard لأنها لا ترفع خطأ إذا لم يكن العنصر موجوداً
                for ws in dead_sockets:
                    self.active_subscriptions[topic].discard(ws)
                
                # تنظيف القناة إذا فرغت
                if not self.active_subscriptions[topic]:
                    del self.active_subscriptions[topic]
        
        logger.warning(f"ZOMBIE_CLEANUP: تم إزالة {len(dead_sockets)} اتصال ميت من الذاكرة.")

    async def broadcast(self, topic: str, message: Dict[str, Any]):
        """
        بث رسالة لجميع المشتركين في قناة معينة (Fan-out).
        """
        if topic not in self.active_subscriptions:
            return

        # تحويل الرسالة لنص مرة واحدة فقط لتقليل استهلاك المعالج
        json_message = json.dumps(message)
        
        # قائمة للعملاء الذين فشل الإرسال لهم (Dead Connections)
        dead_connections = []

        # نأخذ نسخة سطحية للمجموعة لتجنب أخطاء التعديل أثناء الدوران
        # (رغم أننا لا نعدل هنا، ولكن للأمان في Async)
        subscribers = list(self.active_subscriptions[topic])
        
        for connection in subscribers:
            try:
                await connection.send_text(json_message)
            except (WebSocketDisconnect, RuntimeError):
                # العميل قطع الاتصال فجأة
                dead_connections.append(connection)
            except Exception as e:
                logger.error(f"BROADCAST_ERROR: فشل الإرسال لعميل: {e}")

        # تنظيف الاتصالات الميتة ذاتياً (Self-Healing)
        if dead_connections:
            await self._prune_connections(topic, dead_connections)

    async def _prune_connections(self, topic: str, dead_conns: List[WebSocket]):
        """
        إزالة الاتصالات الميتة التي اكتشفت أثناء البث.
        """
        async with self._lock:
            if topic in self.active_subscriptions:
                for ws in dead_conns:
                    self.active_subscriptions[topic].discard(ws)

    async def system_broadcast(self, alert_level: str, message: str):
        """
        قناة الطوارئ: رسالة تصل للجميع بلا استثناء (Override).
        تستخدم في حالات الإغلاق الطارئ أو التنبيهات الأمنية القصوى.
        """
        payload = {
            "type": "SYSTEM_ALERT",
            "level": alert_level,
            "message": message,
            "timestamp": "NOW"
        }
        
        # تجميع كل العملاء الفريدين من كل القنوات
        all_clients = set()
        # نأخذ القفل للقراءة فقط
        async with self._lock:
            for clients in self.active_subscriptions.values():
                all_clients.update(clients)
            
        json_message = json.dumps(payload)
        for client in all_clients:
            try:
                await client.send_text(json_message)
            except:
                pass # لا نهتم بالأخطاء هنا، الأولوية للسرعة

# =================================================================
# Global Instance (Singleton)
# =================================================================
# يتم إنشاء نسخة واحدة فقط يتم استيرادها في باقي أجزاء النظام
stream_manager = StreamManager()
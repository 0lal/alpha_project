# -*- coding: utf-8 -*-
# ALPHA SOVEREIGN - WEBSOCKET HEARTBEAT MONITOR
# =================================================================
# Component Name: shield/nexus/websocket/heartbeat.py
# Core Responsibility: إرسال نبضات دورية (Ping) واكتشاف الاتصالات الميتة (Zombie Connections).
# Design Pattern: Background Worker / Health Check
# Reliability: يضمن أن قائمة المشتركين تحتوي فقط على عملاء أحياء.
# =================================================================

import asyncio
import logging
import time
from typing import Set, List
from fastapi import WebSocket

# استيراد المدير للوصول لقائمة الاتصالات
from shield.nexus.websocket.stream_manager import stream_manager

# إعداد السجلات
logger = logging.getLogger("Alpha.Nexus.Heartbeat")

class HeartbeatMonitor:
    """
    مراقب النبض.
    يعمل في الخلفية (Background Task) ويقوم بفحص دوري لجميع الاتصالات المفتوحة.
    """

    def __init__(self, interval_seconds: int = 30):
        self.interval = interval_seconds
        self.is_running = False
        self._task = None

    async def start(self):
        """
        تشغيل المراقب.
        """
        self.is_running = True
        logger.info(f"HEARTBEAT_INIT: تم تفعيل ناظم ضربات القلب (كل {self.interval} ثانية).")
        
        # تشغيل الحلقة في مهمة مستقلة
        self._task = asyncio.create_task(self._beat_loop())

    async def stop(self):
        """
        إيقاف المراقب.
        """
        self.is_running = False
        if self._task:
            self._task.cancel()
        logger.info("HEARTBEAT_STOP: تم إيقاف المراقب.")

    async def _beat_loop(self):
        """
        حلقة النبض اللانهائية.
        """
        while self.is_running:
            try:
                # الانتظار للفترة المحددة
                await asyncio.sleep(self.interval)
                
                # تنفيذ الفحص
                await self._pulse()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"HEARTBEAT_CRASH: خطأ في حلقة النبض: {e}")
                # ننتظر قليلاً قبل إعادة المحاولة لتجنب التكرار السريع في حال الخطأ المستمر
                await asyncio.sleep(5)

    async def _pulse(self):
        """
        النبضة الواحدة: إرسال PING وتنظيف الموتى.
        """
        # 1. تجميع كل العملاء الفريدين (Unique Clients Snapshot)
        # العميل قد يكون مشتركاً في 10 قنوات، نريد فحصه مرة واحدة فقط.
        unique_clients: Set[WebSocket] = set()
        
        # نستخدم القفل لأخذ لقطة سريعة (Snapshot) لتجنب تعطيل البث
        async with stream_manager._lock:
            for subscribers in stream_manager.active_subscriptions.values():
                unique_clients.update(subscribers)

        if not unique_clients:
            return

        # 2. إعداد رسالة النبض
        ping_payload = {
            "type": "PING",
            "timestamp": time.time(),
            "clients_connected": len(unique_clients)
        }

        # 3. الفحص الجماعي
        dead_sockets: List[WebSocket] = []
        
        # logger.debug(f"HEARTBEAT_PULSE: فحص {len(unique_clients)} عميل...")

        for ws in unique_clients:
            try:
                # نحاول الإرسال مع مهلة زمنية قصيرة جداً (Timeout)
                # إذا تأخر العميل في الاستقبال، نعتبره يعاني من مشاكل لكن لا نقتله فوراً
                # إلا إذا فشل الإرسال تماماً (Broken Pipe)
                await asyncio.wait_for(ws.send_json(ping_payload), timeout=2.0)
            except Exception:
                # أي خطأ هنا يعني أن الاتصال غير مستقر أو مغلق
                dead_sockets.append(ws)

        # 4. تنظيف الجثث (Garbage Collection)
        if dead_sockets:
            logger.warning(f"HEARTBEAT_CLEANUP: تم اكتشاف وإزالة {len(dead_sockets)} اتصالات زومبي.")
            # إزالة الاتصالات الميتة من جميع القنوات
            await stream_manager.disconnect_zombies(dead_sockets)

# =================================================================
# تمديد وظائف StreamManager (Patching/Extension)
# =================================================================
# نحتاج لإضافة دالة disconnect_zombies في stream_manager.py أو التعامل معها هنا.
# الحل الأفضل: سنضيف دالة مساعدة هنا تستخدم disconnect الموجودة.

    async def _disconnect_zombies_helper(self, sockets: List[WebSocket]):
        """
        مساعد لإزالة مجموعة من العملاء دفعة واحدة.
        """
        for ws in sockets:
            # نستدعي دالة الفصل الموجودة في المدير (بدون تحديد قنوات ليتم حذفه من الكل)
            await stream_manager.disconnect(ws)

# نقوم بتحديث الاستدعاء في الأعلى ليكون:
# await self._disconnect_zombies_helper(dead_sockets)
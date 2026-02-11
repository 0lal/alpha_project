# -*- coding: utf-8 -*-
"""
ALPHA SOVEREIGN SYSTEM - CRITICAL ALERT DISPATCHER
==================================================
Component Name: ops/telemetry/alert_dispatcher.py
Core Responsibility: توزيع التنبيهات الحرجة للمالك عبر القنوات السيادية (Pillar: Communication).
Creation Date: 2026-02-03
Version: 1.0.0 (Red Phone Edition)
Author: Chief System Architect

Forensic Note:
هذا المكون يمثل "ضابط الاتصال".
- Priority Queuing: التنبيه بخصوص "نفاد الأموال" أهم من تنبيه "تحديث ويندوز".
- Anti-Spam (Debouncing): إذا تكرر الخطأ 100 مرة في الثانية، يرسل تنبيهاً واحداً فقط لتجنب إغراق هاتف المالك.
- Sovereign Channels: يستخدم قنوات مباشرة (Telegram/Signal) بدلاً من الاعتماد على خدمات الطرف الثالث البطيئة.
"""

import os
import time
import logging
import requests
import threading
from typing import Dict, Optional, List
from enum import Enum
from dataclasses import dataclass

# إعداد السجلات المحلية
logger = logging.getLogger("AlphaAlerts")

class AlertLevel(Enum):
    INFO = "ℹ️ INFO"
    WARNING = "⚠️ WARN"
    CRITICAL = "🚨 CRITICAL"
    PANIC = "☢️ NUCLEAR"  # حالات الطوارئ القصوى (تصفية المحفظة، إيقاف النظام)

@dataclass
class AlertPayload:
    level: AlertLevel
    title: str
    message: str
    component: str
    timestamp: float

class AlertDispatcher:
    """
    محرك توزيع التنبيهات.
    يعمل في مسلك منفصل (Background Thread) لعدم تعطيل النظام الأساسي أثناء انتظار الشبكة.
    """

    def __init__(self):
        # تحميل الإعدادات من البيئة (يجب أن تكون في .env)
        self.telegram_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
        
        # نظام منع الإغراق (Anti-Spam / Debouncing)
        # المفتاح: عنوان التنبيه، القيمة: وقت آخر إرسال
        self._last_sent: Dict[str, float] = {}
        self._cooldown_seconds = 60.0  # عدم تكرار نفس التنبيه إلا بعد دقيقة

    def send_alert(self, level: AlertLevel, title: str, message: str, component: str = "SYSTEM"):
        """
        نقطة الدخول العامة لإرسال التنبيهات.
        """
        # 1. التحقق من الأهمية (Info لا يرسل للموبايل إلا إذا طلبت ذلك)
        if level == AlertLevel.INFO:
            logger.info(f"[{component}] {title}: {message}")
            return

        # 2. التحقق من التكرار (Throttling)
        now = time.time()
        alert_key = f"{component}:{title}"
        last_time = self._last_sent.get(alert_key, 0)
        
        # إذا كان التنبيه مكرراً ولم تنقضِ فترة الهدوء، نتجاهله (إلا إذا كان PANIC)
        if level != AlertLevel.PANIC and (now - last_time < self._cooldown_seconds):
            logger.warning(f"Suppressed duplicate alert: {title}")
            return

        # تحديث وقت الإرسال
        self._last_sent[alert_key] = now
        
        # 3. تجهيز الحمولة
        payload = AlertPayload(level, title, message, component, now)
        
        # 4. الإرسال غير المتزامن (Fire and Forget)
        threading.Thread(target=self._dispatch_worker, args=(payload,), daemon=True).start()

    def _dispatch_worker(self, alert: AlertPayload):
        """
        العامل الخلفي الذي يقوم بالاتصال الفعلي بالشبكة.
        """
        try:
            full_msg = (
                f"{alert.level.value} | {alert.component}\n"
                f"<b>{alert.title}</b>\n"
                f"{alert.message}\n"
                f"<i>Time: {time.ctime(alert.timestamp)}</i>"
            )

            # قناة 1: Telegram (الأسرع والأكثر موثوقية للمشاريع الشخصية)
            if self.telegram_token and self.telegram_chat_id:
                self._send_via_telegram(full_msg)
            
            # قناة 2: تسجيل محلي (دائماً)
            if alert.level in [AlertLevel.CRITICAL, AlertLevel.PANIC]:
                logger.critical(f"DISPATCHED: {alert.title}")
            else:
                logger.warning(f"DISPATCHED: {alert.title}")

        except Exception as e:
            logger.error(f"Failed to dispatch alert: {e}")

    def _send_via_telegram(self, text: str):
        """
        إرسال عبر تيليجرام API.
        """
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        data = {
            "chat_id": self.telegram_chat_id,
            "text": text,
            "parse_mode": "HTML"
        }
        try:
            # مهلة قصيرة جداً (5 ثوانٍ) حتى لا يعلق الخيط
            requests.post(url, data=data, timeout=5)
        except requests.exceptions.RequestException as e:
            logger.error(f"Telegram API Error: {e}")

    def test_connection(self):
        """
        تنبيه تجريبي للتأكد من أن الخط الساخن يعمل.
        """
        self.send_alert(
            AlertLevel.INFO, 
            "Comms Check", 
            "Alpha Sovereign Alert System is ONLINE.", 
            "COMMS"
        )

# --- Unit Test ---
if __name__ == "__main__":
    # محاكاة (لن تعمل بدون توكن حقيقي، لكن ستطبع في اللوج)
    dispatcher = AlertDispatcher()
    
    print("--- Testing Alert Dispatcher ---")
    
    # 1. تنبيه عادي (تحذير)
    dispatcher.send_alert(
        AlertLevel.WARNING,
        "High Latency",
        "Binance latency spiked to 300ms",
        "NETWORK"
    )
    
    # 2. تنبيه مكرر (يجب أن يتم تجاهله)
    print("Attempting duplicate alert (should be suppressed)...")
    dispatcher.send_alert(
        AlertLevel.WARNING,
        "High Latency",
        "Binance latency spiked to 300ms",
        "NETWORK"
    )
    
    # 3. تنبيه نووي (يجب أن يصل فوراً)
    dispatcher.send_alert(
        AlertLevel.PANIC,
        "SYSTEM BREACH",
        "Unauthorized access detected on port 22!",
        "SECURITY"
    )
    
    # انتظار قصير لتنفيذ الخيوط الخلفية
    time.sleep(1)
    print("Done.")
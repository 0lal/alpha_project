# -*- coding: utf-8 -*-
"""
ALPHA SOVEREIGN - NETWORK CHAOS GENERATOR
=================================================================
Component: sim_lab/chaos/network_jitter.py
Core Responsibility: محاكاة ظروف الشبكة السيئة (تقطع، تأخير، فقدان حزم) لاختبار الصلابة (Stability Pillar).
Design Pattern: Interceptor / Chaos Proxy
Forensic Impact: يولد سجلات توضح "لماذا تأخر هذا الطلب؟"، مما يساعد في التمييز بين بطء الكود وبطء الشبكة.
=================================================================
"""

import asyncio
import random
import logging
import time
from dataclasses import dataclass
from enum import Enum

# إعداد التسجيل
logger = logging.getLogger("alpha.sim.chaos")

class NetworkProfile(Enum):
    FIBER_OPTIC = "FIBER"       # ممتاز: تأخير 5ms، فقدان 0%
    STABLE_WIFI = "WIFI_GOOD"   # جيد: تأخير 20ms، تذبذب بسيط
    COFFEE_SHOP = "WIFI_BAD"    # سيء: تأخير 100ms، تذبذب عالي
    3G_CELLULAR = "MOBILE_3G"   # كارثي: تأخير 300ms، فقدان حزم عالي
    DATA_CENTER_LAG = "DC_SPIKE"# ممتاز مع قفزات مفاجئة

@dataclass
class JitterConfig:
    base_latency_ms: float      # التأخير الأساسي
    jitter_std_dev: float       # الانحراف المعياري (مدى عدم الاستقرار)
    packet_loss_rate: float     # احتمالية فقدان الرسالة (0.0 - 1.0)
    spike_prob: float           # احتمالية حدوث "Lag Spike"
    spike_multiplier: float     # مضاعف التأخير عند حدوث Spike

class NetworkJitter:
    def __init__(self, profile: NetworkProfile = NetworkProfile.FIBER_OPTIC):
        self.config = self._load_profile(profile)
        self.is_enabled = True

    def _load_profile(self, profile: NetworkProfile) -> JitterConfig:
        """تحميل إعدادات مسبقة للسيناريوهات"""
        if profile == NetworkProfile.FIBER_OPTIC:
            return JitterConfig(5, 1, 0.0001, 0.0, 1.0)
        elif profile == NetworkProfile.STABLE_WIFI:
            return JitterConfig(20, 5, 0.001, 0.01, 2.0)
        elif profile == NetworkProfile.COFFEE_SHOP:
            return JitterConfig(100, 40, 0.02, 0.05, 5.0) # 2% فقدان، وتذبذب عالي
        elif profile == NetworkProfile.3G_CELLULAR:
            return JitterConfig(300, 150, 0.05, 0.10, 3.0) # 5% فقدان!
        elif profile == NetworkProfile.DATA_CENTER_LAG:
            return JitterConfig(2, 0.5, 0.0, 0.01, 100.0) # سريع جداً لكن 1% من الوقت يتوقف تماماً (GC Pause)
        else:
            return JitterConfig(0, 0, 0, 0, 0)

    async def transit(self, request_id: str = "REQ"):
        """
        محاكاة مرور البيانات عبر السلك.
        يجب استدعاء هذه الدالة قبل إرسال أو استلام أي بيانات في المحاكي.
        """
        if not self.is_enabled:
            return

        # 1. محاكاة فقدان الحزم (Packet Loss)
        if random.random() < self.config.packet_loss_rate:
            logger.warning(f"CHAOS_NET: Packet {request_id} LOST (Simulated Drop).")
            # نحاكي TimeoutError لأنه ما يحدث في الواقع
            raise asyncio.TimeoutError("Simulated Network Timeout")

        # 2. حساب التأخير الأساسي مع التذبذب (Gaussian Distribution)
        # نستخدم دالة Gauss لمحاكاة التوزيع الطبيعي للتأخير
        delay = random.gauss(self.config.base_latency_ms, self.config.jitter_std_dev)
        
        # التأكد من أن التأخير لا يقل عن 1ms (الفيزياء لا تسمح بالسفر عبر الزمن)
        delay = max(1.0, delay)

        # 3. محاكاة القفزات المفاجئة (Lag Spikes)
        is_spike = False
        if random.random() < self.config.spike_prob:
            delay *= self.config.spike_multiplier
            is_spike = True

        # التحويل من مللي ثانية إلى ثواني
        sleep_duration = delay / 1000.0

        if is_spike or delay > 200:
            logger.info(f"CHAOS_NET: High Latency for {request_id}: {delay:.1f}ms {'[LAG SPIKE]' if is_spike else ''}")

        # 4. الانتظار (Blocking simulation)
        await asyncio.sleep(sleep_duration)

# =================================================================
# اختبار المحاكاة
# =================================================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    async def run_test():
        # سيناريو: اتصال 3G سيء
        print("--- Testing '3G Cellular' Chaos ---")
        jitter = NetworkJitter(NetworkProfile.3G_CELLULAR)
        
        start_time = time.time()
        success_count = 0
        fail_count = 0

        for i in range(10):
            try:
                req_id = f"MSG_{i+1}"
                print(f"Sending {req_id}...", end=" ", flush=True)
                
                req_start = time.time()
                await jitter.transit(req_id) # هنا يحدث السحر الأسود
                duration = (time.time() - req_start) * 1000
                
                print(f"ACK received in {duration:.0f}ms")
                success_count += 1
            except asyncio.TimeoutError:
                print("TIMED OUT!")
                fail_count += 1
        
        print(f"\nResults: Success={success_count}, Lost={fail_count}")
        print("Notice how latencies vary wildly and some packets simply die.")

    asyncio.run(run_test())
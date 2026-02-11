# -*- coding: utf-8 -*-
"""
ALPHA SOVEREIGN SYSTEM - NETWORK LATENCY & JITTER PROBE
=======================================================
Component Name: ops/telemetry/network_latency_probe.py
Core Responsibility: قياس زمن التأخير (Latency) والارتعاش (Jitter) لحظياً. (Pillar: Performance)
Creation Date: 2026-02-03
Version: 1.0.0 (Speed of Light Edition)
Author: Chief System Architect

Forensic Note:
هذا المكون يقدم "دليل البراءة" في حالة فشل الصفقات.
- Latency: كم من الوقت تستغرق الرحلة؟
- Jitter: هل الطريق مستقر أم وعر؟ (الارتعاش العالي أخطر من التأخير العالي).
- Packet Loss: هل الطريق مقطوع؟

يستخدم TCP Connect بدلاً من ICMP Ping للحصول على أرقام تمثل واقع التطبيق (Application Layer).
"""

import asyncio
import time
import logging
import statistics
import socket
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple
from urllib.parse import urlparse

# إعداد السجلات
logger = logging.getLogger("AlphaNetProbe")

@dataclass
class NetworkStats:
    target: str
    avg_latency_ms: float
    jitter_ms: float
    min_latency_ms: float
    max_latency_ms: float
    packet_loss_percent: float
    status: str  # EXCELLENT, GOOD, DEGRADED, UNREACHABLE

class NetworkLatencyProbe:
    """
    مسبار شبكة غير متزامن (Asynchronous).
    يقوم بفحص عدة أهداف في وقت واحد لضمان عدم تعطيل دورة التداول الرئيسية.
    """

    def __init__(self, targets: List[str] = None):
        """
        :param targets: قائمة بعناوين URL أو IPs للفحص (مثلاً: api.binance.com)
        """
        self.targets = targets or [
            "https://api.binance.com",
            "https://api.coinbase.com",
            "https://www.google.com",   # مرجع عالمي للإنترنت
            "1.1.1.1"                   # Cloudflare DNS (مرجع سريع)
        ]
        # إعدادات الفحص
        self.samples_per_probe = 5     # عدد العينات لحساب الارتعاش
        self.timeout = 2.0             # مهلة الاتصال بالثواني

    async def scan_network_health(self) -> Dict[str, NetworkStats]:
        """
        تشغيل دورة فحص كاملة على كل الأهداف بالتوازي.
        """
        results = {}
        tasks = []

        logger.info(f"Starting Network Probe on {len(self.targets)} targets...")
        
        for target in self.targets:
            tasks.append(self._probe_single_target(target))
        
        # انتظار انتهاء الجميع (Gather)
        stats_list = await asyncio.gather(*tasks)
        
        for stat in stats_list:
            results[stat.target] = stat
            
            # تسجيل التحذيرات فقط لتقليل الضجيج
            if stat.status != "EXCELLENT":
                logger.warning(f"Network Degradation detected on {stat.target}: {stat.avg_latency_ms:.2f}ms (Jitter: {stat.jitter_ms:.2f}ms)")
        
        return results

    async def _probe_single_target(self, url_or_ip: str) -> NetworkStats:
        """
        فحص هدف واحد عدة مرات لحساب الإحصائيات.
        """
        host, port = self._parse_target(url_or_ip)
        latencies = []
        lost_packets = 0

        for _ in range(self.samples_per_probe):
            latency = await self._tcp_ping(host, port)
            if latency is not None:
                latencies.append(latency)
            else:
                lost_packets += 1
            # انتظار قصير جداً بين العينات لمنع الحظر
            await asyncio.sleep(0.05)

        # حساب الإحصائيات
        total_samples = self.samples_per_probe
        loss_pct = (lost_packets / total_samples) * 100
        
        if not latencies:
            return NetworkStats(url_or_ip, 0, 0, 0, 0, 100.0, "UNREACHABLE")

        avg_lat = statistics.mean(latencies)
        # Jitter هو الانحراف المعياري للعينات
        jitter = statistics.stdev(latencies) if len(latencies) > 1 else 0.0
        min_lat = min(latencies)
        max_lat = max(latencies)

        # تقييم الحالة
        status = "EXCELLENT"
        if loss_pct > 0: status = "DEGRADED"
        elif avg_lat > 200: status = "POOR"   # بطيء جداً للتداول اللحظي
        elif jitter > 50: status = "UNSTABLE" # اتصال غير مستقر (خطر)
        elif avg_lat > 100: status = "GOOD"
        
        return NetworkStats(
            target=url_or_ip,
            avg_latency_ms=round(avg_lat, 2),
            jitter_ms=round(jitter, 2),
            min_latency_ms=round(min_lat, 2),
            max_latency_ms=round(max_lat, 2),
            packet_loss_percent=loss_pct,
            status=status
        )

    async def _tcp_ping(self, host: str, port: int) -> Optional[float]:
        """
        قياس زمن الاتصال بمنفذ TCP.
        يعيد الزمن بالمللي ثانية، أو None في حالة الفشل.
        """
        start_time = time.perf_counter()
        try:
            # محاولة فتح اتصال (Handshake فقط)
            # wait_for يضمن عدم تجمد العملية إذا كان الخادم ميتاً
            future = asyncio.open_connection(host, port)
            reader, writer = await asyncio.wait_for(future, timeout=self.timeout)
            
            # حساب الزمن فوراً بعد النجاح
            end_time = time.perf_counter()
            duration_ms = (end_time - start_time) * 1000
            
            # إغلاق الاتصال بنظافة
            writer.close()
            await writer.wait_closed()
            
            return duration_ms
            
        except (asyncio.TimeoutError, OSError):
            return None

    def _parse_target(self, target: str) -> Tuple[str, int]:
        """
        استخراج المضيف والمنفذ من العنوان.
        """
        # إذا كان IP مباشر
        if "://" not in target:
            return target, 80 # Default port
            
        parsed = urlparse(target)
        host = parsed.hostname or target
        
        # تحديد المنفذ بناءً على البروتوكول
        if parsed.port:
            port = parsed.port
        elif parsed.scheme == "https":
            port = 443
        else:
            port = 80
            
        return host, port

# --- Unit Test ---
if __name__ == "__main__":
    # تشغيل الفحص في الحلقة الرئيسية
    probe = NetworkLatencyProbe()
    
    print("--- Starting Forensic Network Scan ---")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    results = loop.run_until_complete(probe.scan_network_health())
    
    print(f"{'TARGET':<30} | {'STATUS':<10} | {'LATENCY':<8} | {'JITTER':<8} | {'LOSS'}")
    print("-" * 80)
    
    for target, stat in results.items():
        print(f"{target:<30} | {stat.status:<10} | {stat.avg_latency_ms:6.2f}ms | {stat.jitter_ms:6.2f}ms | {stat.packet_loss_percent}%")
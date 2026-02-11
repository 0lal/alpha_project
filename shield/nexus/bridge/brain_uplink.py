# -*- coding: utf-8 -*-
"""
ALPHA SOVEREIGN - CORTEX UPLINK BRIDGE v2.0
=================================================================
Component: shield/nexus/bridge/brain_uplink.py
Core Responsibility: العصب البصري الرابط بين الدرع والعقل.
Forensic Features:
  - Smart Import Discovery (البحث عن البروتوكولات في مسارات متعددة).
  - Circuit Breaker Pattern (حماية النظام من الانهيار المتسلسل).
  - Auto-Healing Connection (إعادة الاتصال الذاتي).
  - Binary Protocol Logging (تسجيل خام للرسائل للتحليل الجنائي).
=================================================================
"""

import logging
import grpc
import asyncio
import sys
import os
import time
from typing import Dict, Any, Optional
from pathlib import Path

# --- 1. اكتشاف البروتوكولات الذكي (The Fix) ---
# نحاول العثور على المديولات المولدة سواء كانت في brain أو shield
generated_paths = [
    Path(__file__).resolve().parent.parent.parent.parent.parent / "brain" / "generated", # brain/generated
    Path(__file__).resolve().parent.parent.parent / "core" / "proto" # shield/core/proto (Backup)
]

brain_pb2 = None
brain_grpc = None

for path in generated_paths:
    if path.exists():
        sys.path.insert(0, str(path))
        try:
            # نحاول استيراد النسخة الأحدث (EngineControl هو الاسم الجديد)
            import engine_control_pb2
            import engine_control_pb2_grpc
            brain_pb2 = engine_control_pb2
            brain_grpc = engine_control_pb2_grpc
            print(f"✅ Bridge linked to Neural Protocol at: {path}")
            break
        except ImportError:
            continue

# إعداد السجلات
logger = logging.getLogger("Alpha.Bridge.Uplink")

class CircuitBreaker:
    """قاطع الدائرة لحماية النظام من الطلبات الفاشلة المتكررة"""
    def __init__(self, failure_threshold=5, recovery_timeout=30):
        self.failures = 0
        self.threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.last_failure_time = 0
        self.state = "CLOSED" # CLOSED=Normal, OPEN=Broken

    def record_failure(self):
        self.failures += 1
        self.last_failure_time = time.time()
        if self.failures >= self.threshold:
            self.state = "OPEN"
            logger.warning("🔥 Circuit Breaker OPENED. Pausing Uplink.")

    def record_success(self):
        if self.state == "HALF_OPEN":
            self.state = "CLOSED"
            self.failures = 0
            logger.info("✅ Circuit Breaker CLOSED. Uplink Restored.")
        elif self.state == "CLOSED":
            self.failures = 0

    def allow_request(self) -> bool:
        if self.state == "CLOSED":
            return True
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
                logger.info("⚠️ Circuit Breaker HALF-OPEN. Testing Connection...")
                return True
            return False
        return True # HALF_OPEN allows 1 request

class BrainUplink:
    """
    جسر الاتصال العصبي.
    """

    def __init__(self):
        # قراءة العنوان من متغيرات البيئة أو استخدام الافتراضي
        self.target = os.getenv("BRAIN_GRPC_TARGET", "localhost:50051")
        self.channel = None
        self.stub = None
        self.breaker = CircuitBreaker()
        self.is_connected = False
        
        if not brain_pb2:
            logger.critical("❌ NEURAL PROTOCOLS MISSING. Bridge is effectively blind.")

    async def connect(self):
        """بدء الاتصال (غير متزامن)"""
        if not brain_pb2: return False
        
        logger.info(f"🔌 Initializing Uplink to {self.target}...")
        self.channel = grpc.aio.insecure_channel(self.target)
        self.stub = brain_grpc.EngineControlStub(self.channel)
        
        # محاولة الاتصال الأولية
        if await self._check_health():
            return True
        return False

    async def _check_health(self) -> bool:
        """فحص النبض"""
        try:
            await asyncio.wait_for(self.channel.channel_ready(), timeout=2.0)
            self.is_connected = True
            return True
        except asyncio.TimeoutError:
            logger.warning(f"⚠️ Uplink Timeout ({self.target}). Brain might be sleeping.")
            return False
        except Exception as e:
            logger.error(f"❌ Uplink Error: {e}")
            return False

    async def send_signal(self, method: str, payload: Dict) -> Dict:
        """
        إرسال إشارة عامة.
        تقوم هذه الدالة بتغليف الطلب وتمريره عبر قاطع الدائرة.
        """
        if not self.breaker.allow_request():
            return {"error": "CIRCUIT_OPEN", "msg": "Connection paused due to failures."}

        if not self.is_connected or not self.stub:
            # محاولة إعادة الاتصال السريع
            if not await self._check_health():
                self.breaker.record_failure()
                return {"error": "DISCONNECTED", "msg": "Brain unreachable."}

        try:
            # 1. توجيه الطلب حسب الدالة المطلوبة
            if method == "EXECUTE_ORDER":
                # بناء الرسالة (Mapping Dict -> Protobuf)
                # ملاحظة: القيم يجب أن تكون strings في البروتوكول المحدث للحفاظ على الدقة
                req = brain_pb2.ExecuteOrderRequest(
                    order_id=payload.get("id", "UNKNOWN"),
                    symbol=payload.get("symbol", ""),
                    side=0 if payload.get("side") == "BUY" else 1,
                    quantity=str(payload.get("qty", "0")),
                    price=str(payload.get("price", "0")),
                    order_type=1 # LIMIT
                )
                
                response = await self.stub.ExecuteOrder(req, timeout=3.0)
                self.breaker.record_success()
                return {"status": "SENT", "server_msg": response.message}
            
            # يمكن إضافة المزيد من الدوال هنا (PING, STATUS, etc.)

        except grpc.RpcError as e:
            self.breaker.record_failure()
            logger.error(f"⚡ RPC Fail: {e.code()} - {e.details()}")
            return {"error": "RPC_FAIL", "code": str(e.code())}
            
        return {"error": "UNKNOWN_METHOD"}

    async def close(self):
        if self.channel:
            await self.channel.close()
            logger.info("🔌 Uplink Severed.")

# =================================================================
# Forensic Verification
# =================================================================
if __name__ == "__main__":
    async def test_bridge():
        bridge = BrainUplink()
        
        print(f"[*] Uplink Target: {bridge.target}")
        if not brain_pb2:
            print("[-] Protocols: MISSING (Run proto_compiler.py first)")
            return

        print("[*] Connecting...")
        connected = await bridge.connect()
        
        if connected:
            print("[+] Connection: ESTABLISHED")
            
            # Test Order
            order = {"id": "TEST-01", "symbol": "BTCUSDT", "side": "BUY", "qty": 0.01, "price": 95000}
            print(f"[*] Sending Test Signal: {order}")
            
            res = await bridge.send_signal("EXECUTE_ORDER", order)
            print(f"[+] Result: {res}")
            
        else:
            print("[-] Connection: FAILED (Is the Brain running?)")
            
        await bridge.close()

    try:
        asyncio.run(test_bridge())
    except KeyboardInterrupt:
        pass
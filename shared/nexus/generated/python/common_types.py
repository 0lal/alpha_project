# =================================================================
# ALPHA SOVEREIGN ORGANISM - PYTHON COMMON TYPES BRIDGE
# =================================================================
# File: schemas/generated/python/common_types.py
# Status: PRODUCTION (Type Aggregation & Utilities)
# Pillar: Integration (الركيزة: التكامل)
# Forensic Purpose: تجميع المكتبات المولدة، توفير أدوات FlatBuffers، وتوحيد الثوابت بين العقل (Python) والمحرك (Rust).
# =================================================================

import os
import sys
import time
import flatbuffers

# إضافة المسار الحالي للمكتبة لضمان قدرة بايثون على رؤية الملفات المولدة المجاورة
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# -----------------------------------------------------------------
# 1. استيراد بروتوكولات gRPC (THE PROTOCOLS)
# -----------------------------------------------------------------
# نقوم باستيراد جميع الخدمات التي تم تعريفها في build.rs لضمان جاهزية العقل للتعامل مع أي جزء من النظام.

try:
    # 1. خدمات العقل والمحرك الأساسية
    from . import brain_service_pb2
    from . import brain_service_pb2_grpc
    from . import engine_control_pb2
    from . import engine_control_pb2_grpc

    # 2. خدمات الحماية والأمان
    from . import shield_alert_pb2
    from . import shield_alert_pb2_grpc
    from . import auth_handshake_pb2
    from . import auth_handshake_pb2_grpc

    # 3. خدمات البيانات والتطور
    from . import telemetry_stream_pb2
    from . import telemetry_stream_pb2_grpc
    from . import swarm_consensus_pb2
    from . import swarm_consensus_pb2_grpc
    from . import evolution_manifest_pb2
    from . import evolution_manifest_pb2_grpc

except ImportError as e:
    # هذا التحذير يظهر فقط إذا لم يتم تشغيل build.rs أو مترجم البروتو بعد
    print(f"[!] Warning: Some Proto files are missing or not generated yet: {e}")
    print("[!] Action Required: Run the protocol compiler script.")

# -----------------------------------------------------------------
# 2. أدوات FlatBuffers (THE FLATBUFFERS HELPERS)
# -----------------------------------------------------------------
# فئات مساعدة للتعامل مع البيانات الثنائية عالية السرعة.

class FlatBufferUtils:
    """
    مجموعة أدوات جنائية لقراءة وكتابة البيانات الثنائية بسرعة وكفاءة.
    """

    @staticmethod
    def create_builder(initial_size=1024):
        """
        إنشاء باني للرسائل (Builder) بحجم مبدئي.
        Note: الحجم 1024 بايت كافٍ لمعظم رسائل التداول (Ticks/Orders).
        """
        return flatbuffers.Builder(initial_size)

    @staticmethod
    def timestamp_now_nanos():
        """
        الحصول على التوقيت الحالي بالنانوثانية.
        Forensic Note: يجب استخدام هذا التوقيت لضمان التوافق مع Rust u64 timestamps.
        """
        return int(time.time() * 1_000_000_000)

    @staticmethod
    def read_string(fb_string):
        """
        تحويل نص FlatBuffers (Bytes) إلى نص بايثون (UTF-8).
        يعالج حالة البيانات الفارغة (None) لتجنب انهيار البرنامج.
        """
        if fb_string is None:
            return ""
        return fb_string.decode('utf-8')

# -----------------------------------------------------------------
# 3. الثوابت المشتركة (SHARED CONSTANTS)
# -----------------------------------------------------------------
# هذه القيم تمثل "الحقيقة الواحدة" (Single Source of Truth) للنظام.

class SystemConstants:
    # هويات المكونات
    COMPONENT_BRAIN = "Alpha_Cognitive_Brain_v1"
    COMPONENT_ENGINE = "Alpha_Execution_Engine_v1"
    
    # قنوات الاتصال عبر الذاكرة المشتركة (Shared Memory Channels)
    # يجب أن تطابق هذه الأسماء تماماً ما هو مكتوب في كود Rust (Module: transport)
    SHM_MARKET_DATA = "/alpha_shm_market_tick"   # لنقل الأسعار
    SHM_ORDER_BOOK  = "/alpha_shm_orderbook"     # لنقل عمق السوق
    SHM_RISK_REPORT = "/alpha_shm_risk"          # لتقارير المخاطر الفورية
    
    # حدود الأمان (نسخة Python للمراقبة)
    MAX_LATENCY_MS = 50
    CRITICAL_LATENCY_MS = 200
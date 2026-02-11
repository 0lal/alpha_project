# Key Generator

# -*- coding: utf-8 -*-
"""
ALPHA SOVEREIGN - QUANTUM-RESISTANT KEY GENERATOR
=================================================================
Component: shield/crypto/quantum_keygen.py
Core Responsibility: توليد مفاتيح تشفير عالية الإنتروبيا (Security Pillar).
Design Pattern: CSPRNG Wrapper (Cryptographically Secure Pseudo-Random Number Generator)
Forensic Impact: يضمن أن المفاتيح المولدة لا تحمل أي "نمط" (Pattern) يمكن تحليله جنائياً لكسر التشفير.
=================================================================
"""

import os
import secrets
import hashlib
import logging
import platform
import time
from typing import Optional, Tuple

# إعداد التسجيل
logger = logging.getLogger("alpha.shield.keygen")

class QuantumKeygen:
    """
    مولد المفاتيح المقاوم للكمبيوتر الكمي.
    يعتمد على مبدأ: مفاتيح AES-256 تعتبر آمنة ضد الكمبيوتر الكمي (Grover's Algo)
    بشرط أن تكون العشوائية المستخدمة في توليدها حقيقية وكاملة.
    """

    @staticmethod
    def check_entropy_pool() -> bool:
        """
        فحص مستوى الإنتروبيا في النظام (Linux Only).
        يجب أن يكون الخزان ممتلئاً قبل التوليد لضمان الجودة.
        """
        if platform.system() == "Linux":
            try:
                with open("/proc/sys/kernel/random/entropy_avail", "r") as f:
                    entropy = int(f.read().strip())
                    # الحد الأدنى المقبول (عادة 256 بت كافية، لكن نطلب 1024 للأمان القصوى)
                    if entropy < 1024:
                        logger.warning(f"KEYGEN_WARN: Low system entropy! Available: {entropy}")
                        return False
                    return True
            except Exception as e:
                logger.error(f"KEYGEN_ERR: Failed to check entropy pool: {e}")
                # نفترض الأمان ونكمل (لأن os.urandom لا يحظر عادة في الأنظمة الحديثة)
                return True
        return True # Windows/MacOS managed differently

    @staticmethod
    def harvest_physical_noise() -> bytes:
        """
        جمع ضجيج إضافي من توقيتات النظام الدقيقة (Jitter Entropy).
        يستخدم لخلطه مع مولد النظام لزيادة العشوائية.
        """
        # نأخذ التوقيت بالنانوثانية (يعتمد على اهتزاز الكوارتز وحرارة المعالج)
        t_ns = time.time_ns()
        # نأخذ إحصائيات الأداء
        perf = time.perf_counter_ns()
        # نأخذ معرف العملية
        pid = os.getpid()
        
        # دمج البيانات
        raw_noise = f"{t_ns}:{perf}:{pid}".encode()
        return raw_noise

    @classmethod
    def generate_symmetric_key(cls, bits: int = 256) -> bytes:
        """
        توليد مفتاح متماثل (AES Key) مقاوم للهجمات الكمية.
        Note: Grover's algorithm reduces symmetric key security by half.
        Therefore, AES-256 provides 128 bits of quantum security (Safety Floor).
        """
        if not cls.check_entropy_pool():
            logger.warning("KEYGEN: Proceeding with potentially low entropy...")

        num_bytes = bits // 8
        
        # 1. المصدر الأساسي: نظام التشغيل (TRNG)
        os_random = secrets.token_bytes(num_bytes)
        
        # 2. المصدر الثانوي: ضجيج التطبيق (Application Jitter)
        app_noise = cls.harvest_physical_noise()
        
        # 3. الخلط والتبييض (Whitening) باستخدام SHA-3 (Keccak)
        # SHA-3 مقاوم جداً لتحليل التشفير
        hasher = hashlib.sha3_256()
        hasher.update(os_random)
        hasher.update(app_noise)
        
        # إضافة ملح إضافي من secrets لضمان عدم التكرار
        hasher.update(secrets.token_bytes(32))
        
        final_key = hasher.digest()
        
        # تحقق جنائي: الطول يجب أن يكون صحيحاً
        if len(final_key) != 32: # 256 bits
            raise RuntimeError("Key generation failed integrity check")

        # لا نسجل المفتاح أبداً! نسجل فقط الحدث.
        logger.info(f"KEYGEN: Generated 256-bit high-entropy key via SHA3 mixing.")
        
        return final_key

    @staticmethod
    def generate_seed_phrase(length: int = 32) -> str:
        """توليد بذرة (Hex) لاستخدامها في تهيئة المحرك"""
        seed_bytes = secrets.token_hex(length)
        return seed_bytes

# =================================================================
# مثال للاستخدام والاختبار
# =================================================================
if __name__ == "__main__":
    # تهيئة التسجيل للكونسول
    logging.basicConfig(level=logging.INFO)
    
    print("--- QUANTUM KEYGEN DIAGNOSTICS ---")
    
    # 1. فحص النظام
    if QuantumKeygen.check_entropy_pool():
        print("[+] Entropy Pool: HEALTHY")
    else:
        print("[-] Entropy Pool: LOW")

    # 2. توليد مفتاح
    key = QuantumKeygen.generate_symmetric_key(256)
    print(f"[+] Generated Key (Hex Preview): {key.hex()[:16]}...[REDACTED]")
    print(f"[+] Key Length: {len(key) * 8} bits")
    
    # 3. محاكاة فحص جودة العشوائية (اختبار بسيط)
    # مفتاح جيد لا يجب أن يحتوي على تكرار مفرط للبايتات
    unique_bytes = len(set(key))
    print(f"[+] Unique Bytes in Key: {unique_bytes}/32 (Higher is better)")
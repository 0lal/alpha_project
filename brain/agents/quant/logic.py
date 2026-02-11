# -*- coding: utf-8 -*-
"""
ALPHA SOVEREIGN - HIGH PERFORMANCE QUANT LOGIC (NUMBA/JIT)
=================================================================
Component: brain/agents/quant/logic.py
Role: المحرك الرياضي النووي (Nuclear Math Engine).
Forensic Features:
  - Zero-Copy Execution (تنفيذ بدون نسخ بيانات الذاكرة).
  - JIT Compilation (ترجمة فورية لكود الآلة).
  - Pre-Flight Warmup (تسخين مسبق لتلافي تأخير أول إشارة).
Technique: LLVM-based Compilation via Numba.
=================================================================
"""

import numpy as np
import logging
import time
# محاولة استيراد Numba مع fallback آمن
try:
    from numba import jit, float64, int64, boolean, prange
    NUMBA_AVAILABLE = True
except ImportError:
    NUMBA_AVAILABLE = False
    # تعريف decorator وهمي في حال غياب Numba لتجنب توقف النظام
    def jit(*args, **kwargs):
        def decorator(func):
            return func
        return decorator

# إعداد السجلات
logger = logging.getLogger("Alpha.Quant.Logic")

# =================================================================
# 1. JIT KERNELS (النواة الرياضية المترجمة)
# =================================================================

@jit(nopython=True, nogil=True, cache=True, fastmath=True)
def _jit_triangular_arb(rates: np.ndarray, fee: float) -> tuple:
    """
    نواة اكتشاف المراجحة المثلثية.
    المسار: Base -> A -> B -> Base
    """
    n = rates.shape[0]
    best_pnl = -1.0
    # path encoded as: asset_a_idx * 1000 + asset_b_idx
    best_path = -1 
    
    # تحسين الحلقة باستخدام prange للتوازي إذا أمكن
    # (ملاحظة: المصفوفات الصغيرة جداً أسرع بدون توازي)
    for i in range(n):
        for j in range(n):
            if i == j: continue
            
            # Base (0) -> Asset A (i) -> Asset B (j) -> Base (0)
            # نفترض أن المصفوفة هي rates[From, To]
            # الصف 0 هو العملة الأساس (مثلاً USDT)
            
            r1 = rates[0, i] # USDT -> ETH
            r2 = rates[i, j] # ETH -> BTC
            r3 = rates[j, 0] # BTC -> USDT
            
            # التحقق من سلامة البيانات
            if np.isnan(r1) or np.isnan(r2) or np.isnan(r3): continue
            
            # المبلغ النهائي بعد دورة كاملة بوحدة واحدة
            gross = r1 * r2 * r3
            
            # تطبيق الرسوم (مركبة لـ 3 صفقات)
            # Net = Gross * (1 - fee)^3
            net = gross * ((1.0 - fee) ** 3)
            
            pnl = net - 1.0
            
            if pnl > best_pnl:
                best_pnl = pnl
                best_path = i * 1000 + j

    return best_pnl, best_path

@jit(nopython=True, nogil=True, cache=True, fastmath=True)
def _jit_order_flow_imbalance(bid_p: np.ndarray, bid_v: np.ndarray, 
                              ask_p: np.ndarray, ask_v: np.ndarray, 
                              decay: float) -> float:
    """
    حساب خلل تدفق الأوامر (OFI) مع وزن متناقص للعمق.
    كلما ابتعدنا عن السعر الحالي، قل تأثير الحجم.
    """
    bid_force = 0.0
    ask_force = 0.0
    
    # Bids Side
    n_bids = len(bid_p)
    for i in range(n_bids):
        w = np.exp(-decay * i) # Exponential Decay
        bid_force += bid_v[i] * w

    # Asks Side
    n_asks = len(ask_p)
    for i in range(n_asks):
        w = np.exp(-decay * i)
        ask_force += ask_v[i] * w
        
    total = bid_force + ask_force
    if total < 1e-9: # حماية ضد القسمة على صفر
        return 0.0
        
    # النتيجة: من -1 (بيع قوي) إلى +1 (شراء قوي)
    return (bid_force - ask_force) / total

@jit(nopython=True, nogil=True, cache=True)
def _jit_ewma_volatility(prices: np.ndarray, alpha: float) -> float:
    """
    حساب التقلب الأسي (Recursive EWMA Volatility).
    """
    n = len(prices)
    if n < 2: return 0.0
    
    curr_var = 0.0
    
    # حساب العائد اللوغاريتمي والتباين في حلقة واحدة
    # نبدأ من العنصر الثاني
    prev_p = prices[0]
    
    # تهيئة التباين
    # في البداية نفترض التباين هو مربع العائد الأول
    if prev_p > 0:
        r0 = np.log(prices[1] / prev_p)
        curr_var = r0 * r0
    
    for i in range(1, n):
        curr_p = prices[i]
        if prev_p <= 0 or curr_p <= 0: 
            ret = 0.0
        else:
            ret = np.log(curr_p / prev_p)
            
        # تحديث التباين
        curr_var = (1.0 - alpha) * curr_var + alpha * (ret * ret)
        prev_p = curr_p
        
    return np.sqrt(curr_var)

# =================================================================
# 2. LOGIC CONTROLLER (المتحكم المنطقي)
# =================================================================

class QuantLogicCore:
    """
    واجهة التحكم في العمليات الرياضية.
    تقوم بتجهيز البيانات (Numpy Arrays) وتمريرها للنواة المترجمة.
    """
    
    def __init__(self):
        self.is_ready = False
        if not NUMBA_AVAILABLE:
            logger.warning("⚠️ Numba not installed. Running in Slow (Interpreted) Mode.")
        
        # تنفيذ التسخين فور الإنشاء
        self._warmup_compiler()

    def _warmup_compiler(self):
        """
        تشغيل الدوال ببيانات وهمية لإجبار المترجم (LLVM) على العمل الآن
        وليس أثناء التداول الحقيقي.
        """
        if not NUMBA_AVAILABLE: return
        
        t0 = time.time()
        logger.info("[Quant] Warming up JIT Kernels...")
        
        # 1. Arb Warmup
        dummy_matrix = np.ones((5, 5), dtype=np.float64)
        _jit_triangular_arb(dummy_matrix, 0.001)
        
        # 2. OFI Warmup
        dummy_arr = np.array([100.0, 99.0], dtype=np.float64)
        _jit_order_flow_imbalance(dummy_arr, dummy_arr, dummy_arr, dummy_arr, 0.5)
        
        # 3. Volatility Warmup
        _jit_ewma_volatility(np.random.rand(100), 0.1)
        
        dt = (time.time() - t0) * 1000
        logger.info(f"[Quant] JIT Compilation Complete in {dt:.2f}ms. Systems HOT.")
        self.is_ready = True

    def scan_triangular_arbitrage(self, rates_matrix: np.ndarray, fee_pct: float = 0.00075) -> dict:
        """واجهة مسح المراجحة"""
        # التأكد من نوع البيانات لضمان السرعة
        if rates_matrix.dtype != np.float64:
            rates_matrix = rates_matrix.astype(np.float64)
            
        pnl, path_code = _jit_triangular_arb(rates_matrix, fee_pct)
        
        if pnl > 0:
            # فك تشفير المسار
            idx_a = path_code // 1000
            idx_b = path_code % 1000
            return {
                "found": True,
                "profit_pct": float(pnl),
                "path_indices": [0, int(idx_a), int(idx_b), 0]
            }
        return {"found": False, "profit_pct": 0.0}

    def calculate_ofi(self, bids: list, asks: list, depth: int = 10) -> float:
        """واجهة حساب ضغط دفتر الأوامر"""
        # تحويل القوائم إلى Numpy Arrays (مكلف قليلاً، لذا يفضل تمرير Numpy مباشرة إذا أمكن)
        # Bids/Asks format: [[price, qty], [price, qty], ...]
        try:
            # استخراج أسرع للبيانات
            b_arr = np.array(bids[:depth], dtype=np.float64)
            a_arr = np.array(asks[:depth], dtype=np.float64)
            
            if len(b_arr) == 0 or len(a_arr) == 0:
                return 0.0
                
            return float(_jit_order_flow_imbalance(
                b_arr[:, 0], b_arr[:, 1], # Bid Price, Bid Vol
                a_arr[:, 0], a_arr[:, 1], # Ask Price, Ask Vol
                0.5 # Decay Factor
            ))
        except Exception as e:
            logger.error(f"OFI Calculation Error: {e}")
            return 0.0

    def calculate_volatility(self, prices: list, span: int = 20) -> float:
        """واجهة حساب التقلب"""
        arr = np.array(prices, dtype=np.float64)
        alpha = 2.0 / (span + 1.0)
        daily_vol = _jit_ewma_volatility(arr, alpha)
        # تحويل لسنوي
        return float(daily_vol * np.sqrt(365 * 24))

# =================================================================
# Self-Diagnostic (تشخيص ذاتي)
# =================================================================
if __name__ == "__main__":
    # اختبار السرعة والدقة
    logging.basicConfig(level=logging.INFO)
    quant = QuantLogicCore()
    
    print("\n--- Speed Test: Triangular Arbitrage ---")
    # محاكاة مصفوفة أسعار لـ 50 عملة (2500 زوج)
    matrix = np.random.uniform(0.9, 1.1, (50, 50))
    # وضع فرصة مراجحة يدوية للتأكد من الكشف
    # 0->1: 1.05 | 1->2: 1.05 | 2->0: 0.95 (Total: 1.047 - Fees)
    matrix[0, 1] = 1.05
    matrix[1, 2] = 1.05
    matrix[2, 0] = 0.95
    
    t_start = time.time()
    # تشغيل 1000 مرة لقياس الأداء
    for _ in range(1000):
        res = quant.scan_triangular_arbitrage(matrix)
    t_end = time.time()
    
    print(f"Result: {res}")
    print(f"Time for 1000 scans (50x50 matrix): {(t_end - t_start):.4f}s")
    print("Forensic Check: High Performance Logic is ACTIVE.")
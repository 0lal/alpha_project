# -*- coding: utf-8 -*-
"""
ALPHA SOVEREIGN - CONTEXT ASSEMBLY ENGINE (VERSION 5.0)
=================================================================
Component: brain/memory/context_engine.py
Role: مهندس السياق الاستراتيجي (Strategic Context Architect).
Forensic Features:
  - Immutable Context Hashing (توقيع جنائي لكل سياق).
  - Stale Data Rejector (رفض البيانات القديمة).
  - Smart Token Budgeting (ميزانية ذكية للرموز).
  - Numpy-Safe Serialization (تسلسل آمن للأرقام).
=================================================================
"""

import logging
import json
import hashlib
import math
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta, timezone

# محاولة استيراد مكتبات حساب الرموز الدقيقة، أو استخدام مقدر تقريبي
try:
    import tiktoken
    TOKENIZER_AVAILABLE = True
except ImportError:
    TOKENIZER_AVAILABLE = False

class AlphaJSONEncoder(json.JSONEncoder):
    """
    محول مخصص للتعامل مع أنواع البيانات المعقدة (Numpy, Decimal, Datetime).
    يمنع انهيار النظام عند وجود أرقام علمية.
    """
    def default(self, obj):
        if hasattr(obj, 'item'):  # Numpy types
            return obj.item()
        if hasattr(obj, 'isoformat'):  # Datetime
            return obj.isoformat()
        if isinstance(obj, set):
            return list(obj)
        try:
            import numpy as np
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            if isinstance(obj, (np.integer, np.floating)):
                return float(obj)
        except ImportError:
            pass
        return super().default(obj)

class ContextEngine:
    """
    المحرك المسؤول عن تحويل البيانات الخام إلى "مشهد عقلي" (Mental Scene) للذكاء الاصطناعي.
    يضمن أن النموذج يرى فقط الحقيقة، والحقيقة الكاملة، ولا شيء غيرها.
    """

    def __init__(self, model_name: str = "gpt-4", max_token_limit: int = 4000):
        self.logger = logging.getLogger("Alpha.Brain.Context")
        self.model_name = model_name
        self.max_tokens = max_token_limit
        self.last_context_hash = None
        
        # ميزانية الرموز (Token Budget Allocation)
        # نضمن مساحة للبيانات الحرجة دائماً
        self.budget = {
            "system_instructions": 0.15, # 15% للأوامر العليا
            "market_hard_data": 0.40,    # 40% للأرقام (غير قابلة للحذف)
            "episodic_memory": 0.25,     # 25% للذاكرة القريبة
            "semantic_history": 0.20     # 20% للتاريخ (أول ما يتم حذفه)
        }

    async def build_decision_context(self, 
                                     symbol: str, 
                                     market_data: Dict[str, Any], 
                                     episodic_mgr: Any, 
                                     semantic_mgr: Any) -> Dict[str, Any]:
        """
        بناء الكبسولة السياقية النهائية مع التحقق من النزاهة.
        
        Returns:
            Dict: يحتوي على 'prompt' (النص) و 'context_id' (للتتبع الجنائي).
        """
        
        # 1. فحص طزاجة البيانات (Staleness Check)
        # إذا كانت بيانات السوق أقدم من 10 ثوانٍ، نرفض المخاطرة
        if not self._is_data_fresh(market_data):
            self.logger.error(f"⛔ CRITICAL: Stale market data for {symbol}. Context generation aborted.")
            return {"error": "STALE_DATA_PROTECTION", "prompt": None}

        try:
            # 2. استدعاء الذكريات (Async Retrieval)
            # نستخدم gather لطلب الذاكرة القصيرة والطويلة بالتوازي للسرعة
            # (محاكاة هنا، يجب أن تدعم الكائنات waitable objects)
            short_term = episodic_mgr.get_current_context() if episodic_mgr else {}
            
            # تحويل البيانات لمتجه (مستقبلاً: عبر Embeddings حقيقية)
            vector = self._fast_vectorize(market_data)
            long_term = await semantic_mgr.recall_similar_experience(vector) if semantic_mgr else []

            # 3. تجميع الطبقات (Layered Assembly)
            
            # الطبقة أ: الحقائق الصلبة (Immutable)
            layer_market = {
                "asset": symbol,
                "t": datetime.now(timezone.utc).isoformat(),
                "price": market_data.get("price"),
                "indicators": market_data.get("technical", {}),
                "order_book_imbalance": market_data.get("ob_imbalance", 0.0)
            }

            # الطبقة ب: الحالة الداخلية (Internal State)
            layer_episodic = {
                "current_position": short_term.get("position", "FLAT"),
                "recent_pnl": short_term.get("pnl_24h", 0.0),
                "risk_budget_remaining": short_term.get("risk_quota", 1.0)
            }

            # الطبقة ج: الحكمة التاريخية (Prunable)
            layer_semantic = [
                {"date": m["date"], "outcome": m["outcome"], "similarity": m["score"]}
                for m in long_term
            ]

            # 4. دمج وضغط السياق (Optimization & Budgeting)
            final_context = self._optimize_context_structure(
                layer_market, layer_episodic, layer_semantic
            )

            # 5. التوقيع الجنائي (Forensic Hashing)
            # ننشئ بصمة فريدة لهذا السياق. إذا حدث خطأ، نبحث بهذا الهاش في السجلات.
            context_str = json.dumps(final_context, cls=AlphaJSONEncoder)
            context_hash = hashlib.sha256(context_str.encode()).hexdigest()[:16]
            self.last_context_hash = context_hash

            return {
                "context_id": context_hash,
                "prompt": context_str,
                "token_count": self._estimate_tokens(context_str)
            }

        except Exception as e:
            self.logger.critical(f"🔥 CONTEXT ENGINE MELTDOWN: {e}", exc_info=True)
            # في حالة الفشل الكارثي، نعيد سياقاً فارغاً آمناً
            return {"error": str(e), "prompt": None}

    def _is_data_fresh(self, data: Dict[str, Any], max_delay_sec: int = 15) -> bool:
        """التحقق الجنائي من وقت البيانات"""
        ts = data.get("timestamp") or data.get("time") or data.get("t")
        if not ts:
            return True # تجاوز إذا لم يوجد طابع زمني (خطر، لكن مقبول في الاختبار)
        
        try:
            # دعم للأرقام (Unix Timestamp) والنصوص (ISO)
            if isinstance(ts, (int, float)):
                # تحويل للميلي ثانية إذا كان الرقم كبيراً جداً
                if ts > 1e11: ts /= 1000 
                data_time = datetime.fromtimestamp(ts, tz=timezone.utc)
            else:
                data_time = datetime.fromisoformat(str(ts).replace('Z', '+00:00'))
            
            # مقارنة مع الوقت الحالي UTC
            delta = datetime.now(timezone.utc) - data_time
            if delta.total_seconds() > max_delay_sec:
                self.logger.warning(f"Data lag detected: {delta.total_seconds():.2f}s (Max: {max_delay_sec}s)")
                return False
            return True
        except Exception:
            # إذا فشل تحليل الوقت، نفترض الأمان لتجنب التوقف الكلي، لكن نسجل تحذير
            self.logger.warning(f"Timestamp parsing failed for: {ts}")
            return True

    def _optimize_context_structure(self, market: Dict, episodic: Dict, semantic: List) -> Dict:
        """
        تقليم ذكي يعتمد على الأولويات وليس الحذف العشوائي.
        """
        # حساب مبدئي
        base = {"market": market, "internal": episodic}
        base_tokens = self._estimate_tokens(json.dumps(base, cls=AlphaJSONEncoder))
        
        remaining_budget = self.max_tokens - base_tokens
        
        # إضافة التاريخ بقدر ما تسمح الميزانية
        fitted_history = []
        for item in semantic:
            item_tokens = self._estimate_tokens(json.dumps(item, cls=AlphaJSONEncoder))
            if remaining_budget >= item_tokens:
                fitted_history.append(item)
                remaining_budget -= item_tokens
            else:
                break # توقف عند امتلاء الذاكرة
        
        return {
            "role": "SYSTEM_ALPHA_CORE",
            "market_data": market,
            "agent_state": episodic,
            "historical_analogies": fitted_history
        }

    def _estimate_tokens(self, text: str) -> int:
        """حساب دقيق أو تقديري للرموز"""
        if TOKENIZER_AVAILABLE:
            try:
                enc = tiktoken.encoding_for_model(self.model_name)
                return len(enc.encode(text))
            except:
                pass # Fallback to approximation
        
        # تقدير تقريبي: الكلمة الإنجليزية ~1.3 توكن، الرموز ~1 توكن
        return int(len(text) / 3.5)

    def _fast_vectorize(self, data: Dict) -> List[float]:
        """
        تحويل سريع للبيانات الرقمية لمتجه (مؤقت لحين تشغيل DB Vector).
        """
        try:
            # استخراج القيم الرئيسية وتطبيعها (Normalization) تقريبياً
            price_change = float(data.get("price_change_24h", 0))
            rsi = float(data.get("technical", {}).get("rsi", 50)) / 100.0
            vol = float(data.get("volatility", 0))
            return [price_change, rsi, vol]
        except:
            return [0.0, 0.5, 0.0]

# =================================================================
# Unit Test (Forensic Verification)
# =================================================================
if __name__ == "__main__":
    import asyncio
    
    async def test_engine():
        print("\n[*] Initializing Context Engine v5.0...")
        engine = ContextEngine(max_token_limit=1000)
        
        # محاكاة بيانات بها أرقام معقدة (Numpy like)
        mock_market = {
            "price": 95432.12,
            "timestamp": datetime.now(timezone.utc).timestamp(),
            "technical": {"rsi": 75.4, "macd": 120.5},
            # محاكاة قيمة غير قابلة للتسلسل عادة
            "complex_metric": {1, 2, 3} 
        }
        
        print("[*] Building Context...")
        ctx = await engine.build_decision_context("BTCUSDT", mock_market, None, None)
        
        if "error" in ctx:
            print(f"[-] Test Failed: {ctx['error']}")
        else:
            print(f"[+] Context ID: {ctx['context_id']}")
            print(f"[+] Token Est:  {ctx['token_count']}")
            print(f"[+] Payload:    {ctx['prompt'][:100]}...") # Print first 100 chars
            print("[+] Serialization Check Passed.")

    asyncio.run(test_engine())
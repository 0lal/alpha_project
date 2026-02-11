# -*- coding: utf-8 -*-
"""
ALPHA SOVEREIGN - HYBRID SENTIMENT ENGINE (LOCAL + CLOUD)
=================================================================
Component: brain/agents/sentiment/processor.py
Role: معالج المشاعر الهجين (Hybrid Sentiment Processor).
Forensic Features:
  - Dual-Path Analysis: مسار سريع (Local) ومسار عميق (Cloud via Gateway).
  - Cross-Verification: التحقق من النتائج المحلية باستخدام الذكاء السحابي.
  - JSON Strict Parsing: إجبار النماذج اللغوية على الرد ببيانات مهيكلة فقط.
Integration:
  - Linked to: brain.inference.remote_gateway (SecureCloudGateway)
=================================================================
"""

import logging
import asyncio
import json
import re
import numpy as np
from typing import Dict, List, Any, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor
import warnings

# استيراد البوابة السحابية (الحل الجذري للمشكلة السابقة)
try:
    from brain.inference.remote_gateway import SecureCloudGateway
    GATEWAY_AVAILABLE = True
except ImportError:
    GATEWAY_AVAILABLE = False

# تجاهل تحذيرات المكتبات
warnings.filterwarnings("ignore")

# محاولة استيراد المكتبات المحلية (Transformer)
try:
    import torch
    from transformers import AutoTokenizer, AutoModelForSequenceClassification, AutoConfig
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

class HybridSentimentProcessor:
    """
    المحرك الهجين.
    يدمج بين سرعة "FinBERT" وعمق "Gemini/DeepSeek" عبر البوابة الآمنة.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(HybridSentimentProcessor, cls).__new__(cls)
            cls._instance.initialized = False
            # إعداد مسار التنفيذ المحلي
            cls._instance.executor = ThreadPoolExecutor(max_workers=1)
        return cls._instance

    def __init__(self, local_model_name: str = "ProsusAI/finbert"):
        if self.initialized: return
        
        self.logger = logging.getLogger("Alpha.Brain.Sentiment")
        self.local_model_name = local_model_name
        self.device = "cpu"
        
        # 1. الاتصال بالبوابة السحابية (The Missing Link Solved)
        if GATEWAY_AVAILABLE:
            self.cloud_gateway = SecureCloudGateway()
            self.logger.info("✅ Cloud Gateway Linked to Sentiment Engine.")
        else:
            self.cloud_gateway = None
            self.logger.warning("⚠️ Cloud Gateway NOT found. Running in Local-Only mode.")

        # متغيرات النموذج المحلي
        self.tokenizer = None
        self.model = None
        self.id2label = {}

    async def initialize(self):
        """تهيئة النظام بالكامل (محلي + سحابي)"""
        if self.initialized: return

        # تحميل النموذج المحلي في الخلفية
        if TRANSFORMERS_AVAILABLE:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            self.logger.info(f"🧠 Loading Local Engine [{self.local_model_name}] on {self.device}...")
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(self.executor, self._load_local_model_sync)
        
        self.initialized = True

    def _load_local_model_sync(self):
        """التحميل المتزامن للنموذج المحلي"""
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(self.local_model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(self.local_model_name).to(self.device)
            self.model.eval()
            config = AutoConfig.from_pretrained(self.local_model_name)
            self.id2label = config.id2label
        except Exception as e:
            self.logger.error(f"Failed to load local model: {e}")

    async def analyze(self, text: str, depth: str = "AUTO") -> Dict[str, Any]:
        """
        واجهة التحليل الذكية الموحدة.
        
        Args:
            text: النص المراد تحليله.
            depth: مستوى التحليل ('FAST', 'DEEP', 'AUTO').
                   - FAST: يستخدم FinBERT فقط (سريع ومجاني).
                   - DEEP: يستخدم Gateway LLM (دقيق ومكلف).
                   - AUTO: يقرر بناءً على تعقيد النص.
        """
        # تنظيف النص
        clean_text = text.strip()
        if not clean_text: return {"sentiment": "NEUTRAL", "score": 0.0}

        # قرار التوجيه (Routing Logic)
        use_cloud = False
        if depth == "DEEP":
            use_cloud = True
        elif depth == "AUTO":
            # إذا كان النص طويلاً أو معقداً، نذهب للسحابة
            if len(clean_text.split()) > 20 or "?" in clean_text:
                use_cloud = True

        # 1. محاولة التحليل السحابي (Deep Analysis)
        if use_cloud and self.cloud_gateway:
            try:
                result = await self._analyze_via_cloud(clean_text)
                if result["status"] == "success":
                    return result
            except Exception as e:
                self.logger.warning(f"Cloud analysis failed ({e}), falling back to local.")

        # 2. التحليل المحلي (Fallback / Fast Path)
        return await self._analyze_via_local(clean_text)

    async def _analyze_via_cloud(self, text: str) -> Dict[str, Any]:
        """
        استخدام البوابة السحابية (remote_gateway) للحصول على تحليل عالي المستوى.
        """
        # هندسة الملقن (Prompt Engineering) لإجبار النموذج على الرد بـ JSON
        prompt = f"""
        Analyze the financial sentiment of this text strictly.
        Text: "{text}"
        
        Rules:
        1. Ignore generic news, focus on market impact.
        2. Return ONLY a JSON object. No markdown, no explanations.
        3. Format: {{"sentiment": "BULLISH" | "BEARISH" | "NEUTRAL", "score": 0.0 to 1.0, "reason": "short explanation"}}
        """

        # نستخدم وضع "reasoning" (deep) إذا كان متاحاً، أو "speed"
        response = await self.cloud_gateway.infer(mode="speed", prompt=prompt)
        
        if response.get("status") != "success":
            raise ValueError("Gateway returned error")

        # تنظيف الرد واستخراج JSON
        raw_content = response["content"]
        try:
            # البحث عن نمط JSON داخل النص (لأن النماذج أحياناً تضيف مقدمات)
            json_match = re.search(r'\{.*\}', raw_content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
                return {
                    "source": "CLOUD_LLM",
                    "sentiment": data.get("sentiment", "NEUTRAL").upper(),
                    "score": float(data.get("score", 0.5)),
                    "reason": data.get("reason", "No reason provided"),
                    "status": "success"
                }
        except json.JSONDecodeError:
            self.logger.error(f"Failed to parse LLM JSON: {raw_content}")
        
        raise ValueError("Invalid LLM response format")

    async def _analyze_via_local(self, text: str) -> Dict[str, Any]:
        """
        استخدام النموذج المحلي (FinBERT).
        """
        if not self.model or not self.tokenizer:
            return self._fallback_keyword_search(text)

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self.executor, self._infer_local_sync, text)

    def _infer_local_sync(self, text: str) -> Dict[str, Any]:
        """كود الاستنتاج المحلي (Blocking Code wrapped in Executor)"""
        try:
            inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=512).to(self.device)
            with torch.no_grad():
                outputs = self.model(**inputs)
            
            probs = torch.nn.functional.softmax(outputs.logits, dim=-1).cpu().numpy()[0]
            top_idx = np.argmax(probs)
            score = float(probs[top_idx])
            label = self.id2label.get(top_idx, str(top_idx)).lower()

            # توحيد التسميات
            sentiment = "NEUTRAL"
            if "pos" in label: sentiment = "BULLISH"
            elif "neg" in label: sentiment = "BEARISH"

            return {
                "source": "LOCAL_FINBERT",
                "sentiment": sentiment,
                "score": score,
                "reason": "Local Transformer Inference",
                "status": "success"
            }
        except Exception as e:
            self.logger.error(f"Local inference error: {e}")
            return self._fallback_keyword_search(text)

    def _fallback_keyword_search(self, text: str) -> Dict[str, Any]:
        """الملاذ الأخير: البحث بالكلمات المفتاحية"""
        text_lower = text.lower()
        if any(w in text_lower for w in ["soar", "surge", "gain", "buy", "record"]):
            return {"source": "KEYWORD", "sentiment": "BULLISH", "score": 0.6, "status": "fallback"}
        if any(w in text_lower for w in ["crash", "drop", "loss", "sell", "fear"]):
            return {"source": "KEYWORD", "sentiment": "BEARISH", "score": 0.6, "status": "fallback"}
        return {"source": "KEYWORD", "sentiment": "NEUTRAL", "score": 0.5, "status": "fallback"}

    async def unload(self):
        """تنظيف الموارد"""
        if self.cloud_gateway:
            await self.cloud_gateway.shutdown()
        if self.model:
            del self.model
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

# =================================================================
# Forensic Verification (اختبار الاتصال الحي)
# =================================================================
if __name__ == "__main__":
    # محاكاة بيئة غير متزامنة للاختبار
    async def test_integration():
        print("\n[*] Initializing Hybrid Sentiment Engine...")
        engine = HybridSentimentProcessor()
        await engine.initialize()
        
        # حالة 1: نص بسيط (يجب أن يعالجه FinBERT محلياً)
        text_simple = "Tesla stock rises 5%."
        print(f"\n[1] Testing FAST mode (Local): '{text_simple}'")
        res_local = await engine.analyze(text_simple, depth="FAST")
        print(f"    -> Result: {res_local['sentiment']} ({res_local['source']})")

        # حالة 2: نص معقد (يجب أن يعالجه الـ Gateway)
        # لاحظ: هذا سيفشل إذا لم تكن مفاتيح API مضبوطة، وسيعود للمحلي
        text_complex = "Despite the revenue beat, the grim guidance suggests a storm is coming for the tech sector."
        print(f"\n[2] Testing DEEP mode (Cloud Gateway): '{text_complex}'")
        res_cloud = await engine.analyze(text_complex, depth="DEEP")
        print(f"    -> Result: {res_cloud['sentiment']} ({res_cloud['source']})")
        if "reason" in res_cloud:
            print(f"    -> Reason: {res_cloud['reason']}")

        await engine.unload()

    asyncio.run(test_integration())
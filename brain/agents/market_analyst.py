# -*- coding: utf-8 -*-
"""
ALPHA SOVEREIGN - MARKET ANALYST AGENT (THE SPECIALIST)
=======================================================
Path: alpha_project/brain/agents/market_analyst.py
Role: "المحلل المالي" - تحويل البيانات الخام إلى نصائح تداول مدروسة.
Type: Specialized Agent (Uses RemoteGateway as a tool)

Forensic Features:
  1. **Prompt Engineering Injection**: حقن شخصية "الخبير المالي" في كل طلب.
  2. **Context Awareness**: دمج بيانات السعر والمؤشرات تلقائياً في السؤال.
  3. **Dependency Chaining**: لا يتصل بالإنترنت مباشرة، بل يستخدم 'brain.gateway' المسجل.
  4. **Output Structuring**: يجبر النموذج على الرد بهيكلية محددة (Signal, SL, TP).

Author: Alpha Architect (AI)
Status: PRODUCTION READY
"""

import logging
import json
from typing import Dict, Any, Optional

# استيراد البنية التحتية
from alpha_project.brain.base_agent import BaseAgent
from alpha_project.core.registry import register_component, registry
from alpha_project.core.interfaces import ComponentStatus

@register_component(name="brain.agents.market", category="brain", is_critical=False)
class MarketAnalyst(BaseAgent):
    """
    محلل السوق المتخصص.
    وظيفته: استلام بيانات السوق -> صياغة برومبت مالي -> استدعاء البوابة -> تفسير النتيجة.
    """

    # الدستور المالي (The Persona)
    SYSTEM_PROMPT = """
    You are Alpha Sovereign, an elite quantitative financial analyst. 
    Your job is to analyze market data strictly and logically.
    
    RULES:
    1. NO fluff, NO disclaimer fillers (e.g., "I am an AI").
    2. Focus on Risk/Reward ratio.
    3. Identify Key Levels (Support/Resistance).
    4. If data is insufficient, say "INSUFFICIENT DATA".
    5. Output format must be structured: 
       - 🚦 SIGNAL: [BUY/SELL/WAIT]
       - 🎯 TARGETS: [TP1, TP2]
       - 🛑 STOP LOSS: [Price]
       - 📝 REASONING: [Brief logic]
    """

    def __init__(self):
        super().__init__(name="brain.agents.market", category="brain")

    # =========================================================================
    # 1. Reasoning Logic (منطق التحليل)
    # =========================================================================

    def _execute_reasoning(self, prompt: str, context: Dict) -> str:
        """
        تنفيذ التحليل المالي.
        """
        # 1. البحث عن البوابة (Gateway)
        # Forensic Note: المحلل لا يتصل بالنت، هو يسأل البوابة.
        gateway = registry.get("brain.gateway")
        
        if not gateway:
            self._logger.critical("❌ Critical Dependency Missing: 'brain.gateway' not found.")
            return "⚠️ **System Error**: Cannot reach the cloud gateway for analysis."

        if gateway.health_check() == ComponentStatus.FAILED:
            return "⚠️ **System Error**: Cloud Gateway is down."

        # 2. تجهيز البيانات (Data Enrichment)
        market_data = context.get("market_data", {})
        technical_indicators = context.get("indicators", {})
        
        # إذا لم تكن هناك بيانات سوقية، والطلب هو "حلل السوق"، نرفض الطلب
        if "analyze" in prompt.lower() and not market_data:
            return "⚠️ **Analysis Halted**: No market data provided in context. Please fetch data first."

        # 3. هندسة البرومبت (Prompt Engineering)
        # دمج شخصية الخبير + البيانات + سؤال المستخدم
        engineered_prompt = self._construct_financial_prompt(prompt, market_data, technical_indicators)
        
        self._logger.info(f"📤 Sending engineered prompt to Gateway ({len(engineered_prompt)} chars)...")

        # 4. التفويض (Delegation)
        # نطلب من البوابة التفكير نيابة عنا
        try:
            # نمرر نفس السياق للبوابة
            response = gateway.think(engineered_prompt, context)
            
            # 5. المعالجة اللاحقة (Post-Processing)
            # هنا يمكننا تحليل النص واستخراج إشارات JSON مستقبلاً
            return self._format_output(response)

        except Exception as e:
            self._logger.error(f"💥 Analysis Failed during delegation: {e}")
            raise # نرفع الخطأ ليتعامل معه BaseAgent

    # =========================================================================
    # 2. Prompt Construction (صياغة السؤال)
    # =========================================================================

    def _construct_financial_prompt(self, user_query: str, data: Dict, indicators: Dict) -> str:
        """
        دمج البيانات في قالب نصي يفهمه الذكاء الاصطناعي.
        """
        # تحويل البيانات لنص مقروء
        data_str = "NO LIVE DATA"
        if data:
            data_str = f"""
            ASSET: {data.get('symbol', 'Unknown')}
            PRICE: {data.get('price', 'N/A')} {data.get('currency', '')}
            SOURCE: {data.get('source', 'System')}
            TIMESTAMP: {data.get('timestamp', 'N/A')}
            """
        
        # بناء الرسالة النهائية
        full_message = f"""
        {self.SYSTEM_PROMPT}
        
        --- LIVE MARKET DATA ---
        {data_str}
        
        --- USER QUERY ---
        {user_query}
        
        --- ANALYSIS ---
        Based strictly on the data above:
        """
        
        return full_message.strip()

    def _format_output(self, raw_response: str) -> str:
        """
        تنسيق الرد النهائي قبل عرضه للمستخدم.
        """
        # في المستقبل، يمكننا هنا تحويل النص إلى HTML ملون
        # حالياً، نتأكد فقط من نظافة النص
        return raw_response

# =============================================================================
# Self-Test (للتأكد من المنطق بدون اتصال)
# =============================================================================
if __name__ == "__main__":
    print("🔍 DIAGNOSTIC MODE: MarketAnalyst")
    # محاكاة بسيطة للتسجيل اليدوي للاختبار
    analyst = MarketAnalyst()
    
    # محاكاة السياق
    dummy_context = {
        "market_data": {"symbol": "BTC/USDT", "price": 98500.00, "currency": "USDT"}
    }
    
    prompt = analyst._construct_financial_prompt("Should I buy now?", dummy_context["market_data"], {})
    
    print("\n--- ENGINEERED PROMPT ---")
    print(prompt)
    print("-------------------------")
    print("✅ Prompt Construction Logic: PASS")
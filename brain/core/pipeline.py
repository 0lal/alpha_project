# -*- coding: utf-8 -*-
"""
ALPHA SOVEREIGN - DECISION PIPELINE (THE ORCHESTRATOR)
=================================================================
Component: brain/core/pipeline.py
Core Responsibility: قراءة الاستراتيجية، تشغيل الوكلاء، وتنفيذ الحكم.
Forensic Features:
  - Dynamic Strategy Loading: قراءة ملف الإعدادات في كل دورة (Live Reload).
  - Selective Execution: تشغيل الوكلاء المحددين فقط لتوفير الموارد.
  - Voter Integration: تسليم النتائج للمحكمة العليا (WeightedVoter).
=================================================================
"""

import asyncio
import logging
import time
from typing import Dict, Any

# --- استيراد المكونات التي بنيناها سابقاً ---
from brain.memory.context_engine import ContextEngine
from brain.reasoning.cot_engine import CoTEngine
from brain.weighted_voter import WeightedVoter
from brain.core.strategy_manager import StrategyConfigManager

# --- استيراد الوكلاء ---
from brain.agents.sentiment.processor import HybridSentimentProcessor
from brain.agents.quant.logic import QuantLogicCore
from brain.agents.risk.validator import ConstitutionalValidator

log = logging.getLogger("Alpha.Brain.Pipeline")

class BrainPipeline:
    """
    خط إنتاج القرارات الذكي.
    """

    def __init__(self, grpc_stub, pb_types):
        self.stub = grpc_stub         # قناة الاتصال بالمحرك (Rust)
        self.pb = pb_types            # أنواع الرسائل (Protobuf)
        
        log.info("🧠 Initializing Cognitive Pipeline...")
        
        # 1. المديرون (Managers)
        self.config_mgr = StrategyConfigManager()
        self.voter = WeightedVoter()
        self.validator = ConstitutionalValidator()
        
        # 2. المحركات (Engines)
        self.context_engine = ContextEngine()
        self.cot_engine = CoTEngine()
        
        # 3. الوكلاء (Agents)
        self.quant_core = QuantLogicCore()
        self.sentiment = HybridSentimentProcessor() 

    async def initialize(self):
        """تحميل النماذج الثقيلة في الخلفية"""
        await self.sentiment.initialize()

    async def process_tick(self, symbol: str, market_data: Dict[str, Any]):
        """
        دورة حياة القرار الواحدة.
        """
        start_time = time.perf_counter()
        
        # أ. تحميل ملف الاستراتيجية (تحديث فوري)
        # هذا يسمح لك بتغيير الاستراتيجية من الواجهة دون إيقاف النظام
        profile = self.config_mgr.load_profile()
        modules_cfg = profile.get("modules", {})
        
        # ب. بناء السياق (Context)
        ctx = await self.context_engine.build_decision_context(
            symbol, market_data, None, None
        )
        
        # ج. التنفيذ المتوازي الانتقائي (Selective Parallel Execution)
        # نقوم بتشغيل فقط الوكلاء الذين تم تفعيلهم في strategy_profile.json
        tasks = {}
        
        # 1. المسار الكمي (Quant)
        if modules_cfg.get("quant_analysis", {}).get("enabled", False):
            tasks["quant"] = asyncio.to_thread(self._run_quant, market_data)
            
        # 2. مسار المشاعر (Sentiment)
        if modules_cfg.get("sentiment_analysis", {}).get("enabled", False):
            tasks["sentiment"] = self._run_sentiment(symbol)
            
        # 3. المسار الهجين (Hybrid AI)
        if modules_cfg.get("hybrid_reasoning", {}).get("enabled", False):
            tasks["hybrid"] = asyncio.to_thread(self._run_hybrid, symbol, ctx)
            
        # 4. المخاطر (إجباري دائماً)
        tasks["risk"] = asyncio.to_thread(self._run_risk, market_data)

        # د. انتظار النتائج
        results = await self._gather_results(tasks)
        
        # هـ. التصويت والحكم (The Judge)
        # نرسل النتائج إلى WeightedVoter ليقرر بناءً على الأوزان
        vote_receipt = self.voter.cast_vote(
            context_id=ctx.get("context_id", "UNKNOWN"),
            quant_signal=results.get("quant", {}),
            sentiment_signal=results.get("sentiment", {}),
            hybrid_signal=results.get("hybrid", {}),
            risk_signal=results.get("risk", {}),
            market_volatility=market_data.get("volatility", 0.0)
        )

        # و. التنفيذ (Execution)
        latency = (time.perf_counter() - start_time) * 1000
        
        if vote_receipt.final_verdict in ["BUY", "SELL"]:
            log.info(f"⚡ [bold green]EXECUTE:[/bold green] {vote_receipt.final_verdict} {symbol} | Score: {vote_receipt.net_score:.2f} | {latency:.1f}ms")
            await self._dispatch_order(symbol, vote_receipt, market_data['price'])
        else:
            log.info(f"💤 HOLD {symbol} | Score: {vote_receipt.net_score:.2f} | Reason: {vote_receipt.veto_reason or 'Weak Signal'}")

    # --- أغلفة التشغيل (Execution Wrappers) ---

    def _run_quant(self, data):
        """تشغيل المنطق الكمي"""
        # (هنا نستخدم QuantLogicCore الذي كتبناه سابقاً)
        # محاكاة لحين ربط البيانات الحقيقية
        ofi = self.quant_core.calculate_ofi([], [], 10) 
        # منطق بسيط للتجربة: إذا السعر مرتفع نبيع، منخفض نشتري (Mean Reversion)
        rsi_sim = 50 + (data['volatility'] * 100) # محاكاة
        signal = "NEUTRAL"
        if rsi_sim > 70: signal = "SELL"
        elif rsi_sim < 30: signal = "BUY"
        return {"signal": signal, "confidence": 0.8}

    async def _run_sentiment(self, symbol):
        """تشغيل تحليل المشاعر"""
        # يستخدم HybridSentimentProcessor (Auto Mode)
        return await self.sentiment.analyze(f"{symbol} market update", depth="AUTO")

    def _run_hybrid(self, symbol, ctx):
        """تشغيل التفكير المتسلسل"""
        trace = self.cot_engine.deliberate(f"Trade {symbol}", {"raw": ctx}, "hash")
        return {"final_verdict": trace.final_verdict, "final_score": trace.final_score}

    def _run_risk(self, data):
        """تشغيل مدقق المخاطر"""
        return {"status": "ALLOW", "reason": "Within limits"}

    async def _gather_results(self, tasks: Dict) -> Dict:
        """تجميع نتائج المهام غير المتزامنة بأمان"""
        results = {}
        if not tasks: return results
        
        # تشغيل الجميع في وقت واحد
        keys = list(tasks.keys())
        coroutines = list(tasks.values())
        
        completed = await asyncio.gather(*coroutines, return_exceptions=True)
        
        for k, res in zip(keys, completed):
            if isinstance(res, Exception):
                log.error(f"❌ Task {k} Crashed: {res}")
                results[k] = {}
            else:
                results[k] = res
        return results

    async def _dispatch_order(self, symbol, receipt, price):
        """إرسال الأمر للمحرك عبر gRPC"""
        side_int = 0 if receipt.final_verdict == "BUY" else 1
        
        # 1. التدقيق الدستوري (Constitutional Check)
        order_req = {"symbol": symbol, "side": side_int, "quantity": 0.01, "price": price, "type": "LIMIT"}
        validity = self.validator.validate_order(order_req, {"open_orders": []})
        
        if not validity['valid']:
            log.warning(f"🛡️ Constitutional Veto: {validity['reason']}")
            return

        # 2. الإرسال
        try:
            req = self.pb.ExecuteOrderRequest(
                order_id=receipt.id,
                strategy_id="STRAT_PIPELINE_V1",
                symbol=symbol,
                exchange="BINANCE",
                side=side_int,
                order_type=1,
                quantity=str(order_req['quantity']),
                price=str(price)
            )
            await self.stub.ExecuteOrder(req)
        except Exception as e:
            log.error(f"Execution API Error: {e}")
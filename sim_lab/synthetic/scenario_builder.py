# -*- coding: utf-8 -*-
"""
ALPHA SOVEREIGN - SCENARIO BUILDER FACTORY
=================================================================
Component: sim_lab/synthetic/scenario_builder.py
Core Responsibility: إنشاء سيناريوهات اختبار معقدة برمجياً (Adaptability Pillar).
Design Pattern: Builder Pattern / Fluent Interface
Forensic Impact: يسمح بتوثيق "نية الاختبار". لماذا قمنا بهذا الاختبار؟ وما هي النتيجة المتوقعة؟
=================================================================
"""

import json
import uuid
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

# إعداد التسجيل
logger = logging.getLogger("alpha.sim.builder")

class ScenarioBuilder:
    """
    باني السيناريوهات باستخدام النمط السلس (Fluent Interface).
    يسمح بتركيب الأحداث تسلسلياً.
    """
    
    def __init__(self, name: str, description: str = ""):
        self.scenario = {
            "_meta": {
                "scenario_id": f"SCN_AUTO_{str(uuid.uuid4())[:8]}",
                "name": name,
                "description": description,
                "created_at": datetime.utcnow().isoformat() + "Z",
                "difficulty": "CUSTOM"
            },
            "configuration": {
                "asset_pair": "BTC/USDT",
                "initial_price": 50000.0,
                "latency_simulation_ms": 0
            },
            "expected_outcomes": {},
            "timeline_events": []
        }

    def set_config(self, asset: str, price: float, latency_ms: int = 0):
        """إعدادات البيئة الأساسية"""
        self.scenario["configuration"]["asset_pair"] = asset
        self.scenario["configuration"]["initial_price"] = price
        self.scenario["configuration"]["latency_simulation_ms"] = latency_ms
        return self # Return self for chaining

    def expect(self, key: str, value: Any):
        """تحديد النتائج المتوقعة (للفحص الآلي)"""
        self.scenario["expected_outcomes"][key] = value
        return self

    def add_event(self, offset_ms: int, event_type: str, data: Dict[str, Any]):
        """إضافة حدث عام"""
        event = {
            "time_offset_ms": offset_ms,
            "type": event_type,
            "data": data
        }
        self.scenario["timeline_events"].append(event)
        return self

    # =========================================================
    # قوالب الأحداث الجاهزة (Helper Methods)
    # =========================================================

    def add_market_shock(self, offset_ms: int, drop_percent: float, duration_ms: int = 1000):
        """إضافة صدمة سعرية (هبوط/صعود مفاجئ)"""
        self.add_event(offset_ms, "PRICE_SHOCK", {
            "change_percent": drop_percent,
            "duration_ms": duration_ms,
            "note": f"Sudden market move of {drop_percent}%"
        })
        return self

    def add_macro_news(self, offset_ms: int, headline: str, sentiment: float):
        """إضافة خبر اقتصادي (مثل رفع الفائدة)"""
        self.add_event(offset_ms, "NEWS_FEED", {
            "headline": headline,
            "sentiment_score": sentiment, # -1.0 to 1.0
            "source": "FED_WIRE",
            "note": "Macro-economic event injection"
        })
        return self

    def add_liquidity_crisis(self, offset_ms: int, spread_widening_factor: float = 10.0):
        """سحب السيولة وتوسيع الفارق"""
        self.add_event(offset_ms, "LIQUIDITY_CHANGE", {
            "action": "WITHDRAW_MAKERS",
            "spread_multiplier": spread_widening_factor,
            "note": "Market makers leaving the book"
        })
        return self

    def add_network_outage(self, offset_ms: int, duration_ms: int):
        """قطع الاتصال (Chaos Injection)"""
        self.add_event(offset_ms, "INFRASTRUCTURE_FAIL", {
            "error_type": "CONNECTION_RESET",
            "duration_ms": duration_ms,
            "note": "Simulated internet blackout"
        })
        return self

    def build(self) -> Dict[str, Any]:
        """إنهاء البناء وإرجاع كائن السيناريو"""
        # ترتيب الأحداث زمنياً لضمان التسلسل الصحيح
        self.scenario["timeline_events"].sort(key=lambda x: x["time_offset_ms"])
        
        event_count = len(self.scenario["timeline_events"])
        logger.info(f"BUILDER: Scenario '{self.scenario['_meta']['name']}' built with {event_count} events.")
        
        return self.scenario

    def export_to_json(self, filepath: str):
        """حفظ السيناريو كملف"""
        data = self.build()
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        logger.info(f"BUILDER: Saved to {filepath}")

# =================================================================
# اختبار المحاكاة
# =================================================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("--- Constructing Custom Scenario ---")
    
    # بناء سيناريو: "The Fed Pivot Trap"
    # القصة: أخبار جيدة ترفع السوق، ثم انقطاع في الشبكة، ثم هبوط مفاجئ (Bull Trap)
    builder = ScenarioBuilder("The Fed Pivot Trap", "Tests handling of volatility during connectivity issues.")
    
    scenario = (
        builder
        .set_config("ETH/USDT", 3000.0, latency_ms=50)
        
        # 1. البداية هادئة
        .add_event(0, "MARKET_STATE", {"note": "Stable"})
        
        # 2. خبر إيجابي (الفيدرالي يخفض الفائدة)
        .add_macro_news(2000, "FED CUTS RATES BY 25 BPS", sentiment=0.9)
        
        # 3. صعود السوق (FOMO)
        .add_market_shock(3000, drop_percent=5.0, duration_ms=2000) # +5% rise
        
        # 4. انقطاع الشبكة في القمة! (أسوأ توقيت)
        .add_network_outage(5000, duration_ms=3000)
        
        # 5. أثناء الانقطاع، السوق ينهار (لا يراه النظام)
        .add_market_shock(6000, drop_percent=-10.0, duration_ms=500) # -10% crash
        
        # 6. عودة الاتصال (النظام يجد نفسه خاسراً)
        .add_event(8100, "CONNECTION_RESTORED", {"note": "System wakes up to a bloodbath"})
        
        # التوقعات: يجب أن يكون Stop-Loss قد تفعل (على السيرفر) أو النظام دخل في Safe Mode
        .expect("max_drawdown_percent", 5.0)
        .expect("system_survival", True)
        
        .build()
    )
    
    print(json.dumps(scenario, indent=2))
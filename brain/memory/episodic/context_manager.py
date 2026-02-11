# -*- coding: utf-8 -*-
# ALPHA SOVEREIGN - EPISODIC (SHORT-TERM) MEMORY MANAGER
# =================================================================
# Component Name: brain/memory/episodic/context_manager.py
# Core Responsibility: إدارة الذاكرة القصيرة المدى والسياق الحالي (Intelligence Pillar).
# Design Pattern: Sliding Window Buffer / State Manager
# Forensic Impact: يفسر "الحالة النفسية" للنظام لحظة اتخاذ القرار (لماذا كان عدوانياً أو دفاعياً؟).
# =================================================================

import logging
from collections import deque
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

class EpisodicMemory:
    """
    مدير الذاكرة العرضية (Episodic Memory).
    يحاكي الذاكرة قصيرة المدى عند البشر. يحتفظ بالأحداث الأخيرة،
    ويشكل "سياقاً" (Context) يساعد في اتخاذ القرار التالي.
    """

    def __init__(self, memory_span_minutes: int = 15):
        self.logger = logging.getLogger("Alpha.Brain.Memory.Episodic")
        self.span_minutes = memory_span_minutes
        
        # 1. المخازن المؤقتة (Sliding Windows)
        # نستخدم deque مع maxlen للحذف التلقائي للأقدم
        self.recent_trades = deque(maxlen=50)      # آخر 50 صفقة
        self.recent_alerts = deque(maxlen=20)      # آخر 20 تنبيه
        self.market_snapshots = deque(maxlen=60)   # لقطة كل دقيقة لآخر ساعة
        
        # 2. الحالة الذهنية الحالية (Current Mental State)
        self.state = {
            "mood": "NEUTRAL",          # AGGRESSIVE, DEFENSIVE, NEUTRAL, PANIC
            "stress_level": 0.0,        # 0.0 to 1.0
            "consecutive_losses": 0,    # عداد الخسائر المتتالية
            "focus_symbol": None        # العملة التي يركز عليها الانتباه حالياً
        }

    def add_event(self, event_type: str, payload: Dict[str, Any]):
        """
        تسجيل حدث جديد في الذاكرة القصيرة.
        """
        event = {
            "timestamp": datetime.utcnow(),
            "type": event_type,
            "data": payload
        }
        
        if event_type == "TRADE_EXECUTED":
            self.recent_trades.append(event)
            self._update_state_after_trade(payload)
            
        elif event_type == "SYSTEM_ALERT":
            self.recent_alerts.append(event)
            self._update_state_after_alert(payload)
            
        elif event_type == "MARKET_SNAPSHOT":
            self.recent_snapshots.append(event)

        # تنظيف الذاكرة القديمة جداً (التي تجاوزت الوقت المسموح وليس العدد)
        self._prune_old_memories()

    def get_current_context(self) -> Dict[str, Any]:
        """
        استرجاع السياق الحالي لاتخاذ القرار.
        هذا ما "يراه" الدماغ قبل أن يقرر.
        """
        return {
            "mental_state": self.state.copy(),
            "recent_activity_summary": {
                "trades_count": len(self.recent_trades),
                "alerts_count": len(self.recent_alerts),
                "last_trade_result": self._get_last_trade_result()
            },
            "short_term_bias": self._calculate_short_term_bias()
        }

    def _update_state_after_trade(self, trade_data: Dict[str, Any]):
        """تحديث الحالة النفسية بناءً على نتيجة الصفقة."""
        pnl = trade_data.get("realized_pnl", 0)
        
        if pnl < 0:
            self.state["consecutive_losses"] += 1
            # زيادة التوتر مع كل خسارة
            self.state["stress_level"] = min(1.0, self.state["stress_level"] + 0.2)
        else:
            self.state["consecutive_losses"] = 0
            # تقليل التوتر مع الربح (الاسترخاء)
            self.state["stress_level"] = max(0.0, self.state["stress_level"] - 0.1)

        # تغيير المزاج بناءً على التوتر
        if self.state["consecutive_losses"] >= 3:
            self.state["mood"] = "DEFENSIVE" # توقف عن الهجوم
            self.logger.warning("STATE_CHANGE: Too many losses -> DEFENSIVE mode.")
        elif self.state["stress_level"] < 0.2 and pnl > 0:
            self.state["mood"] = "AGGRESSIVE" # الثقة بالنفس عالية

    def _update_state_after_alert(self, alert_data: Dict[str, Any]):
        """تفاعل الذاكرة مع الإنذارات."""
        severity = alert_data.get("severity", "LOW")
        if severity == "CRITICAL":
            self.state["mood"] = "PANIC" # تجميد العمليات
            self.state["stress_level"] = 1.0

    def _prune_old_memories(self):
        """نسيان الأحداث التي انتهت صلاحيتها زمنياً."""
        cutoff = datetime.utcnow() - timedelta(minutes=self.span_minutes)
        
        # تنظيف الصفقات
        while self.recent_trades and self.recent_trades[0]["timestamp"] < cutoff:
            self.recent_trades.popleft()
            
        # تنظيف التنبيهات
        while self.recent_alerts and self.recent_alerts[0]["timestamp"] < cutoff:
            self.recent_alerts.popleft()

    def _get_last_trade_result(self) -> str:
        if not self.recent_trades:
            return "NONE"
        last_pnl = self.recent_trades[-1]["data"].get("realized_pnl", 0)
        return "WIN" if last_pnl > 0 else "LOSS"

    def _calculate_short_term_bias(self) -> str:
        """
        هل نميل للشراء أم البيع بناءً على آخر ساعة؟
        """
        # (منطق بسيط للمثال)
        if self.state["mood"] == "AGGRESSIVE":
            return "RISK_ON"
        elif self.state["mood"] in ["DEFENSIVE", "PANIC"]:
            return "RISK_OFF"
        return "NEUTRAL"
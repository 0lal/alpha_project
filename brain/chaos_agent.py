# Internal System Tester

# -*- coding: utf-8 -*-
# ALPHA SOVEREIGN - CHAOS ENGINEERING AGENT (ANTIFRAGILITY TESTER)
# =================================================================
# Component Name: brain/chaos_agent.py
# Core Responsibility: حقن الفوضى واختبار متانة النظام (Stability Pillar).
# Design Pattern: Decorator / Monkey Patching / Singleton
# Forensic Impact: يضع علامة مميزة [CHAOS_TEST] في السجلات لضمان عدم الخلط بين "الفشل المصطنع" و"الهجوم الحقيقي".
# =================================================================

import logging
import random
import time
import functools
from typing import Any, Callable, Optional

class ChaosAgent:
    """
    وكيل الفوضى.
    يستخدم لتزييف (Mock) الكوارث التقنية.
    يجب أن يكون مفعلاً فقط في بيئات: SIMULATION أو STAGING.
    محظور تماماً في LIVE_TRADING إلا في حالة "GameDay" تحت إشراف بشري.
    """
    
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ChaosAgent, cls).__new__(cls)
            cls._instance.initialized = False
        return cls._instance

    def __init__(self):
        if self.initialized: return
        self.logger = logging.getLogger("Alpha.Brain.Chaos")
        self.enabled = False
        self.chaos_probability = 0.1 # 10% احتمالية حدوث كارثة في كل استدعاء
        self.allowed_modes = ["SIMULATION", "BACKTEST"] # أوضاع الأمان
        self.current_system_mode = "UNKNOWN"
        self.initialized = True

    def activate(self, system_mode: str, probability: float = 0.05):
        """تفعيل الفوضى (بحذر شديد)."""
        self.current_system_mode = system_mode
        
        if system_mode not in self.allowed_modes:
            self.logger.critical(f"CHAOS_BLOCK: Attempted to activate chaos in {system_mode} mode! DENIED.")
            self.enabled = False
            return

        self.enabled = True
        self.chaos_probability = probability
        self.logger.warning(f"CHAOS_ACTIVATED: System is now under active sabotage simulation (Prob: {probability*100}%).")

    def deactivate(self):
        """إيقاف الفوضى فوراً."""
        self.enabled = False
        self.logger.info("CHAOS_DEACTIVATED: Peace restored.")

    def inject_chaos(self, func: Callable) -> Callable:
        """
        ديكوريتور (Decorator) يغلف الوظائف الحساسة لحقن الأخطاء.
        يتم استخدامه كـ @ChaosAgent().inject_chaos فوق الدوال.
        """
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # إذا كانت الفوضى معطلة، نفذ الدالة الأصلية فوراً
            if not self.enabled:
                return func(*args, **kwargs)

            # رمي النرد
            if random.random() < self.chaos_probability:
                scenario = random.choice(["LATENCY", "EXCEPTION", "NULL_DATA"])
                
                self.logger.warning(f"[CHAOS_INJECTION] {scenario} triggered on {func.__name__}")

                try:
                    if scenario == "LATENCY":
                        # محاكاة بطء الشبكة
                        delay = random.uniform(0.5, 5.0)
                        time.sleep(delay)
                        return func(*args, **kwargs) # تنفيذ ناجح لكن متأخر
                    
                    elif scenario == "EXCEPTION":
                        # محاكاة انهيار الخدمة
                        raise ConnectionError("Simulated Chaos Network Failure")
                    
                    elif scenario == "NULL_DATA":
                        # محاكاة فقدان البيانات
                        return None

                except Exception as e:
                    # يجب أن يمسك النظام بهذا الخطأ ويعالجه
                    self.logger.info(f"[CHAOS_RESULT] {func.__name__} raised {e}")
                    raise e 

            # التنفيذ الطبيعي
            return func(*args, **kwargs)
        return wrapper

    # أدوات للتخريب اليدوي (Manual Sabotage)
    
    def simulate_database_outage(self):
        """قطع اتصال قاعدة البيانات افتراضياً."""
        if not self.enabled: return
        self.logger.warning("[CHAOS] Simulating DB Connection Loss...")
        # (Logic to disconnect DB client would go here)

    def simulate_flash_crash(self, market_data: dict) -> dict:
        """تزوير انهيار سعري لاختبار وقف الخسارة."""
        if not self.enabled: return market_data
        
        sabotaged_data = market_data.copy()
        sabotaged_data["price"] = market_data["price"] * 0.50 # خصم 50%
        self.logger.warning(f"[CHAOS] Flash Crash Simulated! Price: {market_data['price']} -> {sabotaged_data['price']}")
        return sabotaged_data
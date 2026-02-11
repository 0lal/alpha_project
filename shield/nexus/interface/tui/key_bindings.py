# -*- coding: utf-8 -*-
# ALPHA SOVEREIGN - TACTICAL KEY BINDINGS
# =================================================================
# Component Name: shield/nexus/interface/tui/key_bindings.py
# Core Responsibility: تعريف اختصارات التحكم السريع وربطها بالأوامر التنفيذية.
# Design Pattern: Command Map / Strategy
# UX Philosophy: "Speed of thought to action" - الاستجابة في ميلي ثانية.
# =================================================================

from dataclasses import dataclass
from typing import Dict, List, Optional

@dataclass
class KeyAction:
    """
    نموذج تعريف الإجراء المرتبط بالمفتاح.
    """
    key: str            # المفتاح (مثل 'q', ' ', 'enter')
    command: str        # الأمر الداخلي الذي سيتم تنفيذه
    description: str    # وصف يظهر في شريط المساعدة
    is_critical: bool = False # هل هو أمر خطير يتطلب تمييزاً لونياً؟

class KeyBinder:
    """
    مدير الاختصارات.
    يحول الضغطات الفيزيائية إلى أوامر منطقية يفهمها النظام.
    """

    def __init__(self):
        # خريطة المفاتيح (Key Map)
        self._bindings: Dict[str, KeyAction] = {}
        self._initialize_defaults()

    def _initialize_defaults(self):
        """
        تعريف إعدادات المصنع للاختصارات (Sovereign Defaults).
        """
        # 1. أوامر الطوارئ والحماية (Critical)
        self.register(" ", "EMERGENCY_STOP", "HARD STOP (PANIC)", is_critical=True)
        self.register("l", "LOCK_TERMINAL", "Lock Session")
        
        # 2. أوامر التنقل والعرض (Navigation)
        self.register("tab", "SWITCH_VIEW", "Next Panel")
        self.register("r", "REFRESH_UI", "Force Refresh")
        self.register("c", "CLEAR_LOGS", "Clear Buffer")

        # 3. أوامر التحكم في النظام (System Control)
        self.register("q", "SYSTEM_EXIT", "Quit Nexus")
        self.register("m", "TOGGLE_MODE", "Manual/Auto Mode")
        
        # 4. أوامر التداول (Trading - تتطلب تأكيداً لاحقاً)
        self.register("b", "INIT_BUY", "Quick Buy")
        self.register("s", "INIT_SELL", "Quick Sell")

    def register(self, key: str, command: str, desc: str, is_critical: bool = False):
        """
        تسجيل اختصار جديد.
        """
        self._bindings[key] = KeyAction(key, command, desc, is_critical)

    def get_action(self, key_press: str) -> Optional[str]:
        """
        البحث عن الأمر المرتبط بالمفتاح المضغوط.
        """
        # تحويل المدخلات لأحرف صغيرة لضمان التوافق
        normalized_key = key_press.lower()
        
        binding = self._bindings.get(normalized_key)
        if binding:
            return binding.command
        return None

    def get_legend_data(self) -> List[KeyAction]:
        """
        تجهيز البيانات لعرضها في تذييل الشاشة (Footer Legend).
        يساعد المستخدم على تذكر الاختصارات.
        """
        # ترتيب العرض: الحرجة أولاً، ثم الباقي
        sorted_bindings = sorted(
            self._bindings.values(), 
            key=lambda x: (not x.is_critical, x.key)
        )
        return sorted_bindings

# =================================================================
# Global Instance
# =================================================================
key_binder = KeyBinder()
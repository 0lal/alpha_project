import os
import logging
from pathlib import Path
from PyQt6.QtCore import QObject, QUrl
from PyQt6.QtMultimedia import QSoundEffect

# --- استيراد البنية التحتية ---
from ui.core.config_provider import config
# لا نستورد logger_sink هنا لتجنب Circular Import، سنستخدم logging العادي

class SoundEngine(QObject):
    """
    محرك الصوت الهجين (The Hybrid Audio Engine).
    
    المهمة:
    تشغيل المؤثرات الصوتية للنظام.
    يبحث عن الصوت في مجلدات مختلفة بالأولوية التالية:
    1. Custom User Sounds (ui/assets/sounds/alerts)
    2. System UI Sounds (ui/assets/sounds/ui)
    3. Generated Cache (ui/assets/sounds/_generated_cache)
    """
    
    _instance = None

    def __init__(self):
        super().__init__()
        if SoundEngine._instance is not None:
            raise Exception("SoundEngine is a Singleton!")
            
        self.logger = logging.getLogger("Alpha.SoundEngine")
        
        # تحديد المسارات
        self.assets_dir = config.project_root / "ui" / "assets" / "sounds"
        self.cache_dir = self.assets_dir / "_generated_cache"
        self.ui_dir = self.assets_dir / "ui"
        self.alerts_dir = self.assets_dir / "alerts"
        
        # تخزين المؤثرات المحملة في الذاكرة لعدم إعادة تحميلها كل مرة
        self._effects_cache = {}
        
        # التأكد من أن الصوت مفعل من الإعدادات
        self.enabled = config.get("audio.enabled", True)
        
        self.logger.info("🔊 SoundEngine Initialized.")

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = SoundEngine()
        return cls._instance

    def play(self, sound_name: str):
        """
        تشغيل ملف صوتي بالاسم.
        sound_name: اسم الملف مع الامتداد (مثلاً: "success.wav" أو "click.wav")
        """
        if not self.enabled:
            return

        # إذا كان الصوت محملاً مسبقاً، شغله فوراً
        if sound_name in self._effects_cache:
            self._effects_cache[sound_name].play()
            return

        # البحث عن الملف (Logic: Custom -> UI -> Generated)
        target_path = self._find_sound_file(sound_name)
        
        if target_path and target_path.exists():
            try:
                effect = QSoundEffect()
                effect.setSource(QUrl.fromLocalFile(str(target_path)))
                effect.setVolume(1.0) # ماكس فوليوم
                
                # تخزينه في الذاكرة
                self._effects_cache[sound_name] = effect
                
                effect.play()
            except Exception as e:
                self.logger.error(f"Failed to play sound {sound_name}: {e}")
        else:
            self.logger.warning(f"Sound file not found: {sound_name}")

    def _find_sound_file(self, filename: str) -> Path:
        """البحث الذكي عن الملف في المجلدات"""
        # 1. هل وضعه المستخدم في التنبيهات؟
        p1 = self.alerts_dir / filename
        if p1.exists(): return p1
        
        # 2. هل هو صوت واجهة أساسي؟
        p2 = self.ui_dir / filename
        if p2.exists(): return p2
        
        # 3. هل هو مولد تلقائياً (في الكاش)؟
        p3 = self.cache_dir / filename
        if p3.exists(): return p3
        
        return None

    def set_enabled(self, enabled: bool):
        self.enabled = enabled

# Global Access Point (للتهيئة المبكرة إذا لزم الأمر)
# لكننا نفضل استخدام SoundEngine.get_instance()
import logging
from ui.assets._generators.icon_gen import IconGenerator
from ui.assets._generators.audio_gen import AudioGenerator

# إعداد مسجل الأحداث لهذا المجلد
logger = logging.getLogger("Alpha.Assets")

def initialize_assets():
    """
    دالة الفحص الذاتي والشفاء (Self-Healing Initialization).
    تضمن وجود جميع الموارد الضرورية قبل إقلاع الواجهة.
    """
    logger.info("📂 Verifying asset integrity...")

    # 1. تشغيل مصنع الأيقونات
    try:
        icon_gen = IconGenerator()
        icon_gen.generate_defaults_if_missing()
    except Exception as e:
        logger.error(f"❌ Icon generation failed: {e}")

    # 2. تشغيل مصنع الصوتيات
    try:
        audio_gen = AudioGenerator()
        audio_gen.generate_defaults_if_missing()
    except Exception as e:
        logger.error(f"❌ Audio generation failed: {e}")

    logger.info("✅ Assets are ready.")

# تنفيذ الفحص عند الاستيراد (مرة واحدة فقط)
initialize_assets()
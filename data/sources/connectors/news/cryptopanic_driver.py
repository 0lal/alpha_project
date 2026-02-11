import logging
from typing import Dict, Any, Optional, List, Tuple

# استيراد القالب الأم الذي يطبق سياسات الأمان، المحاسبة، والتدقيق الجنائي
from connectors.base_connector import BaseConnector

# إعداد السجل الجنائي الخاص بـ CryptoPanic
logger = logging.getLogger("Alpha.Drivers.CryptoPanic")

class CryptoPanicDriver(BaseConnector):
    """
    الذراع التنفيذي لأخبار العملات الرقمية (CryptoPanic News Aggregator).
    
    المهام الجنائية:
    1. العمل كمستشعر طوارئ (Emergency Sensor) لجلب الأخبار عند انهيار/انفجار السوق.
    2. إدارة الندرة القصوى (100 طلب/شهر) بصرامة، ومنع الاستدعاءات العشوائية.
    3. استخراج الأخبار المصنفة كـ "مهمة" فقط (Important Filter) لتجنب الضوضاء.
    """

    def __init__(self):
        """
        تهيئة الدرايفر.
        """
        # تمرير اسم المزود للقالب الأم لجلب الإعدادات من cryptopanic_key.json
        super().__init__("cryptopanic")
        
        # استخراج المفتاح من ملفات التكوين الآمنة
        self.auth_token = self.config.get("credentials", {}).get("api_key")
        
        if not self.auth_token:
            logger.critical("❌ FATAL: CryptoPanic Auth Token is missing from secure configuration!")

    def build_url(self, endpoint_key: str) -> str:
        """
        بناء الرابط. 
        CryptoPanic يمتلك نقطة وصول واحدة رئيسية للأخبار.
        """
        # الرابط الأساسي: https://cryptopanic.com/api/v2/posts/
        base_url = self.config.get("connection_policy", {}).get("base_url", "https://cryptopanic.com/api/v2/posts/")
        
        # لا نحتاج لإضافة مسارات إضافية، نقطة الوصول الافتراضية تكفي
        return base_url

    def get_default_params(self) -> Dict[str, str]:
        """
        [تجاوز إجباري]
        CryptoPanic يشترط تمرير المفتاح كمعامل في الرابط (Query Parameter).
        كما نشترط أن تكون الأخبار عامة (public=true).
        """
        return {
            "auth_token": self.auth_token,
            "public": "true"
        }

    def fetch(self, endpoint_key: str, **params) -> Optional[List[Dict[str, Any]]]:
        """
        [تجاوز جنائي]
        إرسال الطلب عبر القالب الأم لضمان المرور على المحاسب (Usage Tracker) والمترجم.
        إذا نفد الرصيد، القالب الأم سيرفض الاتصال وسيعود النظام بـ None.
        """
        # تحذير أمني في السجلات لتذكير النظام بندرة هذا المورد
        logger.warning(f"🚨 FIRING CRYPTOPANIC EMERGENCY SENSOR. (Scarcity Alert: 100 Req/Month limits apply). Params: {params}")
        
        # القالب الأم سيقوم بجلب البيانات، والمترجم (Data Normalizer) سيحول {"results": [...]} إلى قائمة موحدة
        result = super().fetch(endpoint_key, **params)
        
        # بروتوكول "أنا أعمى": إذا لم تكن هناك بيانات، نعيد None (لا نخترع أخباراً)
        if result is None:
            return None
            
        return result

    # =========================================================================
    # أذرع الاستخبارات الإخبارية (News Intelligence Arms)
    # =========================================================================

    def get_market_panic_news(self) -> Optional[List[Dict[str, Any]]]:
        """
        [أداة الطوارئ 1] جلب الأخبار المصنفة كـ "مهمة جداً" (Important) للسوق بالكامل.
        تستخدم عندما يهبط البيتكوين فجأة بنسبة 5% لمعرفة السبب الماكرو-اقتصادي.
        """
        params = {
            "kind": "news",
            "filter": "important" # فلتر يقلل الضوضاء (Noise Reduction) ويجلب الكوارث/الأحداث الكبرى فقط
        }
        
        logger.info("📰 Fetching Global Market Panic News (Filter: Important)")
        return self.fetch("latest_news", **params)

    def get_specific_coin_news(self, coin_symbol: str) -> Optional[List[Dict[str, Any]]]:
        """
        [أداة الطوارئ 2] جلب الأخبار الخاصة بعملة محددة تعرضت لشذوذ سعري (Anomaly).
        
        المعاملات:
        - coin_symbol: رمز العملة (مثال: 'BTC', 'ETH', 'SOL').
        """
        # الحماية الجنائية: التأكد من عدم إرسال رموز فارغة لحرق الرصيد
        if not coin_symbol or not isinstance(coin_symbol, str):
            logger.error("🛑 Blocked CryptoPanic request: Invalid coin symbol.")
            return None

        # تنظيف الرمز (CryptoPanic يقبل الرمز بدون /USD)
        clean_symbol = coin_symbol.split('/')[0].upper()

        params = {
            "kind": "news",
            "currencies": clean_symbol,
            "filter": "important" # لا نبحث عن إشاعات، نبحث عن أخبار مؤكدة
        }
        
        logger.info(f"📰 Fetching Specific Coin News for: {clean_symbol}")
        return self.fetch("specific_coin_news", **params)
import logging
from typing import Dict, Any, Optional, List

# استيراد القالب الأم الذي يحتوي على جدار الحماية (Firewall) والمترجم
from connectors.base_connector import BaseConnector

# إعداد السجل الجنائي الخاص بـ Alpha Vantage
logger = logging.getLogger("Alpha.Drivers.AlphaVantage")

class AlphaVantageDriver(BaseConnector):
    """
    الذراع التنفيذي لبيانات Alpha Vantage (Financial Data Driver).
    
    المهام الجنائية:
    1. الاتصال ببيانات الأسهم والعملات الأجنبية (Forex).
    2. إدارة مصفوفة المفاتيح (Key Matrix) للهروب من حد الـ 500 طلب/يوم.
    3. معالجة "الفشل الصامت" (Silent API Limits) الخاص بهذا المزود حصراً.
    """

    def __init__(self):
        """
        تهيئة الدرايفر وتجهيز ترسانة المفاتيح.
        """
        # تمرير اسم المزود للقالب الأم لجلب الإعدادات من ملف JSON
        super().__init__("alpha_vantage")
        
        # استخراج قائمة المفاتيح التي قام `key_loader.py` بحقنها من الـ .env
        self._keys_pool: List[str] = self.config.get("credentials", {}).get("_rotated_keys_values", [])
        self._current_key_index: int = 0

        # حماية ضد أخطاء التكوين (Misconfiguration)
        if not self._keys_pool:
            single_key = self.config.get("credentials", {}).get("api_key")
            if single_key:
                self._keys_pool = [single_key]
            else:
                logger.critical("❌ FATAL: No API keys found for Alpha Vantage in environment!")
                self._keys_pool = ["DEMO_KEY"] # مفتاح اختباري من الشركة للطوارئ فقط لمنع الانهيار

    def get_current_key(self) -> str:
        """
        جلب المفتاح النشط حالياً من المصفوفة.
        """
        return self._keys_pool[self._current_key_index]

    def _rotate_key(self):
        """
        [استراتيجية التدوير الذكية]
        الانتقال للمفتاح المجاني التالي عند انتهاء رصيد المفتاح الحالي.
        """
        old_index = self._current_key_index
        self._current_key_index = (self._current_key_index + 1) % len(self._keys_pool)
        logger.warning(f"🔄 Alpha Vantage Key Rotated: Index {old_index} -> {self._current_key_index}")

    def build_url(self, endpoint_key: str) -> str:
        """
        تنفيذ إجباري من القالب الأم: بناء الرابط.
        """
        # Alpha Vantage يستخدم رابطاً واحداً لكل شيء، والاختلاف يكون في المعاملات (Query Params)
        return self.config.get("connection_policy", {}).get("base_url", "https://www.alphavantage.co/query")

    def get_default_params(self) -> Dict[str, str]:
        """
        تنفيذ إجباري من القالب الأم: المعاملات الثابتة لكل طلب.
        """
        return {"apikey": self.get_current_key()}

    def fetch(self, endpoint_key: str, **params) -> Optional[List[Dict[str, Any]]]:
        """
        [تجاوز أمني - Security Override]
        تغليف دالة `fetch` الأصلية لاكتشاف فخ الـ HTTP 200 الصامت.
        """
        # 1. إرسال الطلب عبر القالب الأم (الذي سيقوم بالتدقيق والترجمة)
        result = super().fetch(endpoint_key, **params)
        
        # 2. الفحص الجنائي لنتيجة المترجم (Normalizer Result)
        # المترجم (data_normalizer) سيرجع قائمة فارغة [] إذا وجد رسالة "Note" بدلاً من الشموع
        if result is not None and len(result) == 0:
            logger.warning(f"⚠️ Alpha Vantage returned empty standardized data for {endpoint_key}. Suspected Silent Rate Limit!")
            
            # إذا كان لدينا أكثر من مفتاح، نقوم بالتدوير والمحاولة فوراً
            if len(self._keys_pool) > 1:
                self._rotate_key()
                logger.info("⚡ Retrying request with the newly rotated key...")
                
                # تحديث المفتاح في المعاملات (Params) لتجاوز المفتاح القديم المخزن مؤقتاً
                params["apikey"] = self.get_current_key()
                
                # المحاولة الثانية (Retry)
                return super().fetch(endpoint_key, **params)
            else:
                # لا توجد مفاتيح أخرى، النظام يجب أن ينتقل لـ Twelve Data (Failover)
                logger.error("🛑 All Alpha Vantage keys exhausted. Failover required.")
                return None
                
        return result

    # =========================================================================
    # أذرع التداول المالي (Financial Trading Arms)
    # =========================================================================

    def get_market_tick(self, symbol: str, interval: str = "1min") -> Optional[List[Dict[str, Any]]]:
        """
        جلب النبض اللحظي للسوق (Intraday Data).
        يستخدم في التداول السريع (Scalping / High Frequency).
        """
        # استدعاء خريطة العمليات من التكوين لضمان الالتزام بسياسة "compact" لتسريع الشبكة
        ep_config = self.config.get("endpoints_map", {}).get("market_tick", {})
        
        # تجهيز المعاملات الإجبارية
        params = ep_config.get("mandatory_params", {}).copy()
        params["function"] = ep_config.get("function", "TIME_SERIES_INTRADAY")
        params["symbol"] = symbol
        params["interval"] = interval
        
        logger.info(f"📡 Fetching Intraday Tick for {symbol} at {interval}")
        return self.fetch("market_tick", **params)

    def get_historical_candles(self, symbol: str) -> Optional[List[Dict[str, Any]]]:
        """
        جلب الشموع التاريخية اليومية المعدلة (Daily Adjusted).
        يستخدم لبناء المؤشرات طويلة الأمد واختبار الاستراتيجيات (Backtesting).
        ملاحظة: "Adjusted" ضرورية جداً لحساب تقسيم الأسهم (Splits) وتوزيع الأرباح (Dividends).
        """
        ep_config = self.config.get("endpoints_map", {}).get("historical_candles", {})
        
        params = ep_config.get("mandatory_params", {}).copy()
        params["function"] = ep_config.get("function", "TIME_SERIES_DAILY_ADJUSTED")
        params["symbol"] = symbol
        
        logger.info(f"📊 Fetching Historical Adjusted Candles for {symbol}")
        return self.fetch("historical_candles", **params)

    def get_market_sentiment(self, tickers: str) -> Optional[Any]:
        """
        جلب المشاعر الإخبارية للأسهم المحددة.
        يعطي تقييماً من Alpha Vantage (Bullish / Bearish).
        """
        ep_config = self.config.get("endpoints_map", {}).get("market_sentiment", {})
        
        params = ep_config.get("mandatory_params", {}).copy()
        params["function"] = ep_config.get("function", "NEWS_SENTIMENT")
        params["tickers"] = tickers # مثال: "AAPL,MSFT"
        
        logger.info(f"📰 Fetching Market Sentiment for {tickers}")
        return self.fetch("market_sentiment", **params)
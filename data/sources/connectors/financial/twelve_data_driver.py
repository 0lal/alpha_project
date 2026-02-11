import logging
from typing import Dict, Any, Optional, List, Tuple

# استيراد القالب الأم الذي يحتوي على جدار الحماية والمترجم
from connectors.base_connector import BaseConnector

# إعداد السجل الجنائي الخاص بـ Twelve Data
logger = logging.getLogger("Alpha.Drivers.TwelveData")

class TwelveDataDriver(BaseConnector):
    """
    الذراع التنفيذي لبيانات Twelve Data.
    
    المهام الجنائية:
    1. الاتصال ببيانات الأسهم، الفوركس، والكريبتو بدقة عالية.
    2. معالجة "الاستجابة الكاذبة" (HTTP 200 مع رسالة خطأ داخلية).
    3. فرض توحيد الزمن (UTC Strictness) لجميع البيانات التاريخية.
    """

    def __init__(self):
        """
        تهيئة الدرايفر.
        """
        super().__init__("twelvedata")
        
        # استخراج المفتاح من ملفات التكوين الآمنة
        self.api_key = self.config.get("credentials", {}).get("api_key")
        
        if not self.api_key:
            logger.critical("❌ FATAL: Twelve Data API Key is missing from secure configuration!")

    def build_url(self, endpoint_key: str) -> str:
        """
        بناء الرابط بناءً على خريطة العمليات المحددة.
        """
        base_url = self.config.get("connection_policy", {}).get("base_url", "https://api.twelvedata.com")
        
        # خريطة الروابط الداخلية
        endpoints = {
            "time_series": "/time_series",
            "real_time_price": "/price",
            "quote": "/quote",
            "technical_indicators": "/complex_data" # للطلبات المركبة
        }
        
        path = endpoints.get(endpoint_key, f"/{endpoint_key}")
        return f"{base_url}{path}"

    def get_default_params(self) -> Dict[str, str]:
        """
        المعاملات الإجبارية التي ترفق مع كل طلب (المفتاح السري).
        """
        return {
            "apikey": self.api_key
        }

    def fetch(self, endpoint_key: str, **params) -> Optional[Union[List, Dict]]:
        """
        [تجاوز أمني - Security Override]
        تغليف دالة `fetch` الأصلية لاصطياد الأخطاء المتخفية كنجاح (HTTP 200 Error Trap).
        """
        # 1. إرسال الطلب عبر القالب الأم
        result = super().fetch(endpoint_key, **params)
        
        # 2. الفحص الجنائي للرد (إذا كان الرد الخام لم يتم ترجمته بالكامل أو رجع كقاموس يحتوي خطأ)
        if isinstance(result, dict) and result.get("status") == "error":
            error_code = result.get("code", 0)
            error_msg = result.get("message", "Unknown Twelve Data Error")
            
            logger.error(f"🛑 Twelve Data Silent Error Detected! Code: {error_code} | Msg: {error_msg}")
            
            # توثيق الجريمة في السجلات
            if hasattr(self, 'audit_logger') and self.audit_logger:
                self.audit_logger.log_error("TWELVE_DATA_SILENT_ERROR", f"Code {error_code}", error_msg)

            # تبليغ شرطي المرور إذا كان الخطأ هو تجاوز الحد (429)
            if error_code == 429 and hasattr(self, 'rate_limiter') and self.rate_limiter:
                self.rate_limiter.report_violation(self.provider_name, 429)

            # رفض البيانات الفاسدة فوراً لكي لا تنهار خوارزميات التداول
            return None

        return result

    # =========================================================================
    # أذرع التداول المالي (Financial Trading Arms)
    # =========================================================================

    def get_time_series(self, symbol: str, interval: str = "1min", outputsize: int = 30) -> Optional[List[Dict[str, Any]]]:
        """
        جلب الشموع التاريخية (OHLCV).
        
        المعاملات:
        - symbol: رمز الأصل (مثال: 'AAPL', 'BTC/USD', 'EUR/USD').
        - interval: الإطار الزمني (1min, 5min, 1h, 1day).
        - outputsize: عدد الشموع المطلوبة (1 إلى 5000).
        """
        params = {
            "symbol": symbol,
            "interval": interval,
            "outputsize": outputsize,
            "timezone": "UTC",  # [إجباري مالي] لضمان عدم انحراف الشموع بناءً على توقيت البورصة المحلي
            "format": "JSON"
        }
        
        logger.info(f"📊 Fetching Twelve Data Time Series for {symbol} (Interval: {interval}, Size: {outputsize})")
        return self.fetch("time_series", **params)

    def get_realtime_price(self, symbol: str) -> Optional[float]:
        """
        جلب السعر اللحظي الدقيق.
        هذا الطلب خفيف جداً ويستهلك 1 Credit فقط.
        """
        params = {
            "symbol": symbol
        }
        
        logger.info(f"⚡ Fetching Twelve Data Real-Time Price for {symbol}")
        
        # 1. التفتيش المسبق (تجاوز fetch للحصول على الرقم المباشر بدلاً من المرور بالمترجم الكامل)
        if not self._check_permissions("real_time_price"):
            return None

        try:
            url, method, final_params, headers = self._prepare_request_details("real_time_price", params)
            
            response = self.session.request(
                method=method,
                url=url,
                params=final_params,
                headers=headers,
                timeout=5
            )
            response.raise_for_status()
            data = response.json()

            # اصطياد فخ الخطأ الصامت هنا أيضاً
            if data.get("status") == "error":
                logger.error(f"🛑 Twelve Data Realtime Error: {data.get('message')}")
                return None

            price_str = data.get("price")
            if not price_str:
                return None
                
            price = float(price_str)
            
            # الخصم المالي
            if hasattr(self, 'usage_tracker') and self.usage_tracker:
                self.usage_tracker.increment_usage(self.provider_name)
                
            return price

        except Exception as e:
            self._handle_generic_error(e, "real_time_price")
            return None

    def get_detailed_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        جلب عرض أسعار مفصل (Quote).
        يحتوي على: open, high, low, close, volume, average_volume, fifty_two_week, وغيرها.
        """
        params = {
            "symbol": symbol,
            "timezone": "UTC"
        }
        
        logger.info(f"📈 Fetching Twelve Data Detailed Quote for {symbol}")
        return self.fetch("quote", **params)
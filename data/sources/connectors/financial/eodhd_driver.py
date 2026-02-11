import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime

# استيراد القالب الأم الذي يحتوي على جدار الحماية (Firewall) والمترجم
from connectors.base_connector import BaseConnector

# إعداد السجل الجنائي الخاص بـ EODHD
logger = logging.getLogger("Alpha.Drivers.EODHD")

class EODHDDriver(BaseConnector):
    """
    الذراع التنفيذي لبيانات EODHD (End-Of-Day Historical Data).
    
    المهام الجنائية:
    1. جلب بيانات نهاية اليوم (OHLCV) للأسهم وصناديق الاستثمار (ETFs).
    2. معالجة الحقن الديناميكي لرمز السهم داخل الرابط (Path Injection).
    3. الحماية من استهلاك الكوتا (100,000 طلب/يوم) بطلبات خاطئة لا تحتوي على لاحقة البورصة.
    """

    def __init__(self):
        """
        تهيئة الدرايفر.
        """
        # تمرير اسم المزود للقالب الأم لجلب الإعدادات من ملف JSON
        super().__init__("eodhd")
        
        # استخراج المفتاح (سواء كان التجريبي 'demo' أو المدفوع)
        self.api_token = self.config.get("credentials", {}).get("api_key", "demo")

    def build_url(self, endpoint_key: str) -> str:
        """
        [تجاوز أمني - Override]
        هذه الدالة ترجع الرابط الأساسي فقط. الدمج الفعلي للسهم يحدث في `_prepare_request_details`.
        """
        # الرابط الأساسي للبيانات التاريخية بنهاية اليوم
        return self.config.get("connection_policy", {}).get("base_url", "https://eodhd.com/api/eod")

    def get_default_params(self) -> Dict[str, str]:
        """
        المعاملات الإجبارية التي ترفق مع كل طلب.
        """
        return {
            "api_token": self.api_token,
            "fmt": "json"  # إجبار المزود على إرسال JSON بدلاً من CSV الافتراضي
        }

    def _prepare_request_details(self, endpoint_key: str, params: Dict) -> Tuple[str, str, Dict, Dict]:
        """
        [تجاوز جنائي - Structural Override]
        بما أن EODHD يتطلب وضع السهم في الرابط (مثال: /api/eod/AAPL.US)،
        يجب أن نلتقط السهم من المعاملات ونحقنه في الرابط قبل الإرسال.
        """
        url, method, final_params, headers = super()._prepare_request_details(endpoint_key, params)
        
        symbol = final_params.pop("symbol", None)
        if symbol:
            # دمج السهم في الرابط: https://eodhd.com/api/eod/AAPL.US
            url = f"{url}/{symbol}"
            
        return url, method, final_params, headers

    def _validate_symbol_format(self, symbol: str) -> bool:
        """
        الفحص الوقائي لرمز السهم.
        EODHD يتطلب لاحقة البورصة (مثال: MCD.US). إرسال MCD وحدها سيعطي خطأ ويحرق رصيداً.
        """
        if "." not in symbol:
            logger.error(f"🚫 Invalid Symbol Format for EODHD: '{symbol}'. Must include exchange suffix (e.g., AAPL.US)")
            return False
        return True

    # =========================================================================
    # أذرع التداول المالي (Financial Trading Arms)
    # =========================================================================

    def get_historical_candles(self, symbol: str, from_date: str = None, to_date: str = None, period: str = "d") -> Optional[List[Dict[str, Any]]]:
        """
        جلب الشموع التاريخية (End-Of-Day).
        
        المعاملات:
        - symbol: رمز السهم مع البورصة (مثال: 'TSLA.US').
        - from_date: تاريخ البداية 'YYYY-MM-DD'.
        - to_date: تاريخ النهاية 'YYYY-MM-DD'.
        - period: 'd' (يومي)، 'w' (أسبوعي)، 'm' (شهري).
        """
        if not self._validate_symbol_format(symbol):
            return None

        # تجهيز المعاملات
        params = {
            "symbol": symbol,
            "period": period,
            "order": "a"  # ترتيب تصاعدي (من القديم للحديث) كما هو مفضل مالياً
        }
        
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date

        logger.info(f"📊 Fetching EODHD Historical Data for {symbol} (Period: {period})")
        return self.fetch("historical_candles", **params)

    def get_latest_price_only(self, symbol: str) -> Optional[float]:
        """
        جلب آخر سعر إغلاق (Last Close Price) فقط.
        يستخدم لتحديث الواجهة بأقل تكلفة ممكنة من استهلاك الشبكة (Bandwidth).
        """
        if not self._validate_symbol_format(symbol):
            return None

        params = {
            "symbol": symbol,
            "filter": "last_close"  # هذا الفلتر السحري يمنع تحميل آلاف الأسطر ويعيد رقماً واحداً
        }

        logger.info(f"⚡ Fetching EODHD Last Close Price for {symbol}")
        
        # لا نستخدم self.fetch هنا لأن الرد سيكون رقماً مباشراً (Float) وليس قائمة (List of Dicts)
        # القالب الأم (BaseConnector) يتوقع هيكل JSON معقد ليقوم بترجمته. 
        # لذلك سنتصل بالقالب يدوياً لهذه الحالة الخاصة.
        
        # 1. التفتيش الأمني والمالي
        if not self._check_permissions("last_price_check"):
            return None

        try:
            url, method, final_params, headers = self._prepare_request_details("latest_price", params)
            
            response = self.session.request(
                method=method,
                url=url,
                params=final_params,
                headers=headers,
                timeout=5 # مهلة قصيرة جداً
            )
            response.raise_for_status()
            
            # الرد المتوقع هو رقم كنص، مثال: "150.25"
            price = float(response.text.strip())
            
            # خصم الرصيد
            if hasattr(self, 'usage_tracker') and self.usage_tracker:
                self.usage_tracker.increment_usage(self.provider_name)
                
            return price

        except Exception as e:
            self._handle_generic_error(e, "latest_price_check")
            return None
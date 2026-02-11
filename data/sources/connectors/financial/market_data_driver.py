import logging
from typing import Dict, Any, Optional, List, Tuple

# استيراد القالب الأم الذي يحتوي على جدار الحماية (Firewall) والمترجم
from connectors.base_connector import BaseConnector

# إعداد السجل الجنائي الخاص بـ Market Data
logger = logging.getLogger("Alpha.Drivers.MarketData")

class MarketDataDriver(BaseConnector):
    """
    الذراع التنفيذي لبيانات MarketData.app.
    
    المهام الجنائية:
    1. جلب بيانات الأسهم، وعقود الخيارات (Options) الدقيقة.
    2. معالجة نظام الـ "Status" الخاص بالمزود (ok, error, no_data).
    3. تطبيق معايير المصادقة الآمنة (Bearer Token).
    """

    def __init__(self):
        """
        تهيئة الدرايفر.
        """
        super().__init__("market_data")
        
        # استخراج المفتاح من ملفات التكوين الآمنة
        self.api_token = self.config.get("credentials", {}).get("api_key")
        
        if not self.api_token:
            logger.critical("❌ FATAL: Market Data API Token is missing from secure configuration!")

    def build_url(self, endpoint_key: str) -> str:
        """
        بناء الرابط.
        Market Data تقسم الروابط إلى v1/stocks و v1/options إلخ.
        """
        base_url = self.config.get("connection_policy", {}).get("base_url", "https://api.marketdata.app/v1")
        
        endpoints = {
            "stock_candles": "/stocks/candles",
            "stock_quote": "/stocks/quotes",
            "options_chain": "/options/chain",
            "options_quotes": "/options/quotes"
        }
        
        path = endpoints.get(endpoint_key, f"/{endpoint_key}")
        return f"{base_url}{path}"

    def get_default_params(self) -> Dict[str, str]:
        """
        نترك المعاملات فارغة لأننا سنمرر المفتاح في الترويسة (Headers) للأمان.
        """
        return {}

    def _prepare_request_details(self, endpoint_key: str, params: Dict) -> Tuple[str, str, Dict, Dict]:
        """
        [تجاوز أمني - Security Override]
        حقن مفتاح الوصول في الترويسة (Header) بصيغة Bearer Token.
        """
        url, method, final_params, headers = super()._prepare_request_details(endpoint_key, params)
        
        # حقن المصادقة القياسية (Industry Standard Authentication)
        headers["Authorization"] = f"Bearer {self.api_token}"
        
        return url, method, final_params, headers

    def fetch(self, endpoint_key: str, **params) -> Optional[Union[List, Dict]]:
        """
        [تجاوز جنائي - Status Override]
        فحص الرد لاصطياد حالات (no_data) و (error) التي يرسلها المزود كـ HTTP 200.
        """
        result = super().fetch(endpoint_key, **params)
        
        # الفحص خاص بـ Market Data لأنهم يستخدمون مفتاح "s" لبيان الحالة
        if isinstance(result, dict) and "s" in result:
            status = result.get("s")
            
            if status == "no_data":
                logger.warning(f"⚠️ Market Data returned 'no_data' for {endpoint_key} with params {params}")
                # إرجاع قائمة فارغة بأمان بدلاً من الانهيار
                return []
                
            elif status == "error":
                error_msg = result.get("errmsg", "Unknown API Error")
                logger.error(f"🛑 Market Data Logic Error: {error_msg}")
                
                if hasattr(self, 'audit_logger') and self.audit_logger:
                    self.audit_logger.log_error("MARKET_DATA_API_ERROR", "Data Provider Error", error_msg)
                
                return None
                
        return result

    # =========================================================================
    # أذرع التداول المالي (Financial Trading Arms)
    # =========================================================================

    def get_historical_candles(self, symbol: str, resolution: str, from_date: str, to_date: str) -> Optional[List[Dict[str, Any]]]:
        """
        جلب الشموع التاريخية للأسهم (OHLCV).
        
        المعاملات:
        - symbol: رمز السهم (مثال: 'AAPL').
        - resolution: الإطار الزمني (D = يومي، W = أسبوعي، M = شهري، أو دقائق 1, 5, 15).
        - from_date: تاريخ البداية (YYYY-MM-DD).
        - to_date: تاريخ النهاية (YYYY-MM-DD).
        """
        params = {
            "symbol": symbol,
            "resolution": resolution,
            "from": from_date,
            "to": to_date
        }
        
        logger.info(f"📊 Fetching Market Data Candles for {symbol} (Res: {resolution})")
        return self.fetch("stock_candles", **params)

    def get_realtime_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        جلب السعر اللحظي (Quote).
        يعيد السعر، حجم التداول، وأسعار العرض والطلب (Bid/Ask) الدقيقة.
        """
        params = {"symbol": symbol}
        logger.info(f"⚡ Fetching Market Data Quote for {symbol}")
        return self.fetch("stock_quote", **params)

    def get_options_chain(self, symbol: str, expiration_date: str, side: str = "all") -> Optional[List[Dict[str, Any]]]:
        """
        [أداة الخبراء] جلب سلسلة عقود الخيارات (Options Chain).
        
        المعاملات:
        - symbol: رمز السهم الأساسي.
        - expiration_date: تاريخ انتهاء العقد (YYYY-MM-DD). (إجباري مالياً لمنع الـ Memory Leak).
        - side: نوع العقد 'call' للرهان على الصعود، 'put' للرهان على الهبوط، 'all' للاثنين.
        """
        # الحماية الجنائية: رفض الطلب إذا لم يتم تحديد تاريخ الانتهاء
        if not expiration_date:
            logger.error("🛑 Blocked Options Chain request: Missing expiration_date! (Prevents memory overflow)")
            return None

        params = {
            "symbol": symbol,
            "expiration": expiration_date,
            "side": side
        }
        
        logger.info(f"📜 Fetching Options Chain for {symbol} (Exp: {expiration_date}, Side: {side})")
        return self.fetch("options_chain", **params)
import time
import hmac
import hashlib
import logging
from urllib.parse import urlencode
from typing import Dict, Any, Optional, List, Tuple

# استيراد القالب الأم الذي يطبق سياسات الأمان، شرطي المرور، والمحاسب
from connectors.base_connector import BaseConnector

# إعداد السجل الجنائي لمنصة التداول
logger = logging.getLogger("Alpha.Drivers.Binance")

class BinanceDriver(BaseConnector):
    """
    الذراع التنفيذي المشفر لمنصة Binance (Encrypted Trading Engine).
    
    المهام الجنائية:
    1. الاتصال اللحظي ببيانات السوق (الشموع، الأسعار).
    2. توليد التوقيعات الرقمية (HMAC SHA-256) لحماية وتوثيق الصفقات المالية.
    3. المزامنة الزمنية الدقيقة (Time Synchronization) لمنع رفض الطلبات بسبب انحراف ساعة السيرفر.
    4. تنفيذ أوامر التداول الحقيقية (Spot / Margin / Futures) بأعلى درجات الموثوقية.
    """

    def __init__(self):
        """
        تهيئة محرك التداول واستخراج مفاتيح التشفير.
        """
        # تمرير اسم المزود للقالب الأم لجلب الإعدادات (binance_keys.json)
        super().__init__("binance")
        
        # استخراج المفاتيح من ملفات التكوين الآمنة
        self.api_key = self.config.get("credentials", {}).get("api_key")
        self.secret_key = self.config.get("credentials", {}).get("secret_key")
        
        if not self.api_key or not self.secret_key:
            logger.critical("❌ FATAL: Binance API Key or Secret Key is missing! Trading Engine is BLIND and DISABLED.")
            # لن يتم إيقاف البرنامج، لكن أي عملية تداول ستفشل بأمان (Safe Fail)

        # المتغير الأهم في التداول: تعويض الفارق الزمني بين سيرفرك وسيرفر بينانس
        self.time_offset = 0
        
        # المزامنة التلقائية عند الإقلاع
        self._sync_server_time()

    def _sync_server_time(self):
        """
        [آلية حماية التوقيت الجنائية]
        حساب الفارق الزمني (Offset) بالملي ثانية لضمان قبول الصفقات دائماً.
        """
        try:
            # نستخدم القالب الأم لجلب الوقت من بينانس بدون توقيع
            logger.info("⏱️ Synchronizing local clock with Binance Server Time...")
            server_time_response = self.fetch("server_time")
            
            if server_time_response and "serverTime" in server_time_response:
                binance_time = server_time_response["serverTime"]
                local_time = int(time.time() * 1000)
                # حساب الفارق
                self.time_offset = binance_time - local_time
                logger.info(f"✅ Time synced successfully. Offset: {self.time_offset}ms")
            else:
                logger.warning("⚠️ Failed to sync time with Binance. Will rely on local clock. High risk of 'Timestamp out of bounds' errors.")
        except Exception as e:
            logger.error(f"🛑 Error syncing Binance time: {e}")

    def build_url(self, endpoint_key: str) -> str:
        """
        [محرك التوجيه] بناء الرابط الفعلي بناءً على خريطة الـ JSON.
        """
        base_url = self.config.get("connection_policy", {}).get("base_url", "https://api.binance.com")
        
        # جلب المسار من الخريطة بناءً على المفتاح (مثال: 'ticker_price' -> '/api/v3/ticker/price')
        endpoint_config = self.config.get("endpoints_map", {}).get(endpoint_key, {})
        path = endpoint_config.get("path", f"/{endpoint_key}")
        
        return f"{base_url}{path}"

    def get_default_params(self) -> Dict[str, Any]:
        """
        لا نضع أي معاملات افتراضية هنا لأن التشفير يتم في لحظة تجهيز الطلب.
        """
        return {}

    def _generate_signature(self, params: Dict[str, Any]) -> str:
        """
        [محرك التشفير المالي العسكري]
        إنشاء توقيع HMAC SHA-256 باستخدام المفتاح السري لكل العمليات الحساسة.
        """
        if not self.secret_key:
            return ""
            
        # تحويل القاموس إلى سلسلة نصية (Query String) كما تطلبها بينانس
        query_string = urlencode(params)
        
        # تشفير السلسلة
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return signature

    def _prepare_request_details(self, endpoint_key: str, params: Dict) -> Tuple[str, str, Dict, Dict]:
        """
        [تجاوز أمني شديد الحساسية - High Security Override]
        هنا يتم حقن التوقيعات، الطوابع الزمنية، ومفاتيح الواجهة لكل طلب بناءً على نوعه.
        """
        url, method, final_params, headers = super()._prepare_request_details(endpoint_key, params)
        
        # 1. إجبار إرسال مفتاح الـ API في الترويسة لكل الطلبات (حتى العامة منها)
        if self.api_key:
            headers["X-MBX-APIKEY"] = self.api_key

        # 2. تحديد مستوى الأمان المطلوب من خريطة الـ JSON
        endpoint_config = self.config.get("endpoints_map", {}).get(endpoint_key, {})
        security_level = endpoint_config.get("security", "NONE")
        method = endpoint_config.get("method", "GET").upper()
        recv_window = self.config.get("connection_policy", {}).get("recvWindow", 5000)

        # 3. إذا كان الطلب يتطلب صلاحيات تداول (TRADE) أو بيانات مستخدم (USER_DATA)
        if security_level in ["TRADE", "USER_DATA", "MARGIN"]:
            # إضافة الطابع الزمني المزامَن (Synced Timestamp)
            final_params["timestamp"] = int(time.time() * 1000) + self.time_offset
            
            # إضافة نافذة السماح الزمنية
            final_params["recvWindow"] = recv_window
            
            # توليد التوقيع الرقمي وحقنه في المعاملات كأخر عنصر
            final_params["signature"] = self._generate_signature(final_params)

        return url, method, final_params, headers

    # =========================================================================
    # أذرع جلب البيانات (Market Data Arms - Public)
    # =========================================================================

    def get_realtime_price(self, symbol: str) -> Optional[float]:
        """
        جلب السعر اللحظي لزوج عملات (مثال: 'BTCUSDT').
        عملية عامة لا تتطلب تشفيراً.
        """
        # بينانس لا تستخدم علامة "/" في الأزواج
        clean_symbol = symbol.replace("/", "").upper()
        
        logger.info(f"⚡ Fetching Binance REAL-TIME price for {clean_symbol}")
        result = self.fetch("ticker_price", symbol=clean_symbol)
        
        # الفحص الجنائي لبروتوكول "أنا أعمى"
        if result and "price" in result:
            return float(result["price"])
            
        logger.error(f"🛑 Binance Failed to retrieve price for {clean_symbol}.")
        return None

    def get_historical_candles(self, symbol: str, interval: str = "1d", limit: int = 100) -> Optional[List[Dict[str, Any]]]:
        """
        جلب الشموع التاريخية (Klines).
        ملاحظة: البيانات تعود كمصفوفة، المترجم (data_normalizer) سيتولى تحويلها لصيغة Alpha القياسية.
        """
        clean_symbol = symbol.replace("/", "").upper()
        
        params = {
            "symbol": clean_symbol,
            "interval": interval,
            "limit": limit
        }
        
        logger.info(f"📊 Fetching Binance Historical Klines for {clean_symbol} (Interval: {interval})")
        return self.fetch("historical_klines", **params)

    # =========================================================================
    # أذرع التنفيذ المالي (Execution Arms - Private/Encrypted)
    # =========================================================================

    def get_account_balance(self) -> Optional[Dict[str, Any]]:
        """
        جلب أرصدة المحفظة الحقيقية. يتطلب توقيعاً جنائياً (HMAC).
        """
        if not self.secret_key:
            logger.error("🛑 Cannot fetch account balance. Secret Key missing.")
            return None
            
        logger.info("💰 Fetching Binance Account Balances (Encrypted Request)...")
        return self.fetch("account_info")

    def place_order(self, symbol: str, side: str, quantity: float, order_type: str = "MARKET") -> Optional[Dict[str, Any]]:
        """
        [أداة تنفيذية حرجة - LETHAL WEAPON]
        تنفيذ صفقة حقيقية بأموال حقيقية في سوق الـ Spot.
        
        المعاملات:
        - symbol: الزوج (مثال: 'BTCUSDT').
        - side: 'BUY' أو 'SELL'.
        - quantity: الكمية المراد تداولها.
        - order_type: 'MARKET' (افتراضي للتنفيذ الفوري).
        """
        if not self.secret_key:
            logger.critical("🛑 Cannot place trade. Secret Key missing. System is operating in BLIND mode.")
            return None

        clean_symbol = symbol.replace("/", "").upper()
        clean_side = side.upper()
        
        # بناء هيكل أمر التداول
        order_params = {
            "symbol": clean_symbol,
            "side": clean_side,
            "type": order_type.upper(),
            "quantity": quantity
        }
        
        logger.warning(f"🚨 EXECUTING LIVE TRADE: {clean_side} {quantity} {clean_symbol} at {order_type}...")
        
        # سيتم توقيع الطلب وإضافة الطابع الزمني تلقائياً عبر دالة _prepare_request_details
        result = self.fetch("place_order", **order_params)
        
        if result and "orderId" in result:
            logger.info(f"✅ TRADE SUCCESSFUL. Order ID: {result['orderId']} | Status: {result.get('status')}")
            
            # تسجيل الصفقة في التدقيق المالي
            if hasattr(self, 'audit_logger') and self.audit_logger:
                self.audit_logger.log_decision("LIVE_TRADE", f"{clean_side}_{clean_symbol}", f"Qty: {quantity} | ID: {result['orderId']}", confidence=1.0)
                
            return result
            
        logger.error(f"🛑 TRADE FAILED or REJECTED BY BINANCE.")
        return None
import logging
import json
import hashlib
import hmac
from typing import Dict, Any, Optional, List, Tuple

# استيراد القالب الأم الذي يطبق سياسات الأمان والحدود
from connectors.base_connector import BaseConnector

# إعداد السجل الجنائي الخاص بـ Finnhub
logger = logging.getLogger("Alpha.Drivers.Finnhub")

class FinnhubDriver(BaseConnector):
    """
    الذراع التنفيذي لبيانات Finnhub (Financial & Alternative Data).
    
    المهام الجنائية:
    1. الاتصال ببيانات السوق والأساسيات الاقتصادية.
    2. تطبيق مصادقة الترويسة (Header Authentication) الصارمة.
    3. التحقق الأمني من الـ Webhooks لمنع اختراق النظام وتزييف البيانات.
    4. ضمان عدم تجاوز قاعدة "اتصال WebSocket واحد فقط".
    """

    # المفتاح السري للـ Webhook (حسب وثيقة المتطلبات)
    # في بيئة الإنتاج القصوى يفضل نقله لـ .env، لكن تم وضعه هنا بناءً على طلبك بالالتزام بالملف
    WEBHOOK_SECRET = "d656eghr01qppnmrhssg"

    def __init__(self):
        """
        تهيئة الدرايفر.
        """
        # تمرير اسم المزود للقالب الأم
        super().__init__("finnhub")
        
        # استخراج المفتاح الأساسي من ملفات التكوين الآمنة
        self.api_key = self.config.get("credentials", {}).get("api_key")
        
        if not self.api_key:
            logger.critical("❌ FATAL: Finnhub API Key is missing from secure configuration!")

    def build_url(self, endpoint_key: str) -> str:
        """
        [تجاوز إجباري]
        بناء الرابط بناءً على المسار الأساسي (Base URL).
        """
        base_url = self.config.get("connection_policy", {}).get("base_url", "https://finnhub.io/api/v1")
        
        # خريطة الروابط الداخلية (Endpoints Routing)
        endpoints = {
            "quote": "/quote",
            "candles": "/stock/candle",
            "company_news": "/company-news",
            "market_news": "/news",
            "sentiment": "/news-sentiment"
        }
        
        path = endpoints.get(endpoint_key, "")
        if not path:
            # إذا لم يكن موجوداً في الخريطة، نفترض أن المبرمج أرسل المسار مباشرة
            path = endpoint_key if endpoint_key.startswith("/") else f"/{endpoint_key}"
            
        return f"{base_url}{path}"

    def get_default_params(self) -> Dict[str, str]:
        """
        [تجاوز إجباري]
        Finnhub لا يفضل وضع المفتاح في الرابط (Params)، بل في الترويسة (Headers).
        لذلك نترك المعاملات الافتراضية فارغة لتنظيف الرابط.
        """
        return {}

    def _prepare_request_details(self, endpoint_key: str, params: Dict) -> Tuple[str, str, Dict, Dict]:
        """
        [تجاوز أمني - Security Override]
        حقن المفتاح في الترويسة (Header) تحت اسم X-Finnhub-Token لزيادة الأمان.
        """
        url, method, final_params, headers = super()._prepare_request_details(endpoint_key, params)
        
        # حقن مفتاح الوصول في الترويسة
        headers["X-Finnhub-Token"] = self.api_key
        
        return url, method, final_params, headers

    # =========================================================================
    # أذرع التداول المالي (Financial Trading Arms)
    # =========================================================================

    def get_realtime_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        جلب السعر اللحظي (Quote).
        يرجع: السعر الحالي، التغير، أعلى، أدنى، سعر الفتح، والإغلاق السابق.
        """
        params = {"symbol": symbol}
        logger.info(f"⚡ Fetching Finnhub Quote for {symbol}")
        
        # الرد يأتي بصيغة: {"c": 150.5, "d": 1.5, "dp": 1.0, "h": 151, "l": 149, "o": 150, "pc": 149}
        # المترجم (data_normalizer) سيتولى تحويل "c" إلى "close" إلخ.
        return self.fetch("quote", **params)

    def get_historical_candles(self, symbol: str, resolution: str, start_timestamp: int, end_timestamp: int) -> Optional[Dict[str, Any]]:
        """
        جلب الشموع التاريخية (OHLCV).
        
        المعاملات:
        - resolution: الدقة الزمنية المسموحة (1, 5, 15, 30, 60, D, W, M).
        - start_timestamp: وقت البداية (Unix Timestamp).
        - end_timestamp: وقت النهاية (Unix Timestamp).
        """
        params = {
            "symbol": symbol,
            "resolution": resolution,
            "from": start_timestamp,
            "to": end_timestamp
        }
        logger.info(f"📊 Fetching Finnhub Candles for {symbol} (Res: {resolution})")
        return self.fetch("candles", **params)

    # =========================================================================
    # درع الـ Webhook (Webhook Shield)
    # =========================================================================

    def verify_and_parse_webhook(self, payload_body: bytes, received_secret_header: str) -> Optional[Dict[str, Any]]:
        """
        [وظيفة أمنية حرجة]
        التحقق من البيانات القادمة من Finnhub Webhook.
        
        تحذير التشغيل (Operational Rule):
        بناءً على التوثيق، يجب على السيرفر (FastAPI) أن يرسل HTTP 200 فوراً لـ Finnhub 
        بمجرد استلام الطلب وقبل استدعاء هذه الدالة، لمنع حظر نقطة الوصول بسبب الـ Timeout.
        
        المعاملات:
        - payload_body: جسم الطلب الخام (Raw Bytes) لضمان صحة التشفير.
        - received_secret_header: قيمة الحقل "X-Finnhub-Secret" القادم في الترويسة.
        """
        # 1. التحقق من تطابق المفتاح السري (Security Validation)
        if not received_secret_header or received_secret_header != self.WEBHOOK_SECRET:
            logger.error("🛑 Webhook Security Breach: Invalid or missing X-Finnhub-Secret header!")
            if hasattr(self, 'audit_logger') and self.audit_logger:
                self.audit_logger.log_security_event("WEBHOOK_FORGERY_ATTEMPT", "Invalid Finnhub Secret Received")
            return None

        # 2. فك التشفير الآمن
        try:
            data = json.loads(payload_body.decode('utf-8'))
            logger.info("✅ Finnhub Webhook Payload verified and parsed successfully.")
            return data
        except json.JSONDecodeError as e:
            logger.error(f"❌ Webhook Payload is not valid JSON: {e}")
            return None

    # =========================================================================
    # ملاحظة معمارية بخصوص WebSocket
    # =========================================================================
    # شركة Finnhub تمنع فتح أكثر من اتصال WebSocket واحد لكل مفتاح API.
    # لا تقم بوضع كود الـ WebSocket (websockets.connect) بداخل هذا الدرايفر مباشرة 
    # بحيث يتم استدعاؤه مع كل سهم. بدلاً من ذلك، النظام يمتلك مجلد (buffers/raw_stream_buffer.py)
    # يجب أن يكون هو الـ Singleton الوحيد الذي يتصل بـ wss://ws.finnhub.io ويقوم بعمل Subscribe 
    # لكل الأسهم من خلال قناة اتصال (Socket) واحدة فقط.
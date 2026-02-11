import logging
from typing import Dict, Any, Optional, List, Union

# استيراد الأذرع التنفيذية (Drivers) للبيانات المالية
try:
    from connectors.financial.alpha_vantage_driver import AlphaVantageDriver
    from connectors.financial.twelve_data_driver import TwelveDataDriver
    from connectors.financial.finnhub_driver import FinnhubDriver
    from connectors.financial.eodhd_driver import EODHDDriver
    # [تحديث جنائي] استيراد ذراع بينانس لقيادة سوق الكريبتو
    from connectors.financial.binance_driver import BinanceDriver
    
    # استيراد شرطي المرور والمحاسب لمعرفة حالة المزود قبل استدعائه
    from core.usage_tracker import usage_tracker
    from audit.logger_service import audit_logger
except ImportError:
    logging.critical("🔥 FATAL: Missing Core Financial Drivers for Smart Router!")
    AlphaVantageDriver = None
    TwelveDataDriver = None
    FinnhubDriver = None
    EODHDDriver = None
    BinanceDriver = None
    usage_tracker = None
    audit_logger = None

# إعداد السجل الجنائي للموجه
logger = logging.getLogger("Alpha.Core.SmartRouter")

class SmartMarketRouter:
    """
    موجه السوق الذكي (The Financial Data Orchestrator).
    
    المهام الجنائية:
    1. توجيه الطلبات المالية للمزود الأنسب (بناءً على نوع الأصل: سهم، فوركس، كريبتو).
    2. تطبيق بروتوكول "الشلال" (Waterfall Failover) لضمان عدم توقف النظام 24/7.
    3. استبعاد المزودين الذين استنفدوا حصتهم اليومية تلقائياً.
    """

    def __init__(self):
        """
        تهيئة الموجه وتجهيز الأسطول (Drivers).
        """
        # التهيئة الكسولة (Lazy Loading) لضمان عدم الانهيار إذا كان أحد الملفات مفقوداً
        self.drivers = {
            "alpha_vantage": AlphaVantageDriver() if AlphaVantageDriver else None,
            "twelve_data": TwelveDataDriver() if TwelveDataDriver else None,
            "finnhub": FinnhubDriver() if FinnhubDriver else None,
            "eodhd": EODHDDriver() if EODHDDriver else None,
            # إضافة بينانس للأسطول
            "binance": BinanceDriver() if BinanceDriver else None
        }

    def get_realtime_price(self, symbol: str) -> Optional[float]:
        """
        [عملية حرجة] جلب السعر اللحظي (Real-Time Price).
        السرعة هنا هي الأهم. الترتيب تم تحديثه ليدعم بينانس كقائد للكريبتو.
        """
        asset_type = self._classify_asset(symbol)
        
        # 1. تحديد مسار الشلال بناءً على نوع الأصل
        if asset_type == "CRYPTO":
            # [تحديث جنائي] بينانس أولاً للسرعة والدقة، ثم Twelve Data كبديل للطوارئ
            routing_order = ["binance", "twelve_data"] 
        else:
            # ترتيب الأسهم والفوركس يبقى كما هو
            routing_order = ["finnhub", "twelve_data", "alpha_vantage"]

        logger.info(f"🚦 Routing REAL-TIME price request for {symbol} | Asset: {asset_type}")

        # 2. تنفيذ بروتوكول الشلال
        for provider_name in routing_order:
            driver = self.drivers.get(provider_name)
            
            # تخطي المزود إذا لم يكن مثبتاً أو إذا كان محظوراً (استنفد الرصيد)
            if not driver or not self._is_provider_healthy(provider_name):
                continue

            try:
                # استدعاء الدالة المناسبة حسب المزود
                if provider_name == "binance":
                    # [إضافة جنائية] جلب السعر من بينانس
                    price = driver.get_realtime_price(symbol)
                    if price is not None: return float(price)

                elif provider_name == "finnhub":
                    quote = driver.get_realtime_quote(symbol)
                    if quote and "c" in quote: return float(quote["c"])
                
                elif provider_name == "twelve_data":
                    price = driver.get_realtime_price(symbol)
                    if price: return float(price)
                
                elif provider_name == "alpha_vantage":
                    # Alpha Vantage يدمج السعر اللحظي في دالة الـ Quote
                    pass 

            except Exception as e:
                logger.warning(f"⚠️ Failover: {provider_name} failed to get price for {symbol}: {e}")
                continue # فشل؟ انتقل للمزود التالي فوراً

        # 3. بروتوكول "أنا أعمى"
        return self._declare_blindness("REALTIME_PRICE_FAILED", f"All providers in waterfall failed for {symbol}.")

    def get_historical_candles(self, symbol: str, interval: str = "1d", days_back: int = 30) -> Optional[List[Dict[str, Any]]]:
        """
        [عملية تحليلية] جلب الشموع التاريخية (OHLCV).
        الدقة هنا أهم من السرعة. 
        """
        asset_type = self._classify_asset(symbol)
        
        if asset_type == "CRYPTO":
            # [تحديث جنائي] بينانس تقود التحليل التاريخي للكريبتو أيضاً
            routing_order = ["binance", "twelve_data", "alpha_vantage"]
        elif interval == "1d":
            routing_order = ["eodhd", "alpha_vantage", "twelve_data"]
        else:
            # البيانات اللحظية (Intraday) للأسهم مثل 1h أو 15m
            routing_order = ["twelve_data", "alpha_vantage", "finnhub"]

        logger.info(f"🚦 Routing HISTORICAL request for {symbol} | Interval: {interval}")

        for provider_name in routing_order:
            driver = self.drivers.get(provider_name)
            if not driver or not self._is_provider_healthy(provider_name):
                continue

            try:
                if provider_name == "binance":
                    # [إضافة جنائية] جلب الشموع من بينانس وتمرير limit ليتوافق مع أيام البحث
                    data = driver.get_historical_candles(symbol, interval=interval, limit=days_back)
                    if data: return data

                elif provider_name == "eodhd" and interval == "1d":
                    data = driver.get_historical_candles(f"{symbol}.US", period="d") # افتراض السوق الأمريكي
                    if data: return data
                    
                elif provider_name == "alpha_vantage":
                    if interval == "1d":
                        data = driver.get_historical_candles(symbol)
                        if data: return data
                    else:
                        data = driver.get_market_tick(symbol, interval=interval)
                        if data: return data
                        
                elif provider_name == "twelve_data":
                    # توحيد صيغة الإطار الزمني لـ Twelve Data (مثال: '1d' -> '1day')
                    twelve_interval = "1day" if interval == "1d" else interval
                    data = driver.get_time_series(symbol, interval=twelve_interval, outputsize=days_back)
                    if data: return data

            except Exception as e:
                logger.warning(f"⚠️ Failover: {provider_name} failed to get history for {symbol}: {e}")
                continue

        return self._declare_blindness("HISTORICAL_DATA_FAILED", f"All providers failed for {symbol} at {interval}.")

    def _classify_asset(self, symbol: str) -> str:
        """
        التصنيف الجنائي للأصل بناءً على رمزه لضمان توجيهه لأفضل مزود.
        """
        sym = symbol.upper()
        if "/" in sym or sym.endswith("USD") or sym.endswith("USDT") or sym in ["BTC", "ETH", "SOL"]:
            # [تحديث جنائي] دعم لاحقة USDT التي تستخدمها بينانس بكثافة
            if len(sym) == 6 and not "/" in sym and not sym.endswith("USDT"):
                return "FOREX"
            return "CRYPTO"
        return "STOCK"

    def _is_provider_healthy(self, provider_name: str) -> bool:
        """
        سؤال "المحاسب" و "شرطي المرور": هل هذا المزود قادر على استقبال طلبات الآن؟
        """
        if not usage_tracker:
            return True # نفترض الصحة في غياب المحاسب

        status, _, _ = usage_tracker.check_quota_status(provider_name)
        
        # إذا كان المزود محظوراً (BLOCKED) بسبب نفاد الرصيد، نعيده كـ False لتجاوزه
        if status == "BLOCKED":
            logger.warning(f"⏭️ Skipping {provider_name} in Router: Quota Exhausted.")
            return False
            
        return True

    def _declare_blindness(self, error_code: str, details: str) -> None:
        """
        [البروتوكول المالي الصارم] إعلان العمى التام بدلاً من اختراع بيانات.
        """
        logger.critical(f"🛑 [ROUTER BLINDNESS] {error_code}: {details}")
        if audit_logger:
            audit_logger.log_error("SMART_ROUTER_BLINDNESS", error_code, details)
        return None

# نسخة مفردة (Singleton) للاستخدام المباشر
smart_market_router = SmartMarketRouter()
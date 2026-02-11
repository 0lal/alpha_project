import logging
from typing import Dict, Any, Optional, List

# -----------------------------------------------------------------------------
# استيراد "قادة الجيوش" (The Orchestrators) الذين بنيناهم في الخطوات السابقة
# -----------------------------------------------------------------------------
try:
    from core.smart_router import smart_market_router
    from connectors.intelligence.free_router_driver import free_router
    from core.api_status_reporter import api_health_monitor
    from audit.logger_service import audit_logger
    
    # [تحديث جنائي] استيراد ذراع التنفيذ الحي لفتح الصفقات
    from connectors.financial.binance_driver import BinanceDriver
except ImportError as e:
    logging.critical(f"🔥 FATAL: API Manager failed to load core subsystems: {e}")
    # في حالة انهيار الاستيراد، نوقف النظام تماماً (Fail-Stop)
    smart_market_router = None
    free_router = None
    api_health_monitor = None
    audit_logger = None
    BinanceDriver = None

# إعداد السجل الجنائي للقيادة المركزية
logger = logging.getLogger("Alpha.Core.APIManager")

class CentralAPIManager:
    """
    القيادة المركزية لواجهات برمجة التطبيقات (The API Facade).
    
    المهام الجنائية:
    1. توفير نقطة اتصال واحدة (Single Point of Contact) لمحرك التداول والواجهة الأمامية.
    2. إخفاء التعقيد: محرك التداول يطلب "حلل هذا السهم"، والمدير يقرر من سيفعل ذلك.
    3. تطبيق التزام "البيانات الحقيقية أو لا شيء" (True Data or Nothing).
    """

    def __init__(self):
        """
        تهيئة القيادة المركزية والتأكد من جاهزية الأنظمة.
        """
        logger.info("🛡️ Central API Manager initialized. Awaiting financial orders.")
        
        # التأكد من أن الأنظمة الحرجة تعمل، وإلا نطلق إنذاراً
        if not smart_market_router or not free_router:
            logger.critical("🛑 WARNING: Running in Degraded Mode! Some routers are offline.")
            
        # تهيئة الذراع الهجومي (التنفيذي) للعمليات الحية
        self.execution_driver = BinanceDriver() if BinanceDriver else None
        if not self.execution_driver:
            logger.critical("🛑 WARNING: Binance Execution Driver is offline. Trading is DISABLED.")

    # =========================================================================
    # 1. أذرع جلب البيانات المالية (Financial Data Fetching)
    # =========================================================================

    def get_live_price(self, symbol: str) -> Optional[float]:
        """
        طلب السعر اللحظي لأصل مالي.
        يتم تحويل الطلب فوراً لـ Smart Router ليتولى هو اختيار المزود وإدارة الفشل.
        """
        logger.debug(f"▶️ Executing Manager Command: get_live_price({symbol})")
        
        if not smart_market_router:
            return self._declare_system_blindness("SMART_ROUTER_OFFLINE")
            
        price = smart_market_router.get_realtime_price(symbol)
        
        # التزام جنائي: لا تزييف للبيانات
        if price is None:
            logger.error(f"❌ API Manager: Failed to retrieve LIVE price for {symbol}. System is blind.")
            return None
            
        return price

    def get_historical_data(self, symbol: str, interval: str = "1d", days: int = 30) -> Optional[List[Dict[str, Any]]]:
        """
        طلب الشموع التاريخية للتحليل الفني.
        """
        logger.debug(f"▶️ Executing Manager Command: get_historical_data({symbol}, {interval})")
        
        if not smart_market_router:
            return self._declare_system_blindness("SMART_ROUTER_OFFLINE")
            
        data = smart_market_router.get_historical_candles(symbol, interval, days)
        
        if not data:
            logger.error(f"❌ API Manager: Failed to retrieve HISTORICAL data for {symbol}.")
            return None
            
        return data

    # =========================================================================
    # 2. أذرع الذكاء الاصطناعي (Intelligence & Reasoning)
    # =========================================================================

    def analyze_market_condition(self, prompt: str, market_data_json: str) -> Optional[str]:
        """
        طلب تحليل مالي معقد من الذكاء الاصطناعي.
        يتم تحويل الطلب لـ Free Router الذي يوازن بين Groq و Gemini.
        """
        logger.debug("▶️ Executing Manager Command: analyze_market_condition")
        
        if not free_router:
            return self._declare_system_blindness("FREE_ROUTER_OFFLINE")
            
        # نحدد نوع المهمة لتوجيهها للنموذج الأنسب (مثلاً Gemini للبيانات الضخمة)
        analysis = free_router.route_query(
            system_prompt=prompt, 
            context_data=market_data_json, 
            task_type="DEEP_REASONING"
        )
        
        if not analysis:
            logger.error("❌ API Manager: Intelligence Router failed to analyze data. System is blind.")
            return None
            
        return analysis

    # =========================================================================
    # 3. أذرع لوحة التحكم والرقابة (Dashboard & Monitoring)
    # =========================================================================

    def get_system_health(self) -> Dict[str, Any]:
        """
        جلب التقرير الطبي الكامل للنظام لعرضه في واجهة المستخدم (UI Dashboard).
        يعرض حالة الأرصدة، العقوبات، والمشاكل.
        """
        logger.debug("▶️ Executing Manager Command: get_system_health")
        
        if not api_health_monitor:
            return {
                "system_status": "CRITICAL_FAILURE",
                "message": "Health Monitor Subsystem is offline."
            }
            
        return api_health_monitor.get_full_dashboard_report()

    # =========================================================================
    # 4. أذرع التنفيذ المالي (Live Trade Execution) - [تحديث جنائي جديد]
    # =========================================================================

    def execute_trade(self, symbol: str, side: str, quantity: float, order_type: str = "MARKET") -> Optional[Dict[str, Any]]:
        """
        [أداة هجومية حرجة - LETHAL WEAPON]
        إرسال أمر بيع أو شراء حقيقي إلى منصة التداول (Binance).
        هذه الدالة تتعامل مع أموال حقيقية.
        
        المعاملات:
        - symbol: الزوج المالي (مثال: 'BTCUSDT').
        - side: اتجاه الصفقة ('BUY' أو 'SELL').
        - quantity: الكمية المراد تداولها.
        - order_type: نوع الأمر (الافتراضي 'MARKET' للتنفيذ الفوري).
        """
        logger.warning(f"⚠️ Executing Manager Command: LIVE TRADE | {side} {quantity} {symbol} ({order_type})")
        
        if not self.execution_driver:
            return self._declare_system_blindness("EXECUTION_DRIVER_OFFLINE")
            
        # التنفيذ الفعلي عبر الذراع المشفر
        trade_result = self.execution_driver.place_order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type=order_type
        )
        
        # التزام جنائي: لا تزييف لنتيجة الصفقة. إذا لم ترد المنصة بتأكيد، نعتبرها فاشلة.
        if trade_result is None:
            logger.error(f"❌ API Manager: Trade Execution FAILED or REJECTED for {symbol}.")
            return None
            
        return trade_result

    # =========================================================================
    # بروتوكولات الطوارئ (Emergency Protocols)
    # =========================================================================

    def _declare_system_blindness(self, reason: str) -> None:
        """
        تطبيق قاعدة "لا بيانات وهمية". 
        إذا كان المكون المسؤول مفقوداً أو معطلاً، نعلن العمى الكامل بأمان.
        """
        error_msg = f"API MANAGER BLINDNESS: {reason}"
        logger.critical(f"🛑 {error_msg}")
        
        if audit_logger:
            audit_logger.log_error("SYSTEM_BLINDNESS", "Manager Execution Failed", error_msg)
            
        return None

# نسخة مفردة (Singleton) لتكون نقطة الدخول الوحيدة لكل النظام المالي
alpha_api_manager = CentralAPIManager()
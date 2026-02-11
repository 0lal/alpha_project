from PyQt6.QtCore import QObject, pyqtSignal

class AlphaEventHub(QObject):
    """
    الجهاز العصبي المركزي (Central Nervous System).
    
    الوظيفة:
    نقل الإشارات بين الأعضاء المختلفة (المحرك، الواجهة، السجلات) دون أن يعرف أحدهما الآخر (Decoupling).
    """
    
    # -------------------------------------------------------------------------
    # 1. System Signals (إشارات النظام)
    # -------------------------------------------------------------------------
    # (Level, Source, Message HTML) -> لاستخدام LoggerSink
    system_log_received = pyqtSignal(str, str, str) 
    
    # -------------------------------------------------------------------------
    # 2. Market Data Signals (إشارات السوق)
    # -------------------------------------------------------------------------
    # (Symbol, Price, Volume) -> لتحديث التيكر والشارت
    market_tick_received = pyqtSignal(str, float, float)
    
    # (Symbol, Bids List, Asks List) -> لتحديث دفتر الأوامر
    order_book_updated = pyqtSignal(str, list, list)

    # -------------------------------------------------------------------------
    # 3. Portfolio & Engine Signals (إشارات المحفظة والمحرك)
    # -------------------------------------------------------------------------
    # (Data Dict) -> يحتوي على الرصيد، الربح اليومي، الصفقات المفتوحة
    # [تمت إضافتها لإصلاح الخطأ]
    portfolio_update = pyqtSignal(dict)
    
    # (Trade Info Dict) -> عند تنفيذ صفقة جديدة
    trade_executed = pyqtSignal(dict)

    # -------------------------------------------------------------------------
    # Singleton Pattern
    # -------------------------------------------------------------------------
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(AlphaEventHub, cls).__new__(cls)
            # تهيئة QObject ضرورية لعمل الإشارات
            super(AlphaEventHub, cls._instance).__init__()
        return cls._instance

# Global Access Point
event_hub = AlphaEventHub()
import math
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP

class MathUtils:
    """
    العمليات الرياضية الآمنة للتداول (Safe Trading Math).
    
    المهمة الجنائية:
    1. القضاء على أخطاء Floating Point (مثل 0.1 + 0.2 != 0.3).
    2. ضبط الكميات لتتوافق مع قواعد البورصة (LOT_SIZE filters).
    3. منع الانهيارات الناتجة عن القسمة على صفر (ZeroDivisionError).
    """

    @staticmethod
    def safe_div(numerator: float, denominator: float, default: float = 0.0) -> float:
        """
        القسمة الآمنة.
        
        السيناريو الكارثي:
        حساب نسبة التغير لسعر كان 0 ثم أصبح 100. القسمة على 0 ستوقف البرنامج.
        هذه الدالة تمنع "الموت المفاجئ" للواجهة.
        """
        try:
            if denominator == 0:
                return default
            return numerator / denominator
        except Exception:
            return default

    @staticmethod
    def calc_pnl_percent(entry_price: float, current_price: float, side: str = "BUY") -> float:
        """
        حساب نسبة الربح والخسارة (PnL %).
        
        Args:
            side: "BUY" (Long) or "SELL" (Short).
        """
        if entry_price == 0:
            return 0.0
            
        if side.upper() == "BUY":
            # (Current - Entry) / Entry
            return ((current_price - entry_price) / entry_price) * 100
        else:
            # Short: (Entry - Current) / Entry
            # كلما نزل السعر (Current < Entry)، زاد الربح
            return ((entry_price - current_price) / entry_price) * 100

    @staticmethod
    def round_step_size(quantity: float, step_size: float) -> float:
        """
        أخطر دالة في النظام: ضبط الكمية حسب (Step Size).
        
        السيناريو:
        - تريد شراء 1.2345 BTC.
        - البورصة تسمح فقط بمضاعفات 0.001.
        - إذا أرسلت 1.2345 -> ترفض (Filter Failure).
        - هذه الدالة تحولها إلى 1.234 (تقريب للأسفل دائماً).
        
        لماذا للأسفل؟
        لأنك إذا قربت للأعلى (1.235) قد تطلب شراء كمية لا تملك ثمنها، 
        أو بيع كمية لا تملكها في المحفظة. التقريب للأسفل هو "الأمان الجنائي".
        """
        if step_size == 0: return quantity
        if quantity == 0: return 0.0

        # استخدام Decimal للدقة المتناهية
        qty_dec = Decimal(str(quantity))
        step_dec = Decimal(str(step_size))
        
        # المعادلة: (Quantity // Step) * Step
        # نستخدم Floor Division لضمان عدم تجاوز الكمية الأصلية
        down_qty = (qty_dec // step_dec) * step_dec
        
        # تحويل العودة لـ float لاستخدامها في الواجهة
        return float(down_qty)

    @staticmethod
    def round_price(price: float, tick_size: float) -> float:
        """
        ضبط السعر حسب (Tick Size).
        
        الفرق عن الكمية:
        السعر يمكن تقريبه لأقرب رقم (Nearest)، لا يشترط للأسفل.
        مثال: السعر 100.123، الـ Tick هو 0.01 -> النتيجة 100.12
        """
        if tick_size == 0: return price
        
        price_dec = Decimal(str(price))
        tick_dec = Decimal(str(tick_size))
        
        # التقريب لأقرب مضاعف
        # (Price / Tick).quantize(1) * Tick
        rounded = (price_dec / tick_dec).quantize(Decimal('1'), rounding=ROUND_HALF_UP) * tick_dec
        
        return float(rounded)

    @staticmethod
    def calc_position_size(balance: float, risk_per_trade_percent: float, stop_loss_price: float, entry_price: float) -> float:
        """
        إدارة المخاطر: حساب حجم الصفقة بناءً على المخاطرة.
        
        المعادلة:
        كمية المال المخاطر بها = الرصيد * نسبة المخاطرة
        الخسارة للسهم الواحد = سعر الدخول - سعر الوقف
        عدد الأسهم = المال المخاطر به / الخسارة للسهم
        """
        if balance <= 0 or entry_price <= 0:
            return 0.0
            
        risk_amount = balance * (risk_per_trade_percent / 100.0)
        loss_per_share = abs(entry_price - stop_loss_price)
        
        if loss_per_share == 0:
            return 0.0 # الوقف يساوي الدخول! مستحيل الحساب
            
        position_size = risk_amount / loss_per_share
        
        # التأكد من أن حجم الصفقة لا يتجاوز الرصيد الكلي (للتداول الفوري Spot)
        # في العقود الآجلة (Futures) يمكن استخدام الرافعة، لكن هنا نفترض Spot للأمان
        max_affordable = balance / entry_price
        
        return min(position_size, max_affordable)

    @staticmethod
    def clamp(value: float, min_val: float, max_val: float) -> float:
        """
        حصر قيمة داخل نطاق محدد.
        تستخدم لأشرطة التمرير (Sliders) في الواجهة (مثلاً 0-100%).
        """
        return max(min_val, min(value, max_val))

    @staticmethod
    def map_range(x: float, in_min: float, in_max: float, out_min: float, out_max: float) -> float:
        """
        تحويل قيمة من نطاق إلى آخر (Linear Interpolation).
        مثال: تحويل مؤشر RSI (0-100) إلى لون (0-255).
        """
        if (in_max - in_min) == 0: return out_min
        return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min

    @staticmethod
    def is_close(a: float, b: float, rel_tol=1e-9, abs_tol=0.0) -> bool:
        """
        مقارنة رقمين عشريين بأمان.
        بدلاً من if a == b (التي تفشل غالباً)، نستخدم if is_close(a, b).
        """
        return math.isclose(a, b, rel_tol=rel_tol, abs_tol=abs_tol)
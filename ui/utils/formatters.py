import math
from typing import Union, Optional

class TextUtils:
    """
    مكتبة التنسيق الجنائي (Forensic Formatting Library).
    
    المهمة:
    تحويل البيانات الخام (Raw Data) إلى تنسيق بشري دقيق وغير مضلل.
    
    المبادئ:
    1. لا تقريب يؤدي لفقدان القيمة (No Lossy Rounding).
    2. وضوح تام في الفواصل العشرية (Explicit Decimals).
    3. معالجة القيم الفارغة بأمان (Null Safety).
    """

    @staticmethod
    def format_currency(value: Union[float, str, None], symbol: str = "USD", strict_decimals: int = None) -> str:
        """
        تنسيق العملات بذكاء سياقي.
        
        المنطق الجنائي:
        - العملات المستقرة (USD, USDT): تعرض بمنزلتين (مثال: $12,345.00).
        - العملات الرقمية (Crypto): تعتمد على القيمة.
          * إذا كانت القيمة > 1.0: تعرض بمنزلتين (مثال: BTC 65,000.50).
          * إذا كانت القيمة < 1.0: تعرض بدقة تصل لـ 8 منازل (مثال: 0.00004512).
        
        Args:
            value: الرقم المراد تنسيقه.
            symbol: رمز العملة (لإضافة البادئة أو اللاحقة).
            strict_decimals: إجبار عدد معين من المنازل (تجاوز الذكاء التلقائي).
        """
        if value is None or value == "":
            return "0.00"

        try:
            val = float(value)
        except (ValueError, TypeError):
            return str(value) # إعادة النص كما هو في حالة الفشل

        # التعامل مع الصفر المطلق
        if val == 0:
            return f"0.00 {symbol}" if symbol != "USD" else "$0.00"

        # تحديد عدد المنازل العشرية (Precision)
        precision = 2
        if strict_decimals is not None:
            precision = strict_decimals
        else:
            # المنطق الديناميكي
            abs_val = abs(val)
            if abs_val < 0.000001: precision = 8
            elif abs_val < 0.0001: precision = 7
            elif abs_val < 0.01: precision = 6
            elif abs_val < 1.0: precision = 4
            else: precision = 2

        # التنسيق مع فواصل الآلاف
        # {:,.nf} تعني: فاصلة للألوف، و n منازل عشرية
        formatted_num = f"{val:,.{precision}f}"

        # إضافة الرمز
        if symbol in ["USD", "USDT", "USDC", "DAI"]:
            return f"${formatted_num}"
        elif symbol in ["EUR"]:
            return f"€{formatted_num}"
        elif symbol:
            return f"{formatted_num} {symbol}"
        else:
            return formatted_num

    @staticmethod
    def format_quantity(value: Union[float, str, None], asset_type: str = "CRYPTO") -> str:
        """
        تنسيق الكميات (الأحجام).
        
        مشكلة تنبؤية:
        المنصات ترفض الأوامر التي تحتوي على دقة زائدة (مثال: Binance ترفض شراء 0.00123456789 BTC).
        لذا، نعرض هنا ما هو "مفيد" للمستخدم، لكن يجب استخدام math_ops للمعالجة قبل الإرسال.
        """
        if value is None: return "0"
        
        try:
            val = float(value)
        except:
            return str(value)

        if val == 0: return "0"

        # إزالة الأصفار الزائدة في اليمين (Trailing Zeros) للتنظيف
        # مثال: 1.50000 -> 1.5
        # لكن مع الحفاظ على فواصل الآلاف
        if val.is_integer():
             return f"{int(val):,}"
        
        # تنسيق مبدئي بـ 8 منازل
        s = f"{val:,.8f}"
        # قص الأصفار الزائدة
        return s.rstrip('0').rstrip('.')

    @staticmethod
    def format_percentage(value: Union[float, str, None], include_sign: bool = True) -> str:
        """
        تنسيق النسب المئوية.
        
        ميزة جنائية:
        إضافة إشارة '+' بوضوح للأرقام الموجبة لمنع اللبس مع الأرقام السالبة في الجداول المزدحمة.
        """
        if value is None: return "0.00%"
        
        try:
            val = float(value)
        except:
            return str(value)

        sign = "+" if (include_sign and val > 0) else ""
        return f"{sign}{val:.2f}%"

    @staticmethod
    def shorten_hash(text: str, chars: int = 6) -> str:
        """
        تقصير عناوين المحافظ ومعرفات المعاملات (TxID).
        يحافظ على البداية والنهاية للتحقق البصري السريع.
        Example: 0x123456789abcdef -> 0x1234...cdef
        """
        if not text: return ""
        s = str(text)
        if len(s) <= (chars * 2) + 3:
            return s
        return f"{s[:chars]}...{s[-chars:]}"

    @staticmethod
    def format_large_number(value: float) -> str:
        """
        تنسيق الأرقام الضخمة جداً (لأحجام التداول الكبيرة).
        1,000,000 -> 1.00M
        1,000 -> 1.00K
        """
        if value is None: return "0"
        
        try:
            val = float(value)
        except:
            return str(value)
            
        abs_val = abs(val)
        
        if abs_val >= 1_000_000_000:
            return f"{val / 1_000_000_000:.2f}B"
        elif abs_val >= 1_000_000:
            return f"{val / 1_000_000:.2f}M"
        elif abs_val >= 1_000:
            return f"{val / 1_000:.2f}K"
        else:
            return f"{val:,.2f}"

    @staticmethod
    def to_snake_case(text: str) -> str:
        """
        أداة مساعدة للمطورين: تحويل النصوص إلى snake_case.
        مفيدة عند تحويل أسماء الأزواج (BTC/USDT -> btc_usdt) لاستخدامها في API.
        """
        if not text: return ""
        return text.strip().lower().replace(" ", "_").replace("/", "_").replace("-", "_")

    @staticmethod
    def to_upper_pair(text: str) -> str:
        """
        توحيد صيغة أزواج العملات.
        btc_usdt -> BTC/USDT
        """
        if not text: return ""
        clean = text.strip().upper().replace("_", "/").replace("-", "/")
        if "/" not in clean and len(clean) > 6: 
             # محاولة تخمين الفاصل إذا كان مفقوداً (مثل BTCUSDT)
             # هذا تخمين بسيط، الأفضل الاعتماد على البيانات القادمة من المصدر
             pass 
        return clean
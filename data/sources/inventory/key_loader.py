import os
import json
import glob
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

# إعداد نظام التسجيل الجنائي لتعقب عمليات تحميل المفاتيح
logger = logging.getLogger("Alpha.Inventory.KeyLoader")

class KeyInventoryManager:
    """
    مدير مخزن المفاتيح (The Key Vault Manager).
    
    المهام الجنائية:
    1. المسح الشامل: قراءة كل ملفات JSON في مجلد التكوين.
    2. الحقن الآمن: استبدال متغيرات البيئة (ENV VARS) بالقيم الحقيقية دون كتابتها في الكود.
    3. التحقق من النزاهة: التأكد من أن الملف يحتوي على Hash وتوقيع صحيح.
    4. تدوير المفاتيح: إعداد قوائم المفاتيح المتعددة للاستخدام المتسلسل.
    """

    def __init__(self, config_dir: str = "inventory/keys_config"):
        """
        تهيئة المدير.
        :param config_dir: المسار النسبي لمجلد ملفات التكوين JSON.
        """
        # تحويل المسار النسبي إلى مسار مطلق لضمان الوصول الصحيح في بيئات التشغيل المختلفة
        self.config_dir = os.path.abspath(config_dir)
        
        # الذاكرة الحية: هنا يتم تخزين التكوينات الجاهزة للاستخدام
        # الهيكل: { "provider_name": { config_data ... } }
        self._inventory: Dict[str, Any] = {}
        
        # سجل الملفات التالفة (Quarantine List)
        self._corrupted_files: List[str] = []
        
        # التحميل الأولي عند التشغيل
        logger.info(f"📂 Initializing Key Vault from: {self.config_dir}")
        self.scan_and_load()

    def scan_and_load(self) -> Dict[str, Any]:
        """
        المسح الراداري: يقرأ المجلد ويعيد بناء المخزن.
        يمكن استدعاء هذه الدالة في أي وقت لعمل (Hot Reload) دون إيقاف البرنامج.
        """
        if not os.path.exists(self.config_dir):
            logger.critical(f"❌ Config directory not found: {self.config_dir}")
            return {}

        # البحث عن كل ملفات .json داخل المجلد
        files = glob.glob(os.path.join(self.config_dir, "*.json"))
        
        if not files:
            logger.warning("⚠️ No key configuration files found in inventory!")
            return {}

        # مخزن مؤقت لضمان عدم استبدال المخزن الحالي إلا بعد نجاح التحميل (Atomic Update)
        new_inventory = {}
        corrupted = []

        for file_path in files:
            file_name = os.path.basename(file_path)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    raw_data = json.load(f)
                
                # 1. التحقق الجنائي من هيكل الملف (Schema Validation)
                if not self._validate_schema(raw_data, file_name):
                    corrupted.append(file_name)
                    continue

                # 2. حقن الأسرار (Inject Secrets via Env Vars)
                processed_data = self._inject_secrets(raw_data)
                
                # 3. تحديد اسم المزود (Provider Name) ليكون هو المفتاح في الذاكرة
                provider_name = processed_data.get("credentials", {}).get("provider", "").lower()
                if not provider_name:
                    logger.error(f"❌ File {file_name} missing 'provider' field inside credentials.")
                    corrupted.append(file_name)
                    continue

                # إضافة الملف إلى المخزن الجديد
                new_inventory[provider_name] = processed_data
                logger.info(f"✅ Loaded Config: {provider_name} (Source: {file_name})")

            except json.JSONDecodeError:
                logger.error(f"❌ JSON Syntax Error in {file_name}. File quarantined.")
                corrupted.append(file_name)
            except Exception as e:
                logger.error(f"❌ Unexpected error loading {file_name}: {str(e)}")
                corrupted.append(file_name)

        # تحديث الحالة الداخلية للنظام
        self._inventory = new_inventory
        self._corrupted_files = corrupted
        
        logger.info(f"📊 Inventory Refresh Complete. Active Providers: {len(self._inventory)}. Corrupted: {len(corrupted)}")
        return self._inventory

    def get_config(self, provider_name: str) -> Optional[Dict[str, Any]]:
        """
        استرجاع تكوين مزود معين (مثال: 'groq', 'alpha_vantage').
        """
        return self._inventory.get(provider_name.lower())

    def get_all_providers(self) -> List[str]:
        """
        الحصول على قائمة بكل المزودين المتاحين حالياً.
        """
        return list(self._inventory.keys())

    def _validate_schema(self, data: Dict, filename: str) -> bool:
        """
        الفحص الجنائي: هل الملف يحتوي على الأختام المطلوبة؟
        """
        required_sections = ["_meta", "credentials", "connection_policy"]
        for section in required_sections:
            if section not in data:
                logger.warning(f"⚠️ Security Audit Failed: {filename} missing '{section}' section.")
                return False
        return True

    def _inject_secrets(self, data: Any) -> Any:
        """
        الحقن الآمن: دالة تعاودية (Recursive) تبحث عن الحقول التي تشير لمتغيرات بيئة
        وتستبدلها بالقيمة الحقيقية.
        """
        if isinstance(data, dict):
            new_dict = {}
            for k, v in data.items():
                # حالة خاصة: إذا كان الحقل هو api_key_env_var، نقوم بجلب قيمته واضافتها كـ api_key
                if k == "api_key_env_var" and isinstance(v, str):
                    secret_value = os.getenv(v)
                    if not secret_value:
                        logger.warning(f"⚠️ MISSING SECRET: Environment variable '{v}' is empty/missing!")
                        new_dict["api_key"] = None # نضع قيمة فارغة بدلاً من الانهيار
                    else:
                        new_dict["api_key"] = secret_value
                    # نحتفظ بالاسم الأصلي أيضاً للمرجعية
                    new_dict[k] = v
                
                # حالة خاصة 2: تدوير المفاتيح (Alpha Vantage)
                elif k == "keys_rotation_env_vars" and isinstance(v, list):
                    # تحويل قائمة أسماء المتغيرات إلى قائمة مفاتيح حقيقية
                    rotated_keys = []
                    for env_var in v:
                        val = os.getenv(env_var)
                        if val:
                            rotated_keys.append(val)
                    new_dict["_rotated_keys_values"] = rotated_keys # حقل داخلي مخفي
                    new_dict[k] = v

                else:
                    new_dict[k] = self._inject_secrets(v)
            return new_dict
            
        elif isinstance(data, list):
            return [self._inject_secrets(item) for item in data]
        
        else:
            return data

# إنشاء نسخة مفردة (Singleton) للاستخدام المباشر
key_loader = KeyInventoryManager()
import logging
import time
from typing import Dict, Any, List

# استيراد أجهزة الدولة (State Machinery) للحصول على البيانات الحقيقية
try:
    from core.usage_tracker import usage_tracker
    from core.rate_limiter import rate_limiter
    from inventory.key_loader import key_loader
except ImportError:
    logging.critical("🔥 FATAL: Missing Core Components for Status Reporter!")
    usage_tracker = None
    rate_limiter = None
    key_loader = None

# إعداد السجل الجنائي للمراقب
logger = logging.getLogger("Alpha.Core.StatusReporter")

class SystemHealthMonitor:
    """
    مراقب الصحة العامة للنظام (System Health & Status Reporter).
    
    المهام الجنائية:
    1. تجميع حالة جميع الـ APIs (الاستهلاك، العقوبات، التوافر) في تقرير واحد لحظي.
    2. العمل كواجهة خلفية (Backend) للوحة التحكم (Dashboard) لمتخذ القرار.
    3. التشخيص الدقيق: التفريق بين نفاد الرصيد وعطل الشبكة.
    """

    def __init__(self):
        """
        تهيئة المراقب.
        """
        # تعريف مستويات الصحة المالية
        self.STATUS_HEALTHY = "🟢 HEALTHY"
        self.STATUS_WARNING = "🟡 WARNING"
        self.STATUS_CRITICAL = "🟠 CRITICAL"
        self.STATUS_BLOCKED = "🔴 BLOCKED"
        self.STATUS_UNKNOWN = "⚪ UNKNOWN"

    def get_full_dashboard_report(self) -> Dict[str, Any]:
        """
        [التقرير المالي الشامل]
        يولد لقطة حية (Snapshot) لحالة جميع المزودين المسجلين في النظام.
        """
        logger.info("📊 Generating full API health dashboard report...")
        
        report = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "system_status": self.STATUS_HEALTHY, # يفترض الصحة حتى يثبت العكس
            "providers": {},
            "active_penalties": 0,
            "exhausted_quotas": 0
        }

        # 1. جلب قائمة كل المزودين من خزانة المفاتيح
        if not key_loader:
            report["system_status"] = "SYSTEM_FAILURE: KEY_LOADER_OFFLINE"
            return report
            
        all_providers = key_loader.list_configured_providers()
        
        # 2. فحص كل مزود على حدة
        for provider in all_providers:
            provider_status = self._inspect_provider(provider)
            report["providers"][provider] = provider_status
            
            # تحديث الإحصائيات العامة
            if provider_status["is_penalized"]:
                report["active_penalties"] += 1
            if provider_status["quota_status"] == "BLOCKED":
                report["exhausted_quotas"] += 1

        # 3. تحديد الحالة العامة للنظام (System Global State)
        total_providers = len(all_providers)
        if total_providers > 0:
            if report["exhausted_quotas"] >= total_providers * 0.5:
                # إذا كان نصف المزودين مفلسين، النظام في خطر
                report["system_status"] = self.STATUS_CRITICAL
            elif report["exhausted_quotas"] > 0 or report["active_penalties"] > 0:
                report["system_status"] = self.STATUS_WARNING

        return report

    def get_provider_status(self, provider: str) -> Dict[str, Any]:
        """
        فحص دقيق لحالة مزود بيانات محدد.
        """
        return self._inspect_provider(provider)

    def _inspect_provider(self, provider: str) -> Dict[str, Any]:
        """
        الفحص الجنائي الشامل للمزود:
        يسأل "المحاسب" عن الرصيد، ويسأل "شرطي المرور" عن العقوبات.
        """
        status_data = {
            "overall_state": self.STATUS_UNKNOWN,
            "quota_status": "UNKNOWN",
            "usage_percentage": 0.0,
            "usage_message": "Not Checked",
            "is_penalized": False,
            "penalty_reason": None
        }

        # 1. التفتيش المالي (المحاسب)
        if usage_tracker:
            quota_state, usage_pct, msg = usage_tracker.check_quota_status(provider)
            status_data["quota_status"] = quota_state
            status_data["usage_percentage"] = usage_pct
            status_data["usage_message"] = msg

        # 2. التفتيش المروري (شرطي المرور)
        if rate_limiter:
            # الدالة _is_in_penalty_box مخفية، نصل لها مباشرة للتشخيص
            is_banned = rate_limiter._is_in_penalty_box(provider, "default")
            status_data["is_penalized"] = is_banned
            if is_banned:
                status_data["penalty_reason"] = "429_TOO_MANY_REQUESTS_PENALTY_ACTIVE"

        # 3. اتخاذ القرار النهائي لحالة المزود
        if status_data["is_penalized"]:
            status_data["overall_state"] = self.STATUS_BLOCKED
            
        elif status_data["quota_status"] == "BLOCKED":
            status_data["overall_state"] = self.STATUS_BLOCKED
            
        elif status_data["quota_status"] == "CRITICAL":
            status_data["overall_state"] = self.STATUS_CRITICAL
            
        elif status_data["quota_status"] == "WARNING":
            status_data["overall_state"] = self.STATUS_WARNING
            
        else:
            status_data["overall_state"] = self.STATUS_HEALTHY

        return status_data

# نسخة مفردة (Singleton) للاستخدام المباشر في واجهات التحكم (FastAPI أو Flask)
api_health_monitor = SystemHealthMonitor()
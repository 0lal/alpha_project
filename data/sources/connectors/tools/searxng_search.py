import logging
from typing import Dict, Any, Optional, List, Tuple

# استيراد القالب الأم الذي يطبق سياسات الأمان، المحاسبة، والتدقيق الجنائي
from connectors.base_connector import BaseConnector

# إعداد السجل الجنائي الخاص بمحرك البحث
logger = logging.getLogger("Alpha.Drivers.SearXNG")

class SearXNGDriver(BaseConnector):
    """
    الذراع التنفيذي للبحث في الويب الحي (Live Web Search Engine).
    
    المهام الجنائية:
    1. تزويد وكلاء الذكاء الاصطناعي (Agents) بالقدرة على البحث المباشر في جوجل، بينج، وياهو معاً.
    2. تجاوز القيود المفروضة على محركات البحث العادية وضمان الخصوصية (No Tracking).
    3. فلترة النتائج وتغليفها في هيكل بيانات نظيف وخفيف لتجنب استنزاف ذاكرة الـ LLM.
    """

    def __init__(self):
        """
        تهيئة الدرايفر.
        """
        # تمرير اسم المزود للقالب الأم لجلب الإعدادات (مثال: searxng_keys.json)
        super().__init__("searxng")
        
        # التأكد من وجود رابط السيرفر، وإلا نستخدم سيرفراً عاماً كطوارئ (لا ينصح به للبيانات الحساسة)
        self.base_url = self.config.get("connection_policy", {}).get("base_url")
        if not self.base_url:
            logger.warning("⚠️ SearXNG Base URL is missing! Falling back to a public instance. Expect high failure rates.")
            self.base_url = "https://searx.be" # سيرفر عام احتياطي

    def build_url(self, endpoint_key: str) -> str:
        """
        [تجاوز إجباري]
        بناء الرابط. SearXNG يمتلك نقطة وصول واحدة للبحث.
        """
        # مسار البحث القياسي في SearXNG هو /search
        path = "/search"
        clean_base = self.base_url.rstrip("/")
        return f"{clean_base}{path}"

    def get_default_params(self) -> Dict[str, str]:
        """
        المعاملات الإجبارية التي تحمي النظام من الردود غير المتوقعة.
        """
        return {
            "format": "json",       # [حماية حرجة] إجبار السيرفر على رد JSON بدلاً من صفحة ويب HTML
            "language": "en-US",    # توحيد لغة البحث للتحليل المالي
            "safesearch": "1"       # تفعيل البحث الآمن لتقليل الضوضاء والمواقع المشبوهة
        }

    def _prepare_request_details(self, endpoint_key: str, params: Dict) -> Tuple[str, str, Dict, Dict]:
        """
        [تجاوز أمني]
        تمويه هوية النظام (User-Agent Spoofing).
        بعض خوادم SearXNG تحظر البوتات (Bots). لذلك نتنكر كمتصفح عادي لتجنب الرفض.
        """
        url, method, final_params, headers = super()._prepare_request_details(endpoint_key, params)
        
        # التنكر كمتصفح حقيقي لتجنب حظر الـ 403 Forbidden
        headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        
        return url, "GET", final_params, headers

    def fetch(self, endpoint_key: str, **params) -> Optional[List[Dict[str, str]]]:
        """
        [تجاوز جنائي - Extraction Override]
        إرسال الطلب، استلام الـ JSON المعقد، واستخراج النتائج الصافية فقط.
        """
        result = super().fetch(endpoint_key, **params)
        
        # بروتوكول "أنا أعمى": إذا فشل الاتصال أو السيرفر محظور
        if not result or not isinstance(result, dict):
            logger.error(f"🛑 SearXNG Search Failed for query: {params.get('q')}")
            return None

        # استخراج النتائج (Results) من القاموس
        search_results = result.get("results", [])
        if not search_results:
            logger.info(f"텅 No results found in SearXNG for query: {params.get('q')}")
            return []

        # فلترة النتائج: نأخذ فقط ما يحتاجه الذكاء الاصطناعي (عنوان، رابط، مقتطف)
        # لتجنب حرق آلاف التوكنز في بيانات الميتا (Metadata) غير المفيدة
        cleaned_results = []
        for item in search_results[:10]: # نكتفي بأفضل 10 نتائج فقط للمحافظة على التركيز
            cleaned_results.append({
                "title": item.get("title", "No Title"),
                "url": item.get("url", ""),
                "snippet": item.get("content", "") # محتوى المقتطف الذي سيقرأه الـ LLM
            })

        return cleaned_results

    # =========================================================================
    # أذرع البحث المالي (Financial Web Arms)
    # =========================================================================

    def execute_web_search(self, query: str, categories: str = "general", time_range: str = "") -> Optional[List[Dict[str, str]]]:
        """
        [أداة الوكلاء - Agent Tool] 
        تنفيذ بحث مباشر في الويب المفتوح. تُستخدم هذه الدالة بواسطة OpenManus أو Gemini.
        
        المعاملات:
        - query: جملة البحث (مثال: "Apple current CEO announcement").
        - categories: تصنيف البحث (مثال: "news" للأخبار، "general" للبحث العام، "science").
        - time_range: الإطار الزمني للخبر ('day' لليوم، 'week' للأسبوع، 'month' للشهر).
        """
        # الحماية الجنائية: منع البحث الفارغ
        if not query or not query.strip():
            logger.error("🛑 SearXNG Error: Empty search query provided.")
            return None

        params = {
            "q": query,
            "categories": categories
        }
        
        # إضافة الإطار الزمني فقط إذا تم تحديده (مفيد جداً في الأخبار المالية العاجلة)
        if time_range in ["day", "week", "month", "year"]:
            params["time_range"] = time_range

        logger.info(f"🔎 Executing Live Web Search: '{query}' (Category: {categories}, Time: {time_range or 'Any'})")
        
        # تمرير 'search' كـ endpoint_key ليقوم القالب الأم بإدارته
        return self.fetch("search", **params)

    def search_financial_news(self, company_name: str) -> Optional[List[Dict[str, str]]]:
        """
        [أداة سريعة] بحث مخصص لأحدث الأخبار المالية لشركة معينة خلال الـ 24 ساعة الماضية.
        """
        # صياغة بحث مالي دقيق
        optimized_query = f"{company_name} (stock OR shares OR earnings OR CEO OR acquisition)"
        
        # نجبر المحرك على البحث في قسم الأخبار فقط لأحداث اليوم
        return self.execute_web_search(query=optimized_query, categories="news", time_range="day")
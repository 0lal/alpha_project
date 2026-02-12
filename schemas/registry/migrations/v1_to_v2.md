# Goal: خطة ترحيل مفصلة من V1 إلى V2 بدون توقف الخدمات.
# Dependencies: registry manifest, schema builder, compatibility linter.

## 1) التحضير
- أخذ نسخة snapshot من `s/registry/manifest.json`.
- توليد `compiled_catalog.json` قبل أي تعديل.
- تشغيل compatibility checks على جميع ملفات `.proto` الحساسة.

## 2) تنفيذ الترحيل
- إضافة/تعديل schemas الجديدة مع الحفاظ على التوافق الخلفي.
- منع حذف أي field موجود في proto خلال نفس الإصدار.
- تمرير style_check للتأكد من وجود Goal/Dependencies لكل ملف مطلوب.

## 3) التحقق بعد الترحيل
- تشغيل الاختبارات: validators + governance hot-reload.
- مقارنة catalog hashes قبل/بعد للتحقق من نطاق التغيير.
- اعتماد release note يشرح breaking/non-breaking changes.

## 4) خطة الرجوع (Rollback)
- إعادة manifest السابق.
- إعادة catalog السابق.
- إعادة نشر الخدمات باستخدام آخر صورة مستقرة.

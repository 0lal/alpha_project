"""
Goal
----
تهيئة الحزمة وتعريف حدود المسؤولية داخل Bio-Schema.

Dependencies
------------
يعتمد على الوحدات الفرعية في نفس المسار.

شرح إضافي
---------
Validators layer implementing atomic/semantic/contextual checks.
"""

__all__ = ["atomic", "semantic", "contextual", "pipeline"]

# ملاحظة تشغيلية:
# هذه الحزمة جزء من طبقة Bio-Schema المركزية،
# وأي تغيير في الواجهات يجب أن يمر عبر compatibility checks.

PACKAGE_MATURITY = "production-baseline"
PACKAGE_OWNER = "alpha-data-architecture"

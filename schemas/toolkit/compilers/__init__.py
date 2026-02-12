"""
Goal
----
تهيئة الحزمة وتعريف حدود المسؤولية داخل Bio-Schema.

Dependencies
------------
يعتمد على الوحدات الفرعية في نفس المسار.

شرح إضافي
---------
Compiler helpers for generating schema catalogs and build artifacts.
"""

__all__ = ["schema_builder"]

# ملاحظة تشغيلية:
# هذه الحزمة جزء من طبقة Bio-Schema المركزية،
# وأي تغيير في الواجهات يجب أن يمر عبر compatibility checks.

PACKAGE_MATURITY = "production-baseline"
PACKAGE_OWNER = "alpha-data-architecture"

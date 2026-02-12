"""
Goal
----
تهيئة الحزمة وتعريف حدود المسؤولية داخل Bio-Schema.

Dependencies
------------
يعتمد على الوحدات الفرعية في نفس المسار.

شرح إضافي
---------
Toolkit utilities for build/lint/fuzz/bench/test operations.
"""

__all__ = ["compilers", "linters", "generators", "fuzzers", "viewers"]

# ملاحظة تشغيلية:
# هذه الحزمة جزء من طبقة Bio-Schema المركزية،
# وأي تغيير في الواجهات يجب أن يمر عبر compatibility checks.

PACKAGE_MATURITY = "production-baseline"
PACKAGE_OWNER = "alpha-data-architecture"

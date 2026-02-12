#!/usr/bin/env bash
# Goal: فحوص ما قبل الالتزام لضمان الجودة والحوكمة والاستقرار.
# Dependencies: Python runtime, linters, compiler builder, pytest.
#
# هذه الخطوة تحاكي سياسة CI محلياً قبل اعتماد أي commit:
# 1) توثيق الملفات (style_check)
# 2) تحديث كتالوج schema (schema_builder)
# 3) تشغيل اختبارات المناعة (pytest)
set -euo pipefail

python s/toolkit/linters/style_check.py
python s/toolkit/compilers/schema_builder.py
python -m pytest -q s/toolkit/tests/test_smart_validation.py

# يمكن إضافة فحوص إضافية لاحقاً:
# - proto compatibility against previous revision
# - sql lint/format
# - security scanning for governance files
